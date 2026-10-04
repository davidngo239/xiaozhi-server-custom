import time
import json
import uuid
import random
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils.dialogue import Message
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import SentenceType
from core.utils.wakeup_word import WakeupWordsConfig
from core.handle.sendAudioHandle import sendAudioMessage, send_tts_message
from core.utils.util import remove_punctuation_and_length, opus_datas_to_wav_bytes
from core.providers.tools.device_mcp import MCPClient, send_mcp_initialize_message

TAG = __name__

WAKEUP_CONFIG = {
    "refresh_time": 10,
    "responses": [
        "Mình vẫn ở đây, bạn nói đi nhé.",
        "Mình đây, bạn cần gì cứ nói nhé.",
        "Mình tới rồi, bạn nói mình nghe nhé.",
        "Bạn nói đi, mình đang nghe.",
        "Mình sẵn sàng rồi, bạn nói đi nhé.",
        "Bạn muốn mình làm gì?",
        "Mình đang lắng nghe, bạn nói đi.",
        "Bạn cần mình giúp gì?",
        "Mình ở đây và sẵn sàng giúp bạn.",
    ],
}

# Tạo trình quản lý cấu hình từ đánh thức toàn cầu
wakeup_words_config = WakeupWordsConfig()

# Khóa được sử dụng để ngăn các cuộc gọi đồng thời tới WakeupWordsResponse
_wakeup_response_lock = asyncio.Lock()


async def handleHelloMessage(conn: "ConnectionHandler", msg_json):
    """xử lýhellothông điệp"""
    audio_params = msg_json.get("audio_params")
    if audio_params:
        format = audio_params.get("format")
        conn.logger.bind(tag=TAG).debug(f"máy kháchâm thanhđịnh dạng: {format}")
        conn.audio_format = format
        conn.welcome_msg["audio_params"] = audio_params
    features = msg_json.get("features")
    if features:
        conn.logger.bind(tag=TAG).debug(f"客户端特性: {features}")
        conn.features = features
        if features.get("mcp"):
            conn.logger.bind(tag=TAG).debug("客户端支持MCP")
            conn.mcp_client = MCPClient()
        if features.get("aec"):
            conn.logger.bind(tag=TAG).debug("máy khách启用了dịch vụ端AEC")
            conn.client_aec = True

    await conn.websocket.send(json.dumps(conn.welcome_msg))

    # Thiết bị đợi máy chủ xin chào trước khi xử lý tin nhắn MCP.
    if features and features.get("mcp"):
        asyncio.create_task(send_mcp_initialize_message(conn))


async def checkWakeupWords(conn: "ConnectionHandler", text):
    enable_wakeup_words_response_cache = conn.config[
        "enable_wakeup_words_response_cache"
    ]

    # Đợi tts khởi tạo, tối đa 3 giây
    start_time = time.time()
    while time.time() - start_time < 3:
        if conn.tts:
            break
        await asyncio.sleep(0.1)
    else:
        return False

    if not enable_wakeup_words_response_cache:
        return False

    _, filtered_text = remove_punctuation_and_length(text)
    if filtered_text not in conn.config.get("wakeup_words"):
        return False

    conn.just_woken_up = True
    await send_tts_message(conn, "start")

    # Nhận âm thanh hiện tại
    voice = getattr(conn.tts, "voice", "default")
    if not voice:
        voice = "default"

    # Nhận cấu hình trả lời từ đánh thức
    response = wakeup_words_config.get_wakeup_response(voice)
    if not response or not response.get("file_path"):
        response = {
            "voice": "default",
            "file_path": "config/assets/wakeup_words_short.wav",
            "time": 0,
            "text": "Mình đây!",
        }

    # Nhận dữ liệu âm thanh
    opus_packets = await audio_to_data(response.get("file_path"), use_cache=False)
    # Chơi trả lời từ đánh thức
    conn.client_abort = False

    # Coi việc trả lời từ đánh thức là phiên mới, tạo câu_id mới, đảm bảo bộ điều khiển luồng được đặt lại
    conn.sentence_id = str(uuid.uuid4().hex)

    conn.logger.bind(tag=TAG).info(f"播放唤醒词回复: {response.get('text')}")
    await sendAudioMessage(conn, SentenceType.FIRST, opus_packets, response.get("text"))
    await sendAudioMessage(conn, SentenceType.LAST, [], None)

    # Đối thoại bổ sung
    conn.dialogue.put(Message(role="assistant", content=response.get("text")))

    # Kiểm tra xem câu trả lời từ đánh thức có cần được cập nhật không
    if time.time() - response.get("time", 0) > WAKEUP_CONFIG["refresh_time"]:
        if not _wakeup_response_lock.locked():
            asyncio.create_task(wakeupWordsResponse(conn))
    return True


async def wakeupWordsResponse(conn: "ConnectionHandler"):
    if not conn.tts:
        return

    try:
        # Cố gắng lấy khóa và trả lại nếu không lấy được.
        if not await _wakeup_response_lock.acquire():
            return

        # Chọn ngẫu nhiên một câu trả lời từ danh sách các câu trả lời được xác định trước
        result = random.choice(WAKEUP_CONFIG["responses"])
        if not result or len(result) == 0:
            return

        # Tạo âm thanh TTS
        tts_result = await asyncio.to_thread(conn.tts.to_tts, result)
        if not tts_result:
            return

        # Nhận âm thanh hiện tại
        voice = getattr(conn.tts, "voice", "default")

        # Sử dụng sample_rate được liên kết
        wav_bytes = opus_datas_to_wav_bytes(tts_result, sample_rate=conn.sample_rate)
        file_path = wakeup_words_config.generate_file_path(voice)
        with open(file_path, "wb") as f:
            f.write(wav_bytes)
        # Cập nhật cấu hình
        wakeup_words_config.update_wakeup_response(voice, file_path, result)
    finally:
        # Đảm bảo khóa được mở trong mọi trường hợp
        if _wakeup_response_lock.locked():
            _wakeup_response_lock.release()
