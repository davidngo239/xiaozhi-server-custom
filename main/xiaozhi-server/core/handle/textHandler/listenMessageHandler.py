import time
import uuid
import asyncio
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

from core.utils.dialogue import Message
from core.providers.asr.dto.dto import InterfaceType
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.handle.sendAudioHandle import send_stt_message, send_tts_message
from core.handle.textMessageHandler import TextMessageHandler
from core.handle.textMessageType import TextMessageType
from core.utils.util import remove_punctuation_and_length
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType


TAG = __name__


class ListenTextMessageHandler(TextMessageHandler):
    """Listenthông điệpxử lý器"""

    @property
    def message_type(self) -> TextMessageType:
        return TextMessageType.LISTEN

    async def handle(self, conn: "ConnectionHandler", msg_json: Dict[str, Any]) -> None:
        if "mode" in msg_json:
            conn.client_listen_mode = msg_json["mode"]
            conn.logger.bind(tag=TAG).debug(
                f"Chế độ thu âm của thiết bị: {conn.client_listen_mode}"
            )
        if msg_json["state"] == "start":
            # Thiết bị chuyển về chế độ ghi từ chế độ phát lại, xóa tất cả trạng thái âm thanh và bộ đệm
            conn.reset_audio_states()
        elif msg_json["state"] == "stop":
            # Đã nhận được lệnh dừng nhưng asr không được khởi tạo, quá trình xử lý bị bỏ qua
            if conn.asr is None:
                return

            conn.client_voice_stop = True
            if conn.asr.interface_type == InterfaceType.STREAM:
                # Ở chế độ phát trực tuyến, gửi yêu cầu kết thúc
                asyncio.create_task(conn.asr._send_stop_request())
            else:
                # Chế độ không phát trực tuyến: kích hoạt trực tiếp nhận dạng ASR
                if len(conn.asr_audio) > 0:
                    asr_audio_task = conn.asr_audio.copy()
                    conn.reset_audio_states()

                    if len(asr_audio_task) > 0:
                        await conn.asr.handle_voice_stop(conn, asr_audio_task)
        elif msg_json["state"] == "detect":
            conn.client_have_voice = False
            conn.reset_audio_states()
            if "text" in msg_json:
                conn.last_activity_time = time.time() * 1000
                original_text = msg_json["text"]  # Giữ văn bản gốc
                filtered_len, filtered_text = remove_punctuation_and_length(
                    original_text
                )

                # Kiểm tra xem đó có phải là lệnh gọi thiết bị [device_call] không
                if original_text.startswith("[device_call]"):
                    # Trích xuất văn bản sau thẻ
                    call_text = original_text[len("[device_call]") :].strip()
                    conn.logger.bind(tag=TAG).info(
                        f"Nhận lệnh gọi thiết bị: {call_text}"
                    )

                    # Đánh dấu là chế độ trả lời cuộc gọi
                    conn.incoming_call = True

                    # Sẵn sàng bắt đầu một phiên mới
                    conn.sentence_id = uuid.uuid4().hex

                    await send_stt_message(conn, call_text)

                    # Đợi tts khởi tạo, tối đa 3 giây
                    start_time = time.time()
                    while time.time() - start_time < 3:
                        if conn.tts:
                            break
                        await asyncio.sleep(0.1)

                    if conn.tts:
                        conn.tts.store_tts_text(conn.sentence_id, call_text)
                        conn.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=conn.sentence_id,
                                sentence_type=SentenceType.FIRST,
                                content_type=ContentType.ACTION,
                            )
                        )
                        conn.tts.tts_one_sentence(
                            conn, ContentType.TEXT, content_detail=call_text
                        )
                        conn.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=conn.sentence_id,
                                sentence_type=SentenceType.LAST,
                                content_type=ContentType.ACTION,
                            )
                        )

                    # Thêm vào lịch sử hội thoại để mô hình hiểu ngữ cảnh
                    conn.dialogue.put(Message(role="assistant", content=call_text))
                    return

                # Xác định xem đó có phải là một từ đánh thức hay không
                is_wakeup_words = filtered_text in conn.config.get("wakeup_words")
                # Có bật tính năng trả lời từ đánh thức hay không
                enable_greeting = conn.config.get("enable_greeting", True)

                if is_wakeup_words and not enable_greeting:
                    # Nếu đó là từ đánh thức và tính năng trả lời từ đánh thức bị tắt thì không cần phải trả lời.
                    await send_stt_message(conn, original_text)
                    await send_tts_message(conn, "stop", None)
                    conn.client_is_speaking = False
                elif is_wakeup_words:
                    conn.just_woken_up = True
                    # Báo cáo dữ liệu văn bản thuần túy (sử dụng lại chức năng báo cáo ASR nhưng không cung cấp dữ liệu âm thanh)
                    enqueue_asr_report(conn, "Xin chào!", [])
                    await startToChat(conn, "Xin chào!")
                else:
                    conn.just_woken_up = True
                    # Báo cáo dữ liệu văn bản thuần túy (sử dụng lại chức năng báo cáo ASR nhưng không cung cấp dữ liệu âm thanh)
                    enqueue_asr_report(conn, original_text, [])
                    # Nếu không, LLM bắt buộc phải trả lời nội dung văn bản.
                    await startToChat(conn, original_text)
