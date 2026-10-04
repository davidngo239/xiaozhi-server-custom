import os
import re
import math
import uuid
import queue
import asyncio
import threading
import traceback
import concurrent.futures

from core.utils import p3
from datetime import datetime
from core.utils import textUtils
from typing import Callable, Any
from abc import ABC, abstractmethod
from config.logger import setup_logging
from core.utils import opus_encoder_utils
from core.utils.tts import MarkdownCleaner, convert_percentage_to_range
from core.utils.output_counter import add_device_output
from core.handle.reportHandle import enqueue_tts_report
from core.handle.sendAudioHandle import sendAudioMessage
from core.utils.util import audio_bytes_to_data_stream, audio_to_data_stream
from core.providers.tts.dto.dto import (
    TTSMessageDTO,
    SentenceType,
    ContentType,
    InterfaceType,
)

TAG = __name__
logger = setup_logging()


class TTSProviderBase(ABC):
    def __init__(self, config, delete_audio_file):
        self.interface_type = InterfaceType.NON_STREAM
        self.conn = None
        self.delete_audio_file = delete_audio_file
        self.audio_file_type = "wav"
        self.output_file = config.get("output_dir", "tmp/")
        self.tts_timeout = float(config.get("tts_timeout", 15))
        if not math.isfinite(self.tts_timeout) or self.tts_timeout <= 0:
            raise ValueError("tts_timeout must be a positive finite number")
        self.tts_text_queue = queue.Queue()
        self.tts_audio_queue = queue.Queue()
        self.tts_audio_first_sentence = True
        self.before_stop_play_files = []
        self.report_on_last = False
        # Ánh xạ của question_id thành văn bản, được sử dụng để truyền phát TTS để có được văn bản phụ đề chính xác
        self._sentence_text_map = {}
        # Tải các từ thay thế để thay thế thường xuyên một lần
        raw_words = config.get("correct_words", [])
        self.correct_words = {}
        for item in raw_words:
            parts = item.split("|", 1)
            if len(parts) == 2:
                self.correct_words[parts[0]] = parts[1]
        # Xây dựng các biểu thức chính quy, sử dụng kết quả khớp dài nhất trước tiên (thoát nối sau khi sắp xếp)
        if self.correct_words:
            # Sắp xếp theo độ dài khóa theo thứ tự giảm dần, những khóa dài hơn sẽ được so khớp trước để tránh nhiễu với các từ ngắn.
            sorted_keys = sorted(self.correct_words.keys(), key=len, reverse=True)
            pattern_str = "|".join(re.escape(k) for k in sorted_keys)
            self._correct_words_pattern = re.compile(pattern_str)
            # Xây dựng một trình thay thế ngược thường xuyên để khôi phục văn bản được thay thế được dịch vụ TTS trả về văn bản gốc (hiển thị phụ đề)
            reverse_map = {v: k for k, v in self.correct_words.items()}
            sorted_reverse_keys = sorted(reverse_map.keys(), key=len, reverse=True)
            reverse_pattern_str = "|".join(re.escape(k) for k in sorted_reverse_keys)
            self._reverse_words_pattern = re.compile(reverse_pattern_str)
            self._reverse_words_map = reverse_map
            # Cửa sổ trượt trực tuyến: Từ điển các từ thay thế được nhóm theo từ đầu tiên để tra cứu nhanh
            self._words_by_first_char = {}
            for key in sorted_keys:  # Duyệt khóa theo độ dài giảm dần để ưu tiên khớp từ dài
                first_char = key[0] if key else ""
                if first_char not in self._words_by_first_char:
                    self._words_by_first_char[first_char] = []
                self._words_by_first_char[first_char].append(key)
        else:
            self._correct_words_pattern = None
            self._reverse_words_pattern = None
            self._reverse_words_map = None

        # Cửa sổ trượt phát trực tuyến: văn bản được lưu trong bộ nhớ đệm cần khớp
        self._pending_prefix = ""
        self.tts_text_buff = []
        self.punctuations = (
            "。",
            "？",
            "?",
            "！",
            "!",
            "；",
            ";",
            "：",
        )
        self.first_sentence_punctuations = (
            "，",
            "~",
            "、",
            ",",
            "。",
            "？",
            "?",
            "！",
            "!",
            "；",
            ";",
            "：",
        )
        self.tts_stop_request = False
        self.processed_chars = 0
        self.is_first_sentence = True

    def generate_filename(self, extension=".wav"):
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}",
        )

    def handle_opus(self, opus_data: bytes):
        logger.bind(tag=TAG).debug(f"推送dữ liệu到队列里面帧数～～ {len(opus_data)}")
        self.tts_audio_queue.put(
            (
                SentenceType.MIDDLE,
                opus_data,
                None,
                getattr(self, "current_sentence_id", None),
            )
        )

    def handle_audio_file(self, file_audio: bytes, text):
        self.before_stop_play_files.append((file_audio, text))

    def to_tts_stream(self, text, opus_handler: Callable[[bytes], None] = None) -> None:
        # Giữ văn bản gốc để hiển thị/chuyển tiếp
        original_text = text
        text = MarkdownCleaner.clean_markdown(text)
        # Sử dụng thay thế một lần thường xuyên để tránh các vấn đề lặp đi lặp lại và khớp một phần
        if self._correct_words_pattern:
            text = self._correct_words_pattern.sub(
                lambda m: self.correct_words[m.group(0)], text
            )
        max_repeat_time = 5
        if self.delete_audio_file:
            # Các tập tin cần xóa sẽ được chuyển đổi trực tiếp thành dữ liệu âm thanh
            while max_repeat_time > 0:
                try:
                    audio_bytes = asyncio.run(self.text_to_speak(text, None))
                    if audio_bytes:
                        # Sử dụng văn bản gốc để hiển thị/chuyển tiếp
                        self.tts_audio_queue.put(
                            (
                                SentenceType.FIRST,
                                None,
                                original_text,
                                getattr(self, "current_sentence_id", None),
                            )
                        )
                        audio_bytes_to_data_stream(
                            audio_bytes,
                            file_type=self.audio_file_type,
                            is_opus=True,
                            callback=opus_handler,
                            sample_rate=self.conn.sample_rate,
                            opus_encoder=self.opus_encoder,
                        )
                        break
                    else:
                        max_repeat_time -= 1
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"giọng nói生成thất bại{5 - max_repeat_time + 1}次: {original_text} , Lỗi: {e}"
                    )
                    max_repeat_time -= 1
            if max_repeat_time > 0:
                logger.bind(tag=TAG).info(
                    f"语音生成成功: {original_text}，重试{5 - max_repeat_time}次"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"giọng nói生成thất bại: {original_text} , 请kiểm tra网络或dịch vụ是否正常"
                )
            return None
        else:
            tmp_file = self.generate_filename()
            try:
                while not os.path.exists(tmp_file) and max_repeat_time > 0:
                    try:
                        asyncio.run(self.text_to_speak(text, tmp_file))
                    except Exception as e:
                        logger.bind(tag=TAG).warning(
                            f"giọng nói生成thất bại{5 - max_repeat_time + 1}次: {original_text} , Lỗi: {e}"
                        )
                        # Thực thi không thành công, tập tin đã bị xóa
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                        max_repeat_time -= 1

                if max_repeat_time > 0:
                    logger.bind(tag=TAG).info(
                        f"语音生成成功: {original_text}:{tmp_file}，重试{5 - max_repeat_time}次"
                    )
                else:
                    logger.bind(tag=TAG).error(
                        f"giọng nói生成thất bại: {original_text} , 请kiểm tra网络或dịch vụ是否正常"
                    )
                self.tts_audio_queue.put(
                    (
                        SentenceType.FIRST,
                        None,
                        original_text,
                        getattr(self, "current_sentence_id", None),
                    )
                )
                self._process_audio_file_stream(tmp_file, callback=opus_handler)
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
                return None

    def to_tts(self, text):
        # Giữ văn bản gốc để đăng nhập/hiển thị
        original_text = text
        text = MarkdownCleaner.clean_markdown(text)
        if self._correct_words_pattern:
            text = self._correct_words_pattern.sub(
                lambda m: self.correct_words[m.group(0)], text
            )
        max_repeat_time = 5
        if self.delete_audio_file:
            # Các tập tin cần xóa sẽ được chuyển đổi trực tiếp thành dữ liệu âm thanh
            while max_repeat_time > 0:
                try:
                    audio_bytes = asyncio.run(self.text_to_speak(text, None))
                    if audio_bytes:
                        audio_datas = []
                        audio_bytes_to_data_stream(
                            audio_bytes,
                            file_type=self.audio_file_type,
                            is_opus=True,
                            callback=lambda data: audio_datas.append(data),
                            sample_rate=self.conn.sample_rate,
                        )
                        return audio_datas
                    else:
                        max_repeat_time -= 1
                except Exception as e:
                    logger.bind(tag=TAG).warning(
                        f"giọng nói生成thất bại{5 - max_repeat_time + 1}次: {original_text} , Lỗi: {e}"
                    )
                    max_repeat_time -= 1
            if max_repeat_time > 0:
                logger.bind(tag=TAG).info(
                    f"语音生成成功: {original_text}，重试{5 - max_repeat_time}次"
                )
            else:
                logger.bind(tag=TAG).error(
                    f"giọng nói生成thất bại: {original_text} , 请kiểm tra网络或dịch vụ是否正常"
                )
            return None
        else:
            tmp_file = self.generate_filename()
            try:
                while not os.path.exists(tmp_file) and max_repeat_time > 0:
                    try:
                        asyncio.run(self.text_to_speak(text, tmp_file))
                    except Exception as e:
                        logger.bind(tag=TAG).warning(
                            f"giọng nói生成thất bại{5 - max_repeat_time + 1}次: {original_text} , Lỗi: {e}"
                        )
                        # Thực thi không thành công, tập tin đã bị xóa
                        if os.path.exists(tmp_file):
                            os.remove(tmp_file)
                        max_repeat_time -= 1

                if max_repeat_time > 0:
                    logger.bind(tag=TAG).info(
                        f"语音生成成功: {original_text}:{tmp_file}，重试{5 - max_repeat_time}次"
                    )
                else:
                    logger.bind(tag=TAG).error(
                        f"giọng nói生成thất bại: {original_text} , 请kiểm tra网络或dịch vụ是否正常"
                    )

                return tmp_file
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to generate TTS file: {e}")
                return None

    @abstractmethod
    async def text_to_speak(self, text, output_file):
        pass

    def audio_to_pcm_data_stream(
        self, audio_file_path, callback: Callable[[Any], Any] = None
    ):
        """音频文件转换为PCM编码"""
        return audio_to_data_stream(
            audio_file_path,
            is_opus=False,
            callback=callback,
            sample_rate=self.conn.sample_rate,
            opus_encoder=None,
        )

    def audio_to_opus_data_stream(
        self, audio_file_path, callback: Callable[[Any], Any] = None
    ):
        """音频文件转换为Opus编码"""
        return audio_to_data_stream(
            audio_file_path,
            is_opus=True,
            callback=callback,
            sample_rate=self.conn.sample_rate,
            opus_encoder=self.opus_encoder,
        )

    def tts_one_sentence(
        self,
        conn,
        content_type,
        content_detail=None,
        content_file=None,
        sentence_id=None,
    ):
        """发送一句话"""
        if not sentence_id:
            if conn.sentence_id:
                sentence_id = conn.sentence_id
            else:
                sentence_id = str(uuid.uuid4().hex)
                conn.sentence_id = sentence_id
        # Đối với văn bản một câu, hãy thực hiện xử lý phân đoạn
        segments = re.split(r"([。！？!?；;\n])", content_detail)
        for seg in segments:
            self.tts_text_queue.put(
                TTSMessageDTO(
                    sentence_id=sentence_id,
                    sentence_type=SentenceType.MIDDLE,
                    content_type=content_type,
                    content_detail=seg,
                    content_file=content_file,
                )
            )

    async def open_audio_channels(self, conn):
        self.conn = conn

        # Tạo bộ mã hóa dựa trên sample_rate của conn. Nếu lớp con đã được tạo, nó sẽ không bị ghi đè (giao diện IndexTTS trả về 24kHZ - sẽ được lấy mẫu lại)
        if not hasattr(self, "opus_encoder") or self.opus_encoder is None:
            self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
                sample_rate=conn.sample_rate, channels=1, frame_size_ms=60
            )

        # Luồng xử lý TTS
        self.tts_priority_thread = threading.Thread(
            target=self.tts_text_priority_thread, daemon=True
        )
        self.tts_priority_thread.start()

        # Phát lại âm thanh
        self.audio_play_priority_thread = threading.Thread(
            target=self._audio_play_priority_thread, daemon=True
        )
        self.audio_play_priority_thread.start()

    def store_tts_text(self, sentence_id, text):
        """存储指定 sentence_id 对应的文本，用于流式TTS获取正确的字幕文本

        Args:
            sentence_id: 会话ID
            text: 要存储的文本
        """
        if sentence_id and text:
            self._sentence_text_map[sentence_id] = text
            # Chỉ giữ lại 5 cái mới nhất để tránh rò rỉ bộ nhớ
            if len(self._sentence_text_map) > 5:
                oldest = next(iter(self._sentence_text_map))
                del self._sentence_text_map[oldest]

    def get_tts_text(self, sentence_id):
        """获取指定 sentence_id 对应的文本

        Args:
            sentence_id: 会话ID

        Returns:
            str: 对应的文本，如果不存在返回 None
        """
        return self._sentence_text_map.get(sentence_id)

    def clear_tts_text(self, sentence_id):
        """清除指定 sentence_id 的文本

        Args:
            sentence_id: 会话ID
        """
        if sentence_id in self._sentence_text_map:
            del self._sentence_text_map[sentence_id]

    def _restore_original_text(self, text):
        if not self._reverse_words_pattern or not text:
            return text
        return self._reverse_words_pattern.sub(
            lambda m: self._reverse_words_map[m.group(0)], text
        )

    # Mặc định ở đây là xử lý không phát trực tuyến.
    # Vui lòng viết lại phương thức xử lý phát trực tuyến trong một lớp con
    def tts_text_priority_thread(self):
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info(
                        "nhận打断thông tin , 终止TTSvăn bảnxử lý线程"
                    )
                    continue
                # Lọc tin nhắn cũ: kiểm tra xem câu_id có khớp không
                if message.sentence_id != self.conn.sentence_id:
                    continue
                if message.sentence_type == SentenceType.FIRST:
                    self.current_sentence_id = message.sentence_id
                    self.tts_stop_request = False
                    self.processed_chars = 0
                    self.tts_text_buff = []
                    self.is_first_sentence = True
                    self.tts_audio_first_sentence = True
                elif ContentType.TEXT == message.content_type:
                    self.tts_text_buff.append(message.content_detail)
                    segment_text = self._get_segment_text()
                    if segment_text:
                        self.to_tts_stream(segment_text, opus_handler=self.handle_opus)
                elif ContentType.FILE == message.content_type:
                    self._process_remaining_text_stream(opus_handler=self.handle_opus)
                    tts_file = message.content_file
                    if tts_file and os.path.exists(tts_file):
                        self._process_audio_file_stream(
                            tts_file, callback=self.handle_opus
                        )
                if message.sentence_type == SentenceType.LAST:
                    self._process_remaining_text_stream(opus_handler=self.handle_opus)
                    self.tts_audio_queue.put(
                        (
                            message.sentence_type,
                            [],
                            message.content_detail,
                            message.sentence_id,
                        )
                    )

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"xử lýTTSvăn bảnthất bại: {str(e)}, loại: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue

    def _audio_play_priority_thread(self):
        # Danh sách các văn bản và âm thanh được báo cáo
        enqueue_text = None
        enqueue_audio = []
        while not self.conn.stop_event.is_set():
            text = None
            try:
                try:
                    item = self.tts_audio_queue.get(timeout=0.1)
                    if len(item) == 4:
                        sentence_type, audio_datas, text, sentence_id = item
                    else:
                        sentence_type, audio_datas, text = item
                        sentence_id = None
                except queue.Empty:
                    if self.conn.stop_event.is_set():
                        break
                    continue

                if self.conn.client_abort:
                    logger.bind(tag=TAG).debug(
                        "nhận打断信号 , bỏ quahiện tạiâm thanhdữ liệu"
                    )
                    enqueue_text, enqueue_audio = None, []
                    continue

                # Báo cáo lên khi nhận được văn bản tiếp theo hoặc khi phiên kết thúc
                if sentence_type is not SentenceType.MIDDLE:
                    if self.report_on_last:
                        # Chế độ tích lũy: phù hợp với TTS chỉ có một luồng giọng nói trong toàn bộ quá trình (chẳng hạn như Seed-tts-2.0)
                        # Chỉ văn bản được ghi trong FIRST, âm thanh tiếp tục tích lũy và chỉ được báo cáo thống nhất trong LAST.
                        if text:
                            enqueue_text = text
                        if sentence_type == SentenceType.LAST:
                            enqueue_tts_report(self.conn, enqueue_text, enqueue_audio)
                            enqueue_audio = []
                            enqueue_text = None
                    else:
                        # Chế độ không tích lũy: mỗi câu được báo cáo riêng
                        if enqueue_text is not None:
                            enqueue_tts_report(self.conn, enqueue_text, enqueue_audio)
                        enqueue_audio = []
                        enqueue_text = text

                # Thu thập và báo cáo dữ liệu âm thanh
                if isinstance(audio_datas, bytes):
                    enqueue_audio.append(audio_datas)

                # Gửi âm thanh
                future = asyncio.run_coroutine_threadsafe(
                    sendAudioMessage(
                        self.conn, sentence_type, audio_datas, text, sentence_id
                    ),
                    self.conn.loop,
                )
                future.result()

                # Ghi nhật ký đầu ra và báo cáo
                if self.conn.max_output_size > 0 and text:
                    add_device_output(self.conn.headers.get("device-id"), len(text))

            except Exception as e:
                logger.bind(tag=TAG).error(f"audio_play_priority_thread: {text} {e}")

    async def start_session(self, session_id):
        pass

    async def finish_session(self, session_id):
        pass

    async def close(self):
        """资源清理方法"""
        self._sentence_text_map.clear()
        if hasattr(self, "ws") and self.ws:
            await self.ws.close()

    def _get_segment_text(self):
        # Hợp nhất tất cả văn bản hiện tại và xử lý các phần không phân chia
        full_text = "".join(self.tts_text_buff)
        current_text = full_text[self.processed_chars :]  # Bắt đầu từ vị trí chưa xử lý
        last_punct_pos = -1

        # Chọn các bộ dấu câu khác nhau dựa trên việc đó có phải là câu đầu tiên hay không
        punctuations_to_use = (
            self.first_sentence_punctuations
            if self.is_first_sentence
            else self.punctuations
        )

        for punct in punctuations_to_use:
            pos = current_text.rfind(punct)
            if (pos != -1 and last_punct_pos == -1) or (
                pos != -1 and pos < last_punct_pos
            ):
                last_punct_pos = pos

        if last_punct_pos != -1:
            segment_text_raw = current_text[: last_punct_pos + 1]
            segment_text = textUtils.get_string_no_punctuation_or_emoji(
                segment_text_raw
            )
            self.processed_chars += len(segment_text_raw)  # Cập nhật vị trí ký tự đã xử lý

            # Nếu là câu đầu tiên, sau khi tìm thấy dấu phẩy đầu tiên, hãy đặt cờ thành Sai
            if self.is_first_sentence:
                self.is_first_sentence = False

            return segment_text
        elif self.tts_stop_request and current_text:
            segment_text = current_text
            self.is_first_sentence = True  # đặt lại cờ
            return segment_text
        else:
            return None

    def _process_audio_file_stream(
        self, tts_file, callback: Callable[[Any], Any]
    ) -> None:
        """xử lýâm thanh文件并转换为指定định dạng

        Args:
            tts_file: âm thanh文件路径
            callback: 文件xử lýhàm
        """
        if tts_file.endswith(".p3"):
            p3.decode_opus_from_file_stream(tts_file, callback=callback)
        elif self.conn.audio_format == "pcm":
            self.audio_to_pcm_data_stream(tts_file, callback=callback)
        else:
            self.audio_to_opus_data_stream(tts_file, callback=callback)

        if (
            self.delete_audio_file
            and tts_file is not None
            and os.path.exists(tts_file)
            and tts_file.startswith(self.output_file)
        ):
            os.remove(tts_file)

    def _process_before_stop_play_files(self):
        for audio_datas, text in self.before_stop_play_files:
            self.tts_audio_queue.put(
                (
                    SentenceType.MIDDLE,
                    audio_datas,
                    text,
                    getattr(self, "current_sentence_id", None),
                )
            )
        self.before_stop_play_files.clear()
        self.tts_audio_queue.put(
            (SentenceType.LAST, [], None, getattr(self, "current_sentence_id", None))
        )

    def _process_remaining_text_stream(
        self, opus_handler: Callable[[bytes], None] = None
    ):
        """处理剩余的文本并生成语音

        Returns:
            bool: 是否成功处理了文本
        """
        full_text = "".join(self.tts_text_buff)
        remaining_text = full_text[self.processed_chars :]
        if remaining_text:
            segment_text = textUtils.get_string_no_punctuation_or_emoji(remaining_text)
            if segment_text:
                self.to_tts_stream(segment_text, opus_handler=opus_handler)
                self.processed_chars += len(full_text)
                return True
        return False

    def _apply_percentage_params(self, config):
        """根据子类定义的 TTS_PARAM_CONFIG 批量应用百分比tham số"""
        for (
            config_key,
            attr_name,
            min_val,
            max_val,
            base_val,
            transform,
        ) in self.TTS_PARAM_CONFIG:
            if config_key in config:
                val = convert_percentage_to_range(
                    config[config_key], min_val, max_val, base_val
                )
                setattr(self, attr_name, transform(val) if transform else val)

    def _match_stream_text(self, text):
        """流式文本滑动窗口匹配，用于处理跨分片的替换词

        Args:
            text: 输入的文本片段

        Returns:
            tuple: (确定的文本列表, 剩余待匹配的前缀)
        """
        if not self.correct_words or not text:
            return [text] if text else [], ""

        result = []
        pending = self._pending_prefix
        i = 0

        while i < len(text):
            char = text[i]

            # Hãy thử: đang chờ xử lý + ký tự hiện tại để xem nó có khớp với từ thay thế không
            test_text = pending + char

            matched = False
            # Lặp lại các từ thay thế phù hợp có thể
            candidates = (
                self._words_by_first_char.get(pending[0], [])
                if pending
                else self._words_by_first_char.get(char, [])
            )
            for key in candidates:
                if test_text == key:
                    # Hoàn thành trận đấu, gửi sau khi thay thế
                    result.append(self.correct_words[key])
                    pending = ""
                    matched = True
                    break
                elif key.startswith(test_text):
                    # là tiền tố của từ thay thế, tiếp tục đợi
                    pending = test_text
                    matched = True
                    break

            if matched:
                i += 1
                continue

            # Không còn từ nào trùng khớp nữa và nội dung đang chờ xử lý chắc chắn có thể được gửi đi.
            if pending:
                result.append(pending)
                pending = ""

            # Kiểm tra xem ký tự hiện tại có phải là phần đầu của từ thay thế không
            if char in self._words_by_first_char:
                pending = char
            else:
                result.append(char)

            i += 1

        return result, pending

    def reset_stream_state(self):
        """重置流式xử lýtrạng thái , 用于sẽ话开始khi清理残留trạng thái"""
        self._pending_prefix = ""
