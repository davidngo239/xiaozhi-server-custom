"""
TTS上报功能đã集成到ConnectionHandler类trong.

上报功能包括:
1. 每个kết nối对象拥有自己的上报队列和xử lý线程
2. 上报线程的生命周期与kết nối对象绑定
3. 使用ConnectionHandler.enqueue_tts_report方法tiến hành上报

cụ thể实现请参考core/connection.pytrong的相关代码.
"""

import time
import json
import opuslib_next
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

from config.manage_api_client import report as manage_report

TAG = __name__


async def report(conn: "ConnectionHandler", chat_type, text, audio_data, report_time):
    """thực thi聊天记录上报操作

    Args:
        conn: kết nối对象
        chat_type: 上报loại , 1为người dùng(ASR/PCM) , 2为智能体(TTS/Opus) , 3为công cụgọi
        text: 合成văn bản
        audio_data: âm thanhdữ liệu（chat_type=1khi为PCMđịnh dạng , chat_type=2khi为Opusđịnh dạng）
        report_time: 上报khi间
    """
    try:
        if audio_data:
            if chat_type == 1:
                wav_data = pcm_to_wav(conn, audio_data)
            elif chat_type == 2:
                wav_data = opus_to_wav(conn, audio_data)
            else:
                wav_data = None
        else:
            wav_data = None
        # Thực hiện báo cáo không đồng bộ
        await manage_report(
            mac_address=conn.device_id,
            session_id=conn.session_id,
            chat_type=chat_type,
            content=text,
            audio=wav_data,
            report_time=report_time,
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"聊天记录上报thất bại: {e}")


def pcm_to_wav(conn: "ConnectionHandler", pcm_data):
    """sẽPCMdữ liệu转换为WAVđịnh dạng的字节流

    Args:
        conn: kết nối对象
        pcm_data: PCMâm thanhdữ liệu（可能是列表或bytes）

    Returns:
        bytes: WAVđịnh dạng的âm thanhdữ liệu
    """
    try:
        # Xử lý dữ liệu PCM có thể là danh sách hoặc byte
        if isinstance(pcm_data, list):
            pcm_data_bytes = b"".join(pcm_data)
        else:
            pcm_data_bytes = pcm_data

        if not pcm_data_bytes:
            raise ValueError("Không có dữ liệu PCM hợp lệ")

        # Tạo tiêu đề tệp WAV
        num_samples = len(pcm_data_bytes) // 2  # 16-bit samples

        # tiêu đề tập tin WAV
        wav_header = bytearray()
        wav_header.extend(b"RIFF")  # ChunkID
        wav_header.extend((36 + len(pcm_data_bytes)).to_bytes(4, "little"))  # ChunkSize
        wav_header.extend(b"WAVE")  # Format
        wav_header.extend(b"fmt ")  # Subchunk1ID
        wav_header.extend((16).to_bytes(4, "little"))  # Subchunk1Size
        wav_header.extend((1).to_bytes(2, "little"))  # AudioFormat (PCM)
        wav_header.extend((1).to_bytes(2, "little"))  # NumChannels
        wav_header.extend((16000).to_bytes(4, "little"))  # SampleRate
        wav_header.extend((32000).to_bytes(4, "little"))  # ByteRate
        wav_header.extend((2).to_bytes(2, "little"))  # BlockAlign
        wav_header.extend((16).to_bytes(2, "little"))  # BitsPerSample
        wav_header.extend(b"data")  # Subchunk2ID
        wav_header.extend(len(pcm_data_bytes).to_bytes(4, "little"))  # Subchunk2Size

        # Trả về dữ liệu WAV hoàn chỉnh
        return bytes(wav_header) + pcm_data_bytes
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"PCM转WAVthất bại: {e}", exc_info=True)
        raise


def opus_to_wav(conn: "ConnectionHandler", opus_data):
    """sẽOpusdữ liệu转换为WAVđịnh dạng的字节流

    Args:
        conn: kết nối对象
        opus_data: Opusâm thanhdữ liệu（可能是列表或bytes）

    Returns:
        bytes: WAVđịnh dạng的âm thanhdữ liệu
    """
    decoder = None
    try:
        decoder = opuslib_next.Decoder(16000, 1)
        pcm_data = []

        if isinstance(opus_data, list):
            for opus_packet in opus_data:
                try:
                    pcm_frame = decoder.decode(opus_packet, 960)
                    pcm_data.append(pcm_frame)
                except opuslib_next.OpusError as e:
                    conn.logger.bind(tag=TAG).error(f"Opus解码Lỗi: {e}", exc_info=True)
        elif isinstance(opus_data, bytes):
            pcm_frame = decoder.decode(opus_data, 960)
            pcm_data.append(pcm_frame)

        if not pcm_data:
            raise ValueError("Không có dữ liệu âm thanh hợp lệ")

        pcm_data_bytes = b"".join(pcm_data)

        wav_header = bytearray()
        wav_header.extend(b"RIFF")
        wav_header.extend((36 + len(pcm_data_bytes)).to_bytes(4, "little"))
        wav_header.extend(b"WAVE")
        wav_header.extend(b"fmt ")
        wav_header.extend((16).to_bytes(4, "little"))
        wav_header.extend((1).to_bytes(2, "little"))
        wav_header.extend((1).to_bytes(2, "little"))
        wav_header.extend((16000).to_bytes(4, "little"))
        wav_header.extend((32000).to_bytes(4, "little"))
        wav_header.extend((2).to_bytes(2, "little"))
        wav_header.extend((16).to_bytes(2, "little"))
        wav_header.extend(b"data")
        wav_header.extend(len(pcm_data_bytes).to_bytes(4, "little"))

        return bytes(wav_header) + pcm_data_bytes
    finally:
        if decoder is not None:
            try:
                del decoder
            except Exception as e:
                conn.logger.bind(tag=TAG).debug(f"释放decoder资源时出错: {e}")


def enqueue_tts_report(conn: "ConnectionHandler", text, opus_data):
    """sẽTTSdữ liệu加入上报队列

    Args:
        conn: kết nối对象
        text: 合成văn bản
        opus_data: opusâm thanhdữ liệu
    """
    if not conn.read_config_from_api or conn.need_bind or not conn.report_tts_enable:
        return
    if conn.chat_history_conf == 0:
        return
    try:
        # Sử dụng hàng đợi các đối tượng kết nối, truyền văn bản và dữ liệu nhị phân thay vì đường dẫn tệp
        if conn.chat_history_conf == 2:
            conn.report_queue.put((2, text, opus_data, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"TTSdữ liệuđã加入上报队列: {conn.device_id}, âm thanh大小: {len(opus_data)} "
            )
        else:
            conn.report_queue.put((2, text, None, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"TTSdữ liệuđã加入上报队列: {conn.device_id}, 不上报âm thanh"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"加入TTS上报队列thất bại: {text}, {e}")


def enqueue_tool_report(
    conn: "ConnectionHandler",
    tool_name: str,
    tool_input: dict,
    tool_result: str = None,
    report_tool_call: bool = True,
):
    """sẽcông cụgọidữ liệu加入上报队列

    Args:
        conn: kết nối对象
        tool_name: công cụ名称
        tool_input: công cụ输入tham số
        tool_result: công cụthực thikết quả（可选）
        report_tool_call: 是否上报công cụgọi本身 , 默认True; 仅上报kết quảkhi设为False
    """
    if not conn.read_config_from_api or conn.need_bind:
        return
    if conn.chat_history_conf == 0:
        return

    try:
        timestamp = int(time.time() * 1000)

        # Xây dựng nội dung cuộc gọi công cụ
        if report_tool_call:
            tool_text = json.dumps(
                [
                    {
                        "type": "tool",
                        "text": f"{tool_name}({json.dumps(tool_input, ensure_ascii=False)})",
                    }
                ]
            )
            conn.report_queue.put((3, tool_text, None, timestamp))

        # Xây dựng nội dung kết quả công cụ
        if tool_result:
            result_display = f'{{"result":"{str(tool_result)}"}}'
            result_content = json.dumps(
                [{"type": "tool_result", "text": result_display}], ensure_ascii=False
            )
            conn.report_queue.put((3, result_content, None, timestamp + 1))
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"加入công cụ上报队列thất bại: {e}")


def enqueue_asr_report(conn: "ConnectionHandler", text, opus_data):
    """sẽASRdữ liệu加入上报队列

    Args:
        conn: kết nối对象
        text: 合成văn bản
        opus_data: opusâm thanhdữ liệu
    """
    if not conn.read_config_from_api or conn.need_bind or not conn.report_asr_enable:
        return
    if conn.chat_history_conf == 0:
        return
    try:
        # Sử dụng hàng đợi các đối tượng kết nối, truyền văn bản và dữ liệu nhị phân thay vì đường dẫn tệp
        if conn.chat_history_conf == 2:
            conn.report_queue.put((1, text, opus_data, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"ASRdữ liệuđã加入上报队列: {conn.device_id}, âm thanh大小: {len(opus_data)} "
            )
        else:
            conn.report_queue.put((1, text, None, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"ASRdữ liệuđã加入上报队列: {conn.device_id}, 不上报âm thanh"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).debug(f"加入ASR上报队列thất bại: {text}, {e}")
