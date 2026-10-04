import time
import json
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils.util import audio_to_data
from core.handle.abortHandle import handleAbortMessage
from core.handle.intentHandler import handle_user_intent
from core.utils.output_counter import check_device_output_limit
from core.handle.sendAudioHandle import send_stt_message, SentenceType

TAG = __name__


async def handleAudioMessage(conn: "ConnectionHandler", pcm_frame):
    # Có ai đang nói trong phần hiện tại không?
    have_voice = conn.vad.is_vad(conn, pcm_frame)
    # Nếu thiết bị vừa thức dậy, hãy nhanh chóng bỏ qua phát hiện VAD
    if hasattr(conn, "just_woken_up") and conn.just_woken_up:
        have_voice = False
        # Đặt độ trễ ngắn trước khi tiếp tục phát hiện VAD
        if not hasattr(conn, "vad_resume_task") or conn.vad_resume_task.done():
            conn.vad_resume_task = asyncio.create_task(resume_vad_detection(conn))
        return
    # Chức năng AEC phía máy chủ cần kích hoạt sự gián đoạn trong thời gian thực.
    if conn.client_aec and have_voice:
        if conn.client_is_speaking and conn.client_listen_mode != "manual":
            await handleAbortMessage(conn)
    # Phát hiện thiết bị không hoạt động trong thời gian dài, dùng để nói lời tạm biệt
    await no_voice_close_connect(conn, have_voice)
    # nhận âm thanh
    await conn.asr.receive_audio(conn, pcm_frame, have_voice)


async def resume_vad_detection(conn: "ConnectionHandler"):
    # Đợi 2 giây rồi tiếp tục phát hiện VAD.
    await asyncio.sleep(2)
    conn.just_woken_up = False


async def startToChat(conn: "ConnectionHandler", text):
    # Kiểm tra xem đầu vào có ở định dạng JSON hay không (chứa thông tin người nói)
    speaker_name = None
    actual_text = text

    try:
        # Cố gắng phân tích đầu vào có định dạng JSON
        if text.strip().startswith("{") and text.strip().endswith("}"):
            data = json.loads(text)
            if "speaker" in data and "content" in data:
                speaker_name = data["speaker"]
                actual_content = data["content"]
                conn.logger.bind(tag=TAG).info(
                    f"phân tích到người nóithông tin: {speaker_name}"
                )

                # Chỉ giữ lại JSON {"loa":...} khi người nói xuất hiện lần đầu tiên, cho phép mô hình gọi nó một cách tự nhiên;
                # Các vòng tiếp theo được chuyển thành văn bản thuần túy để tránh lặp lại tên trong mỗi vòng khiến mô hình gọi chúng nhiều lần.
                if speaker_name not in conn.introduced_speakers:
                    conn.introduced_speakers.add(speaker_name)
                    actual_text = text
                else:
                    actual_text = actual_content
    except (json.JSONDecodeError, KeyError):
        # Nếu phân tích cú pháp không thành công, hãy tiếp tục sử dụng văn bản gốc
        pass

    # Lưu thông tin loa vào đối tượng kết nối
    if speaker_name:
        conn.current_speaker = speaker_name
    else:
        conn.current_speaker = None

    if conn.need_bind:
        await check_bind_device(conn)
        return

    # Nếu số lượng từ xuất ra trong ngày đó lớn hơn số lượng từ giới hạn,
    if conn.max_output_size > 0:
        if check_device_output_limit(
            conn.headers.get("device-id"), conn.max_output_size
        ):
            await max_out_size(conn)
            return

    # Ở chế độ thủ công, nội dung đang phát sẽ không bị gián đoạn.
    if conn.client_is_speaking and conn.client_listen_mode != "manual":
        await handleAbortMessage(conn)

    # Thực hiện phân tích ý định trước bằng cách sử dụng nội dung văn bản thực tế
    intent_handled = await handle_user_intent(conn, actual_text)

    if intent_handled:
        # Nếu ý định đã được xử lý, cuộc trò chuyện sẽ không còn tiếp tục nữa
        return

    # Ý định chưa được xử lý, hãy tiếp tục luồng trò chuyện thông thường với nội dung văn bản thực tế
    await send_stt_message(conn, actual_text)

    # Sẵn sàng bắt đầu một phiên mới
    conn.client_abort = False

    conn.executor.submit(conn.chat, actual_text)


async def no_voice_close_connect(conn: "ConnectionHandler", have_voice):
    if have_voice:
        conn.last_activity_time = time.time() * 1000
        return
    # Chỉ thực hiện kiểm tra thời gian chờ nếu dấu thời gian đã được khởi tạo
    if conn.last_activity_time > 0.0:
        no_voice_time = time.time() * 1000 - conn.last_activity_time
        close_connection_no_voice_time = int(
            conn.config.get("close_connection_no_voice_time", 120)
        )
        if (
            not conn.close_after_chat
            and no_voice_time > 1000 * close_connection_no_voice_time
        ):
            conn.close_after_chat = True
            conn.client_abort = False
            end_prompt = conn.config.get("end_prompt", {})
            if end_prompt and end_prompt.get("enable", True) is False:
                conn.logger.bind(tag=TAG).info("结束对话，无需发送结束提示语")
                await conn.close()
                return
            prompt = end_prompt.get("prompt")
            if not prompt:
                prompt = 'Hãy mở đầu bằng "Thời gian trôi nhanh thật" và kết thúc bằng lời tạm biệt ấm áp, lưu luyến bằng tiếng Việt.'
            await startToChat(conn, prompt)


async def max_out_size(conn: "ConnectionHandler"):
    # Lời nhắc phát vượt quá số từ đầu ra tối đa
    conn.client_abort = False
    text = "Mình đang có chút việc bận. Hẹn bạn vào giờ này ngày mai nhé! Tạm biệt!"
    await send_stt_message(conn, text)
    file_path = "config/assets/max_output_size.wav"
    opus_packets = await audio_to_data(file_path)
    conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
    conn.close_after_chat = True


async def check_bind_device(conn: "ConnectionHandler"):
    if conn.bind_code:
        # Đảm bảo bind_code có 6 chữ số
        if len(conn.bind_code) != 6:
            conn.logger.bind(tag=TAG).error(f"无效的绑定码định dạng: {conn.bind_code}")
            text = "Mã liên kết không đúng định dạng. Vui lòng kiểm tra cấu hình."
            await send_stt_message(conn, text)
            return

        text = f"Vui lòng đăng nhập bảng quản lý, nhập mã {conn.bind_code} để liên kết thiết bị."
        await send_stt_message(conn, text)

        # Phát giai điệu
        music_path = "config/assets/bind_code.wav"
        opus_packets = await audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.FIRST, opus_packets, text))

        # Chơi từng số một
        for i in range(6):  # Đảm bảo chỉ chơi 6 chữ số
            try:
                digit = conn.bind_code[i]
                num_path = f"config/assets/bind_code/{digit}.wav"
                num_packets = await audio_to_data(num_path)
                conn.tts.tts_audio_queue.put((SentenceType.MIDDLE, num_packets, None))
            except Exception as e:
                conn.logger.bind(tag=TAG).error(f"播放数字âm thanhthất bại: {e}")
                continue
        conn.tts.tts_audio_queue.put((SentenceType.LAST, [], None))
    else:
        # Phát lời nhắc không liên kết
        conn.client_abort = False
        text = f"Không tìm thấy phiên bản thiết bị. Cấu hình đúng địa chỉ OTA rồi biên dịch lại firmware."
        await send_stt_message(conn, text)
        music_path = "config/assets/bind_not_found.wav"
        opus_packets = await audio_to_data(music_path)
        conn.tts.tts_audio_queue.put((SentenceType.LAST, opus_packets, text))
