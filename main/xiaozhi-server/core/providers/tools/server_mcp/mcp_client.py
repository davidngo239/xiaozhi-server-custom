"""dịch vụ端Máy khách MCP"""

from __future__ import annotations

from datetime import timedelta
import asyncio
import os
import shutil
import concurrent.futures
from contextlib import AsyncExitStack
from typing import Optional, List, Dict, Any

from mcp import ClientSession, StdioServerParameters, Implementation
from mcp.client.session import (
    SamplingFnT,
    ElicitationFnT,
    ListRootsFnT,
    LoggingFnT,
    MessageHandlerFnT,
)
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.session import ProgressFnT

from config.logger import setup_logging
from core.utils.util import sanitize_tool_name

TAG = __name__


class ServerMCPClient:
    """dịch vụ端Máy khách MCP , 用于kết nối和管理MCPdịch vụ"""

    def __init__(self, config: Dict[str, Any]):
        """khởi tạodịch vụ端Máy khách MCP

        Args:
            config: MCPdịch vụcấu hình字典
        """
        self.logger = setup_logging()
        self.config = config

        self._worker_task: Optional[asyncio.Task] = None
        self._ready_evt = asyncio.Event()
        self._shutdown_evt = asyncio.Event()

        self.session: Optional[ClientSession] = None
        self.tools: List = []  # Các đối tượng công cụ ban đầu
        self.tools_dict: Dict[str, Any] = {}
        self.name_mapping: Dict[str, str] = {}

    async def initialize(
        self,
        read_timeout_seconds: timedelta | None = None,
        sampling_callback: SamplingFnT | None = None,
        elicitation_callback: ElicitationFnT | None = None,
        list_roots_callback: ListRootsFnT | None = None,
        logging_callback: LoggingFnT | None = None,
        message_handler: MessageHandlerFnT | None = None,
        client_info: Implementation | None = None,
    ):
        """khởi tạoMáy khách MCPkết nối"""
        if self._worker_task:
            return

        self._worker_task = asyncio.create_task(
            self._worker(
                read_timeout_seconds=read_timeout_seconds,
                sampling_callback=sampling_callback,
                elicitation_callback=elicitation_callback,
                list_roots_callback=list_roots_callback,
                logging_callback=logging_callback,
                message_handler=message_handler,
                client_info=client_info,
            ),
            name="ServerMCPClientWorker",
        )
        await self._ready_evt.wait()

        self.logger.bind(tag=TAG).info(
            f"dịch vụ端Máy khách MCPđãkết nối , 可用công cụ: {[name for name in self.name_mapping.values()]}"
        )

    async def cleanup(self):
        """清理Máy khách MCP资源"""
        if not self._worker_task:
            return

        self._shutdown_evt.set()
        try:
            await asyncio.wait_for(self._worker_task, timeout=20)
        except (asyncio.TimeoutError, Exception) as e:
            self.logger.bind(tag=TAG).error(f"dịch vụ端Máy khách MCPđóngLỗi: {e}")
        finally:
            self._worker_task = None

    def has_tool(self, name: str) -> bool:
        """kiểm tra是否包含指定công cụ

        Args:
            name: công cụ名称

        Returns:
            bool: 是否包含该công cụ
        """
        return name in self.tools_dict

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """lấy所有可用công cụ的定义

        Returns:
            List[Dict[str, Any]]: công cụ定义列表
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for name, tool in self.tools_dict.items()
        ]

    async def call_tool(
        self,
        name: str,
        arguments: dict,
        read_timeout_seconds: timedelta | None = None,
        progress_callback: ProgressFnT | None = None,
        *,
        meta: dict[str, Any] | None = None,
    ) -> Any:
        """gọi指定công cụ

        Args:
            name: công cụ名称
            arguments: công cụtham số
            read_timeout_seconds:
            progress_callback: 进度回调hàm
            meta:

        Returns:
            Any: công cụthực thikết quả

        Raises:
            RuntimeError: máy khách未khởi tạokhi抛出
        """
        if not self.session:
            raise RuntimeError("Máy khách MCP phía máy chủ chưa được khởi tạo")

        real_name = self.name_mapping.get(name, name)
        loop = self._worker_task.get_loop()
        coro = self.session.call_tool(
            real_name,
            arguments=arguments,
            read_timeout_seconds=read_timeout_seconds,
            progress_callback=progress_callback,
            meta=meta,
        )

        if loop is asyncio.get_running_loop():
            return await coro

        fut: concurrent.futures.Future = asyncio.run_coroutine_threadsafe(coro, loop)
        return await asyncio.wrap_future(fut)

    def is_connected(self) -> bool:
        """kiểm traMáy khách MCP是否kết nối正常

        Returns:
            bool: 如果máy kháchđãkết nối并正常工作 , trả vềTrue , 否则trả vềFalse
        """
        # Kiểm tra xem nhiệm vụ công việc có tồn tại không
        if self._worker_task is None:
            return False

        # Kiểm tra xem một nhiệm vụ công việc đã được hoàn thành hay bị hủy bỏ
        if self._worker_task.done():
            return False

        # Kiểm tra xem phiên có tồn tại không
        if self.session is None:
            return False

        # Tất cả các lần kiểm tra đã thành công và kết nối vẫn bình thường
        return True

    async def _worker(
        self,
        read_timeout_seconds: timedelta | None = None,
        sampling_callback: SamplingFnT | None = None,
        elicitation_callback: ElicitationFnT | None = None,
        list_roots_callback: ListRootsFnT | None = None,
        logging_callback: LoggingFnT | None = None,
        message_handler: MessageHandlerFnT | None = None,
        client_info: Implementation | None = None,
    ):
        """Máy khách MCP工作协程"""
        async with AsyncExitStack() as stack:
            try:
                # Tạo StdioClient
                if "command" in self.config:
                    cmd = (
                        shutil.which("npx")
                        if self.config["command"] == "npx"
                        else self.config["command"]
                    )
                    env = {**os.environ, **self.config.get("env", {})}
                    params = StdioServerParameters(
                        command=cmd,
                        args=self.config.get("args", []),
                        env=env,
                    )
                    stdio_r, stdio_w = await stack.enter_async_context(
                        stdio_client(params)
                    )
                    read_stream, write_stream = stdio_r, stdio_w

                # Tạo SSEClient
                elif "url" in self.config:
                    headers = dict(self.config.get("headers", {}))
                    # TODO tương thích với các phiên bản cũ hơn
                    if "API_ACCESS_TOKEN" in self.config:
                        headers["Authorization"] = (
                            f"Bearer {self.config['API_ACCESS_TOKEN']}"
                        )
                        self.logger.bind(tag=TAG).warning(
                            f"你đang使用旧过khi的cấu hình API_ACCESS_TOKEN  , 请在.mcp_server_settings.jsontrongsẽAPI_ACCESS_TOKEN直接设置在headerstrong , 例如 'Authorization': 'Bearer API_ACCESS_TOKEN'"
                        )

                    # Chọn các máy khách khác nhau tùy theo loại phương tiện vận chuyển, mặc định là SSE
                    transport_type = self.config.get("transport", "sse")

                    if transport_type == "streamable-http" or transport_type == "http":
                        # Sử dụng phương tiện truyền tải HTTP có thể phát trực tuyến
                        (
                            http_r,
                            http_w,
                            get_session_id,
                        ) = await stack.enter_async_context(
                            streamablehttp_client(
                                url=self.config["url"],
                                headers=headers,
                                timeout=self.config.get("timeout", 30),
                                sse_read_timeout=self.config.get(
                                    "sse_read_timeout", 60 * 5
                                ),
                                terminate_on_close=self.config.get(
                                    "terminate_on_close", True
                                ),
                            )
                        )
                        read_stream, write_stream = http_r, http_w
                    else:
                        # Sử dụng phương tiện vận chuyển SSE truyền thống
                        sse_r, sse_w = await stack.enter_async_context(
                            sse_client(
                                url=self.config["url"],
                                headers=headers,
                                timeout=self.config.get("timeout", 5),
                                sse_read_timeout=self.config.get(
                                    "sse_read_timeout", 60 * 5
                                ),
                            )
                        )
                        read_stream, write_stream = sse_r, sse_w

                else:
                    raise ValueError(
                        "Cấu hình máy khách MCP phải có 'command' hoặc 'url'"
                    )

                self.session = await stack.enter_async_context(
                    ClientSession(
                        read_stream=read_stream,
                        write_stream=write_stream,
                        read_timeout_seconds=read_timeout_seconds,
                        sampling_callback=sampling_callback,
                        elicitation_callback=elicitation_callback,
                        list_roots_callback=list_roots_callback,
                        logging_callback=logging_callback,
                        message_handler=message_handler,
                        client_info=client_info,
                    )
                )
                await self.session.initialize()

                # Nhận công cụ
                self.tools = (await self.session.list_tools()).tools
                for t in self.tools:
                    sanitized = sanitize_tool_name(t.name)
                    self.tools_dict[sanitized] = t
                    self.name_mapping[sanitized] = t.name

                self._ready_evt.set()

                # đang chờ tắt máy
                await self._shutdown_evt.wait()

            except Exception as e:
                self.logger.bind(tag=TAG).error(
                    f"dịch vụ端Máy khách MCP工作协程Lỗi: {e}"
                )
                self._ready_evt.set()
                raise
