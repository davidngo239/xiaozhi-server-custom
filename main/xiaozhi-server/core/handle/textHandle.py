from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry
from core.handle.textMessageProcessor import TextMessageProcessor

TAG = __name__

# Đăng ký bộ xử lý toàn cầu
message_registry = TextMessageHandlerRegistry()

# Tạo một phiên bản xử lý tin nhắn toàn cầu
message_processor = TextMessageProcessor(message_registry)


async def handleTextMessage(conn: "ConnectionHandler", message):
    """xử lývăn bảnthông điệp"""
    await message_processor.process_message(conn, message)
