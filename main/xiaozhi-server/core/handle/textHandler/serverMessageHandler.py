import asyncio
import json
from typing import Dict, Any

from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType
from core.providers.tools.device_mcp import handle_mcp_message

TAG = __name__


class ServerTextMessageHandler(TextMessageHandler):
    """MCPthông điệpxử lý器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.SERVER

    async def handle(self, conn, msg_json: Dict[str, Any]) -> None:
        # Nếu cấu hình được đọc từ API thì bí mật cần được xác minh
        if not conn.read_config_from_api:
            return
        # Nhận bí mật của yêu cầu bài viết
        post_secret = msg_json.get("content", {}).get("secret", "")
        secret = conn.config["manager-api"].get("secret", "")
        # Nếu bí mật không khớp, hãy trả lại
        if post_secret != secret:
            await conn.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": "Xác minh khóa server thất bại",
                    }
                )
            )
            return
        # Cập nhật cấu hình động
        if msg_json["action"] == "update_config":
            try:
                # Cập nhật cấu hình của WebSocketServer
                if not conn.server:
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": "Không thể lấy đối tượng server",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                    return

                if not await conn.server.update_config():
                    await conn.websocket.send(
                        json.dumps(
                            {
                                "type": "server",
                                "status": "error",
                                "message": "Không thể cập nhật cấu hình server",
                                "content": {"action": "update_config"},
                            }
                        )
                    )
                    return

                # Gửi phản hồi thành công
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "success",
                            "message": "Đã cập nhật cấu hình",
                            "content": {"action": "update_config"},
                        }
                    )
                )
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"Cập nhật cấu hình thất bại: {str(e)}")
                await conn.websocket.send(
                    json.dumps(
                        {
                            "type": "server",
                            "status": "error",
                            "message": f"Cập nhật cấu hình thất bại: {str(e)}",
                            "content": {"action": "update_config"},
                        }
                    )
                )
        # Khởi động lại máy chủ
        elif msg_json["action"] == "restart":
            await conn.handle_restart(msg_json)
