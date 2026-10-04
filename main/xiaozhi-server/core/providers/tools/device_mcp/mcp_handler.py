"""thiết bị端Máy khách MCP支持mô-đun"""

import json
import asyncio
import re
from concurrent.futures import Future
from core.utils.util import get_vision_url, sanitize_tool_name
from core.utils.auth import AuthToken
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


class MCPClient:
    """thiết bị端Máy khách MCP , 用于管理MCPtrạng thái和công cụ"""

    def __init__(self):
        self.tools = {}  # sanitized_name -> tool_data
        self.name_mapping = {}
        self.ready = False
        self.call_results = {}  # Để lưu trữ Hợp đồng tương lai cho các phản hồi cuộc gọi công cụ
        self.next_id = 1
        self.lock = asyncio.Lock()
        self._cached_available_tools = None  # Bộ nhớ đệm cho get_available_tools

    def has_tool(self, name: str) -> bool:
        return name in self.tools

    def get_available_tools(self) -> list:
        # Kiểm tra xem bộ đệm có hợp lệ không
        if self._cached_available_tools is not None:
            return self._cached_available_tools

        # Nếu bộ đệm không hợp lệ, hãy tạo lại danh sách
        result = []
        for tool_name, tool_data in self.tools.items():
            function_def = {
                "name": tool_name,
                "description": tool_data["description"],
                "parameters": {
                    "type": tool_data["inputSchema"].get("type", "object"),
                    "properties": tool_data["inputSchema"].get("properties", {}),
                    "required": tool_data["inputSchema"].get("required", []),
                },
            }
            result.append({"type": "function", "function": function_def})

        self._cached_available_tools = result  # Lưu trữ danh sách đã tạo trong bộ đệm
        return result

    async def is_ready(self) -> bool:
        async with self.lock:
            return self.ready

    async def set_ready(self, status: bool):
        async with self.lock:
            self.ready = status

    async def add_tool(self, tool_data: dict):
        async with self.lock:
            sanitized_name = sanitize_tool_name(tool_data["name"])
            self.tools[sanitized_name] = tool_data
            self.name_mapping[sanitized_name] = tool_data["name"]
            self._cached_available_tools = (
                None  # Vô hiệu hóa bộ nhớ đệm khi thêm công cụ
            )

    async def get_next_id(self) -> int:
        async with self.lock:
            current_id = self.next_id
            self.next_id += 1
            return current_id

    async def register_call_result_future(self, id: int, future: Future):
        async with self.lock:
            self.call_results[id] = future

    async def resolve_call_result(self, id: int, result: any):
        async with self.lock:
            if id in self.call_results:
                future = self.call_results.pop(id)
                if not future.done():
                    future.set_result(result)

    async def reject_call_result(self, id: int, exception: Exception):
        async with self.lock:
            if id in self.call_results:
                future = self.call_results.pop(id)
                if not future.done():
                    future.set_exception(exception)

    async def cleanup_call_result(self, id: int):
        async with self.lock:
            if id in self.call_results:
                self.call_results.pop(id)


async def send_mcp_message(conn: "ConnectionHandler", payload: dict):
    """Helper to send MCP messages, encapsulating common logic."""
    if not conn.features.get("mcp"):
        logger.bind(tag=TAG).warning("máy khách不支持MCP , không thểgửiMCPthông điệp")
        return

    message = json.dumps({"type": "mcp", "payload": payload})

    try:
        await conn.websocket.send(message)
        logger.bind(tag=TAG).debug(f"thành cônggửiMCPthông điệp: {message}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"gửiMCPthông điệpthất bại: {e}")


async def handle_mcp_message(
    conn: "ConnectionHandler", mcp_client: MCPClient, payload: dict
):
    """xử lýMCPthông điệp,包括khởi tạo、công cụ列表和công cụgọiphản hồi等"""
    logger.bind(tag=TAG).debug(f"xử lýMCPthông điệp: {str(payload)[:100]}")

    if not isinstance(payload, dict):
        logger.bind(tag=TAG).error("MCPthông điệp缺少payload字段或định dạngLỗi")
        return

    # Xử lý kết quả
    if "result" in payload:
        result = payload["result"]
        msg_id = int(payload.get("id", 0))

        # Trước tiên hãy kiểm tra phản hồi cuộc gọi công cụ
        if msg_id in mcp_client.call_results:
            logger.bind(tag=TAG).debug(
                f"nhậncông cụgọiphản hồi，ID: {msg_id}, kết quả: {result}"
            )
            await mcp_client.resolve_call_result(msg_id, result)
            return

        if msg_id == 1:  # mcpInitializeID
            logger.bind(tag=TAG).debug("nhậnMCPkhởi tạophản hồi")
            server_info = result.get("serverInfo")
            if isinstance(server_info, dict):
                name = server_info.get("name")
                version = server_info.get("version")
                logger.bind(tag=TAG).debug(
                    f"máy kháchMCPdịch vụ器thông tin: name={name}, version={version}"
                )

            await asyncio.sleep(1)
            logger.bind(tag=TAG).debug("khởi tạohoàn tất , 开始yêu cầuMCPcông cụ列表")
            await send_mcp_tools_list_request(conn)

            return

        elif msg_id == 2:  # mcpToolsListID
            logger.bind(tag=TAG).debug("nhậnMCPcông cụ列表phản hồi")
            if isinstance(result, dict) and "tools" in result:
                tools_data = result["tools"]
                if not isinstance(tools_data, list):
                    logger.bind(tag=TAG).error("công cụ列表định dạngLỗi")
                    return

                logger.bind(tag=TAG).info(
                    f"máy kháchthiết bị支持的công cụ数量: {len(tools_data)}"
                )

                for i, tool in enumerate(tools_data):
                    if not isinstance(tool, dict):
                        continue

                    name = tool.get("name", "")
                    description = tool.get("description", "")
                    input_schema = {"type": "object", "properties": {}, "required": []}

                    if "inputSchema" in tool and isinstance(tool["inputSchema"], dict):
                        schema = tool["inputSchema"]
                        input_schema["type"] = schema.get("type", "object")
                        input_schema["properties"] = schema.get("properties", {})
                        input_schema["required"] = [
                            s for s in schema.get("required", []) if isinstance(s, str)
                        ]

                    new_tool = {
                        "name": name,
                        "description": description,
                        "inputSchema": input_schema,
                    }
                    await mcp_client.add_tool(new_tool)
                    logger.bind(tag=TAG).debug(f"máy kháchcông cụ #{i + 1}: {name}")

                # Thay thế tên công cụ trong tất cả các mô tả công cụ
                for tool_data in mcp_client.tools.values():
                    if "description" in tool_data:
                        description = tool_data["description"]
                        # Lặp lại tất cả các tên công cụ để thay thế
                        for (
                            sanitized_name,
                            original_name,
                        ) in mcp_client.name_mapping.items():
                            description = description.replace(
                                original_name, sanitized_name
                            )
                        tool_data["description"] = description

                next_cursor = result.get("nextCursor", "")
                if next_cursor:
                    logger.bind(tag=TAG).debug(
                        f"有更多công cụ , nextCursor: {next_cursor}"
                    )
                    await send_mcp_tools_list_continue_request(conn, next_cursor)
                else:
                    await mcp_client.set_ready(True)
                    logger.bind(tag=TAG).debug(
                        "所有công cụđãlấy , Máy khách MCP准备就绪"
                    )

                    # Làm mới bộ đệm công cụ để đảm bảo rằng công cụ MCP được đưa vào danh sách chức năng
                    if hasattr(conn, "func_handler") and conn.func_handler:
                        conn.func_handler.tool_manager.refresh_tools()
                        conn.func_handler.current_support_functions()
            return

    # Xử lý lời gọi phương thức từ máy khách
    elif "method" in payload:
        method = payload["method"]
        logger.bind(tag=TAG).info(f"nhậnMáy khách MCPyêu cầu: {method}")

    elif "error" in payload:
        error_data = payload["error"]
        error_msg = error_data.get("message", "Lỗi không xác định")
        logger.bind(tag=TAG).error(f"nhậnMCPLỗiphản hồi: {error_msg}")

        msg_id = int(payload.get("id", 0))
        if msg_id in mcp_client.call_results:
            await mcp_client.reject_call_result(
                msg_id, Exception(f"MCPLỗi: {error_msg}")
            )


async def send_mcp_initialize_message(conn: "ConnectionHandler"):
    """gửiMCPkhởi tạothông điệp"""

    vision_url = get_vision_url(conn.config)

    # Mã thông báo tạo khóa
    auth = AuthToken(conn.config["server"]["auth_key"])
    token = auth.generate_token(conn.headers.get("device-id"))

    vision = {
        "url": vision_url,
        "token": token,
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,  # mcpInitializeID
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
                "vision": vision,
            },
            "clientInfo": {
                "name": "XiaozhiClient",
                "version": "1.0.0",
            },
        },
    }
    logger.bind(tag=TAG).debug("gửiMCPkhởi tạothông điệp")
    await send_mcp_message(conn, payload)


async def send_mcp_tools_list_request(conn: "ConnectionHandler"):
    """gửiMCPcông cụ列表yêu cầu"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID
        "method": "tools/list",
    }
    logger.bind(tag=TAG).debug("gửiMCPcông cụ列表yêu cầu")
    await send_mcp_message(conn, payload)


async def send_mcp_tools_list_continue_request(conn: "ConnectionHandler", cursor: str):
    """gửi带有cursor的MCPcông cụ列表yêu cầu"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID (cùng một ID để tiếp tục)
        "method": "tools/list",
        "params": {"cursor": cursor},
    }
    logger.bind(tag=TAG).info(f"gửi带cursor的MCPcông cụ列表yêu cầu: {cursor}")
    await send_mcp_message(conn, payload)


async def call_mcp_tool(
    conn: "ConnectionHandler",
    mcp_client: MCPClient,
    tool_name: str,
    args: str = "{}",
    timeout: int = 30,
):
    """
    gọi指定的công cụ , 并chờphản hồi
    """
    if not await mcp_client.is_ready():
        raise RuntimeError("Máy khách MCP chưa sẵn sàng")

    if not mcp_client.has_tool(tool_name):
        raise ValueError(f"Công cụ {tool_name} không tồn tại")

    tool_call_id = await mcp_client.get_next_id()
    result_future = asyncio.Future()
    await mcp_client.register_call_result_future(tool_call_id, result_future)

    # Thông số xử lý
    try:
        if isinstance(args, str):
            # Đảm bảo chuỗi đó là JSON hợp lệ
            if not args.strip():
                arguments = {}
            else:
                try:
                    # Cố gắng phân tích trực tiếp
                    arguments = json.loads(args)
                except json.JSONDecodeError:
                    # Nếu phân tích cú pháp không thành công, hãy thử hợp nhất nhiều đối tượng JSON
                    try:
                        # Khớp tất cả các đối tượng JSON bằng biểu thức chính quy
                        json_objects = re.findall(r"\{[^{}]*\}", args)
                        if len(json_objects) > 1:
                            # Hợp nhất tất cả các đối tượng JSON
                            merged_dict = {}
                            for json_str in json_objects:
                                try:
                                    obj = json.loads(json_str)
                                    if isinstance(obj, dict):
                                        merged_dict.update(obj)
                                except json.JSONDecodeError:
                                    continue
                            if merged_dict:
                                arguments = merged_dict
                            else:
                                raise ValueError(
                                    f"Không phân tích được đối tượng JSON hợp lệ: {args}"
                                )
                        else:
                            raise ValueError(f"Phân tích JSON tham số thất bại: {args}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"Phân tích JSON tham số thất bại: {str(e)}, gốcTham số: {args}"
                        )
                        raise ValueError(f"Phân tích JSON tham số thất bại: {str(e)}")
        elif isinstance(args, dict):
            arguments = args
        else:
            raise ValueError(
                f"Kiểu tham số không hợp lệ: cần chuỗi hoặc từ điển, nhận được {type(args)}"
            )

        # Đảm bảo tham số là loại từ điển
        if not isinstance(arguments, dict):
            raise ValueError(
                f"Tham số phải là từ điển, kiểu thực tế: {type(arguments)}"
            )

    except Exception as e:
        if not isinstance(e, ValueError):
            raise ValueError(f"Xử lý tham số thất bại: {str(e)}")
        raise e

    actual_name = mcp_client.name_mapping.get(tool_name, tool_name)
    payload = {
        "jsonrpc": "2.0",
        "id": tool_call_id,
        "method": "tools/call",
        "params": {"name": actual_name, "arguments": arguments},
    }

    logger.bind(tag=TAG).info(
        f"gửimáy kháchmcpcông cụgọiyêu cầu: {actual_name} , Tham số: {args}"
    )
    await send_mcp_message(conn, payload)

    try:
        # Chờ phản hồi hoặc hết thời gian chờ
        raw_result = await asyncio.wait_for(result_future, timeout=timeout)
        logger.bind(tag=TAG).info(
            f"máy kháchmcpcông cụgọi {actual_name} thành công , gốckết quả: {raw_result}"
        )

        if isinstance(raw_result, dict):
            if raw_result.get("isError") is True:
                error_msg = raw_result.get(
                    "error", "công cụgọitrả vềLỗi , 但未提供cụ thểLỗithông tin"
                )
                raise RuntimeError(f"công cụgọiLỗi: {error_msg}")

            content = raw_result.get("content")
            if isinstance(content, list) and len(content) > 0:
                if isinstance(content[0], dict) and "text" in content[0]:
                    # Trả về nội dung văn bản trực tiếp mà không cần phân tích cú pháp JSON
                    return content[0]["text"]
        # Nếu kết quả không ở định dạng mong đợi, hãy chuyển đổi nó thành chuỗi
        return str(raw_result)
    except asyncio.TimeoutError:
        await mcp_client.cleanup_call_result(tool_call_id)
        raise TimeoutError("Gọi công cụ quá thời gian chờ")
    except Exception as e:
        await mcp_client.cleanup_call_result(tool_call_id)
        raise e
