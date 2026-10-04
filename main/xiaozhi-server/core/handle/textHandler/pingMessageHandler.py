import json
import time
from typing import Dict, Any

from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType

TAG = __name__


class PingMessageHandler(TextMessageHandler):
    """Pingthông điệpxử lý器 , 用于保持WebSocketkết nối"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.PING

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        """
        xử lýPINGthông điệp , gửiPONGphản hồi
        thông điệpđịnh dạng: {"type": "ping"}
        Args:
            conn: WebSocketkết nối对象
            msg_json: PINGthông điệp的JSONdữ liệu
        """
        # Kiểm tra xem chức năng nhịp tim WebSocket có được bật không
        enable_websocket_ping = conn.config.get("enable_websocket_ping", False)
        if not enable_websocket_ping:
            conn.logger.debug(f"WebSocket心跳功能未启用 , 忽略PINGthông điệp")
            return

        try:
            conn.logger.debug(f"nhậnPINGthông điệp , gửiPONGphản hồi")
            conn.last_activity_time = time.time() * 1000
            # Xây dựng thông báo phản hồi PONG
            pong_message = {
                "type": "pong",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            }

            # Gửi phản hồi PONG
            await conn.websocket.send(json.dumps(pong_message))

        except Exception as e:
            conn.logger.error(f"xử lýPINGthông điệpkhixảy raLỗi: {e}")
