from typing import Dict, Optional

from core.handle.textHandler.abortMessageHandler import AbortTextMessageHandler
from core.handle.textHandler.helloMessageHandler import HelloTextMessageHandler
from core.handle.textHandler.iotMessageHandler import IotTextMessageHandler
from core.handle.textHandler.listenMessageHandler import ListenTextMessageHandler
from core.handle.textHandler.mcpMessageHandler import McpTextMessageHandler
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textHandler.serverMessageHandler import ServerTextMessageHandler
from core.handle.textHandler.pingMessageHandler import PingMessageHandler

TAG = __name__


class TextMessageHandlerRegistry:
    """thông điệpxử lý器注册表"""

    def __init__(self):
        self._handlers: Dict[str, TextMessageHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """注册默认的thông điệpxử lý器"""
        handlers = [
            HelloTextMessageHandler(),
            AbortTextMessageHandler(),
            ListenTextMessageHandler(),
            IotTextMessageHandler(),
            McpTextMessageHandler(),
            ServerTextMessageHandler(),
            PingMessageHandler(),
        ]

        for handler in handlers:
            self.register_handler(handler)

    def register_handler(self, handler: TextMessageHandler) -> None:
        """注册thông điệpxử lý器"""
        self._handlers[handler.message_type.value] = handler

    def get_handler(self, message_type: str) -> Optional[TextMessageHandler]:
        """获hủy息xử lý器"""
        return self._handlers.get(message_type)

    def get_supported_types(self) -> list:
        """lấy支持的thông điệploại"""
        return list(self._handlers.keys())
