import json
import hmac
import base64
import hashlib
import asyncio
import websockets
import gc
from time import mktime
from datetime import datetime
from urllib.parse import urlencode
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from config.logger import setup_logging
from wsgiref.handlers import format_date_time
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()

# Trạng thái khung không đổi
STATUS_FIRST_FRAME = 0  # Mã định danh khung đầu tiên
STATUS_CONTINUE_FRAME = 1  # Mã định danh khung trung gian
STATUS_LAST_FRAME = 2  # Mã định danh của khung cuối cùng


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False
        self.server_ready = False

        # cấu hình iFlytek
        self.app_id = config.get("app_id")
        self.api_key = config.get("api_key")
        self.api_secret = config.get("api_secret")

        if not all([self.app_id, self.api_key, self.api_secret]):
            raise ValueError("Cần cung cấp app_id, api_key và api_secret")

        # Thông số nhận dạng
        self.iat_params = {
            "domain": config.get("domain", "slm"),
            "language": config.get("language", "zh_cn"),
            "accent": config.get("accent", "mandarin"),
            "result": {"encoding": "utf8", "compress": "raw", "format": "plain"},
        }

        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file

    def create_url(self) -> str:
        """生成认证URL"""
        url = "ws://iat.cn-huabei-1.xf-yun.com/v1"
        # Tạo dấu thời gian ở định dạng RFC1123
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        # Nối chuỗi
        signature_origin = "host: " + "iat.cn-huabei-1.xf-yun.com" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v1 " + "HTTP/1.1"

        # Mã hóa bằng hmac-sha256
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding="utf-8")

        authorization_origin = (
            'api_key="%s", algorithm="%s", headers="%s", signature="%s"'
            % (self.api_key, "hmac-sha256", "host date request-line", signature_sha)
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            encoding="utf-8"
        )

        # Kết hợp các tham số xác thực được yêu cầu vào một từ điển
        v = {
            "authorization": authorization,
            "date": date,
            "host": "iat.cn-huabei-1.xf-yun.com",
        }

        # Ghép các tham số xác thực để tạo url
        url = url + "?" + urlencode(v)
        return url

    async def open_audio_channels(self, conn: "ConnectionHandler"):
        await super().open_audio_channels(conn)

    async def receive_audio(
        self, conn: "ConnectionHandler", pcm_frame, audio_have_voice
    ):
        # Đầu tiên hãy gọi phương thức của lớp cha để xử lý logic cơ bản
        await super().receive_audio(conn, pcm_frame, audio_have_voice)

        # Nếu lần này có âm thanh và chưa có kết nối nào được thiết lập trước đó
        if audio_have_voice and self.asr_ws is None and not self.is_processing:
            try:
                await self._start_recognition(conn)
            except Exception as e:
                logger.bind(tag=TAG).error(f"thiết lậpASRKết nối thất bại: {str(e)}")
                await self._cleanup()
                return

        # Gửi dữ liệu âm thanh hiện tại
        if self.asr_ws and self.is_processing and self.server_ready:
            try:
                await self._send_audio_frame(pcm_frame, STATUS_CONTINUE_FRAME)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"gửiâm thanhdữ liệukhixảy raLỗi: {e}")
                await self._cleanup()

    async def _start_recognition(self, conn: "ConnectionHandler"):
        """开始识别会话"""
        try:
            self.is_processing = True
            # Thiết lập kết nối WebSocket
            ws_url = self.create_url()
            logger.bind(tag=TAG).info(f"đangkết nốiASRdịch vụ: {ws_url[:50]}...")

            # Nếu là chế độ thủ công, hãy đặt thời gian chờ thành một phút
            if conn.client_listen_mode == "manual":
                self.iat_params["eos"] = 60000

            self.asr_ws = await websockets.connect(
                ws_url,
                max_size=1000000000,
                ping_interval=None,
                ping_timeout=None,
                close_timeout=10,
            )

            logger.bind(tag=TAG).info("ASR WebSocketkết nốiđãthiết lập")
            self.server_ready = False
            self.forward_task = asyncio.create_task(self._forward_results(conn))

            # Gửi khung âm thanh đầu tiên
            if conn.asr_audio and len(conn.asr_audio) > 0:
                first_pcm = conn.asr_audio[-1] if conn.asr_audio else b""
                await self._send_audio_frame(first_pcm, STATUS_FIRST_FRAME)
                self.server_ready = True
                logger.bind(tag=TAG).info("已发送首帧，开始识别")

                # Gửi dữ liệu âm thanh được đệm
                for cached_pcm in conn.asr_audio[-10:]:
                    try:
                        await self._send_audio_frame(cached_pcm, STATUS_CONTINUE_FRAME)
                    except Exception as e:
                        logger.bind(tag=TAG).info(
                            f"gửibộ nhớ đệmâm thanhdữ liệukhixảy raLỗi: {e}"
                        )
                        break

        except Exception as e:
            logger.bind(tag=TAG).error(f"thiết lậpASRKết nối thất bại: {str(e)}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.bind(tag=TAG).error(f"Lỗinguyên nhân: {str(e.__cause__)}")
            if self.asr_ws:
                await self.asr_ws.close()
                self.asr_ws = None
            self.is_processing = False
            raise

    async def _send_audio_frame(self, audio_data: bytes, status: int):
        """发送音频帧"""
        if not self.asr_ws:
            return

        audio_b64 = base64.b64encode(audio_data).decode("utf-8")

        frame_data = {
            "header": {"status": status, "app_id": self.app_id},
            "parameter": {"iat": self.iat_params},
            "payload": {
                "audio": {"audio": audio_b64, "sample_rate": 16000, "encoding": "raw"}
            },
        }

        await self.asr_ws.send(json.dumps(frame_data, ensure_ascii=False))

    async def _forward_results(self, conn: "ConnectionHandler"):
        """转发nhận dạngkết quả"""
        try:
            while not conn.stop_event.is_set():
                try:
                    response = await asyncio.wait_for(self.asr_ws.recv(), timeout=60)
                    result = json.loads(response)
                    logger.bind(tag=TAG).debug(f"nhậnASRkết quả: {result}")

                    header = result.get("header", {})
                    payload = result.get("payload", {})
                    code = header.get("code", 0)
                    status = header.get("status", 0)

                    if code != 0:
                        logger.bind(tag=TAG).error(
                            f"nhận dạngLỗi , Lỗi码: {code}, thông điệp: {header.get('message', '')}"
                        )
                        if code in [10114, 10160]:  # vấn đề kết nối
                            break
                        continue

                    # Kết quả nhận dạng quá trình
                    if payload and "result" in payload:
                        text_data = payload["result"]["text"]
                        if text_data:
                            # Giải mã văn bản base64
                            decoded_text = base64.b64decode(text_data).decode("utf-8")
                            text_json = json.loads(decoded_text)
                            # Trích xuất nội dung văn bản
                            text_ws = text_json.get("ws", [])
                            for i in text_ws:
                                for j in i.get("cw", []):
                                    w = j.get("w", "")
                                    self.text += w

                    if status == 2:
                        logger.bind(tag=TAG).debug(
                            "nhận最终nhận dạngkết quả , 触发xử lý"
                        )
                        await self.handle_voice_stop(conn, conn.asr_audio)
                        break

                except asyncio.TimeoutError:
                    logger.bind(tag=TAG).error("接收kết quảquá thời gian chờ")
                    break
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).info("ASRdịch vụkết nốiđãđóng")
                    self.is_processing = False
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"xử lýASRkết quảkhixảy raLỗi: {str(e)}")
                    if hasattr(e, "__cause__") and e.__cause__:
                        logger.bind(tag=TAG).error(
                            f"Lỗinguyên nhân: {str(e.__cause__)}"
                        )
                    self.is_processing = False
                    break

        except Exception as e:
            logger.bind(tag=TAG).error(f"ASRkết quả转发tác vụxảy raLỗi: {str(e)}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.bind(tag=TAG).error(f"Lỗinguyên nhân: {str(e.__cause__)}")
        finally:
            # Dọn dẹp tài nguyên kết nối
            await self._cleanup()
            conn.reset_audio_states()

    async def handle_voice_stop(
        self, conn: "ConnectionHandler", asr_audio_task: List[bytes]
    ):
        """xử lýgiọng nói停止 , gửi最后一帧并xử lýnhận dạngkết quả"""
        try:
            # Gửi khung cuối cùng trước để cho biết phần cuối của âm thanh
            if self.asr_ws and self.is_processing:
                try:
                    await self._send_audio_frame(b"", STATUS_LAST_FRAME)
                    logger.bind(tag=TAG).debug(f"đãgửi停止yêu cầu")

                    await asyncio.sleep(0.25)
                except Exception as e:
                    logger.bind(tag=TAG).error(f"gửi停止Yêu cầu thất bại: {e}")

            await super().handle_voice_stop(conn, asr_audio_task)
        except Exception as e:
            logger.bind(tag=TAG).error(f"xử lýgiọng nói停止thất bại: {e}")
            import traceback

            logger.bind(tag=TAG).debug(f"sự cố详情: {traceback.format_exc()}")

    def stop_ws_connection(self):
        if self.asr_ws:
            asyncio.create_task(self.asr_ws.close())
            self.asr_ws = None
        self.is_processing = False

    async def _send_stop_request(self):
        """gửi停止nhận dạngyêu cầu（不đóngkết nối）"""
        if self.asr_ws:
            try:
                # Dừng gửi âm thanh trước
                self.is_processing = False
                await self._send_audio_frame(b"", STATUS_LAST_FRAME)
                logger.bind(tag=TAG).debug("đãgửi停止yêu cầu")
            except Exception as e:
                logger.bind(tag=TAG).error(f"gửi停止Yêu cầu thất bại: {e}")

    async def _cleanup(self):
        """清理资源（đóngkết nối）"""
        logger.bind(tag=TAG).debug(
            f"开始ASRsẽ话清理 | hiện tạitrạng thái: processing={self.is_processing}, server_ready={self.server_ready}"
        )

        # thiết lập lại trạng thái
        self.is_processing = False
        self.server_ready = False
        logger.bind(tag=TAG).debug("ASRtrạng tháiđã重置")

        # đóng kết nối
        if self.asr_ws:
            try:
                logger.bind(tag=TAG).debug("đangđóngWebSocketkết nối")
                await asyncio.wait_for(self.asr_ws.close(), timeout=2.0)
                logger.bind(tag=TAG).debug("WebSocketkết nốiđãđóng")
            except Exception as e:
                logger.bind(tag=TAG).error(f"đóngWebSocketKết nối thất bại: {e}")
            finally:
                self.asr_ws = None

        # Dọn dẹp tài liệu tham khảo nhiệm vụ
        self.forward_task = None

        logger.bind(tag=TAG).debug("ASR会话清理完成")

    async def speech_to_text(self, opus_data, session_id, artifacts=None):
        """lấynhận dạngkết quả"""
        result = self.text
        self.text = ""
        return result, None

    async def close(self):
        """资源清理方法"""
        if self.asr_ws:
            await self.asr_ws.close()
            self.asr_ws = None
        if self.forward_task:
            self.forward_task.cancel()
            try:
                await self.forward_task
            except asyncio.CancelledError:
                pass
            self.forward_task = None
        self.is_processing = False
