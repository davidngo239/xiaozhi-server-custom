import json
import time
import uuid
import hmac
import base64
import hashlib
import asyncio
import requests
import websockets
from urllib import parse
from datetime import datetime
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


class AccessToken:
    @staticmethod
    def _encode_text(text):
        encoded_text = parse.quote_plus(text)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def _encode_dict(dic):
        keys = dic.keys()
        dic_sorted = [(key, dic[key]) for key in sorted(keys)]
        encoded_text = parse.urlencode(dic_sorted)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def create_token(access_key_id, access_key_secret):
        parameters = {
            "AccessKeyId": access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "cn-shanghai",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid1()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": "2019-02-28",
        }
        query_string = AccessToken._encode_dict(parameters)
        string_to_sign = (
            "GET"
            + "&"
            + AccessToken._encode_text("/")
            + "&"
            + AccessToken._encode_text(query_string)
        )
        secreted_string = hmac.new(
            bytes(access_key_secret + "&", encoding="utf-8"),
            bytes(string_to_sign, encoding="utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(secreted_string)
        signature = AccessToken._encode_text(signature)
        full_url = "http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s" % (
            signature,
            query_string,
        )
        response = requests.get(full_url)
        if response.ok:
            root_obj = response.json()
            if "Token" in root_obj:
                return root_obj["Token"]["Id"], root_obj["Token"]["ExpireTime"]
        return None, None


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False
        self.server_ready = False  # Trạng thái sẵn sàng của máy chủ

        # Cấu hình cơ bản
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.appkey = config.get("appkey")
        self.token = config.get("token")
        self.host = config.get("host", "nls-gateway-cn-shanghai.aliyuncs.com")
        # Nếu địa chỉ mạng nội bộ được định cấu hình (bao gồm -internal.aliyuncs.com), giao thức ws sẽ được sử dụng. Mặc định là giao thức wss.
        if "-internal." in self.host:
            self.ws_url = f"ws://{self.host}/ws/v1"
        else:
            # Sử dụng giao thức wss theo mặc định
            self.ws_url = f"wss://{self.host}/ws/v1"

        self.max_sentence_silence = config.get("max_sentence_silence")
        self.output_dir = config.get("output_dir", "./audio_output")
        self.delete_audio_file = delete_audio_file
        self.expire_time = None

        self.task_id = uuid.uuid4().hex

        # Quản lý mã thông báo
        if self.access_key_id and self.access_key_secret:
            self._refresh_token()
        elif not self.token:
            raise ValueError(
                "Cần cung cấp access_key_id và access_key_secret hoặc token trực tiếp"
            )

    def _refresh_token(self):
        """刷新Token"""
        self.token, expire_time_str = AccessToken.create_token(
            self.access_key_id, self.access_key_secret
        )
        if not self.token:
            raise ValueError("Không thể lấy token truy cập hợp lệ")

        try:
            expire_str = str(expire_time_str).strip()
            if expire_str.isdigit():
                expire_time = datetime.fromtimestamp(int(expire_str))
            else:
                expire_time = datetime.strptime(expire_str, "%Y-%m-%dT%H:%M:%SZ")
            self.expire_time = expire_time.timestamp() - 60
        except:
            self.expire_time = None

    def _is_token_expired(self):
        """检查Token是否过期"""
        return self.expire_time and time.time() > self.expire_time

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(self, conn, pcm_frame, audio_have_voice):
        # Đầu tiên hãy gọi phương thức của lớp cha để xử lý logic cơ bản
        await super().receive_audio(conn, pcm_frame, audio_have_voice)

        # Chỉ kết nối khi có âm thanh và không có kết nối (trừ dừng)
        if audio_have_voice and not self.is_processing and not self.asr_ws:
            try:
                await self._start_recognition(conn)
            except Exception as e:
                logger.bind(tag=TAG).error(f"开始nhận dạngthất bại: {str(e)}")
                await self._cleanup()
                return

        if self.asr_ws and self.is_processing and self.server_ready:
            try:
                await self.asr_ws.send(pcm_frame)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"gửiâm thanhthất bại: {str(e)}")
                await self._cleanup()

    async def _start_recognition(self, conn: "ConnectionHandler"):
        """开始识别会话"""
        if self._is_token_expired():
            self._refresh_token()

        # Thiết lập kết nối
        headers = {"X-NLS-Token": self.token}
        self.asr_ws = await websockets.connect(
            self.ws_url,
            additional_headers=headers,
            max_size=1000000000,
            ping_interval=None,
            ping_timeout=None,
            close_timeout=5,
        )

        self.task_id = uuid.uuid4().hex

        logger.bind(tag=TAG).debug(
            f"WebSocketkết nốithiết lậpthành công, task_id: {self.task_id}"
        )

        self.is_processing = True
        self.server_ready = False  # Đặt lại trạng thái sẵn sàng của máy chủ
        self.forward_task = asyncio.create_task(self._forward_results(conn))

        # Gửi yêu cầu bắt đầu
        start_request = {
            "header": {
                "namespace": "SpeechTranscriber",
                "name": "StartTranscription",
                "message_id": uuid.uuid4().hex,
                "task_id": self.task_id,
                "appkey": self.appkey,
            },
            "payload": {
                "format": "pcm",
                "sample_rate": 16000,
                "enable_intermediate_result": True,
                "enable_punctuation_prediction": True,
                "enable_inverse_text_normalization": True,
                "max_sentence_silence": self.max_sentence_silence,
                "enable_voice_detection": False,
            },
        }
        await self.asr_ws.send(json.dumps(start_request, ensure_ascii=False))
        logger.bind(tag=TAG).debug("đãgửi开始yêu cầu , chờdịch vụ器准备...")

    async def _forward_results(self, conn: "ConnectionHandler"):
        """转发nhận dạngkết quả"""
        try:
            while not conn.stop_event.is_set():
                # Lấy dữ liệu âm thanh của kết nối hiện tại
                audio_data = conn.asr_audio
                try:
                    response = await self.asr_ws.recv()
                    result = json.loads(response)

                    header = result.get("header", {})
                    payload = result.get("payload", {})
                    message_name = header.get("name", "")
                    status = header.get("status", 0)

                    if status != 20000000:
                        if status == 40010004:
                            logger.bind(tag=TAG).warning(
                                f"请在dịch vụ端phản hồihoàn tất后再đóng链接 , trạng thái码: {status}"
                            )
                            break
                        if status in [40000004, 40010003]:  # Đã hết thời gian kết nối hoặc máy khách bị ngắt kết nối
                            logger.bind(tag=TAG).warning(
                                f"kết nối问题 , trạng thái码: {status}"
                            )
                            break
                        elif status in [40270002, 40270003]:  # Sự cố âm thanh
                            logger.bind(tag=TAG).warning(
                                f"âm thanhxử lý问题 , trạng thái码: {status}"
                            )
                            continue
                        else:
                            logger.bind(tag=TAG).error(
                                f"nhận dạngLỗi , trạng thái码: {status}, thông điệp: {header.get('status_text', '')}"
                            )
                            continue

                    # Việc nhận TranscriptionStarted cho biết máy chủ đã sẵn sàng nhận dữ liệu âm thanh
                    if message_name == "TranscriptionStarted":
                        self.server_ready = True
                        logger.bind(tag=TAG).debug(
                            "dịch vụ器đã准备 , 开始gửibộ nhớ đệmâm thanh..."
                        )

                        # Gửi âm thanh đệm
                        if conn.asr_audio:
                            for cached_pcm in conn.asr_audio[-10:]:
                                try:
                                    await self.asr_ws.send(cached_pcm)
                                except Exception as e:
                                    logger.bind(tag=TAG).warning(
                                        f"gửibộ nhớ đệmâm thanhthất bại: {e}"
                                    )
                                    break
                        continue
                    elif message_name == "SentenceEnd":
                        # Kết thúc câu (kích hoạt cho mỗi câu)
                        text = payload.get("result", "")
                        if text:
                            logger.bind(tag=TAG).info(f"识别到文本: {text}")

                            # Kết quả nhận dạng tích lũy ở chế độ thủ công
                            if conn.client_listen_mode == "manual":
                                if self.text:
                                    self.text += text
                                else:
                                    self.text = text

                                # Ở chế độ thủ công, quá trình xử lý chỉ được kích hoạt sau khi nhận được tín hiệu dừng (chỉ được xử lý một lần)
                                if conn.client_voice_stop:
                                    logger.bind(tag=TAG).debug(
                                        "nhận最终nhận dạngkết quả , 触发xử lý"
                                    )
                                    await self.handle_voice_stop(conn, audio_data)
                                    break
                            else:
                                # Bảo hiểm trực tiếp ở chế độ tự động
                                self.text = text
                                await self.handle_voice_stop(conn, audio_data)
                                break

                except asyncio.TimeoutError:
                    logger.bind(tag=TAG).error("接收kết quảquá thời gian chờ")
                    break
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).info("ASRdịch vụkết nốiđãđóng")
                    self.is_processing = False
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"xử lýkết quảthất bại: {str(e)}")
                    break

        except Exception as e:
            logger.bind(tag=TAG).error(f"kết quả转发thất bại: {str(e)}")
        finally:
            # Xóa bộ nhớ đệm âm thanh được kết nối
            await self._cleanup()
            conn.reset_audio_states()

    async def _send_stop_request(self):
        """gửi停止nhận dạngyêu cầu（不đóngkết nối）"""
        if self.asr_ws:
            try:
                # Dừng gửi âm thanh trước
                self.is_processing = False

                stop_msg = {
                    "header": {
                        "namespace": "SpeechTranscriber",
                        "name": "StopTranscription",
                        "message_id": uuid.uuid4().hex,
                        "task_id": self.task_id,
                        "appkey": self.appkey,
                    }
                }
                logger.bind(tag=TAG).debug("停止nhận dạngyêu cầuđãgửi")
                await self.asr_ws.send(json.dumps(stop_msg, ensure_ascii=False))
            except Exception as e:
                logger.bind(tag=TAG).error(f"gửi停止nhận dạngYêu cầu thất bại: {e}")

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
        """đóng资源"""
        await self._cleanup()
