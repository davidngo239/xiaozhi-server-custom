import os
import uuid
import json
import time
import queue
import asyncio
import traceback
import websockets

from typing import Callable, Any
from config.logger import setup_logging
from core.utils.tts import MarkdownCleaner
from core.utils.alibl_endpoint import build_ws_connect_options, resolve_ws_url
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType

TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    TTS_PARAM_CONFIG = [
        ("ttsVolume", "volume", 0, 100, 50, int),
        ("ttsRate", "rate", 0.5, 2.0, 1.0, lambda v: round(v, 1)),
        ("ttsPitch", "pitch", 0.5, 2.0, 1.0, lambda v: round(v, 1)),
    ]

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        self.interface_type = InterfaceType.DUAL_STREAM
        # Cấu hình cơ bản
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("api_key is required for CosyVoice TTS")

        # Cấu hình WebSocket
        self.ws_url = resolve_ws_url(config.get("ws_url"))
        self.ws_connect_options = build_ws_connect_options(self.tts_timeout)
        self.ws = None
        self._monitor_task = None
        self.activate_session = False
        self.last_active_time = None

        # Cấu hình model và giai điệu
        self.model = config.get("model", "cosyvoice-v2")
        self.voice = config.get("voice", "longxiaochun_v2")  # Giọng mặc định
        if config.get("private_voice"):
            self.voice = config.get("private_voice")

        # Cấu hình tham số âm thanh
        self.format = config.get("format", "pcm")

        volume = config.get("volume", "50")
        self.volume = int(volume) if volume else 50

        rate = config.get("rate", "1.0")
        self.rate = float(rate) if rate else 1.0

        pitch = config.get("pitch", "1.0")
        self.pitch = float(pitch) if pitch else 1.0

        # Áp dụng điều chỉnh tỷ lệ phần trăm nếu có, nếu không thì sử dụng cấu hình công khai
        self._apply_percentage_params(config)

        self.header = {
            "Authorization": f"Bearer {self.api_key}",
            # "user-agent": "your_platform_info", // tùy chọn
            # "X-DashScope-WorkSpace": không gian làm việc, // Tùy chọn, ID không gian kinh doanh của Alibaba Cloud Bailian
            "X-DashScope-DataInspection": "enable",
        }

    async def _ensure_connection(self):
        """确保WebSocketkết nối可用 , 支持60秒内kết nối复用"""
        try:
            current_time = time.time()
            if self.ws and current_time - self.last_active_time < 60:
                # Liên kết có thể được sử dụng lại cho các cuộc trò chuyện liên tục trong vòng một phút.
                logger.bind(tag=TAG).debug(f"使用已有链接...")
                return self.ws
            logger.bind(tag=TAG).debug("开始thiết lập新kết nối...")

            # Hủy tác vụ nghe cũ trước khi thiết lập kết nối mới
            await self._cancel_monitor_task()

            self.ws = await websockets.connect(
                self.ws_url,
                additional_headers=self.header,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10,
                **self.ws_connect_options,
            )

            logger.bind(tag=TAG).debug("WebSocketkết nốithiết lậpthành công")
            self.last_active_time = current_time
            return self.ws
        except Exception as e:
            logger.bind(tag=TAG).error(f"thiết lậpKết nối thất bại: {str(e)}")
            self.ws = None
            self.last_active_time = None
            raise

    def tts_text_priority_thread(self):
        """流式TTS文本处理线程"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)

                if self.conn.client_abort:
                    try:
                        logger.bind(tag=TAG).info(
                            "nhận打断thông tin , 终止TTSvăn bảnxử lý线程"
                        )
                        asyncio.run_coroutine_threadsafe(
                            self.finish_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        continue
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"hủyTTSsẽ话thất bại: {str(e)}")
                        continue

                # Lọc tin nhắn cũ: kiểm tra xem câu_id có khớp không
                if message.sentence_id != self.conn.sentence_id:
                    continue

                logger.bind(tag=TAG).debug(
                    f"nhậnTTStác vụ｜{message.sentence_type.name} ｜ {message.content_type.name} | sẽ话ID: {message.sentence_id}"
                )

                if message.sentence_type == SentenceType.FIRST:
                    # Đặt lại trạng thái phát trực tuyến
                    self.reset_stream_state()
                    # Khởi tạo phiên
                    try:
                        if not getattr(self.conn, "sentence_id", None):
                            self.conn.sentence_id = uuid.uuid4().hex
                            logger.bind(tag=TAG).debug(
                                f"自动生成新的 会话ID: {self.conn.sentence_id}"
                            )

                        logger.bind(tag=TAG).debug("开始khởi độngTTSsẽ话...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.start_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result(timeout=self.tts_timeout)
                        self.before_stop_play_files.clear()
                        logger.bind(tag=TAG).debug("TTSsẽ话khởi độngthành công")
                    except Exception as e:
                        logger.bind(tag=TAG).error(
                            f"khởi độngTTSsẽ话thất bại: {str(e)}"
                        )
                        continue

                elif ContentType.TEXT == message.content_type:
                    if message.content_detail:
                        try:
                            logger.bind(tag=TAG).debug(
                                f"开始发送TTS文本: {message.content_detail}"
                            )
                            future = asyncio.run_coroutine_threadsafe(
                                self.text_to_speak(message.content_detail, None),
                                loop=self.conn.loop,
                            )
                            future.result(timeout=self.tts_timeout)
                        except Exception as e:
                            logger.bind(tag=TAG).error(
                                f"gửiTTSvăn bảnthất bại: {str(e)}"
                            )
                            continue

                elif ContentType.FILE == message.content_type:
                    logger.bind(tag=TAG).info(
                        f"添加音频文件到待播放列表: {message.content_file}"
                    )
                    if message.content_file and os.path.exists(message.content_file):
                        # Trước tiên hãy xử lý dữ liệu âm thanh của tệp
                        self._process_audio_file_stream(
                            message.content_file,
                            callback=lambda audio_data: self.handle_audio_file(
                                audio_data, message.content_detail
                            ),
                        )

                if message.sentence_type == SentenceType.LAST:
                    try:
                        logger.bind(tag=TAG).debug("开始结束TTS会话...")
                        future = asyncio.run_coroutine_threadsafe(
                            self.finish_session(self.conn.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result()
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"结束TTSsẽ话thất bại: {str(e)}")
                        continue

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"xử lýTTSvăn bảnthất bại: {str(e)}, loại: {type(e).__name__}, 堆栈: {traceback.format_exc()}"
                )
                continue

    async def text_to_speak(self, text, _):
        """gửivăn bản到TTSdịch vụtiến hành合成"""
        try:
            if self.ws is None:
                logger.bind(tag=TAG).warning("WebSocketkết nối不存在 , 终止gửivăn bản")
                return

            # Lọc đánh dấu
            filtered_text = MarkdownCleaner.clean_markdown(text)

            if filtered_text:
                # Sử dụng tính năng khớp cửa sổ trượt để xử lý các từ thay thế trên các phân đoạn
                confirmed_texts, self._pending_prefix = self._match_stream_text(
                    filtered_text
                )

                # Gửi từng đoạn văn bản được xác định
                for txt in confirmed_texts:
                    if txt and self.ws:
                        continue_task_message = {
                            "header": {
                                "action": "continue-task",
                                "task_id": self.conn.sentence_id,
                                "streaming": "duplex",
                            },
                            "payload": {"input": {"text": txt}},
                        }
                        await self.ws.send(json.dumps(continue_task_message))
                        self.last_active_time = time.time()
            return
        except Exception as e:
            logger.bind(tag=TAG).error(f"gửiTTSvăn bảnthất bại: {str(e)}")
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
            raise

    async def start_session(self, session_id):
        """khởi độngTTSsẽ话"""
        logger.bind(tag=TAG).debug(f"开始会话～～{session_id}")
        try:
            # Đóng kết nối cuối cùng trong khi phiên trước đó đang hoạt động Liên kết mới
            if self.activate_session:
                await self.close()

            # Đặt cờ kích hoạt phiên
            self.activate_session = True

            # Đảm bảo kết nối có sẵn
            await self._ensure_connection()

            # Bắt đầu nhiệm vụ nghe
            if self._monitor_task is None or self._monitor_task.done():
                logger.bind(tag=TAG).debug("khởi động监听tác vụ...")
                self._monitor_task = asyncio.create_task(
                    self._start_monitor_tts_response()
                )

            # Gửi tin nhắn run-task để bắt đầu phiên
            run_task_message = {
                "header": {
                    "action": "run-task",
                    "task_id": session_id,
                    "streaming": "duplex",
                },
                "payload": {
                    "task_group": "audio",
                    "task": "tts",
                    "function": "SpeechSynthesizer",
                    "model": self.model,
                    "parameters": {
                        "text_type": "PlainText",
                        "voice": self.voice,
                        "format": self.format,
                        "sample_rate": self.conn.sample_rate,
                        "volume": self.volume,
                        "rate": self.rate,
                        "pitch": self.pitch,
                    },
                    "input": {},
                },
            }

            await self.ws.send(json.dumps(run_task_message))
            self.last_active_time = time.time()
            logger.bind(tag=TAG).debug("sẽ话khởi độngyêu cầuđãgửi")
        except Exception as e:
            logger.bind(tag=TAG).error(f"khởi độngsẽ话thất bại: {str(e)}")
            await self.close()
            raise

    async def finish_session(self, session_id):
        """结束TTS会话"""
        logger.bind(tag=TAG).debug(f"đóngsẽ话～～{session_id}")
        try:
            if self.ws and session_id:
                # Gửi tin nhắn hoàn thành nhiệm vụ
                finish_task_message = {
                    "header": {
                        "action": "finish-task",
                        "task_id": session_id,
                        "streaming": "duplex",
                    },
                    "payload": {"input": {}},
                }

                await self.ws.send(json.dumps(finish_task_message))
                self.last_active_time = time.time()

        except Exception as e:
            logger.bind(tag=TAG).error(f"đóngsẽ话thất bại: {str(e)}")
            await self.close()
            raise

    async def close(self):
        """清理资源"""
        await super().close()
        self.activate_session = False
        await self._cancel_monitor_task()

        # Đóng kết nối WebSocket
        if self.ws:
            try:
                await self.ws.close()
            except:
                pass
            self.ws = None
            self.last_active_time = None

    async def _cancel_monitor_task(self):
        """hủy监听tác vụ"""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.bind(tag=TAG).warning(f"hủy监听tác vụLỗi: {e}")
        self._monitor_task = None

    async def _start_monitor_tts_response(self):
        """监听TTSphản hồi - 长期运行"""
        try:
            while not self.conn.stop_event.is_set():
                try:
                    msg = await self.ws.recv()
                    self.last_active_time = time.time()

                    if isinstance(msg, str):  # Công cụ JSON
                        try:
                            data = json.loads(msg)
                            header = data.get("header", {})
                            event = header.get("event")
                            task_id = header.get("task_id")

                            # Chỉ xử lý phản hồi từ các phiên hiện đang hoạt động
                            if task_id and self.conn.sentence_id != task_id:
                                if event in ["task-finished", "task-failed"]:
                                    logger.bind(tag=TAG).debug(
                                        f"nhận残余下行结束phản hồi重置sẽ话trạng thái～～"
                                    )
                                    self.activate_session = False
                                continue

                            if event == "task-started":
                                logger.bind(tag=TAG).debug(
                                    "TTStác vụkhởi độngthành công~"
                                )
                            elif event == "result-generated":
                                output = data.get("payload", {}).get("output", {})
                                if output.get("type") == "sentence-begin":
                                    original_text = output.get("original_text")
                                    self.tts_text = self._restore_original_text(
                                        original_text
                                    )
                                    logger.bind(tag=TAG).debug(
                                        f"句子语音生成开始: {self.tts_text}"
                                    )
                                    self.tts_audio_queue.put(
                                        (SentenceType.FIRST, [], self.tts_text)
                                    )
                                elif output.get("type") == "sentence-end":
                                    logger.bind(tag=TAG).info(
                                        f"句子语音生成成功： {self.tts_text}"
                                    )
                            elif event == "task-finished":
                                logger.bind(tag=TAG).debug("TTStác vụhoàn tất~")
                                self.activate_session = False
                                self._process_before_stop_play_files()
                            elif event == "task-failed":
                                error_code = header.get("error_code", "unknown")
                                error_message = header.get(
                                    "error_message", "Lỗi không xác định"
                                )
                                logger.bind(tag=TAG).error(
                                    f"TTStác vụthất bại: {error_code} - {error_message}"
                                )
                                break
                        except json.JSONDecodeError:
                            logger.bind(tag=TAG).warning("nhận无效的JSONthông điệp")
                    elif isinstance(msg, (bytes, bytearray)):
                        self.opus_encoder.encode_pcm_to_opus_stream(
                            msg, False, callback=self.handle_opus
                        )
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("WebSocketkết nốiđãđóng")
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"xử lýTTSphản hồikhi出错: {e}\n{traceback.format_exc()}"
                    )
                    break

            # Đóng WebSocket khi kết nối không bình thường
            if self.ws:
                try:
                    await self.ws.close()
                except:
                    pass
                self.ws = None
        # Dọn dẹp các tài liệu tham khảo khi thoát khỏi tác vụ nghe
        finally:
            self.activate_session = False
            self._monitor_task = None

    def audio_to_opus_data_stream(
        self, audio_file_path, callback: Callable[[Any], Any] = None
    ):
        """重写父类方法: 使用独立的临khi编码器xử lýâm thanh文件 , 避免与TTS流式编码器并发冲突.
        双流式TTStrong , monitortác vụ在event loop线程接收TTSâm thanh并使用self.opus_encoder编码 ,
        同khitts_text_priority_threadxử lý音乐文件也使用self.opus_encoder ,
        共享的encoder.buffer非线程安全 , 并发访问sẽ导致SILK resampler断言thất bại.
        """
        from core.utils.util import audio_to_data_stream

        return audio_to_data_stream(
            audio_file_path,
            is_opus=True,
            callback=callback,
            sample_rate=self.conn.sample_rate,
            opus_encoder=None,
        )

    def to_tts(self, text: str) -> list:
        """非流式生成âm thanhdữ liệu , 用于生成âm thanh及测试场景"""
        try:
            # Tạo vòng lặp sự kiện
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Tạo ID phiên
            session_id = uuid.uuid4().hex
            # Lưu trữ dữ liệu âm thanh
            audio_data = []

            async def _generate_audio():
                ws = await websockets.connect(
                    self.ws_url,
                    additional_headers=self.header,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                    max_size=10 * 1024 * 1024,
                    **self.ws_connect_options,
                )

                try:
                    # Gửi tin nhắn run-task để bắt đầu phiên
                    run_task_message = {
                        "header": {
                            "action": "run-task",
                            "task_id": session_id,
                            "streaming": "duplex",
                        },
                        "payload": {
                            "task_group": "audio",
                            "task": "tts",
                            "function": "SpeechSynthesizer",
                            "model": self.model,
                            "parameters": {
                                "text_type": "PlainText",
                                "voice": self.voice,
                                "format": self.format,
                                "sample_rate": self.conn.sample_rate,
                                "volume": self.volume,
                                "rate": self.rate,
                                "pitch": self.pitch,
                            },
                            "input": {},
                        },
                    }
                    await ws.send(json.dumps(run_task_message))

                    # Chờ nhiệm vụ bắt đầu
                    task_started = False
                    while not task_started:
                        msg = await ws.recv()
                        if isinstance(msg, str):
                            data = json.loads(msg)
                            header = data.get("header", {})
                            if header.get("event") == "task-started":
                                task_started = True
                                logger.bind(tag=TAG).debug("TTStác vụđãkhởi động")
                            elif header.get("event") == "task-failed":
                                error_code = header.get("error_code", "unknown")
                                error_message = header.get(
                                    "error_message", "Lỗi không xác định"
                                )
                                raise Exception(
                                    f"Khởi chạy tác vụ thất bại: {error_code} - {error_message}"
                                )

                    # Gửi văn bản
                    filtered_text = MarkdownCleaner.clean_markdown(text)
                    if self._correct_words_pattern:
                        filtered_text = self._correct_words_pattern.sub(
                            lambda m: self.correct_words[m.group(0)], filtered_text
                        )
                    # Gửi tin nhắn tiếp tục nhiệm vụ
                    continue_task_message = {
                        "header": {
                            "action": "continue-task",
                            "task_id": session_id,
                            "streaming": "duplex",
                        },
                        "payload": {"input": {"text": filtered_text}},
                    }
                    await ws.send(json.dumps(continue_task_message))

                    # Gửi tin nhắn hoàn thành nhiệm vụ
                    finish_task_message = {
                        "header": {
                            "action": "finish-task",
                            "task_id": session_id,
                            "streaming": "duplex",
                        },
                        "payload": {"input": {}},
                    }
                    await ws.send(json.dumps(finish_task_message))

                    # Nhận dữ liệu âm thanh
                    task_finished = False
                    while not task_finished:
                        msg = await ws.recv()
                        if isinstance(msg, (bytes, bytearray)):
                            self.opus_encoder.encode_pcm_to_opus_stream(
                                msg,
                                end_of_stream=False,
                                callback=lambda opus: audio_data.append(opus),
                            )
                        elif isinstance(msg, str):
                            data = json.loads(msg)
                            header = data.get("header", {})
                            if header.get("event") == "task-finished":
                                task_finished = True
                                logger.bind(tag=TAG).debug("TTStác vụhoàn tất")
                            elif header.get("event") == "task-failed":
                                error_code = header.get("error_code", "unknown")
                                error_message = header.get(
                                    "error_message", "Lỗi không xác định"
                                )
                                raise Exception(
                                    f"Tổng hợp giọng nói thất bại: {error_code} - {error_message}"
                                )

                finally:
                    # Dọn dẹp tài nguyên
                    try:
                        await ws.close()
                    except:
                        pass

            # Chạy các tác vụ không đồng bộ
            loop.run_until_complete(_generate_audio())
            loop.close()

            return audio_data

        except Exception as e:
            logger.bind(tag=TAG).error(f"生成âm thanhdữ liệuthất bại: {str(e)}")
            return []
