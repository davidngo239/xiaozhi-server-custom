import os
import io
import wave
import uuid
import json
import time
import queue
import shutil
import asyncio
import tempfile
import traceback
import threading

from abc import ABC, abstractmethod
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType
from core.handle.receiveAudioHandle import startToChat
from core.handle.reportHandle import enqueue_asr_report
from core.utils.util import remove_punctuation_and_length
from core.handle.receiveAudioHandle import handleAudioMessage
from typing import Optional, Tuple, List, NamedTuple, TYPE_CHECKING


if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


class ASRProviderBase(ABC):
    def __init__(self):
        pass

    # Mở kênh âm thanh
    async def open_audio_channels(self, conn: "ConnectionHandler"):
        conn.asr_priority_thread = threading.Thread(
            target=self.asr_text_priority_thread, args=(conn,), daemon=True
        )
        conn.asr_priority_thread.start()

    # Xử lý âm thanh ASR theo thứ tự
    def asr_text_priority_thread(self, conn: "ConnectionHandler"):
        while not conn.stop_event.is_set():
            try:
                message = conn.asr_audio_queue.get(timeout=1)
                future = asyncio.run_coroutine_threadsafe(
                    handleAudioMessage(conn, message),
                    conn.loop,
                )
                future.result()
            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"xử lýASRvăn bảnthất bại: {str(e)}, loại: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue

    # nhận âm thanh
    async def receive_audio(
        self, conn: "ConnectionHandler", pcm_frame, audio_have_voice
    ):
        if conn.client_listen_mode == "manual":
            # Chế độ thủ công: lưu trữ âm thanh để nhận dạng ASR
            conn.asr_audio.append(pcm_frame)
        else:
            # Chế độ tự động/thời gian thực: phát hiện bằng VAD
            conn.asr_audio.append(pcm_frame)

            # Nếu không có giọng nói và không có âm thanh trước đó, hãy lưu một phần âm thanh vào bộ đệm
            if not audio_have_voice and not conn.client_have_voice:
                conn.asr_audio = conn.asr_audio[-10:]
                return

            # Quá trình nhận dạng được kích hoạt khi phát hiện thấy giọng nói dừng qua VAD ở chế độ tự động
            if (
                conn.asr.interface_type != InterfaceType.STREAM
                and conn.client_voice_stop
            ):
                # Sử dụng trực tiếp dữ liệu PCM trong asr_audio
                pcm_bytes = b"".join(conn.asr_audio)
                # Kiểm tra xem có đủ dữ liệu âm thanh hay không (1920 byte mỗi khung hình, khoảng 28800 byte cho 15 khung hình)
                if len(pcm_bytes) > 1920 * 15:
                    await self.handle_voice_stop(conn, [pcm_bytes])
                conn.reset_audio_states()

    # Xử lý các điểm dừng giọng nói
    async def handle_voice_stop(
        self, conn: "ConnectionHandler", asr_audio_task: List[bytes]
    ):
        """并行处理ASR和声纹识别"""
        try:
            total_start_time = time.monotonic()

            # Dữ liệu đã được PCM sử dụng trực tiếp
            pcm_data = asr_audio_task
            combined_pcm_data = b"".join(pcm_data)

            # Chuẩn bị trước dữ liệu WAV
            wav_data = None
            if conn.voiceprint_provider and combined_pcm_data:
                wav_data = self._pcm_to_wav(combined_pcm_data)

            # Xác định nhiệm vụ ASR
            asr_task = self.speech_to_text_wrapper(asr_audio_task, conn.session_id)

            if conn.voiceprint_provider and wav_data:
                voiceprint_task = conn.voiceprint_provider.identify_speaker(
                    wav_data, conn.session_id
                )
                # Chờ hai kết quả cùng lúc
                asr_result, voiceprint_result = await asyncio.gather(
                    asr_task, voiceprint_task, return_exceptions=True
                )
            else:
                asr_result = await asr_task
                voiceprint_result = None

            # Ghi lại kết quả nhận dạng - kiểm tra xem có bất thường không
            if isinstance(asr_result, Exception):
                logger.bind(tag=TAG).error(f"ASRnhận dạngthất bại: {asr_result}")
                raw_text = ""
            else:
                raw_text, _ = asr_result

            if isinstance(voiceprint_result, Exception):
                logger.bind(tag=TAG).error(
                    f"声纹nhận dạngthất bại: {voiceprint_result}"
                )
                speaker_name = ""
            else:
                speaker_name = voiceprint_result

            # Xác định loại kết quả ASR
            if isinstance(raw_text, dict):
                # định dạng dict được trả về bởi FunASR
                if speaker_name:
                    raw_text["speaker"] = speaker_name

                # Ghi lại kết quả nhận dạng
                if raw_text.get("language"):
                    logger.bind(tag=TAG).info(f"识别语言: {raw_text['language']}")
                if raw_text.get("emotion"):
                    logger.bind(tag=TAG).info(f"识别情绪: {raw_text['emotion']}")
                if raw_text.get("content"):
                    logger.bind(tag=TAG).info(f"识别文本: {raw_text['content']}")
                if speaker_name:
                    logger.bind(tag=TAG).info(f"识别说话人: {speaker_name}")

                # Chuyển đổi sang chuỗi JSON để sử dụng tiếp theo
                enhanced_text = json.dumps(raw_text, ensure_ascii=False)
                content_for_length_check = raw_text.get("content", "")
            else:
                # Văn bản thuần túy được trả về bởi các ASR khác
                if raw_text:
                    logger.bind(tag=TAG).info(f"识别文本: {raw_text}")
                if speaker_name:
                    logger.bind(tag=TAG).info(f"识别说话人: {speaker_name}")

                # Xây dựng chuỗi JSON chứa thông tin người nói
                enhanced_text = self._build_enhanced_text(raw_text, speaker_name)
                content_for_length_check = raw_text

            # Giám sát hiệu suất
            total_time = time.monotonic() - total_start_time
            logger.bind(tag=TAG).debug(f"总处理耗时: {total_time:.3f}s")

            # Kiểm tra độ dài văn bản
            text_len, _ = remove_punctuation_and_length(content_for_length_check)
            self.stop_ws_connection()

            if text_len > 0:
                audio_snapshot = asr_audio_task.copy()
                enqueue_asr_report(conn, enhanced_text, audio_snapshot)
                # Báo cáo sử dụng mô-đun tùy chỉnh
                await startToChat(conn, enhanced_text)
        except Exception as e:
            logger.bind(tag=TAG).error(f"xử lýgiọng nói停止thất bại: {e}")
            import traceback

            logger.bind(tag=TAG).debug(f"sự cố详情: {traceback.format_exc()}")

    def _build_enhanced_text(self, text: str, speaker_name: Optional[str]) -> str:
        """构建包含说话人信息的文本（仅用于纯文本ASR）"""
        if speaker_name and speaker_name.strip():
            return json.dumps(
                {"speaker": speaker_name, "content": text}, ensure_ascii=False
            )
        else:
            return text

    def _pcm_to_wav(self, pcm_data: bytes) -> bytes:
        """sẽPCMdữ liệu转换为WAVđịnh dạng"""
        if len(pcm_data) == 0:
            logger.bind(tag=TAG).warning("PCMdữ liệu为空 , không thể转换WAV")
            return b""

        # Đảm bảo độ dài dữ liệu bằng nhau (âm thanh 16 bit)
        if len(pcm_data) % 2 != 0:
            pcm_data = pcm_data[:-1]

        # Tạo tiêu đề tệp WAV
        wav_buffer = io.BytesIO()
        try:
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)  # đơn sắc
                wav_file.setsampwidth(2)  # 16 bit
                wav_file.setframerate(16000)  # Tốc độ lấy mẫu 16kHz
                wav_file.writeframes(pcm_data)

            wav_buffer.seek(0)
            wav_data = wav_buffer.read()

            return wav_data
        except Exception as e:
            logger.bind(tag=TAG).error(f"WAV转换thất bại: {e}")
            return b""

    def stop_ws_connection(self):
        pass

    async def close(self):
        pass

    class AudioArtifacts(NamedTuple):
        pcm_frames: List[bytes]
        """PCM音频帧列表"""
        pcm_bytes: bytes
        """合并后的PCMâm thanh字节dữ liệu"""
        file_path: Optional[str]
        """WAV文件路径"""
        temp_path: Optional[str]
        """临时WAV文件路径"""

    def get_current_artifacts(self) -> Optional["ASRProviderBase.AudioArtifacts"]:
        return self._current_artifacts

    def requires_file(self) -> bool:
        """是否需要文件输入"""
        return False

    def prefers_temp_file(self) -> bool:
        """是否优先使用临时文件"""
        return False

    def build_temp_file(self, pcm_bytes: bytes) -> Optional[str]:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
            with wave.open(temp_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(pcm_bytes)
            return temp_path
        except Exception as e:
            logger.bind(tag=TAG).error(f"临khiâm thanh文件生成thất bại: {e}")
            return None

    def save_audio_to_file(self, pcm_data: List[bytes], session_id: str) -> str:
        """PCMdữ liệulưu为WAV文件"""
        module_name = __name__.split(".")[-1]
        file_name = f"asr_{module_name}_{session_id}_{uuid.uuid4()}.wav"
        file_path = os.path.join(self.output_dir, file_name)

        with wave.open(file_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 2 bytes = 16-bit
            wf.setframerate(16000)
            wf.writeframes(b"".join(pcm_data))

        return file_path

    async def speech_to_text_wrapper(
        self, pcm_data: List[bytes], session_id: str
    ) -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        temp_path = None
        try:
            combined_pcm_data = b"".join(pcm_data)

            free_space = shutil.disk_usage(self.output_dir).free
            if free_space < len(combined_pcm_data) * 2:
                raise OSError("Không đủ dung lượng ổ đĩa")

            if self.requires_file() and self.prefers_temp_file():
                temp_path = self.build_temp_file(combined_pcm_data)

            if (hasattr(self, "delete_audio_file") and not self.delete_audio_file) or (
                self.requires_file() and not self.prefers_temp_file()
            ):
                file_path = self.save_audio_to_file(pcm_data, session_id)

            if len(combined_pcm_data) == 0:
                artifacts = None
            else:
                artifacts = ASRProviderBase.AudioArtifacts(
                    pcm_frames=pcm_data,
                    pcm_bytes=combined_pcm_data,
                    file_path=file_path,
                    temp_path=temp_path,
                )

            text, _ = await self.speech_to_text(pcm_data, session_id, artifacts)
            return text, file_path
        except OSError as e:
            logger.bind(tag=TAG).error(f"文件操作Lỗi: {e}")
            return None, None
        except Exception as e:
            logger.bind(tag=TAG).error(f"giọng nóinhận dạngthất bại: {e}")
            return None, None
        finally:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
                if (
                    hasattr(self, "delete_audio_file")
                    and self.delete_audio_file
                    and file_path
                    and os.path.exists(file_path)
                ):
                    os.remove(file_path)
            except Exception as e:
                logger.bind(tag=TAG).error(f"文件清理thất bại: {e}")

    @abstractmethod
    async def speech_to_text(
        self,
        opus_data: List[bytes],
        session_id: str,
        artifacts: Optional[AudioArtifacts] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """sẽgiọng nóidữ liệu转换为văn bản

        :param opus_data: 输入的Opusâm thanhdữ liệu
        :param session_id: sẽ话ID
        :param artifacts: âm thanh工件 , 包含PCMdữ liệu、文件路径等
        :return: nhận dạngkết quảvăn bản和文件路径（如果有）
        """
        pass
