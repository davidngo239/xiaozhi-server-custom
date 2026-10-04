import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
TAG = __name__


async def handleAbortMessage(conn: "ConnectionHandler"):
    conn.logger.bind(tag=TAG).info("Abort message received")
    # Đặt ở trạng thái ngắt, nó sẽ tự động ngắt các tác vụ llm và tts
    conn.close_after_chat = False
    conn.client_abort = True
    conn.clear_queues()
    # Ngắt trạng thái đang nói của máy khách
    await conn.websocket.send(
        json.dumps({"type": "tts", "state": "stop", "session_id": conn.session_id})
    )
    conn.clearSpeakStatus()
    conn.logger.bind(tag=TAG).info("Abort message received-end")
