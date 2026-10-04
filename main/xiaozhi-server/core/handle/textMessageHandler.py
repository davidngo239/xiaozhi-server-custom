from abc import abstractmethod, ABC
from typing import Dict, Any

from core.handle.textMessageType import TextMessageType

TAG = __name__


class TextMessageHandler(ABC):
    """thông điệpxử lý器抽象基类"""

    @abstractmethod
    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        """xử lýthông điệp的抽象方法"""
        pass

    @property
    @abstractmethod
    def message_type(self) -> TextMessageType:
        """trả vềxử lý的thông điệploại"""
        pass
