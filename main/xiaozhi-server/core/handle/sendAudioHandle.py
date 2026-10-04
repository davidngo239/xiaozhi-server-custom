import json
import time
import asyncio
import opuslib_next
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils import textUtils
from core.utils.util import audio_to_data
from core.providers.tts.dto.dto import SentenceType
from core.utils.audioRateController import AudioRateController

TAG = __name__
# Thời lượng khung âm thanh (mili giây)
AUDIO_FRAME_DURATION = 60
# Số lượng gói được đệm trước, được gửi trực tiếp để giảm độ trễ
PRE_BUFFER_COUNT = 5


async def sendAudioMessage(
    conn: "ConnectionHandler", sentenceType, audios, text, sentence_id=None
):
    # Bỏ qua phần âm thanh còn sót lại của câu cũ
    if sentence_id is not None and sentence_id != conn.sentence_id:
        return

    if conn.tts.tts_audio_first_sentence:
        conn.logger.bind(tag=TAG).info(f"发送第一段语音: {text}")
        conn.tts.tts_audio_first_sentence = False

    if sentenceType == SentenceType.FIRST:
        # Các tin nhắn tiếp theo của cùng một câu sẽ được thêm vào hàng đợi kiểm soát luồng và các tin nhắn khác sẽ được gửi ngay lập tức.
        if (
            hasattr(conn, "audio_rate_controller")
            and conn.audio_rate_controller
            and getattr(conn, "audio_flow_control", {}).get("sentence_id")
            == conn.sentence_id
        ):
            conn.audio_rate_controller.add_message(
                lambda: send_tts_message(conn, "sentence_start", text)
            )
        else:
            # Câu hoặc bộ điều khiển luồng mới không được khởi tạo và sẽ được gửi ngay lập tức.
            await send_tts_message(conn, "sentence_start", text)

    await sendAudio(conn, audios)
    # Gửi tin nhắn bắt đầu câu
    if sentenceType is not SentenceType.MIDDLE:
        conn.logger.bind(tag=TAG).info(f"gửiâm thanhthông điệp: {sentenceType}, {text}")

    # Gửi tin nhắn kết thúc (nếu là văn bản cuối cùng)
    # Cuộc gọi cần duy trì trạng thái nói
    if not conn.calling and sentenceType == SentenceType.LAST:
        await send_tts_message(conn, "stop", None)
        if conn.close_after_chat:
            await conn.close()


async def _wait_for_audio_completion(conn: "ConnectionHandler"):
    """
    chờâm thanh队列清空并chờ预缓冲包播放hoàn tất

    Args:
        conn: kết nối对象
    """
    if hasattr(conn, "audio_rate_controller") and conn.audio_rate_controller:
        rate_controller = conn.audio_rate_controller
        send_delay_ms = conn.config.get("tts_audio_send_delay", 0)
        conn.logger.bind(tag=TAG).debug(
            f"等待音频发送完成，队列中还有 {len(rate_controller.queue)} 个包"
        )
        await rate_controller.queue_empty_event.wait()

        if send_delay_ms > 0:
            # Nhịp điệu tùy chỉnh: đợi khung hình cuối cùng phát xong trên máy khách
            playback_time = 2 * rate_controller.interval_ms / 1000.0
        else:
            # Nhịp độ mặc định: N khung hình đầu tiên của bộ đệm trước đã được phát trực tiếp và bạn cần đợi chúng phát lại hoàn tất
            playback_time = (
                (PRE_BUFFER_COUNT + 2) * rate_controller.interval_ms / 1000.0
            )
        await asyncio.sleep(playback_time)

        conn.logger.bind(tag=TAG).debug("音频发送完成")


async def _send_to_mqtt_gateway(
    conn: "ConnectionHandler", opus_packet, timestamp, sequence
):
    """
    gửi带16字节头部的opusdữ liệu包给mqtt_gateway , 同khibộ nhớ đệmâm thanh用于AECxử lý
    Args:
        conn: kết nối对象
        opus_packet: opusdữ liệu包
        timestamp: khi间戳
        sequence: 序列号
    """
    # Nếu AEC phía máy chủ được bật, hãy lưu dữ liệu PCM vào bộ đệm để xử lý AEC tiếp theo
    if conn.client_aec and timestamp > 0:
        if not hasattr(conn, "aec_audio_cache"):
            conn.aec_audio_cache = {}
            conn.aec_audio_cache_time = {}
            conn._send_opus_decoder = opuslib_next.Decoder(16000, 1)
        # Bộ nhớ đệm sau khi giải mã opus sang PCM
        pcm_data = conn._send_opus_decoder.decode(bytes(opus_packet), 960)
        conn.aec_audio_cache[timestamp] = bytes(pcm_data)
        conn.aec_audio_cache_time[timestamp] = time.time()

    # Thêm tiêu đề 16 byte vào gói opus
    header = bytearray(16)
    header[0] = 1  # type
    header[2:4] = len(opus_packet).to_bytes(2, "big")  # payload length
    header[4:8] = sequence.to_bytes(4, "big")  # sequence
    header[8:12] = timestamp.to_bytes(4, "big")  # Dấu thời gian
    header[12:16] = len(opus_packet).to_bytes(4, "big")  # chiều dài tác phẩm

    # Gửi gói hoàn chỉnh bao gồm các tiêu đề
    complete_packet = bytes(header) + opus_packet
    await conn.websocket.send(complete_packet)


async def sendAudio(
    conn: "ConnectionHandler", audios, frame_duration=AUDIO_FRAME_DURATION
):
    """
    gửiâm thanh包 , 使用 AudioRateController tiến hành精确的流量控制

    Args:
        conn: kết nối对象
        audios: 单个opus包(bytes) 或 opus包列表
        frame_duration: 帧khi长（毫秒） , 默认使用全局常量AUDIO_FRAME_DURATION
    """
    if audios is None or len(audios) == 0:
        return

    send_delay_ms = conn.config.get("tts_audio_send_delay", 0)
    is_single_packet = isinstance(audios, bytes)

    # Khởi tạo hoặc nhận RateController
    rate_controller, flow_control = _get_or_create_rate_controller(
        conn, frame_duration, is_single_packet, send_delay_ms
    )

    # Chuyển đổi thống nhất để xử lý danh sách
    audio_list = [audios] if is_single_packet else audios

    # Gửi gói âm thanh
    await _send_audio_with_rate_control(
        conn, audio_list, rate_controller, flow_control, send_delay_ms
    )


def _get_or_create_rate_controller(
    conn: "ConnectionHandler", frame_duration, is_single_packet, send_delay_ms=0
):
    """
    lấy或tạo RateController 和 flow_control

    Args:
        conn: kết nối对象
        frame_duration: 帧khi长
        is_single_packet: 是否单包模式（True: TTS流式单包, False: 批量包）
        send_delay_ms: 自定义gửi间隔（毫秒）.

    Returns:
        (rate_controller, flow_control)
    """
    # Kiểm tra xem bộ điều khiển có cần được thiết lập lại không
    need_reset = False

    if not hasattr(conn, "audio_rate_controller"):
        # Bộ điều khiển không tồn tại và cần được tạo
        need_reset = True
    else:
        rate_controller = conn.audio_rate_controller

        # Tác vụ gửi nền đã bị dừng và cần được đặt lại.
        if (
            not rate_controller.pending_send_task
            or rate_controller.pending_send_task.done()
        ):
            need_reset = True
        # Khi câu_id thay đổi, nó cần được đặt lại
        elif (
            getattr(conn, "audio_flow_control", {}).get("sentence_id")
            != conn.sentence_id
        ):
            need_reset = True

    if need_reset:
        # Tạo hoặc nhận rate_controller
        if not hasattr(conn, "audio_rate_controller"):
            conn.audio_rate_controller = AudioRateController(
                frame_duration, send_delay=send_delay_ms
            )
        else:
            conn.audio_rate_controller.reset()

        # khởi tạo flow_control
        conn.audio_flow_control = {
            "packet_count": 0,
            "sequence": 0,
            "sentence_id": conn.sentence_id,
        }

        # Bắt đầu vòng lặp gửi nền
        _start_background_sender(
            conn, conn.audio_rate_controller, conn.audio_flow_control
        )

    return conn.audio_rate_controller, conn.audio_flow_control


def _start_background_sender(conn: "ConnectionHandler", rate_controller, flow_control):
    """
    khởi động后台gửi循环tác vụ

    Args:
        conn: kết nối对象
        rate_controller: 速率控制器
        flow_control: 流控trạng thái
    """

    async def send_callback(packet):
        # Kiểm tra xem nó có nên hủy bỏ không
        if conn.client_abort:
            raise asyncio.CancelledError("Máy khách đã hủy")

        conn.last_activity_time = time.time() * 1000
        await _do_send_audio(conn, packet, flow_control)

    # Sử dụng start_sending để bắt đầu vòng lặp nền
    rate_controller.start_sending(send_callback)


async def _send_audio_with_rate_control(
    conn: "ConnectionHandler", audio_list, rate_controller, flow_control, send_delay_ms
):
    """
    使用 rate_controller gửiâm thanh包

    Args:
        conn: kết nối对象
        audio_list: âm thanh包列表
        rate_controller: 速率控制器
        flow_control: 流控trạng thái
        send_delay_ms: 自定义gửi间隔（毫秒）.
    """
    for packet in audio_list:
        if conn.client_abort:
            return

        conn.last_activity_time = time.time() * 1000

        if send_delay_ms > 0:
            # Chế độ nhịp điệu tùy chỉnh: tất cả các gói trong hàng đợi sẽ được gửi theo send_delay (tắt tính năng đệm trước)
            rate_controller.add_audio(packet)
        else:
            # Chế độ nhịp mặc định (60ms/gói): N gói đầu tiên được đệm trước và gửi trực tiếp, các hàng đợi tiếp theo được tác vụ nền gửi theo nhịp interval_ms.
            if flow_control["packet_count"] < PRE_BUFFER_COUNT:
                await _do_send_audio(conn, packet, flow_control)
            else:
                rate_controller.add_audio(packet)


async def _do_send_audio(conn: "ConnectionHandler", opus_packet, flow_control):
    """
    执行实际的音频发送
    """
    packet_index = flow_control.get("packet_count", 0)
    sequence = flow_control.get("sequence", 0)

    if conn.conn_from_mqtt_gateway:
        # Tính dấu thời gian (dựa trên vị trí phát lại)
        start_time = time.time()
        timestamp = int(start_time * 1000) % (2**32)
        await _send_to_mqtt_gateway(conn, opus_packet, timestamp, sequence)
    else:
        # Gửi gói opus trực tiếp
        await conn.websocket.send(opus_packet)

    # Cập nhật trạng thái kiểm soát luồng
    flow_control["packet_count"] = packet_index + 1
    flow_control["sequence"] = sequence + 1


async def send_tts_message(conn: "ConnectionHandler", state, text=None):
    """gửi TTS trạng tháithông điệp"""
    if text is None and state == "sentence_start":
        return
    message = {"type": "tts", "state": state, "session_id": conn.session_id}
    if text is not None:
        message["text"] = textUtils.check_emoji(text)

    # Trò chơi TTS kết thúc
    if state == "stop":
        # Lưu câu_id hiện tại để đánh giá tiếp theo cho dù đó là vòng hiện tại.
        current_sentence_id = conn.sentence_id
        # Phát giai điệu
        tts_notify = conn.config.get("enable_stop_tts_notify", False)
        if tts_notify:
            stop_tts_notify_voice = conn.config.get(
                "stop_tts_notify_voice", "config/assets/tts_notify.mp3"
            )
            audios = await audio_to_data(stop_tts_notify_voice, is_opus=True)
            await sendAudio(conn, audios)
        # Đợi tất cả các gói âm thanh được gửi
        await _wait_for_audio_completion(conn)

        # Kiểm tra xem đây có phải là vòng hiện tại không
        if current_sentence_id != conn.sentence_id:
            return

        # Dừng vòng gửi âm thanh (chỉ được gọi khi bộ truyền phát đã được khởi tạo)
        if hasattr(conn, "audio_rate_controller") and conn.audio_rate_controller:
            conn.audio_rate_controller.stop_sending()
        conn.clearSpeakStatus()

    # Gửi thông điệp cho máy khách
    await conn.websocket.send(json.dumps(message))


async def send_stt_message(conn: "ConnectionHandler", text):
    """gửi STT trạng tháithông điệp"""
    end_prompt_str = conn.config.get("end_prompt", {}).get("prompt")
    if end_prompt_str and end_prompt_str == text:
        await send_tts_message(conn, "start")
        return

    # Phân tích định dạng JSON và trích xuất nội dung lời nói thực tế của người dùng
    display_text = text
    try:
        # Cố gắng phân tích định dạng JSON
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                # Nếu nó ở định dạng JSON chứa thông tin người nói thì chỉ hiển thị phần nội dung.
                display_text = parsed_data["content"]
                # Lưu thông tin người nói vào đối tượng conn
                if "speaker" in parsed_data:
                    conn.current_speaker = parsed_data["speaker"]
    except (json.JSONDecodeError, TypeError):
        # Nếu nó không ở định dạng JSON, hãy sử dụng trực tiếp văn bản gốc.
        display_text = text
    stt_text = textUtils.get_string_no_punctuation_or_emoji(display_text)
    await conn.websocket.send(
        json.dumps({"type": "stt", "text": stt_text, "session_id": conn.session_id})
    )
    await send_tts_message(conn, "start")
    # Sau khi gửi tin nhắn bắt đầu, trạng thái máy khách sẽ ở trạng thái nói chuyện và trạng thái máy chủ sẽ được đồng bộ hóa.
    conn.client_is_speaking = True


async def send_display_message(conn: "ConnectionHandler", text):
    """gửi纯显示thông điệp"""
    message = {"type": "stt", "text": text, "session_id": conn.session_id}
    await conn.websocket.send(json.dumps(message))
