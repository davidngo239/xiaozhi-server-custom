"""dịch vụ端MCP管理器"""

import asyncio
import os
import json
from typing import Dict, Any, List

from mcp.types import LoggingMessageNotificationParams

from config.config_loader import get_project_dir
from config.logger import setup_logging
from .mcp_client import ServerMCPClient

TAG = __name__
logger = setup_logging()


class ServerMCPManager:
    """管理多个dịch vụ端MCPdịch vụ的集trong管理器"""

    def __init__(self, conn) -> None:
        """初始化MCP管理器"""
        self.conn = conn
        self.config_path = get_project_dir() + "data/.mcp_server_settings.json"
        if not os.path.exists(self.config_path):
            self.config_path = ""
            logger.bind(tag=TAG).warning(
                f"请kiểm tramcpdịch vụcấu hình文件: data/.mcp_server_settings.json"
            )
        self.clients: Dict[str, ServerMCPClient] = {}
        self.tools = []
        self._init_lock = asyncio.Lock()

    def load_config(self) -> Dict[str, Any]:
        """tảiMCPdịch vụcấu hình"""
        if len(self.config_path) == 0:
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("mcpServers", {})
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Error loading MCP config from {self.config_path}: {e}"
            )
            return {}

    async def _init_server(self, name: str, srv_config: Dict[str, Any]):
        """khởi tạo单个MCPdịch vụ"""
        client = None
        try:
            # Khởi tạo máy khách MCP máy chủ
            logger.bind(tag=TAG).info(f"khởi tạodịch vụ端Máy khách MCP: {name}")
            client = ServerMCPClient(srv_config)
            # Đặt thời gian chờ thành 10 giây
            await asyncio.wait_for(
                client.initialize(logging_callback=self.logging_callback), timeout=10
            )

            # Sử dụng khóa để bảo vệ các sửa đổi đối với trạng thái chia sẻ
            async with self._init_lock:
                self.clients[name] = client
                client_tools = client.get_available_tools()
                self.tools.extend(client_tools)

        except asyncio.TimeoutError:
            logger.bind(tag=TAG).error(
                f"Failed to initialize MCP server {name}: Timeout"
            )
            if client:
                await client.cleanup()
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to initialize MCP server {name}: {e}")
            if client:
                await client.cleanup()

    async def initialize_servers(self) -> None:
        """khởi tạo所有MCPdịch vụ"""
        config = self.load_config()
        tasks = []
        for name, srv_config in config.items():
            if not srv_config.get("command") and not srv_config.get("url"):
                logger.bind(tag=TAG).warning(
                    f"Skipping server {name}: neither command nor url specified"
                )
                continue

            tasks.append(self._init_server(name, srv_config))

        if tasks:
            await asyncio.gather(*tasks)

        # Xuất danh sách các công cụ MCP máy chủ hiện được hỗ trợ
        if hasattr(self.conn, "func_handler") and self.conn.func_handler:
            # Làm mới bộ đệm công cụ để đảm bảo rằng công cụ MCP phía máy chủ được tải chính xác
            if hasattr(self.conn.func_handler, "tool_manager"):
                self.conn.func_handler.tool_manager.refresh_tools()
            self.conn.func_handler.current_support_functions()

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """lấy所有dịch vụ的công cụfunction定义"""
        return self.tools

    def is_mcp_tool(self, tool_name: str) -> bool:
        """kiểm tra是否是MCPcông cụ"""
        for tool in self.tools:
            if (
                tool.get("function") is not None
                and tool["function"].get("name") == tool_name
            ):
                return True
        return False

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """thực thicông cụgọi , thất bạikhisẽthử重新kết nối"""
        logger.bind(tag=TAG).info(
            f"thực thidịch vụ端MCPcông cụ {tool_name} , Tham số: {arguments}"
        )

        max_retries = 3  # Số lần thử lại tối đa
        retry_interval = 2  # Khoảng cách giữa các lần thử lại (giây)

        # Tìm máy khách tương ứng
        client_name = None
        target_client = None
        for name, client in self.clients.items():
            if client.has_tool(tool_name):
                client_name = name
                target_client = client
                break

        if not target_client:
            raise ValueError(
                f"Không tìm thấy công cụ {tool_name} trong dịch vụ MCP nào"
            )

        # Cuộc gọi công cụ với cơ chế thử lại
        for attempt in range(max_retries):
            try:
                return await target_client.call_tool(
                    tool_name, arguments, progress_callback=self.progress_callback
                )
            except Exception as e:
                # Ném một ngoại lệ trực tiếp khi lần thử cuối cùng thất bại
                if attempt == max_retries - 1:
                    raise

                logger.bind(tag=TAG).warning(
                    f"thực thicông cụ {tool_name} thất bại (thử {attempt + 1}/{max_retries}): {e}"
                )

                # Hãy thử kết nối lại
                logger.bind(tag=TAG).info(
                    f"thử lại前thử重新kết nối MCP máy khách {client_name}"
                )
                try:
                    # đóng kết nối cũ
                    await target_client.cleanup()

                    # Khởi tạo lại ứng dụng khách
                    config = self.load_config()
                    if client_name in config:
                        client = ServerMCPClient(config[client_name])
                        await client.initialize(logging_callback=self.logging_callback)
                        self.clients[client_name] = client
                        target_client = client
                        logger.bind(tag=TAG).info(
                            f"thành công重新kết nối MCP máy khách: {client_name}"
                        )
                    else:
                        logger.bind(tag=TAG).error(
                            f"Cannot reconnect MCP client {client_name}: config not found"
                        )
                except Exception as reconnect_error:
                    logger.bind(tag=TAG).error(
                        f"Failed to reconnect MCP client {client_name}: {reconnect_error}"
                    )

                # Đợi một lúc và thử lại
                await asyncio.sleep(retry_interval)

    async def cleanup_all(self) -> None:
        """đóng所有 Máy khách MCP"""
        for name, client in list(self.clients.items()):
            try:
                if hasattr(client, "cleanup"):
                    await asyncio.wait_for(client.cleanup(), timeout=20)
                logger.bind(tag=TAG).info(f"dịch vụ端Máy khách MCPđãđóng: {name}")
            except (asyncio.TimeoutError, Exception) as e:
                logger.bind(tag=TAG).error(
                    f"đóngdịch vụ端Máy khách MCP {name} khi出错: {e}"
                )
        self.clients.clear()

    # Phương thức gọi lại tùy chọn

    async def logging_callback(self, params: LoggingMessageNotificationParams):
        logger.bind(tag=TAG).info(
            f"[Server Log - {params.level.upper()}] {params.data}"
        )

    async def progress_callback(
        self, progress: float, total: float | None, message: str | None
    ) -> None:
        logger.bind(tag=TAG).info(f"[Progress {progress}/{total}]: {message}")
