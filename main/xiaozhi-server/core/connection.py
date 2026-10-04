import os
import sys
import copy
import json
import re
import uuid
import time
import queue
import asyncio
import threading
import traceback
import subprocess
import websockets
import opuslib_next
import numpy as np

from core.utils.util import (
    extract_json_from_string,
    check_vad_update,
    check_asr_update,
    filter_sensitive_info,
)
from typing import Dict, Any
from collections import deque
from core.utils.modules_initialize import (
    initialize_modules,
    initialize_tts,
    initialize_asr,
)
from core.handle.reportHandle import report, enqueue_tool_report
from core.providers.tts.default import DefaultTTS
from concurrent.futures import ThreadPoolExecutor
from core.utils.dialogue import Message, Dialogue
from core.providers.asr.dto.dto import InterfaceType
from core.handle.textHandle import handleTextMessage
from core.providers.tools.unified_tool_handler import UnifiedToolHandler
from plugins_func.loadplugins import auto_import_modules
from plugins_func.register import (
    Action,
    ActionResponse,
    all_function_registry,
    module_func_map,
)
from core.auth import AuthenticationError
from config.config_loader import get_private_config_from_api
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from config.logger import setup_logging, build_module_string, create_connection_logger
from config.manage_api_client import (
    DeviceNotFoundException,
    DeviceBindException,
    generate_and_save_chat_title,
)
from core.utils.prompt_manager import PromptManager
from core.utils.voiceprint_provider import VoiceprintProvider
from core.utils.util import get_system_error_response
from core.utils import textUtils


TAG = __name__

auto_import_modules("plugins_func.functions")


class TTSException(RuntimeError):
    pass


# định nghĩa công cụ ảo direct_answer
# Đây là cơ chế định tuyến, không phải công cụ thật: thay lựa chọn có gọi công cụ hay không bằng lựa chọn gọi công cụ nào, giúp mô hình nhỏ tránh gọi nhầm công cụ thật.
DIRECT_ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": "direct_answer",
        "description": "Dùng để trả lời trực tiếp khi yêu cầu không phù hợp với công cụ nào khác. Đặt toàn bộ câu trả lời vào tham số response.",
        "parameters": {
            "type": "object",
            "properties": {
                "response": {
                    "type": "string",
                    "description": "Toàn bộ nội dung trả lời người dùng",
                },
            },
            "required": ["response"],
        },
    },
}


class ConnectionHandler:
    def __init__(
        self,
        config: Dict[str, Any],
        _vad,
        _asr,
        _llm,
        _memory,
        _intent,
        server=None,
    ):
        self.common_config = config
        self.config = copy.deepcopy(config)
        self.session_id = str(uuid.uuid4())
        self.logger = setup_logging()
        self.server = server  # Lưu một tham chiếu đến phiên bản máy chủ

        self.need_bind = False  # Bạn có cần liên kết thiết bị không?
        self.bind_completed_event = asyncio.Event()
        self.bind_code = None  # Mã xác minh cho thiết bị bị ràng buộc
        self.last_bind_prompt_time = 0  # Dấu thời gian (giây) của lần cuối cùng lời nhắc liên kết được phát
        self.bind_prompt_interval = 60  # Khoảng thời gian phát lại lời nhắc ràng buộc (giây)

        self.read_config_from_api = self.config.get("read_config_from_api", False)

        self.websocket: websockets.ServerConnection | None = None
        self.headers = None
        self.device_id = None
        self.client_ip = None
        self.prompt = None
        self.welcome_msg = None
        self.max_output_size = 0
        self.chat_history_conf = 0
        self.audio_format = "opus"
        self.sample_rate = 24000  # Tốc độ lấy mẫu mặc định, được cập nhật động từ tin nhắn xin chào của khách hàng

        # Trạng thái của máy khách
        self.client_abort = False
        self.client_is_speaking = False
        self.client_listen_mode = "auto"
        self.client_aec = False  # AEC phía máy chủ có được bật hay không

        # Các tác vụ liên quan đến luồng
        self.loop = None  # Nhận vòng lặp sự kiện đang chạy trong hand_connection
        self.stop_event = threading.Event()
        self.executor = ThreadPoolExecutor(max_workers=5)

        # Tạo nhóm luồng để gửi báo cáo
        self.report_queue = queue.Queue()
        self.report_thread = None
        # Trong tương lai, bạn có thể điều chỉnh báo cáo asr và tts bằng cách sửa đổi mục này. Hiện tại, cả hai đều được bật theo mặc định.
        self.report_asr_enable = self.read_config_from_api
        self.report_tts_enable = self.read_config_from_api

        # thành phần phụ thuộc
        self.vad = None
        self.asr = None
        self.tts = None
        self._asr = _asr
        self._vad = _vad
        self.llm = _llm
        self.memory = _memory
        self.intent = _intent

        # Quản lý nhận dạng giọng nói riêng cho từng kết nối
        self.voiceprint_provider = None

        # các biến liên quan đến vad
        self.client_audio_buffer = bytearray()
        self.client_have_voice = False
        self.client_voice_window = deque(maxlen=5)
        self.first_activity_time = 0.0  # Thời gian ghi lại hoạt động đầu tiên (mili giây)
        self.last_activity_time = 0.0  # Dấu thời gian hoạt động thống nhất (mili giây)
        self.vad_last_voice_time = 0.0  # Ghi lại thời gian người dùng nói lần cuối (mili giây)
        self.client_voice_stop = False
        self.last_is_voice = False

        # biến liên quan đến asr
        # Vì ASR cục bộ công khai có thể được sử dụng trong quá trình triển khai thực tế nên các biến không thể hiển thị với ASR công khai.
        # Do đó, các biến liên quan đến ASR cần được xác định ở đây, đó là các biến riêng tư của kết nối.
        self.asr_audio = []  # Lưu trữ danh sách khung PCM để VAD và ASR chia sẻ
        self.asr_audio_queue = queue.Queue()
        self.current_speaker = None  # Lưu trữ loa hiện tại
        self.introduced_speakers = set()  # Các diễn giả được “giới thiệu lần đầu” được kiểm soát chỉ được ghi tên ở vòng đầu tiên.
        self.system_introduced_speakers = (
            set()
        )  # Đối với những người phát biểu đã được đưa danh tính vào hệ thống, danh tính hệ thống sẽ chỉ xuất hiện ở vòng đầu tiên.

        # các biến liên quan đến llm
        self.dialogue = Dialogue()

        # các biến liên quan đến tts
        self.sentence_id = None
        # Xử lý phản hồi TTS không có văn bản được trả về
        self.tts_MessageText = ""

        # các biến liên quan đến iot
        self.iot_descriptors = {}
        self.func_handler = None

        self.cmd_exit = self.config["exit_commands"]

        # Có đóng kết nối sau khi trò chuyện kết thúc hay không
        self.close_after_chat = False
        self.load_function_plugin = False
        self.intent_type = "nointent"

        self.timeout_seconds = (
            int(self.config.get("close_connection_no_voice_time", 120)) + 60
        )  # Thêm 60 giây vào lần đóng đầu tiên ban đầu để thực hiện lần đóng thứ hai
        self.timeout_task = None

        # {"mcp":true} có nghĩa là bật chức năng MCP
        self.features = None

        # Đánh dấu xem kết nối có phải từ MQTT hay không
        self.conn_from_mqtt_gateway = False

        # Khởi tạo trình quản lý văn bản nhắc nhở
        self.prompt_manager = PromptManager(self.config, self.logger)

        # Khởi tạo trạng thái cuộc gọi
        self.calling = False
        # Đánh dấu xem chế độ trả lời cuộc gọi hiện tại có
        self.incoming_call = None

    async def handle_connection(self, ws: websockets.ServerConnection):
        try:
            # Nhận vòng lặp sự kiện đang chạy (phải ở trong bối cảnh không đồng bộ)
            self.loop = asyncio.get_running_loop()

            # Nhận và xác minh tiêu đề
            self.headers = dict(ws.request.headers)
            real_ip = self.headers.get("x-real-ip") or self.headers.get(
                "x-forwarded-for"
            )
            if real_ip:
                self.client_ip = real_ip.split(",")[0].strip()
            else:
                self.client_ip = ws.remote_address[0]
            self.logger.bind(tag=TAG).info(
                f"{self.client_ip} conn - Headers: {self.headers}"
            )

            self.device_id = self.headers.get("device-id", None)

            # Chứng nhận đã được thông qua, tiếp tục xử lý
            self.websocket = ws

            # Kiểm tra xem có đến từ kết nối MQTT không
            request_path = ws.request.path
            self.conn_from_mqtt_gateway = request_path.endswith("?from=mqtt_gateway")
            if self.conn_from_mqtt_gateway:
                self.logger.bind(tag=TAG).info("kết nối来自:MQTT网关")

            # Khởi tạo dấu thời gian hoạt động
            self.first_activity_time = time.time() * 1000
            self.last_activity_time = time.time() * 1000

            # Bắt đầu nhiệm vụ kiểm tra thời gian chờ
            self.timeout_task = asyncio.create_task(self._check_timeout())

            # Bắt đầu tác vụ dọn dẹp bộ đệm AEC
            self._aec_cache_cleanup_task = asyncio.create_task(
                self._check_aec_cache_expiry()
            )

            self.welcome_msg = self.config["xiaozhi"]
            self.welcome_msg["session_id"] = self.session_id

            # Đọc tốc độ mẫu từ cấu hình
            self.sample_rate = self.welcome_msg["audio_params"]["sample_rate"]
            self.logger.bind(tag=TAG).info(
                f"cấu hình输出âm thanh采样率为: {self.sample_rate}"
            )

            # Khởi tạo cấu hình và các thành phần ở chế độ nền (hoàn toàn không chặn vòng lặp chính)
            asyncio.create_task(self._background_initialize())

            try:
                async for message in self.websocket:
                    await self._route_message(message)
            except websockets.exceptions.ConnectionClosed:
                self.logger.bind(tag=TAG).info("máy khách断开kết nối")

        except AuthenticationError as e:
            self.logger.bind(tag=TAG).error(f"Authentication failed: {str(e)}")
            return
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.bind(tag=TAG).error(f"Connection error: {str(e)}-{stack_trace}")
            return
        finally:
            try:
                await self._save_and_close(ws)
            except Exception as final_error:
                self.logger.bind(tag=TAG).error(f"最终清理时出错: {final_error}")
                # Đảm bảo đóng kết nối ngay cả khi việc lưu bộ nhớ không thành công
                try:
                    await self.close(ws)
                except Exception as close_error:
                    self.logger.bind(tag=TAG).error(
                        f"强制đóngkết nốikhi出错: {close_error}"
                    )

    async def _save_and_close(self, ws):
        """lưu记忆并đóngkết nối"""
        try:
            # Chuỗi Daemon 1: Tạo tiêu đề độc lập (không dựa vào mô hình bộ nhớ)
            # Việc tạo tiêu đề chỉ được kích hoạt khi tính năng báo cáo chat_history được bật trên máy chủ.
            # Nếu không, máy chủ không thể tìm thấy tác nhân/chat_history tương ứng theo session_id.
            # sẽ đưa ra lỗi "không tìm thấy tác nhân"
            if self.session_id and self.chat_history_conf != 0:

                def generate_title_task():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            generate_and_save_chat_title(self.session_id)
                        )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"生成标题thất bại: {e}")
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass

                threading.Thread(target=generate_title_task, daemon=True).start()

            # Daemon Thread 2: Bảo toàn bộ nhớ của tiến trình cũ (chỉ bộ nhớ, không có tiêu đề)
            if self.memory:
                # Lưu bộ nhớ không đồng bộ bằng cách sử dụng nhóm luồng
                def save_memory_task():
                    try:
                        # Tạo vòng lặp sự kiện mới (để tránh xung đột với vòng lặp chính)
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            self.memory.save_memory(
                                self.dialogue.dialogue, self.session_id
                            )
                        )
                    except Exception as e:
                        self.logger.bind(tag=TAG).error(f"lưu记忆thất bại: {e}")
                    finally:
                        try:
                            loop.close()
                        except Exception:
                            pass

                # Bắt đầu chuỗi để tiết kiệm bộ nhớ mà không cần chờ hoàn thành
                threading.Thread(target=save_memory_task, daemon=True).start()
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"lưu记忆thất bại: {e}")
        finally:
            # Đóng kết nối ngay lập tức mà không cần đợi quá trình lưu bộ nhớ hoàn tất
            try:
                await self.close(ws)
            except Exception as close_error:
                self.logger.bind(tag=TAG).error(
                    f"lưu记忆后đóngKết nối thất bại: {close_error}"
                )

    async def _discard_message_with_bind_prompt(self):
        """丢弃thông điệp并kiểm tra是否需要播放绑定hướng dẫn"""
        current_time = time.time()
        # Kiểm tra xem bạn có cần phát lời nhắc ràng buộc không
        if current_time - self.last_bind_prompt_time >= self.bind_prompt_interval:
            self.last_bind_prompt_time = current_time
            # Sử dụng lại logic gợi ý ràng buộc hiện có
            from core.handle.receiveAudioHandle import check_bind_device

            asyncio.create_task(check_bind_device(self))

    async def _route_message(self, message):
        """thông điệp路由"""
        # Kiểm tra xem trạng thái ràng buộc thực đã đạt được chưa
        if not self.bind_completed_event.is_set():
            # Tình trạng thực sự vẫn chưa được lấy. Đợi cho đến khi có được trạng thái thực hoặc hết thời gian chờ.
            try:
                await asyncio.wait_for(self.bind_completed_event.wait(), timeout=1)
            except asyncio.TimeoutError:
                # Nếu không nhận được trạng thái thực sau khi hết thời gian chờ, tin nhắn sẽ bị loại bỏ.
                await self._discard_message_with_bind_prompt()
                return

        # Đã có được trạng thái thực, kiểm tra xem có cần ràng buộc không
        if self.need_bind:
            # Cần ràng buộc, loại bỏ tin nhắn
            await self._discard_message_with_bind_prompt()
            return

        # Không cần ràng buộc, tiếp tục xử lý tin nhắn

        if isinstance(message, str):
            await handleTextMessage(self, message)
        elif isinstance(message, bytes):
            if self.vad is None or self.asr is None:
                return

            # Xử lý các gói âm thanh từ cổng MQTT
            if self.conn_from_mqtt_gateway and len(message) >= 16:
                handled = await self._process_mqtt_audio_message(message)
                if handled:
                    return

            # Giải mã PCM trực tiếp ở lối vào để tránh giải mã lặp lại VAD và ASR
            pcm_frame = self._decode_opus_packet(message)
            if pcm_frame:
                self.asr_audio_queue.put(pcm_frame)

    async def _process_mqtt_audio_message(self, message):
        """
        xử lý来自MQTT网关的âm thanhthông điệp , phân tích16字节头部并提取âm thanhdữ liệu , 在入队前tiến hànhAECxử lý

        Args:
            message: 包含头部的âm thanhthông điệp

        Returns:
            bool: 是否thành côngxử lý了thông điệp
        """
        try:
            # Phân tích dấu thời gian
            timestamp = int.from_bytes(message[8:12], "big")

            audio_data = message[16:]
            # Giải mã PCM trực tiếp tại lối vào
            pcm_frame = self._decode_opus_packet(audio_data)
            if not pcm_frame:
                return True

            # Xử lý AEC: nếu dấu thời gian>0 và AEC được bật
            if timestamp > 0 and self.client_aec:
                pcm_frame = self._apply_aec(timestamp, pcm_frame)

            self.asr_audio_queue.put(pcm_frame)
            return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"phân tíchWebSocketâm thanh包thất bại: {e}"
            )

        # Nếu quá trình xử lý không thành công, hàm trả về Sai để cho biết rằng quá trình xử lý cần tiếp tục.
        return False

    def _apply_aec(self, timestamp: int, pcm_frame: bytes) -> bytes:
        """应用AEC处理 - 综合算法：互相关延迟估计 + Wiener滤波 + 频谱减法"""
        try:
            if not pcm_frame or len(pcm_frame) == 0:
                return pcm_frame

            if not hasattr(self, "aec_audio_cache") or not self.aec_audio_cache:
                return pcm_frame

            mic_audio = np.frombuffer(pcm_frame, dtype=np.int16).astype(np.float32)
            mic_rms = np.sqrt(np.mean(mic_audio**2))

            if mic_rms < 100:
                return pcm_frame

            sorted_timestamps = sorted(self.aec_audio_cache.keys())
            if len(sorted_timestamps) < 2:
                return pcm_frame

            # ========== Khớp các khung tham chiếu (khớp phổ công suất log) ==========
            n = len(mic_audio)

            # Tìm dấu thời gian gần nhất làm điểm bắt đầu
            closest_idx = min(
                range(len(sorted_timestamps)),
                key=lambda i: abs(sorted_timestamps[i] - timestamp),
            )

            # Tính toán trước phổ công suất logarit của mic_audio (được chia sẻ trong vòng lặp để tránh FFT lặp lại)
            mic_window = np.hanning(n)
            mic_fft = np.fft.rfft(mic_audio * mic_window)
            mic_psd = np.abs(mic_fft) ** 2
            mic_log_psd = 10 * np.log10(mic_psd + 1e-8)
            mic_P_xx = np.dot(mic_log_psd, mic_log_psd)

            # Sử dụng kết hợp phổ công suất logarit để tìm khung hình tốt nhất: tìm 2 khung hình trước và sau
            best_corr = -1
            best_ref_idx = closest_idx
            best_ref_rms = 0.0

            for offset in range(-2, 3):  # T-2, T-1, T, T+1, T+2
                test_idx = closest_idx + offset
                if test_idx < 0 or test_idx >= len(sorted_timestamps):
                    continue
                test_ts = sorted_timestamps[test_idx]
                test_ref = np.frombuffer(
                    self.aec_audio_cache[test_ts], dtype=np.int16
                ).astype(np.float32)
                test_ref_rms = np.sqrt(np.mean(test_ref**2))
                if test_ref_rms < 50:
                    continue

                # Đăng nhập tương quan phổ công suất
                test_window = np.hanning(len(test_ref))
                test_fft = np.fft.rfft(test_ref * test_window)
                test_psd = np.abs(test_fft) ** 2
                test_log_psd = 10 * np.log10(test_psd + 1e-8)
                P_xy = np.dot(mic_log_psd, test_log_psd)
                P_yy = np.dot(test_log_psd, test_log_psd)
                corr = abs(P_xy) / (np.sqrt(mic_P_xx) * np.sqrt(P_yy) + 1e-8)

                if corr > best_corr:
                    best_corr = corr
                    best_ref_idx = test_idx
                    best_ref_rms = test_ref_rms

            best_ts = sorted_timestamps[best_ref_idx]
            best_ref = np.frombuffer(
                self.aec_audio_cache[best_ts], dtype=np.int16
            ).astype(np.float32)
            ref_rms = best_ref_rms

            if ref_rms < 50:
                return pcm_frame

            # Căn chỉnh các tín hiệu tham chiếu (chặn trực tiếp cùng độ dài)
            aligned_ref = best_ref[:n]
            if len(aligned_ref) < n:
                aligned_ref = np.pad(aligned_ref, (0, n - len(aligned_ref)))

            # ========== Xử lý AEC trong miền tần số (Trừ quang phổ) ==========
            # Pha của tín hiệu miền thời gian bị biến dạng sau khi đi qua đường âm thanh, dẫn đến tương quan miền thời gian thấp và P_xy dương và âm không chắc chắn
            # Phổ biên độ miền tần số không bị ảnh hưởng bởi pha và tương quan phổ công suất logarit ổn định ở mức 0,97+
            # Công thức: result_mag = max(|mic_fft| - |ref_fft| * tỉ lệ * coef, 0)

            mic_mag = np.abs(mic_fft)
            mic_phase = np.angle(mic_fft)
            ref_fft = np.fft.rfft(aligned_ref * np.hanning(n))
            ref_mag = np.abs(ref_fft)

            # Tính toán miền tần số của thang tỷ lệ tiếng vang
            scale = np.sum(mic_mag * ref_mag) / (np.dot(ref_mag, ref_mag) + 1e-8)

            # Hệ số thích ứng: được điều chỉnh linh hoạt theo thang đo và coh
            # Quy mô lớn (tiếng vang mạnh) -> coef lớn; coh cao (kết hợp chính xác) -> coef lớn
            raw_coef = 1.0 + scale * 3 + (best_corr - 0.97) * 30
            coef = max(0.5, min(3.0, raw_coef))

            # Trừ quang phổ (trừ quá mức + chỉnh lưu nửa sóng)
            echo_mag = ref_mag * scale * coef
            result_mag = np.maximum(mic_mag - echo_mag * 1.5, mic_mag * 0.1)

            # Bảo toàn tín hiệu tái tạo pha
            result_fft = result_mag * np.exp(1j * mic_phase)
            output = np.fft.irfft(result_fft, n)

            # Khi mức tin cậy cao là tiếng vang thuần, hãy nhấn lại để đảm bảo rằng VAD không thể phát hiện ra tiếng vang đó.
            if best_corr >= 0.97 and ref_rms > 500:
                output = output * 0.3

            # Xử lý hậu kỳ: cắt bớt
            output = np.clip(output, -32768, 32767)

            # Chuyển đổi sang byte
            result = output.astype(np.int16).tobytes()

            return result

        except Exception as e:
            self.logger.bind(tag=TAG).warning(f"[AEC] xử lýthất bại: {e}")
            return pcm_frame

    def _decode_opus_packet(self, opus_packet: bytes) -> bytes:
        """
        解码Opusdữ liệu包为PCMdữ liệu

        Args:
            opus_packet: Opus编码的âm thanhdữ liệu

        Returns:
            bytes: 解码后的PCMdữ liệu , thất bạitrả vềNone
        """
        try:
            if not opus_packet or len(opus_packet) == 0:
                return None

            self._init_connection_state(self)
            pcm_frame = self._connection_opus_decoder.decode(opus_packet, 960)
            return pcm_frame
        except Exception as e:
            self.logger.bind(tag=TAG).debug(f"Opus解码thất bại: {e}")
            return None

    def _init_connection_state(self, conn):
        """为kết nốikhởi tạo独立的Opus解码器"""
        if not hasattr(conn, "_connection_opus_decoder"):
            conn._connection_opus_decoder = opuslib_next.Decoder(16000, 1)

    async def handle_restart(self, message):
        """xử lýdịch vụ器重启yêu cầu"""
        try:
            self.logger.bind(tag=TAG).info("nhậndịch vụ器重启指令 , 准备thực thi...")

            # Gửi phản hồi xác nhận
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "success",
                        "message": "Server đang khởi động lại...",
                        "content": {"action": "restart"},
                    }
                )
            )

            # Thực hiện thao tác khởi động lại không đồng bộ
            def restart_server():
                """实际执行重启的方法"""
                time.sleep(1)
                self.logger.bind(tag=TAG).info("thực thidịch vụ器重启...")
                subprocess.Popen(
                    [sys.executable, "app.py"],
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr,
                    start_new_session=True,
                )
                os._exit(0)

            # Sử dụng khởi động lại thực thi luồng để tránh chặn vòng lặp sự kiện
            threading.Thread(target=restart_server, daemon=True).start()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"重启thất bại: {str(e)}")
            await self.websocket.send(
                json.dumps(
                    {
                        "type": "server",
                        "status": "error",
                        "message": f"Restart failed: {str(e)}",
                        "content": {"action": "restart"},
                    }
                )
            )

    def _initialize_components(self):
        try:
            if self.tts is None:
                self.tts = self._initialize_tts()
            # Kênh tổng hợp giọng nói mở
            asyncio.run_coroutine_threadsafe(
                self.tts.open_audio_channels(self), self.loop
            )
            if self.need_bind:
                self.bind_completed_event.set()
                return
            self.selected_module_str = build_module_string(
                self.config.get("selected_module", {})
            )
            self.logger = create_connection_logger(self.selected_module_str)

            """初始化组件"""
            if self.config.get("prompt") is not None:
                user_prompt = self.config["prompt"]
                # Khởi tạo bằng cách sử dụng các từ nhắc nhanh
                prompt = self.prompt_manager.get_quick_prompt(user_prompt)
                self.change_system_prompt(prompt)
                self.logger.bind(tag=TAG).info(
                    f"快速初始化组件: prompt成功 {prompt[:50]}..."
                )

            """初始化本地组件"""
            if self.vad is None:
                self.vad = self._vad
            if self.asr is None:
                self.asr = self._initialize_asr()

            # Khởi tạo nhận dạng giọng nói
            self._initialize_voiceprint()
            # Kênh nhận dạng giọng nói mở
            asyncio.run_coroutine_threadsafe(
                self.asr.open_audio_channels(self), self.loop
            )

            """tải记忆"""
            self._initialize_memory()
            """tảiý địnhnhận dạng"""
            self._initialize_intent()
            """初始化上报线程"""
            self._init_report_threads()
            """cập nhậthệ thốnghướng dẫn词"""
            self._init_prompt_enhancement()
            """注入công cụgọifew-shot示例（仅function_call模式）"""
            self._inject_tool_call_fewshot()

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"实例化组件thất bại: {e}")

    def _init_prompt_enhancement(self):

        # Cập nhật thông tin ngữ cảnh
        self.prompt_manager.update_context_info(self, self.client_ip)
        enhanced_prompt = self.prompt_manager.build_enhanced_prompt(
            self.config["prompt"],
            self.device_id,
            self.client_ip,
            emoji_enabled=(self.features or {}).get("emoji", True),
        )
        if enhanced_prompt:
            self.change_system_prompt(enhanced_prompt)
            self.logger.bind(tag=TAG).debug("hệ thốnghướng dẫn词đã增强cập nhật")

    def _inject_tool_call_fewshot(self):
        """注入công cụgọi few-shot 示例到对话历史.
        结构: 正样本（công cụgọi示例）放在动态 system 之前 , 可命trong前缀bộ nhớ đệm;
        负样本（直接回答示例）放在动态 system 之后、紧挨真实người dùngthông điệp ,
        确保模型在xử lýngười dùngthông điệp前最后看到的是"不调công cụ"的行为模式.
        """
        if self.intent_type != "function_call":
            return
        if not hasattr(self, "func_handler") or self.func_handler is None:
            return

        tools = self.func_handler.get_functions()
        if not tools:
            return

        tool_names = {t.get("function", {}).get("name") for t in tools}

        # === ví dụ về vài ảnh (is_temporary) ===
        # Hiển thị cách sử dụng direct_answer mang tham số phản hồi và hoàn thành phản hồi trong một cuộc gọi

        # Ví dụ 1: direct_answer (nội dung trả lời được ghi trong tham số phản hồi, không cần đệ quy)
        da_tc_id = "fewshot_da_001"
        self.dialogue.put(
            Message(
                role="user", content="Kể cho mình một câu chuyện nhé", is_temporary=True
            )
        )
        self.dialogue.put(
            Message(
                role="assistant",
                tool_calls=[
                    {
                        "id": da_tc_id,
                        "function": {
                            "arguments": '{"response": "Được nhé! Bạn muốn nghe truyện cổ tích, phiêu lưu hay hài hước? Chọn một thể loại để mình kể nào!"}',
                            "name": "direct_answer",
                        },
                        "type": "function",
                        "index": 0,
                    }
                ],
                is_temporary=True,
            )
        )
        self.dialogue.put(
            Message(
                role="tool",
                tool_call_id=da_tc_id,
                content="Đã trả lời trực tiếp",
                is_temporary=True,
            )
        )

        # Ví dụ 2: Lệnh gọi công cụ thực (handle_exit_intent)
        if "handle_exit_intent" in tool_names:
            tc_id = "fewshot_exit_001"
            self.dialogue.put(
                Message(role="user", content="Tạm biệt", is_temporary=True)
            )
            self.dialogue.put(
                Message(
                    role="assistant",
                    tool_calls=[
                        {
                            "id": tc_id,
                            "function": {
                                "arguments": '{"say_goodbye": "Tạm biệt, lần sau mình trò chuyện tiếp nhé!"}',
                                "name": "handle_exit_intent",
                            },
                            "type": "function",
                            "index": 0,
                        }
                    ],
                    is_temporary=True,
                )
            )
            self.dialogue.put(
                Message(
                    role="tool",
                    tool_call_id=tc_id,
                    content="Đã xử lý yêu cầu kết thúc",
                    is_temporary=True,
                )
            )
            self.dialogue.put(
                Message(
                    role="assistant",
                    content="Tạm biệt, lần sau mình trò chuyện tiếp nhé!",
                    is_temporary=True,
                )
            )

        self.logger.bind(tag=TAG).debug("đã注入công cụgọi few-shot 示例")

    def _init_report_threads(self):
        """初始化ASR和TTS上报线程"""
        if not self.read_config_from_api or self.need_bind:
            return
        if self.chat_history_conf == 0:
            return
        if self.report_thread is None or not self.report_thread.is_alive():
            self.report_thread = threading.Thread(
                target=self._report_worker, daemon=True
            )
            self.report_thread.start()
            self.logger.bind(tag=TAG).info("TTS上报线程đãkhởi động")

    def _initialize_tts(self):
        """初始化TTS"""
        tts = None
        if not self.need_bind:
            tts = initialize_tts(self.config)

        if tts is None:
            tts = DefaultTTS(self.config, delete_audio_file=True)

        return tts

    def _initialize_asr(self):
        """初始化ASR"""
        if (
            self._asr is not None
            and hasattr(self._asr, "interface_type")
            and self._asr.interface_type == InterfaceType.LOCAL
        ):
            # Nếu ASR công cộng là dịch vụ địa phương, hãy trả lại trực tiếp
            # Bởi vì một ASR cục bộ có thể được chia sẻ bởi nhiều kết nối
            asr = self._asr
        else:
            # Nếu ASR công cộng là một dịch vụ từ xa, hãy khởi tạo một phiên bản mới
            # Vì ASR từ xa liên quan đến các kết nối websocket và nhận các luồng nên cần có một phiên bản cho mỗi kết nối.
            asr = initialize_asr(self.config)

        return asr

    def _initialize_voiceprint(self):
        """为hiện tạikết nốikhởi tạo声纹nhận dạng"""
        try:
            voiceprint_config = self.config.get("voiceprint", {})
            if voiceprint_config:
                voiceprint_provider = VoiceprintProvider(voiceprint_config)
                if voiceprint_provider is not None and voiceprint_provider.enabled:
                    self.voiceprint_provider = voiceprint_provider
                    self.logger.bind(tag=TAG).info(
                        "声纹nhận dạng功能đã在kết nốikhi动态启用"
                    )
                else:
                    self.logger.bind(tag=TAG).warning(
                        "声纹nhận dạng功能启用但cấu hình不完整"
                    )
            else:
                self.logger.bind(tag=TAG).info("声纹识别功能未启用")
        except Exception as e:
            self.logger.bind(tag=TAG).warning(
                f"声纹nhận dạngKhởi tạo thất bại: {str(e)}"
            )

    async def _background_initialize(self):
        """在后台khởi tạocấu hình和组件（完全不阻塞主循环）"""
        try:
            # Có được cấu hình khác biệt một cách không đồng bộ
            await self._initialize_private_config_async()
            # Khởi tạo các thành phần trong nhóm luồng
            self.executor.submit(self._initialize_components)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"后台Khởi tạo thất bại: {e}")

    async def _initialize_private_config_async(self):
        """从接口异步lấy差异化cấu hình（异步版本 , 不阻塞主循环）"""
        if not self.read_config_from_api:
            self.need_bind = False
            self.bind_completed_event.set()
            return
        try:
            begin_time = time.time()
            private_config = await get_private_config_from_api(
                self.config,
                self.headers.get("device-id"),
                self.headers.get("client-id", self.headers.get("device-id")),
            )
            private_config["delete_audio"] = bool(self.config.get("delete_audio", True))
            private_config["tts_timeout"] = self.config.get("tts_timeout", 15)
            self.logger.bind(tag=TAG).info(
                f"{time.time() - begin_time} giây , 异步lấy差异化cấu hìnhthành công: {json.dumps(filter_sensitive_info(private_config), ensure_ascii=False)}"
            )
            self.need_bind = False
            self.bind_completed_event.set()
        except DeviceNotFoundException as e:
            self.need_bind = True
            private_config = {}
        except DeviceBindException as e:
            self.need_bind = True
            self.bind_code = e.bind_code
            private_config = {}
        except Exception as e:
            self.need_bind = True
            self.logger.bind(tag=TAG).error(f"异步lấy差异化cấu hìnhthất bại: {e}")
            private_config = {}

        init_llm, init_tts, init_memory, init_intent = (
            False,
            False,
            False,
            False,
        )

        init_vad = check_vad_update(self.common_config, private_config)
        init_asr = check_asr_update(self.common_config, private_config)

        if init_vad:
            self.config["VAD"] = private_config["VAD"]
            self.config["selected_module"]["VAD"] = private_config["selected_module"][
                "VAD"
            ]
        if init_asr:
            self.config["ASR"] = private_config["ASR"]
            self.config["selected_module"]["ASR"] = private_config["selected_module"][
                "ASR"
            ]
        if private_config.get("TTS", None) is not None:
            init_tts = True
            self.config["TTS"] = private_config["TTS"]
            self.config["selected_module"]["TTS"] = private_config["selected_module"][
                "TTS"
            ]
        if private_config.get("LLM", None) is not None:
            init_llm = True
            self.config["LLM"] = private_config["LLM"]
            self.config["selected_module"]["LLM"] = private_config["selected_module"][
                "LLM"
            ]
        if private_config.get("VLLM", None) is not None:
            self.config["VLLM"] = private_config["VLLM"]
            self.config["selected_module"]["VLLM"] = private_config["selected_module"][
                "VLLM"
            ]
        if private_config.get("Memory", None) is not None:
            init_memory = True
            self.config["Memory"] = private_config["Memory"]
            self.config["selected_module"]["Memory"] = private_config[
                "selected_module"
            ]["Memory"]
        if private_config.get("Intent", None) is not None:
            init_intent = True
            self.config["Intent"] = private_config["Intent"]
            model_intent = private_config.get("selected_module", {}).get("Intent", {})
            self.config["selected_module"]["Intent"] = model_intent
            # Tải cấu hình plugin
            if model_intent != "Intent_nointent":
                plugin_from_server = private_config.get("plugins", {})
                for plugin, config_str in plugin_from_server.items():
                    plugin_from_server[plugin] = json.loads(config_str)
                # Sao chép cấu hình trình cắm cấp mô-đun vào từng tên chức năng cụ thể,
                # Thuận tiện cho việc tìm kiếm mô tả, nguồn tin tức và các cấu hình khác theo chức năng tiếp theo
                for module_name, func_names in module_func_map.items():
                    if module_name in plugin_from_server:
                        module_config = plugin_from_server[module_name]
                        for func_name in func_names:
                            if func_name not in plugin_from_server:
                                plugin_from_server[func_name] = module_config
                self.config["plugins"] = plugin_from_server
                # Mở rộng tên trình cắm cấp mô-đun thành tên chức năng cụ thể
                expanded_functions = []
                for plugin_key in plugin_from_server.keys():
                    if plugin_key in all_function_registry:
                        expanded_functions.append(plugin_key)
                    elif plugin_key in module_func_map:
                        expanded_functions.extend(module_func_map[plugin_key])
                    else:
                        expanded_functions.append(plugin_key)
                self.config["Intent"][self.config["selected_module"]["Intent"]][
                    "functions"
                ] = expanded_functions
        if private_config.get("prompt", None) is not None:
            self.config["prompt"] = private_config["prompt"]
        # Nhận thông tin giọng nói
        if private_config.get("voiceprint", None) is not None:
            self.config["voiceprint"] = private_config["voiceprint"]
        if private_config.get("summaryMemory", None) is not None:
            self.config["summaryMemory"] = private_config["summaryMemory"]
        if private_config.get("device_max_output_size", None) is not None:
            self.max_output_size = int(private_config["device_max_output_size"])
        if private_config.get("chat_history_conf", None) is not None:
            self.chat_history_conf = int(private_config["chat_history_conf"])
        if private_config.get("mcp_endpoint", None) is not None:
            self.config["mcp_endpoint"] = private_config["mcp_endpoint"]
        if private_config.get("context_providers", None) is not None:
            self.config["context_providers"] = private_config["context_providers"]

        # Đưa các từ thay thế vào cấu hình mô-đun TTS
        if private_config.get("correct_words", None) is not None:
            select_tts_module = self.config["selected_module"]["TTS"]
            self.config["TTS"][select_tts_module]["correct_words"] = private_config[
                "correct_words"
            ]

        # Sử dụng run_in_executor để thực thi initize_modules trong nhóm luồng để tránh chặn vòng lặp chính
        try:
            modules = await self.loop.run_in_executor(
                None,  # Sử dụng nhóm chủ đề mặc định
                initialize_modules,
                self.logger,
                private_config,
                init_vad,
                init_asr,
                init_llm,
                init_tts,
                init_memory,
                init_intent,
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"khởi tạo组件thất bại: {e}")
            modules = {}
        if modules.get("tts", None) is not None:
            self.tts = modules["tts"]
        if modules.get("vad", None) is not None:
            self.vad = modules["vad"]
        if modules.get("asr", None) is not None:
            self.asr = modules["asr"]
        if modules.get("llm", None) is not None:
            self.llm = modules["llm"]
        if modules.get("intent", None) is not None:
            self.intent = modules["intent"]
        if modules.get("memory", None) is not None:
            self.memory = modules["memory"]

    def _initialize_memory(self):
        if self.memory is None:
            return
        """初始化记忆模块"""
        self.memory.init_memory(
            role_id=self.device_id,
            llm=self.llm,
            summary_memory=self.config.get("summaryMemory", None),
            save_to_file=not self.read_config_from_api,
        )

        # Nhận cấu hình tóm tắt bộ nhớ
        memory_config = self.config["Memory"]
        memory_type = self.config["Memory"][self.config["selected_module"]["Memory"]][
            "type"
        ]
        # Nếu nomen hoặc mem_report_only được sử dụng, hãy quay lại trực tiếp
        if memory_type == "nomem" or memory_type == "mem_report_only":
            return
        # Sử dụng chế độ mem_local_short
        elif memory_type == "mem_local_short":
            memory_llm_name = memory_config[self.config["selected_module"]["Memory"]][
                "llm"
            ]
            if memory_llm_name and memory_llm_name in self.config["LLM"]:
                # Nếu LLM chuyên dụng được định cấu hình, hãy tạo một phiên bản LLM độc lập
                from core.utils import llm as llm_utils

                memory_llm_config = self.config["LLM"][memory_llm_name]
                memory_llm_type = memory_llm_config.get("type", memory_llm_name)
                memory_llm = llm_utils.create_instance(
                    memory_llm_type, memory_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为记忆总结tạo了专用LLM: {memory_llm_name}, loại: {memory_llm_type}"
                )
                self.memory.set_llm(memory_llm)
            else:
                # Nếu không thì sử dụng LLM chính
                self.memory.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

    def _initialize_intent(self):
        if self.intent is None:
            return
        self.intent_type = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ]["type"]
        if self.intent_type == "function_call" or self.intent_type == "intent_llm":
            self.load_function_plugin = True
        """初始化意图识别模块"""
        # Nhận cấu hình nhận dạng ý định
        intent_config = self.config["Intent"]
        intent_type = self.config["Intent"][self.config["selected_module"]["Intent"]][
            "type"
        ]

        # Nếu nointent được sử dụng, hãy quay lại trực tiếp
        if intent_type == "nointent":
            return
        # Sử dụng chế độ Intent_llm
        elif intent_type == "intent_llm":
            intent_llm_name = intent_config[self.config["selected_module"]["Intent"]][
                "llm"
            ]

            if intent_llm_name and intent_llm_name in self.config["LLM"]:
                # Nếu LLM chuyên dụng được định cấu hình, hãy tạo một phiên bản LLM độc lập
                from core.utils import llm as llm_utils

                intent_llm_config = self.config["LLM"][intent_llm_name]
                intent_llm_type = intent_llm_config.get("type", intent_llm_name)
                intent_llm = llm_utils.create_instance(
                    intent_llm_type, intent_llm_config
                )
                self.logger.bind(tag=TAG).info(
                    f"为ý địnhnhận dạngtạo了专用LLM: {intent_llm_name}, loại: {intent_llm_type}"
                )
                self.intent.set_llm(intent_llm)
            else:
                # Nếu không thì sử dụng LLM chính
                self.intent.set_llm(self.llm)
                self.logger.bind(tag=TAG).info("使用主LLM作为意图识别模型")

        """tải统一công cụxử lý器"""
        self.func_handler = UnifiedToolHandler(self)

        # Trình xử lý công cụ khởi tạo không đồng bộ
        if hasattr(self, "loop") and self.loop:
            asyncio.run_coroutine_threadsafe(self.func_handler._initialize(), self.loop)

    def change_system_prompt(self, prompt):
        self.prompt = prompt
        # Cập nhật lời nhắc hệ thống vào ngữ cảnh
        self.dialogue.update_system_message(self.prompt)

    def chat(self, query, depth=0):
        # Lưu câu_id của tác vụ hiện tại vào một biến cục bộ để tránh bị ghi đè bởi tác vụ mới
        current_sentence_id = None

        if query is not None:
            self.logger.bind(tag=TAG).info(f"大模型nhậnngười dùngthông điệp: {query}")

        # Tạo ID phiên mới và gửi yêu cầu ĐẦU TIÊN cho cấp cao nhất
        if depth == 0:
            current_sentence_id = str(uuid.uuid4().hex)
            self.sentence_id = current_sentence_id  # Cập nhật thuộc tính được chia sẻ
            self.dialogue.put(Message(role="user", content=query))
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=current_sentence_id,
                    sentence_type=SentenceType.FIRST,
                    content_type=ContentType.ACTION,
                )
            )
        else:
            # Khi gọi đệ quy, hãy sử dụng câu_id hiện tại
            current_sentence_id = self.sentence_id

        # Đặt độ sâu đệ quy tối đa để tránh vòng lặp vô hạn và có thể điều chỉnh theo nhu cầu thực tế
        MAX_DEPTH = 5
        force_final_answer = False  # Gắn cờ xem có buộc phải trả lời cuối cùng không

        if depth >= MAX_DEPTH:
            self.logger.bind(tag=TAG).debug(
                f"đã达到最大công cụgọi深度 {MAX_DEPTH} , sẽ强制基于现有thông tin回答"
            )
            force_final_answer = True
            # Thêm lệnh hệ thống để yêu cầu LLM trả lời dựa trên thông tin có sẵn
            self.dialogue.put(
                Message(
                    role="user",
                    content="[Thông báo hệ thống] Đã đạt giới hạn gọi công cụ. Hãy dùng thông tin đã thu thập để trả lời cuối cùng, không gọi thêm công cụ.",
                )
            )

        # Define intent functions
        functions = None
        # Vô hiệu hóa lệnh gọi công cụ khi đạt đến độ sâu tối đa, buộc LLM phải trả lời trực tiếp
        if (
            self.intent_type == "function_call"
            and hasattr(self, "func_handler")
            and not force_final_answer
        ):
            functions = list(self.func_handler.get_functions())
            # Công cụ ảo direct_answer chỉ được đưa vào lệnh gọi lớp đầu tiên
            # Các cuộc gọi đệ quy (độ sâu>0) không được đưa vào để ngăn mô hình gọi lại direct_answer khi tạo câu trả lời văn bản, gây ra vòng lặp.
            if functions is not None and depth == 0:
                functions.append(DIRECT_ANSWER_TOOL)

        response_message = []

        try:
            # Sử dụng các cuộc hội thoại đã ghi nhớ
            memory_str = None
            # Chỉ truy vấn bộ nhớ khi truy vấn không trống (yêu cầu thay mặt người dùng)
            if self.memory is not None and query:
                future = asyncio.run_coroutine_threadsafe(
                    self.memory.query_memory(query), self.loop
                )
                memory_str = future.result()

            # Danh tính chỉ được đưa vào hệ thống khi người nói xuất hiện lần đầu tiên và được giữ lại sau vòng lịch sử cuộc trò chuyện đầu tiên.
            # Tránh lặp lại tên trong hệ thống mỗi vòng để khiến người mẫu gọi chúng nhiều lần
            speaker_for_system = None
            cs = (self.current_speaker or "").strip()
            if (
                cs
                and cs != "Người nói chưa xác định"
                and cs not in self.system_introduced_speakers
            ):
                self.system_introduced_speakers.add(cs)
                speaker_for_system = cs

            if self.intent_type == "function_call" and functions is not None:
                # Sử dụng giao diện phát trực tuyến hỗ trợ các chức năng
                llm_responses = self.llm.response_with_functions(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(
                        memory_str,
                        self.config.get("voiceprint", {}),
                        speaker_for_system,
                    ),
                    functions=functions,
                )
            else:
                llm_responses = self.llm.response(
                    self.session_id,
                    self.dialogue.get_llm_dialogue_with_memory(
                        memory_str,
                        self.config.get("voiceprint", {}),
                        speaker_for_system,
                    ),
                )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM 处理出错 {query}: {e}")
            return None

        # Xử lý phản hồi phát trực tuyến
        tool_call_flag = False
        # Hỗ trợ nhiều cuộc gọi công cụ song song - sử dụng lưu trữ danh sách
        tool_calls_list = []  # Định dạng: [{"id": "", "name": "", "đối số": ""}]
        content_arguments = ""
        emotion_flag = True
        try:
            for response in llm_responses:
                if self.client_abort:
                    break
                if self.intent_type == "function_call" and functions is not None:
                    content, tools_call = response
                    if "content" in response:
                        content = response["content"]
                        tools_call = None
                    if content is not None and len(content) > 0:
                        content_arguments += content

                    if not tool_call_flag and content_arguments.startswith(
                        "<tool_call>"
                    ):
                        # print("content_arguments", content_arguments)
                        tool_call_flag = True

                    if tools_call is not None and len(tools_call) > 0:
                        tool_call_flag = True
                        self._merge_tool_calls(tool_calls_list, tools_call)

                    # Trích xuất trực tuyến tham số phản hồi của direct_answer và gửi TTS trong thời gian thực
                    # Sử dụng bộ đệm an toàn để ngăn các ký hiệu đóng JSON bị rò rỉ sang TTS
                    _DA_STREAM_BUFFER = 5
                    for tc in tool_calls_list:
                        if tc["name"] == "direct_answer" and tc.get("arguments"):
                            da_text = self._extract_direct_answer_response(
                                tc["arguments"]
                            )
                            sent_len = tc.get("_da_sent", 0)
                            if da_text and len(da_text) > sent_len:
                                safe_end = max(
                                    sent_len, len(da_text) - _DA_STREAM_BUFFER
                                )
                                if safe_end > sent_len:
                                    new_part = da_text[sent_len:safe_end]
                                    # Dọn dẹp rác đóng JSON có khả năng bị rò rỉ ở delta
                                    new_part = self._clean_response_garbage(new_part)
                                    if new_part:
                                        tc["_da_sent"] = safe_end
                                        self.tts.tts_text_queue.put(
                                            TTSMessageDTO(
                                                sentence_id=current_sentence_id,
                                                sentence_type=SentenceType.MIDDLE,
                                                content_type=ContentType.TEXT,
                                                content_detail=new_part,
                                            )
                                        )
                else:
                    content = response

                # Nhận những biểu hiện cảm xúc trong câu trả lời llm, chỉ một lần khi bắt đầu cuộc trò chuyện
                if emotion_flag and content is not None and content.strip():
                    if (self.features or {}).get("emoji", True):
                        asyncio.run_coroutine_threadsafe(
                            textUtils.get_emotion(self, content),
                            self.loop,
                        )
                    emotion_flag = False

                if content is not None and len(content) > 0:
                    if not tool_call_flag:
                        response_message.append(content)
                        self.tts.tts_text_queue.put(
                            TTSMessageDTO(
                                sentence_id=current_sentence_id,
                                sentence_type=SentenceType.MIDDLE,
                                content_type=ContentType.TEXT,
                                content_detail=content,
                            )
                        )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"LLM stream processing error: {e}")
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=current_sentence_id,
                    sentence_type=SentenceType.MIDDLE,
                    content_type=ContentType.TEXT,
                    content_detail=get_system_error_response(self.config),
                )
            )
            if depth == 0:
                self.tts.tts_text_queue.put(
                    TTSMessageDTO(
                        sentence_id=current_sentence_id,
                        sentence_type=SentenceType.LAST,
                        content_type=ContentType.ACTION,
                    )
                )
            return
        # Xử lý các cuộc gọi hàm
        if tool_call_flag:
            bHasError = False
            # Xử lý các định dạng lệnh gọi công cụ dựa trên văn bản
            if len(tool_calls_list) == 0 and content_arguments:
                a = extract_json_from_string(content_arguments)
                if a is not None:
                    try:
                        content_arguments_json = json.loads(a)
                        tool_calls_list.append(
                            {
                                "id": str(uuid.uuid4().hex),
                                "name": content_arguments_json["name"],
                                "arguments": json.dumps(
                                    content_arguments_json["arguments"],
                                    ensure_ascii=False,
                                ),
                            }
                        )
                    except Exception as e:
                        bHasError = True
                        response_message.append(a)
                else:
                    bHasError = True
                    response_message.append(content_arguments)
                if bHasError:
                    self.logger.bind(tag=TAG).error(
                        f"function call error: {content_arguments}"
                    )

            if not bHasError and len(tool_calls_list) > 0:
                # Xử lý công cụ ảo direct_answer
                direct_answer_calls = [
                    tc for tc in tool_calls_list if tc["name"] == "direct_answer"
                ]
                real_tool_calls = [
                    tc for tc in tool_calls_list if tc["name"] != "direct_answer"
                ]

                if direct_answer_calls:
                    self.logger.bind(tag=TAG).debug(
                        f"模型选择 direct_answer，流式已播报，写入对话历史"
                    )
                    for tc in direct_answer_calls:
                        da_response = self._extract_direct_answer_response(
                            tc.get("arguments", "{}")
                        )
                        if da_response:
                            # Xóa phần chưa gửi của bộ đệm phát trực tuyến
                            sent_len = tc.get("_da_sent", 0)
                            remaining = da_response[sent_len:]
                            if remaining:
                                remaining = self._clean_response_garbage(remaining)
                                if remaining:
                                    self.tts.tts_text_queue.put(
                                        TTSMessageDTO(
                                            sentence_id=current_sentence_id,
                                            sentence_type=SentenceType.MIDDLE,
                                            content_type=ContentType.TEXT,
                                            content_detail=remaining,
                                        )
                                    )
                            # Viết lịch sử cuộc trò chuyện
                            da_response = self._clean_response_garbage(da_response)
                            self.tts.store_tts_text(current_sentence_id, da_response)
                            self.dialogue.put(
                                Message(role="assistant", content=da_response)
                            )

                    if not real_tool_calls:
                        if depth == 0:
                            self.tts.tts_text_queue.put(
                                TTSMessageDTO(
                                    sentence_id=current_sentence_id,
                                    sentence_type=SentenceType.LAST,
                                    content_type=ContentType.ACTION,
                                )
                            )
                        return

                    tool_calls_list = real_tool_calls

            if not bHasError and len(tool_calls_list) > 0:
                self.logger.bind(tag=TAG).debug(
                    f"kiểm tra到 {len(tool_calls_list)} công cụgọi"
                )

                # Văn bản đã được phát trong giai đoạn phát trực tuyến LLM
                streamed_text = ""
                if len(response_message) > 0:
                    streamed_text = "".join(response_message)
                    self.tts.store_tts_text(current_sentence_id, streamed_text)
                    self.dialogue.put(Message(role="assistant", content=streamed_text))
                response_message.clear()

                # Thu thập Tương lai của tất cả các lệnh gọi công cụ
                futures_with_data = []
                for tool_call_data in tool_calls_list:
                    self.logger.bind(tag=TAG).debug(
                        f"function_name={tool_call_data['name']}, function_id={tool_call_data['id']}, function_arguments={tool_call_data['arguments']}"
                    )

                    # Sử dụng các phương thức công khai để báo cáo các cuộc gọi công cụ
                    tool_input = json.loads(tool_call_data.get("arguments") or "{}")
                    enqueue_tool_report(self, tool_call_data["name"], tool_input)

                    future = asyncio.run_coroutine_threadsafe(
                        self.func_handler.handle_llm_function_call(
                            self, tool_call_data
                        ),
                        self.loop,
                    )
                    futures_with_data.append((future, tool_call_data, tool_input))

                # Thời gian chờ cuộc gọi công cụ, có thể định cấu hình, mặc định 30 giây
                tool_call_timeout = int(self.config.get("tool_call_timeout", 30))
                # Chờ cho đến khi coroutine kết thúc (thời gian chờ thực tế là chậm nhất)
                tool_results = []

                for future, tool_call_data, tool_input in futures_with_data:
                    try:
                        result = future.result(timeout=tool_call_timeout)
                        tool_results.append((result, tool_call_data))
                        # Sử dụng các phương pháp công khai để báo cáo kết quả cuộc gọi công cụ
                        enqueue_tool_report(
                            self,
                            tool_call_data["name"],
                            tool_input,
                            str(result.result) if result.result else None,
                            report_tool_call=False,
                        )

                    except Exception as e:
                        self.logger.bind(tag=TAG).error(
                            f"công cụgọiquá thời gian chờ或sự cố: {tool_call_data['name']}, Lỗi: {e}"
                        )
                        # Trả về phản hồi lỗi khi hết thời gian chờ để tránh toàn bộ quá trình bị kẹt.
                        tool_results.append(
                            (
                                ActionResponse(
                                    action=Action.ERROR,
                                    result="Kết nối mạng đang có vấn đề, bạn thử lại sau nhé!",
                                ),
                                tool_call_data,
                            )
                        )
                        # Báo cáo lỗi gọi công cụ
                        enqueue_tool_report(
                            self,
                            tool_call_data["name"],
                            tool_input,
                            str(e),
                            report_tool_call=False,
                        )

                # Xử lý thống nhất các kết quả cuộc gọi công cụ
                if tool_results:
                    self._handle_function_result(
                        tool_results, depth=depth, streamed_text=streamed_text
                    )

        # Lưu nội dung hội thoại
        if len(response_message) > 0:
            text_buff = "".join(response_message)
            self.tts.store_tts_text(current_sentence_id, text_buff)
            self.dialogue.put(Message(role="assistant", content=text_buff))

        if depth == 0:
            self.tts.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=current_sentence_id,
                    sentence_type=SentenceType.LAST,
                    content_type=ContentType.ACTION,
                )
            )
            # Sử dụng phép tính lười biếng lambda, get_llm_dialogue() chỉ được thực thi ở cấp DEBUG
            self.logger.bind(tag=TAG).debug(
                lambda: json.dumps(
                    self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False
                )
            )

        return True

    def _handle_function_result(self, tool_results, depth, streamed_text=""):
        need_llm_tools = []
        record_tools = []

        for result, tool_call_data in tool_results:
            if result.action in [
                Action.RESPONSE,
                Action.NOTFOUND,
                Action.ERROR,
            ]:
                text = result.response if result.response else result.result
                if streamed_text and text in streamed_text:
                    self.logger.bind(tag=TAG).debug(
                        f"Skipping duplicate TTS for tool {tool_call_data['name']}, already streamed"
                    )
                else:
                    self.tts.tts_one_sentence(
                        self, ContentType.TEXT, content_detail=text
                    )
                    self.tts.store_tts_text(self.sentence_id, text)
                self.dialogue.put(Message(role="assistant", content=text))
            elif result.action == Action.REQLLM:
                need_llm_tools.append((result, tool_call_data))
            elif result.action == Action.RECORD:
                record_tools.append((result, tool_call_data))
            else:
                pass

        # Action.RECORD: Viết chuỗi lệnh gọi công cụ hoàn chỉnh (trợ lý(tool_calls) → công cụ(kết quả) → trợ lý(phản hồi))
        # Mô hình tìm hiểu các mẫu gọi công cụ từ lịch sử mà không cần gọi thêm tới LLM
        if record_tools:
            # Xây dựng các thông báo trợ lý (bao gồm tool_calls) và ghi lại "những công cụ nào được mô hình gọi"
            all_tool_calls = [
                {
                    "id": tool_call_data["id"],
                    "function": {
                        "arguments": (
                            "{}"
                            if tool_call_data["arguments"] == ""
                            else tool_call_data["arguments"]
                        ),
                        "name": tool_call_data["name"],
                    },
                    "type": "function",
                    "index": idx,
                }
                for idx, (_, tool_call_data) in enumerate(record_tools)
            ]
            self.dialogue.put(Message(role="assistant", tool_calls=all_tool_calls))

            # Ghi kết quả thực hiện của từng công cụ và ghi "những gì công cụ trả về"
            for result, tool_call_data in record_tools:
                text = result.result or ""
                self.dialogue.put(
                    Message(
                        role="tool",
                        tool_call_id=(
                            str(uuid.uuid4())
                            if tool_call_data["id"] is None
                            else tool_call_data["id"]
                        ),
                        content=text,
                    )
                )

            # Sử dụng văn bản cố định làm câu trả lời cuối cùng, hoàn thành biểu mẫu ba đoạn tiêu chuẩn và đảm bảo rằng tin nhắn tiếp theo là người dùng thay vì công cụ.
            response_parts = []
            for result, _ in record_tools:
                resp = result.response or result.result
                if resp:
                    response_parts.append(resp)
            if response_parts:
                self.dialogue.put(
                    Message(role="assistant", content="，".join(response_parts))
                )

        if need_llm_tools:
            all_tool_calls = [
                {
                    "id": tool_call_data["id"],
                    "function": {
                        "arguments": (
                            "{}"
                            if tool_call_data["arguments"] == ""
                            else tool_call_data["arguments"]
                        ),
                        "name": tool_call_data["name"],
                    },
                    "type": "function",
                    "index": idx,
                }
                for idx, (_, tool_call_data) in enumerate(need_llm_tools)
            ]
            self.dialogue.put(Message(role="assistant", tool_calls=all_tool_calls))

            for result, tool_call_data in need_llm_tools:
                text = result.result
                if text is not None and len(text) > 0:
                    self.dialogue.put(
                        Message(
                            role="tool",
                            tool_call_id=(
                                str(uuid.uuid4())
                                if tool_call_data["id"] is None
                                else tool_call_data["id"]
                            ),
                            content=text,
                        )
                    )

            self.chat(None, depth=depth + 1)

    def _report_worker(self):
        """聊天记录上报工作线程"""
        while not self.stop_event.is_set():
            try:
                # Nhận dữ liệu từ hàng đợi, đặt thời gian chờ để kiểm tra định kỳ các sự kiện dừng
                item = self.report_queue.get(timeout=1)
                if item is None:  # Phát hiện vật thể thuốc độc
                    break
                try:
                    # Kiểm tra trạng thái nhóm luồng
                    if self.executor is None:
                        continue
                    # Gửi tác vụ đến nhóm luồng
                    self.executor.submit(self._process_report, *item)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"聊天记录上报线程sự cố: {e}")
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"聊天记录上报工作线程sự cố: {e}")

        self.logger.bind(tag=TAG).info("聊天记录上报线程已退出")

    def _process_report(self, type, text, audio_data, report_time):
        """xử lý上报tác vụ"""
        try:
            # Thực hiện báo cáo không đồng bộ (chạy trong vòng lặp sự kiện)
            asyncio.run(report(self, type, text, audio_data, report_time))
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"上报xử lýsự cố: {e}")
        finally:
            # Đánh dấu nhiệm vụ hoàn thành
            self.report_queue.task_done()

    def clearSpeakStatus(self):
        self.client_is_speaking = False
        self.logger.bind(tag=TAG).debug(f"清除dịch vụ端讲话trạng thái")

    async def close(self, ws=None):
        """资源清理方法"""
        try:
            # Dọn dẹp tài nguyên kết nối VAD
            if (
                hasattr(self, "vad")
                and self.vad
                and hasattr(self.vad, "release_conn_resources")
            ):
                self.vad.release_conn_resources(self)

            # Bộ giải mã opus sạch
            if hasattr(self, "_connection_opus_decoder"):
                try:
                    delattr(self, "_connection_opus_decoder")
                except Exception:
                    pass

            # Xóa bộ đệm âm thanh
            if hasattr(self, "audio_buffer"):
                self.audio_buffer.clear()

            # Hủy tác vụ hết thời gian chờ
            if self.timeout_task and not self.timeout_task.done():
                self.timeout_task.cancel()
                try:
                    await self.timeout_task
                except asyncio.CancelledError:
                    pass
                self.timeout_task = None

            # Hủy tác vụ dọn dẹp bộ đệm AEC
            if (
                hasattr(self, "_aec_cache_cleanup_task")
                and self._aec_cache_cleanup_task
                and not self._aec_cache_cleanup_task.done()
            ):
                self._aec_cache_cleanup_task.cancel()
                try:
                    await self._aec_cache_cleanup_task
                except asyncio.CancelledError:
                    pass
                self._aec_cache_cleanup_task = None

            # Làm sạch bộ đệm AEC
            if hasattr(self, "aec_audio_cache"):
                self.aec_audio_cache.clear()
                self.aec_audio_cache_time.clear()

            # Làm sạch tài nguyên bộ xử lý công cụ
            if hasattr(self, "func_handler") and self.func_handler:
                try:
                    await self.func_handler.cleanup()
                except Exception as cleanup_error:
                    self.logger.bind(tag=TAG).error(
                        f"清理công cụxử lý器khi出错: {cleanup_error}"
                    )

            # sự kiện dừng kích hoạt
            if self.stop_event:
                self.stop_event.set()

            # Xóa hàng đợi nhiệm vụ
            self.clear_queues()

            # Đóng kết nối WebSocket
            try:
                if ws:
                    # Kiểm tra trạng thái WebSocket một cách an toàn và đóng
                    try:
                        if hasattr(ws, "closed") and not ws.closed:
                            await ws.close()
                        elif hasattr(ws, "state") and ws.state.name != "CLOSED":
                            await ws.close()
                        else:
                            # Nếu không có thuộc tính đóng, hãy thử đóng trực tiếp.
                            await ws.close()
                    except Exception:
                        # Nếu tắt máy không thành công, bỏ qua lỗi
                        pass
                elif self.websocket:
                    try:
                        if (
                            hasattr(self.websocket, "closed")
                            and not self.websocket.closed
                        ):
                            await self.websocket.close()
                        elif (
                            hasattr(self.websocket, "state")
                            and self.websocket.state.name != "CLOSED"
                        ):
                            await self.websocket.close()
                        else:
                            # Nếu không có thuộc tính đóng, hãy thử đóng trực tiếp.
                            await self.websocket.close()
                    except Exception:
                        # Nếu tắt máy không thành công, bỏ qua lỗi
                        pass
            except Exception as ws_error:
                self.logger.bind(tag=TAG).error(
                    f"đóngWebSocketkết nốikhi出错: {ws_error}"
                )

            if self.tts:
                await self.tts.close()
            if self.asr:
                await self.asr.close()

            # Cuối cùng đóng nhóm luồng (để tránh bị chặn)
            if self.executor:
                try:
                    self.executor.shutdown(wait=False)
                except Exception as executor_error:
                    self.logger.bind(tag=TAG).error(
                        f"đóng线程池khi出错: {executor_error}"
                    )
                self.executor = None
            self.logger.bind(tag=TAG).info("kết nối资源đã释放")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"đóngkết nốikhi出错: {e}")
        finally:
            # Đảm bảo sự kiện dừng được đặt
            if self.stop_event:
                self.stop_event.set()

    def clear_queues(self):
        """清空所有tác vụ队列"""
        if self.tts:
            self.logger.bind(tag=TAG).debug(
                f"开始清理: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

            # Xóa hàng đợi bằng phương pháp không chặn
            for q in [
                self.tts.tts_text_queue,
                self.tts.tts_audio_queue,
                self.report_queue,
            ]:
                if not q:
                    continue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

            # Đặt lại bộ điều khiển luồng âm thanh (hủy tác vụ nền và xóa hàng đợi)
            if hasattr(self, "audio_rate_controller") and self.audio_rate_controller:
                self.audio_rate_controller.reset()
                self.logger.bind(tag=TAG).debug("已重置音频流控器")

            self.logger.bind(tag=TAG).debug(
                f"清理结束: TTS队列大小={self.tts.tts_text_queue.qsize()}, 音频队列大小={self.tts.tts_audio_queue.qsize()}"
            )

    def reset_audio_states(self):
        """
        重置所有âm thanh相关trạng thái(VAD + ASR)
        """
        # Reset VAD states
        self.client_audio_buffer.clear()
        self.client_have_voice = False
        self.client_voice_stop = False
        self.client_voice_window.clear()
        self.last_is_voice = False
        self.vad_last_voice_time = 0.0

        # Clear ASR buffers
        self.asr_audio.clear()

        self.logger.bind(tag=TAG).debug("All audio states reset.")

    def chat_and_close(self, text):
        """Chat with the user and then close the connection"""
        try:
            # Sử dụng phương thức trò chuyện hiện có
            self.chat(text)

            # Sau khi trò chuyện xong, hãy ngắt kết nối
            self.close_after_chat = True
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Chat and close error: {str(e)}")

    async def _check_timeout(self):
        """kiểm trakết nốiquá thời gian chờ"""
        try:
            while not self.stop_event.is_set():
                last_activity_time = self.last_activity_time
                if self.need_bind:
                    last_activity_time = self.first_activity_time

                # Kiểm tra thời gian chờ (chỉ khi dấu thời gian đã được khởi tạo)
                if last_activity_time > 0.0:
                    current_time = time.time() * 1000
                    if current_time - last_activity_time > self.timeout_seconds * 1000:
                        if not self.stop_event.is_set():
                            self.logger.bind(tag=TAG).info(
                                "kết nốiquá thời gian chờ , 准备đóng"
                            )
                            # Đặt sự kiện dừng để ngăn việc xử lý lặp lại
                            self.stop_event.set()
                            # Sử dụng thử ngoại trừ để bao bọc thao tác tắt máy nhằm đảm bảo nó không bị chặn do ngoại lệ
                            try:
                                await self.close(self.websocket)
                            except Exception as close_error:
                                self.logger.bind(tag=TAG).error(
                                    f"quá thời gian chờđóngkết nốikhi出错: {close_error}"
                                )
                        break
                # Kiểm tra 10 giây một lần để tránh quá thường xuyên
                await asyncio.sleep(10)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"quá thời gian chờkiểm tratác vụ出错: {e}")
        finally:
            self.logger.bind(tag=TAG).info("quá thời gian chờkiểm tratác vụđã退出")

    async def _check_aec_cache_expiry(self):
        """定期清理过期的AEC缓存"""
        try:
            while not self.stop_event.is_set():
                if hasattr(self, "aec_audio_cache") and self.aec_audio_cache:
                    current_time = time.time()
                    expired_keys = [
                        ts
                        for ts, cache_time in list(self.aec_audio_cache_time.items())
                        if current_time - cache_time > 120  # Hết hạn sau 2 phút
                    ]
                    for ts in expired_keys:
                        self.aec_audio_cache.pop(ts, None)
                        self.aec_audio_cache_time.pop(ts, None)
                    if expired_keys:
                        self.logger.bind(tag=TAG).debug(
                            f"[AEC] 清理过期缓存 {len(expired_keys)} 条"
                        )
                # Kiểm tra mỗi 30 giây
                await asyncio.sleep(30)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"AECbộ nhớ đệm清理tác vụ出错: {e}")

    @staticmethod
    def _extract_direct_answer_response(arguments_str):
        """从 direct_answer 的tham sốtrong提取 response 值.
        优先使用 json.loads 标准phân tích , 流式阶段 fallback 到字符串提取.
        """
        if not arguments_str:
            return ""
        # Phân tích cú pháp JSON tiêu chuẩn được thử trước tiên (đối với JSON hoàn chỉnh và được định dạng đúng)
        try:
            data = json.loads(arguments_str)
            if isinstance(data, dict) and "response" in data:
                return data["response"]
        except (json.JSONDecodeError, TypeError):
            pass
        # Dự phòng: JSON của giai đoạn phát trực tuyến có thể không đầy đủ, hãy sử dụng tính năng trích xuất chuỗi
        marker = '"response": "'
        idx = arguments_str.find(marker)
        if idx < 0:
            marker = '"response":"'
            idx = arguments_str.find(marker)
        if idx < 0:
            return ""
        start = idx + len(marker)
        raw = arguments_str[start:]
        # Xóa ký hiệu đóng JSON ở cuối (nếu hoàn thành)
        if raw.endswith('"}'):
            raw = raw[:-2]
        elif raw.endswith('"'):
            raw = raw[:-1]
        # Xử lý việc thoát JSON
        raw = raw.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        return raw

    @staticmethod
    def _clean_response_garbage(text):
        """清理 response trong可能泄漏的 JSON 闭合符号.
        模型有khisẽ在 response nội dungtrong生成 JSON 闭合字符（如 ）"}} 或 '}) ,
        这些不是故事nội dung的一部分 , 需要去除.
        """
        if not text:
            return text
        # Dọn sạch rác đóng JSON của một dòng duy nhất (chẳng hạn như )"}} '}} "}} }} } )
        _garbage_chars = frozenset("\")'}）")
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if (
                stripped
                and len(stripped) <= 8
                and all(c in _garbage_chars for c in stripped)
            ):
                continue
            cleaned.append(line)
        result = "\n".join(cleaned)
        # Dọn dẹp các ký hiệu đóng JSON còn lại ở cuối
        result = re.sub(r'["\'}\]]+$', "", result.rstrip()).rstrip()
        return result

    def _merge_tool_calls(self, tool_calls_list, tools_call):
        """合并công cụgọi列表

        Args:
            tool_calls_list: đã收集的công cụgọi列表
            tools_call: 新的công cụgọi
        """
        for tool_call in tools_call:
            tool_index = getattr(tool_call, "index", None)
            if tool_index is None:
                if tool_call.function.name:
                    # Có function_name, cho biết đó là lệnh gọi công cụ mới
                    tool_index = len(tool_calls_list)
                else:
                    tool_index = len(tool_calls_list) - 1 if tool_calls_list else 0

            # Đảm bảo danh sách có đủ địa điểm
            if tool_index >= len(tool_calls_list):
                tool_calls_list.append({"id": "", "name": "", "arguments": ""})

            # Cập nhật thông tin cuộc gọi công cụ
            if tool_call.id:
                tool_calls_list[tool_index]["id"] = tool_call.id
            if tool_call.function.name:
                tool_calls_list[tool_index]["name"] = tool_call.function.name
            if tool_call.function.arguments:
                tool_calls_list[tool_index]["arguments"] += tool_call.function.arguments
