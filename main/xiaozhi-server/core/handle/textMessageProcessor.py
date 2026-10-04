import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.handle.textMessageHandlerRegistry import TextMessageHandlerRegistry

TAG = __name__


class TextMessageProcessor:
    """thông điệpxử lý器主类"""

    def __init__(self, registry: TextMessageHandlerRegistry):
        self.registry = registry

    async def process_message(self, conn: "ConnectionHandler", message: str) -> None:
        """xử lýthông điệp的主入口"""
        try:
            # Phân tích thông điệp JSON
            msg_json = json.loads(message)

            # Xử lý tin nhắn JSON
            if isinstance(msg_json, dict):
                message_type = msg_json.get("type")

                # khai thác gỗ
                conn.logger.bind(tag=TAG).info(
                    f"nhận{message_type}thông điệp：{message}"
                )

                # Nhận và thực thi bộ xử lý
                handler = self.registry.get_handler(message_type)
                if handler:
                    await handler.handle(conn, msg_json)
                else:
                    conn.logger.bind(tag=TAG).error(
                        f"nhậnChưa xác địnhloạithông điệp：{message}"
                    )
            # Xử lý tin nhắn kỹ thuật số thuần túy
            elif isinstance(msg_json, int):
                conn.logger.bind(tag=TAG).info(f"nhận数字thông điệp: {message}")
                await conn.websocket.send(message)

        except json.JSONDecodeError:
            # Tin nhắn không phải JSON được chuyển tiếp trực tiếp
            conn.logger.bind(tag=TAG).error(f"phân tích到Lỗi的thông điệp: {message}")
            await conn.websocket.send(message)
