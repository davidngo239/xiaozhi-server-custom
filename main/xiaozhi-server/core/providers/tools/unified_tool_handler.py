"""统一công cụxử lý器"""

import json
from typing import Dict, List, Any, Optional
from config.logger import setup_logging
from plugins_func.loadplugins import auto_import_modules

from .base import ToolType
from plugins_func.register import Action, ActionResponse
from .unified_tool_manager import ToolManager
from .server_plugins import ServerPluginExecutor
from .server_mcp import ServerMCPExecutor
from .device_iot import DeviceIoTExecutor
from .device_mcp import DeviceMCPExecutor
from .mcp_endpoint import MCPEndpointExecutor
from core.handle.sendAudioHandle import send_display_message


class UnifiedToolHandler:
    """统一công cụxử lý器"""

    def __init__(self, conn):
        self.conn = conn
        self.config = conn.config
        self.logger = setup_logging()

        # Tạo trình quản lý công cụ
        self.tool_manager = ToolManager(conn)

        # Tạo nhiều loại người thực thi khác nhau
        self.server_plugin_executor = ServerPluginExecutor(conn)
        self.server_mcp_executor = ServerMCPExecutor(conn)
        self.device_iot_executor = DeviceIoTExecutor(conn)
        self.device_mcp_executor = DeviceMCPExecutor(conn)
        self.mcp_endpoint_executor = MCPEndpointExecutor(conn)

        # Đăng ký người thi hành
        self.tool_manager.register_executor(
            ToolType.SERVER_PLUGIN, self.server_plugin_executor
        )
        self.tool_manager.register_executor(
            ToolType.SERVER_MCP, self.server_mcp_executor
        )
        self.tool_manager.register_executor(
            ToolType.DEVICE_IOT, self.device_iot_executor
        )
        self.tool_manager.register_executor(
            ToolType.DEVICE_MCP, self.device_mcp_executor
        )
        self.tool_manager.register_executor(
            ToolType.MCP_ENDPOINT, self.mcp_endpoint_executor
        )

        # cờ khởi tạo
        self.finish_init = False

    async def _initialize(self):
        """异步初始化"""
        try:
            # Tự động nhập các mô-đun plug-in
            auto_import_modules("plugins_func.functions")

            # Khởi tạo máy chủ MCP
            await self.server_mcp_executor.initialize()

            # Khởi tạo điểm truy cập MCP
            await self._initialize_mcp_endpoint()

            # Khởi tạo Home Assistant (nếu cần)
            self._initialize_home_assistant()

            self.finish_init = True
            self.logger.debug("统一công cụxử lý器khởi tạohoàn tất")

            # Xuất ra danh sách tất cả các công cụ hiện được hỗ trợ
            self.current_support_functions()

        except Exception as e:
            self.logger.error(f"Khởi tạo bộ xử lý công cụ thống nhất thất bại: {e}")

    async def _initialize_mcp_endpoint(self):
        """初始化MCP接入点"""
        try:
            from .mcp_endpoint import connect_mcp_endpoint

            # Nhận URL điểm truy cập MCP từ cấu hình
            mcp_endpoint_url = self.config.get("mcp_endpoint", "")

            if (
                mcp_endpoint_url
                and "你的" not in mcp_endpoint_url
                and "YOUR_" not in mcp_endpoint_url
                and mcp_endpoint_url != "null"
            ):
                self.logger.info(f"Đang khởi tạo điểm kết nối MCP: {mcp_endpoint_url}")
                mcp_endpoint_client = await connect_mcp_endpoint(
                    mcp_endpoint_url, self.conn
                )

                if mcp_endpoint_client:
                    # Lưu ứng dụng khách điểm truy cập MCP vào đối tượng kết nối
                    self.conn.mcp_endpoint_client = mcp_endpoint_client
                    self.logger.info("Khởi tạo điểm kết nối MCP thành công")
                else:
                    self.logger.warning("Khởi tạo điểm kết nối MCP thất bại")

        except Exception as e:
            self.logger.error(f"Khởi tạo điểm kết nối MCP thất bại: {e}")

    def _initialize_home_assistant(self):
        """初始化Home Assistant提示词"""
        try:
            from plugins_func.functions.hass_init import append_devices_to_prompt

            append_devices_to_prompt(self.conn)
        except ImportError:
            pass  # Bỏ qua lỗi nhập mô-đun
        except Exception as e:
            self.logger.error(f"khởi tạoHome Assistantthất bại: {e}")

    def get_functions(self) -> List[Dict[str, Any]]:
        """lấy所有công cụ的hàm描述"""
        return self.tool_manager.get_function_descriptions()

    def current_support_functions(self) -> List[str]:
        """lấyhiện tại支持的hàm名称列表"""
        func_names = self.tool_manager.get_supported_tool_names()
        self.logger.info(f"Danh sách hàm hiện được hỗ trợ: {func_names}")
        return func_names

    def upload_functions_desc(self):
        """刷新函数描述列表"""
        self.tool_manager.refresh_tools()
        self.logger.info("Đã làm mới danh sách mô tả hàm")

    def has_tool(self, tool_name: str) -> bool:
        """kiểm tra是否有指定công cụ"""
        return self.tool_manager.has_tool(tool_name)

    async def handle_llm_function_call(
        self, conn, function_call_data: Dict[str, Any]
    ) -> Optional[ActionResponse]:
        """xử lýLLMhàmgọi"""
        try:
            # Xử lý nhiều cuộc gọi chức năng
            if "function_calls" in function_call_data:
                responses = []
                for call in function_call_data["function_calls"]:
                    result = await self.tool_manager.execute_tool(
                        call["name"], call.get("arguments", {})
                    )
                    responses.append(result)
                return self._combine_responses(responses)

            # Xử lý cuộc gọi chức năng đơn
            function_name = function_call_data["name"]
            arguments = function_call_data.get("arguments", {})

            # Nếu đối số là chuỗi, hãy thử phân tích thành JSON
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments else {}
                except json.JSONDecodeError:
                    self.logger.error(f"không thểphân tíchhàmTham số: {arguments}")
                    return ActionResponse(
                        action=Action.ERROR,
                        response="Không phân tích được tham số hàm",
                    )

            self.logger.debug(f"gọihàm: {function_name}, Tham số: {arguments}")

            # Gửi tin nhắn hiển thị cuộc gọi công cụ tới thiết bị
            try:
                await send_display_message(self.conn, f"% {function_name}")
            except Exception as e:
                self.logger.warning(f"Gửi thông báo gọi công cụ thất bại: {e}")

            # Thực hiện lệnh gọi công cụ
            result = await self.tool_manager.execute_tool(function_name, arguments)
            return result

        except Exception as e:
            self.logger.error(f"xử lýfunction callLỗi: {e}")
            return ActionResponse(action=Action.ERROR, response=str(e))

    def _combine_responses(self, responses: List[ActionResponse]) -> ActionResponse:
        """合并多个hàmgọi的phản hồi"""
        if not responses:
            return ActionResponse(action=Action.NONE, response="Không có phản hồi")

        # Nếu có lỗi thì trả về lỗi đầu tiên
        for response in responses:
            if response.action == Action.ERROR:
                return response

        # Hợp nhất tất cả các phản hồi thành công
        contents = []
        responses_text = []

        for response in responses:
            if response.content:
                contents.append(response.content)
            if response.response:
                responses_text.append(response.response)

        # Xác định loại hành động cuối cùng
        final_action = Action.RESPONSE
        for response in responses:
            if response.action == Action.REQLLM:
                final_action = Action.REQLLM
                break

        return ActionResponse(
            action=final_action,
            result="; ".join(contents) if contents else None,
            response="; ".join(responses_text) if responses_text else None,
        )

    async def register_iot_tools(self, descriptors: List[Dict[str, Any]]):
        """注册IoTthiết bịcông cụ"""
        self.device_iot_executor.register_iot_tools(descriptors)
        self.tool_manager.refresh_tools()
        self.logger.info(f"Đã đăng ký công cụ cho {len(descriptors)} thiết bị IoT")

    def get_tool_statistics(self) -> Dict[str, int]:
        """lấycông cụ统计thông tin"""
        return self.tool_manager.get_tool_statistics()

    async def cleanup(self):
        """清理资源"""
        try:
            await self.server_mcp_executor.cleanup()

            # Dọn dẹp các kết nối điểm truy cập MCP
            if (
                hasattr(self.conn, "mcp_endpoint_client")
                and self.conn.mcp_endpoint_client
            ):
                await self.conn.mcp_endpoint_client.close()

            self.logger.info("Đã dọn dẹp bộ xử lý công cụ")
        except Exception as e:
            self.logger.error(f"Dọn dẹp bộ xử lý công cụ thất bại: {e}")
