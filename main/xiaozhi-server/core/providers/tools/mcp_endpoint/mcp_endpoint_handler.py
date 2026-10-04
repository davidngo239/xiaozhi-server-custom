"""MCP接入点处理器"""

import json
import asyncio
import re
import websockets
from config.logger import setup_logging
from .mcp_endpoint_client import MCPEndpointClient

TAG = __name__
logger = setup_logging()


async def connect_mcp_endpoint(mcp_endpoint_url: str, conn=None) -> MCPEndpointClient:
    """kết nối到MCP接入点"""
    if (
        not mcp_endpoint_url
        or "你的" in mcp_endpoint_url
        or "YOUR_" in mcp_endpoint_url
        or mcp_endpoint_url == "null"
    ):
        return None

    try:
        websocket = await websockets.connect(mcp_endpoint_url)

        mcp_client = MCPEndpointClient(conn)
        mcp_client.set_websocket(websocket)

        # Bắt đầu nghe tin nhắn
        asyncio.create_task(_message_listener(mcp_client))

        # Gửi tin nhắn khởi tạo
        await send_mcp_endpoint_initialize(mcp_client)

        # Gửi thông báo hoàn thành khởi tạo
        await send_mcp_endpoint_notification(mcp_client, "notifications/initialized")

        # Lấy danh sách các công cụ
        await send_mcp_endpoint_tools_list(mcp_client)

        logger.bind(tag=TAG).info("MCP接入点kết nốithành công")
        return mcp_client

    except Exception as e:
        logger.bind(tag=TAG).error(f"kết nốiMCP接入点thất bại: {e}")
        return None


async def _message_listener(mcp_client: MCPEndpointClient):
    """监听MCP接入点thông điệp"""
    try:
        async for message in mcp_client.websocket:
            await handle_mcp_endpoint_message(mcp_client, message)
    except websockets.exceptions.ConnectionClosed:
        logger.bind(tag=TAG).info("MCP接入点kết nốiđãđóng")
    except Exception as e:
        logger.bind(tag=TAG).error(f"MCP接入点thông điệp监听器Lỗi: {e}")
    finally:
        await mcp_client.set_ready(False)


async def handle_mcp_endpoint_message(mcp_client: MCPEndpointClient, message: str):
    """xử lýMCP接入点thông điệp"""
    try:
        payload = json.loads(message)
        logger.bind(tag=TAG).debug(f"nhậnMCP接入点thông điệp: {payload}")

        if not isinstance(payload, dict):
            logger.bind(tag=TAG).error("MCP接入点thông điệpđịnh dạngLỗi")
            return

        # Xử lý kết quả
        if "result" in payload:
            result = payload["result"]
            # Lấy ID tin nhắn một cách an toàn, sử dụng 0 nếu Không
            msg_id_raw = payload.get("id")
            msg_id = int(msg_id_raw) if msg_id_raw is not None else 0

            # Trước tiên hãy kiểm tra phản hồi cuộc gọi công cụ
            if msg_id in mcp_client.call_results:
                logger.bind(tag=TAG).debug(
                    f"nhậncông cụgọiphản hồi，ID: {msg_id}, kết quả: {result}"
                )
                await mcp_client.resolve_call_result(msg_id, result)
                return

            if msg_id == 1:  # mcpInitializeID
                logger.bind(tag=TAG).debug("nhậnMCP接入点khởi tạophản hồi")
                if result is not None and isinstance(result, dict):
                    server_info = result.get("serverInfo")
                    if isinstance(server_info, dict):
                        name = server_info.get("name")
                        version = server_info.get("version")
                        logger.bind(tag=TAG).info(
                            f"MCP接入点dịch vụ器thông tin: name={name}, version={version}"
                        )
                else:
                    logger.bind(tag=TAG).warning(
                        "MCP接入点khởi tạophản hồikết quả为空或định dạngLỗi"
                    )
                return

            elif msg_id == 2:  # mcpToolsListID
                logger.bind(tag=TAG).debug("nhậnMCP接入点công cụ列表phản hồi")
                if (
                    result is not None
                    and isinstance(result, dict)
                    and "tools" in result
                ):
                    tools_data = result["tools"]
                    if not isinstance(tools_data, list):
                        logger.bind(tag=TAG).error("công cụ列表định dạngLỗi")
                        return

                    logger.bind(tag=TAG).info(
                        f"MCP接入点支持的công cụ数量: {len(tools_data)}"
                    )

                    for i, tool in enumerate(tools_data):
                        if not isinstance(tool, dict):
                            continue

                        name = tool.get("name", "")
                        description = tool.get("description", "")
                        input_schema = {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        }

                        if "inputSchema" in tool and isinstance(
                            tool["inputSchema"], dict
                        ):
                            schema = tool["inputSchema"]
                            input_schema["type"] = schema.get("type", "object")
                            input_schema["properties"] = schema.get("properties", {})
                            input_schema["required"] = [
                                s
                                for s in schema.get("required", [])
                                if isinstance(s, str)
                            ]

                        new_tool = {
                            "name": name,
                            "description": description,
                            "inputSchema": input_schema,
                        }
                        await mcp_client.add_tool(new_tool)
                        logger.bind(tag=TAG).debug(f"MCP接入点công cụ #{i + 1}: {name}")

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

                    next_cursor = (
                        result.get("nextCursor", "") if result is not None else ""
                    )
                    if next_cursor:
                        logger.bind(tag=TAG).info(
                            f"有更多công cụ , nextCursor: {next_cursor}"
                        )
                        await send_mcp_endpoint_tools_list_continue(
                            mcp_client, next_cursor
                        )
                    else:
                        await mcp_client.set_ready(True)
                        logger.bind(tag=TAG).info(
                            "所有MCP接入点công cụđãlấy , máy khách准备就绪"
                        )

                        # Làm mới bộ đệm công cụ để đảm bảo rằng công cụ điểm truy cập MCP được đưa vào danh sách chức năng
                        if (
                            hasattr(mcp_client, "conn")
                            and mcp_client.conn
                            and hasattr(mcp_client.conn, "func_handler")
                            and mcp_client.conn.func_handler
                        ):
                            mcp_client.conn.func_handler.tool_manager.refresh_tools()
                            mcp_client.conn.func_handler.current_support_functions()

                        logger.bind(tag=TAG).info(
                            f"MCP接入点công cụlấyhoàn tất , 共 {len(mcp_client.tools)} công cụ"
                        )
                else:
                    logger.bind(tag=TAG).warning(
                        "MCP接入点công cụ列表phản hồikết quả为空或định dạngLỗi"
                    )
                return

        # Xử lý các cuộc gọi phương thức (yêu cầu từ điểm cuối)
        elif "method" in payload:
            method = payload["method"]
            logger.bind(tag=TAG).info(f"nhậnMCP接入点yêu cầu: {method}")

        elif "error" in payload:
            error_data = payload["error"]
            error_msg = error_data.get("message", "Lỗi không xác định")
            logger.bind(tag=TAG).error(f"nhậnMCP接入点Lỗiphản hồi: {error_msg}")

            # Lấy ID tin nhắn một cách an toàn, sử dụng 0 nếu Không
            msg_id_raw = payload.get("id")
            msg_id = int(msg_id_raw) if msg_id_raw is not None else 0

            if msg_id in mcp_client.call_results:
                await mcp_client.reject_call_result(
                    msg_id, Exception(f"MCP接入点Lỗi: {error_msg}")
                )

    except json.JSONDecodeError as e:
        logger.bind(tag=TAG).error(f"MCP接入点thông điệpJSONphân tíchthất bại: {e}")
    except Exception as e:
        logger.bind(tag=TAG).error(f"xử lýMCP接入点thông điệpkhi出错: {e}")
        import traceback

        logger.bind(tag=TAG).error(f"Lỗi详情: {traceback.format_exc()}")


async def send_mcp_endpoint_initialize(mcp_client: MCPEndpointClient):
    """gửiMCP接入点khởi tạothông điệp"""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,  # mcpInitializeID
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "roots": {"listChanged": True},
                "sampling": {},
            },
            "clientInfo": {
                "name": "XiaozhiMCPEndpointClient",
                "version": "1.0.0",
            },
        },
    }
    message = json.dumps(payload)
    logger.bind(tag=TAG).info("gửiMCP接入点khởi tạothông điệp")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_notification(mcp_client: MCPEndpointClient, method: str):
    """gửiMCP接入点通知thông điệp"""
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": {},
    }
    message = json.dumps(payload)
    logger.bind(tag=TAG).debug(f"发送MCP接入点通知: {method}")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_tools_list(mcp_client: MCPEndpointClient):
    """gửiMCP接入点công cụ列表yêu cầu"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID
        "method": "tools/list",
    }
    message = json.dumps(payload)
    logger.bind(tag=TAG).debug("gửiMCP接入点công cụ列表yêu cầu")
    await mcp_client.send_message(message)


async def send_mcp_endpoint_tools_list_continue(
    mcp_client: MCPEndpointClient, cursor: str
):
    """gửi带有cursor的MCP接入点công cụ列表yêu cầu"""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,  # mcpToolsListID (cùng một ID để tiếp tục)
        "method": "tools/list",
        "params": {"cursor": cursor},
    }
    message = json.dumps(payload)
    logger.bind(tag=TAG).info(f"gửi带cursor的MCP接入点công cụ列表yêu cầu: {cursor}")
    await mcp_client.send_message(message)


async def call_mcp_endpoint_tool(
    mcp_client: MCPEndpointClient, tool_name: str, args: str = "{}", timeout: int = 30
):
    """
    gọi指定的MCP接入点công cụ , 并chờphản hồi
    """
    if not await mcp_client.is_ready():
        raise RuntimeError("Máy khách điểm truy cập MCP chưa sẵn sàng")

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

    message = json.dumps(payload)
    logger.bind(tag=TAG).info(
        f"gửiMCP接入点công cụgọiyêu cầu: {actual_name} , Tham số: {json.dumps(arguments, ensure_ascii=False)}"
    )
    await mcp_client.send_message(message)

    try:
        # Chờ phản hồi hoặc hết thời gian chờ
        raw_result = await asyncio.wait_for(result_future, timeout=timeout)
        logger.bind(tag=TAG).info(
            f"MCP接入点công cụgọi {actual_name} thành công , gốckết quả: {raw_result}"
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
