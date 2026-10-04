import json
import gzip
import uuid
import asyncio
import websockets
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False  # Thêm cờ trạng thái xử lý
        self._is_stopping = False  # Thêm biển báo dừng để ngăn chặn tình trạng cuộc đua

        # Thông số cấu hình
        self.appid = str(config.get("appid"))
        self.access_token = config.get("access_token")
        # ID tài nguyên, được sử dụng để phân biệt các mô hình ASR khác nhau (phiên bản giờ mô hình 1.0 mặc định, phiên bản v2 sử dụng Seed-asr)
        self.resource_id = config.get("resource_id", "volc.bigasr.sauc.duration")

        self.boosting_table_name = config.get("boosting_table_name", "")
        self.correct_table_name = config.get("correct_table_name", "")
        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file

        # Cấu hình ASR động cơ núi lửa
        enable_multilingual = config.get("enable_multilingual", False)
        self.enable_multilingual = (
            False if str(enable_multilingual).lower() == "false" else True
        )
        if self.enable_multilingual:
            self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream"
        else:
            self.ws_url = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async"
        self.uid = config.get("uid", "streaming_asr_service")
        self.workflow = config.get(
            "workflow", "audio_in,resample,partition,vad,fe,decode,itn,nlu_punctuate"
        )
        self.result_type = config.get("result_type", "single")
        self.format = config.get("format", "pcm")
        self.codec = config.get("codec", "pcm")
        self.rate = config.get("sample_rate", 16000)
        # Tham số ngôn ngữ chỉ hợp lệ ở chế độ đa ngôn ngữ (bigmodel_nostream)
        self.language = config.get("language") if self.enable_multilingual else None
        self.bits = config.get("bits", 16)
        self.channel = config.get("channel", 1)
        self.auth_method = config.get("auth_method", "token")
        self.secret = config.get("secret", "access_secret")
        end_window_size = config.get("end_window_size")
        self.end_window_size = int(end_window_size) if end_window_size else 200

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(
        self, conn: "ConnectionHandler", pcm_frame, audio_have_voice
    ):
        # Đầu tiên hãy gọi phương thức của lớp cha để xử lý logic cơ bản
        await super().receive_audio(conn, pcm_frame, audio_have_voice)

        # Nếu lần này có âm thanh và chưa có kết nối nào được thiết lập trước đó
        if audio_have_voice and self.asr_ws is None and not self.is_processing:
            try:
                self.is_processing = True
                # Thiết lập kết nối WebSocket mới
                headers = self.token_auth() if self.auth_method == "token" else None
                logger.bind(tag=TAG).info(f"đangkết nốiASRdịch vụ , headers: {headers}")

                self.asr_ws = await websockets.connect(
                    self.ws_url,
                    additional_headers=headers,
                    max_size=1000000000,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=10,
                )

                # Gửi yêu cầu khởi tạo
                request_params = self.construct_request(str(uuid.uuid4()))
                try:
                    payload_bytes = str.encode(json.dumps(request_params))
                    payload_bytes = gzip.compress(payload_bytes)
                    full_client_request = self.generate_header()
                    full_client_request.extend((len(payload_bytes)).to_bytes(4, "big"))
                    full_client_request.extend(payload_bytes)

                    logger.bind(tag=TAG).info(f"gửikhởi tạoyêu cầu: {request_params}")
                    await self.asr_ws.send(full_client_request)

                    # Chờ phản hồi khởi tạo
                    init_res = await self.asr_ws.recv()
                    result = self.parse_response(init_res)
                    logger.bind(tag=TAG).info(f"nhậnkhởi tạophản hồi: {result}")

                    # Kiểm tra phản hồi khởi tạo
                    if "code" in result and result["code"] != 1000:
                        error_msg = f"Không thể khởi tạo dịch vụ ASR: {result.get('payload_msg', {}).get('error', 'Lỗi không xác định')}"
                        logger.bind(tag=TAG).error(error_msg)
                        raise Exception(error_msg)

                except Exception as e:
                    logger.bind(tag=TAG).error(f"gửikhởi tạoYêu cầu thất bại: {str(e)}")
                    if hasattr(e, "__cause__") and e.__cause__:
                        logger.bind(tag=TAG).error(
                            f"Lỗinguyên nhân: {str(e.__cause__)}"
                        )
                    raise e

                # Bắt đầu tác vụ không đồng bộ nhận kết quả ASR
                self.forward_task = asyncio.create_task(self._forward_asr_results(conn))

                # Gửi dữ liệu âm thanh được đệm
                if conn.asr_audio and len(conn.asr_audio) > 0:
                    for cached_pcm in conn.asr_audio[-10:]:
                        try:
                            payload = gzip.compress(cached_pcm)
                            audio_request = bytearray(
                                self.generate_audio_default_header()
                            )
                            audio_request.extend(len(payload).to_bytes(4, "big"))
                            audio_request.extend(payload)
                            await self.asr_ws.send(audio_request)
                        except Exception as e:
                            logger.bind(tag=TAG).info(
                                f"gửibộ nhớ đệmâm thanhdữ liệukhixảy raLỗi: {e}"
                            )

            except Exception as e:
                logger.bind(tag=TAG).error(f"thiết lậpASRKết nối thất bại: {str(e)}")
                if hasattr(e, "__cause__") and e.__cause__:
                    logger.bind(tag=TAG).error(f"Lỗinguyên nhân: {str(e.__cause__)}")
                if self.asr_ws:
                    await self.asr_ws.close()
                    self.asr_ws = None
                self.is_processing = False
                return

        # Gửi dữ liệu âm thanh hiện tại
        if self.asr_ws and self.is_processing and not self._is_stopping:
            try:
                payload = gzip.compress(pcm_frame)
                audio_request = bytearray(self.generate_audio_default_header())
                audio_request.extend(len(payload).to_bytes(4, "big"))
                audio_request.extend(payload)
                await self.asr_ws.send(audio_request)
            except Exception as e:
                logger.bind(tag=TAG).info(f"gửiâm thanhdữ liệukhixảy raLỗi: {e}")

    async def _forward_asr_results(self, conn: "ConnectionHandler"):
        try:
            while self.asr_ws and not conn.stop_event.is_set():
                # Lấy dữ liệu âm thanh của kết nối hiện tại
                audio_data = conn.asr_audio
                try:
                    response = await self.asr_ws.recv()
                    result = self.parse_response(response)
                    logger.bind(tag=TAG).debug(f"nhậnASRkết quả: {result}")

                    if "payload_msg" in result:
                        payload = result["payload_msg"]
                        # Kiểm tra xem có phải mã lỗi 1013 không (không có giọng nói hợp lệ)
                        if "code" in payload and payload["code"] == 1013:
                            # Xử lý âm thầm và không ghi lại nhật ký lỗi
                            continue

                        if "result" in payload:
                            utterances = payload["result"].get("utterances", [])
                            # Kiểm tra thời lượng và văn bản trống
                            if (
                                not self.enable_multilingual  # Lưu ý: Chế độ đa ngôn ngữ không trả về kết quả trung gian, bạn cần đợi kết quả cuối cùng
                                and payload.get("audio_info", {}).get("duration", 0)
                                > 2000
                                and not utterances
                                and not payload["result"].get("text")
                                and conn.client_listen_mode != "manual"
                            ):
                                logger.bind(tag=TAG).error(f"识别文本：空")
                                self.text = ""
                                if len(audio_data) > 15:  # Đảm bảo có đủ dữ liệu âm thanh
                                    await self.handle_voice_stop(conn, audio_data)
                                break

                            # Đặc biệt xử lý kết quả nhận dạng không có văn bản (ở chế độ thủ công, nhận dạng có thể đã hoàn tất nhưng phím chưa được nhả)
                            elif not payload["result"].get("text") and not utterances:
                                # Chế độ đa ngôn ngữ sẽ tiếp tục trả về văn bản trống cho đến khi trả về kết quả hoàn chỉnh cuối cùng, vì vậy cần phải loại trừ nó
                                if self.enable_multilingual:
                                    continue

                                if (
                                    conn.client_listen_mode == "manual"
                                    and conn.client_voice_stop
                                    and len(audio_data) > 15
                                ):
                                    logger.bind(tag=TAG).debug(
                                        "thông điệp结束nhận停止信号 , 触发xử lý"
                                    )
                                    await self.handle_voice_stop(conn, audio_data)
                                    break

                            for utterance in utterances:
                                if utterance.get("definite", False):
                                    current_text = utterance["text"]
                                    logger.bind(tag=TAG).info(
                                        f"识别到文本: {current_text}"
                                    )

                                    # Kết quả nhận dạng tích lũy ở chế độ thủ công
                                    if conn.client_listen_mode == "manual":
                                        if self.text:
                                            self.text += current_text
                                        else:
                                            self.text = current_text

                                        # Đã nhận được tín hiệu dừng giữa chừng khi đang nhận tin nhắn
                                        if (
                                            conn.client_voice_stop
                                            and len(audio_data) > 0
                                        ):
                                            logger.bind(tag=TAG).debug(
                                                "thông điệptrong途nhận停止信号 , 触发xử lý"
                                            )
                                            await self.handle_voice_stop(
                                                conn, audio_data
                                            )
                                        break
                                    else:
                                        # Bảo hiểm trực tiếp ở chế độ tự động
                                        self.text = current_text
                                        if len(audio_data) > 15:  # Đảm bảo có đủ dữ liệu âm thanh
                                            await self.handle_voice_stop(
                                                conn, audio_data
                                            )
                                    break
                        elif "error" in payload:
                            error_msg = payload.get("error", "Lỗi không xác định")
                            logger.bind(tag=TAG).error(
                                f"ASRdịch vụtrả vềLỗi: {error_msg}"
                            )
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
            if self.asr_ws:
                await self.asr_ws.close()
                self.asr_ws = None
            self.is_processing = False
            self._is_stopping = False
            # Đặt lại tất cả các trạng thái liên quan đến âm thanh
            conn.reset_audio_states()

    def stop_ws_connection(self):
        if self.asr_ws:
            asyncio.create_task(self.asr_ws.close())
            self.asr_ws = None
        self.is_processing = False
        self._is_stopping = False

    async def _send_stop_request(self):
        """gửi最后一个âm thanh帧以通知dịch vụ器结束"""
        self._is_stopping = True  # Đánh dấu nó là đã dừng trước để ngăn việc truyền âm thanh tiếp theo
        if self.asr_ws:
            try:
                # Gửi các khung âm thanh được gắn thẻ cuối (dữ liệu trống được nén bằng gzip)
                empty_payload = gzip.compress(b"")
                last_audio_request = bytearray(
                    self.generate_last_audio_default_header()
                )
                last_audio_request.extend(len(empty_payload).to_bytes(4, "big"))
                last_audio_request.extend(empty_payload)
                await self.asr_ws.send(last_audio_request)
                logger.bind(tag=TAG).debug("已发送结束音频帧")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"发送结束音频帧时出错: {e}")

    def construct_request(self, reqid):
        req = {
            "app": {
                "appid": self.appid,
                "token": self.access_token,
            },
            "user": {"uid": self.uid},
            "request": {
                "reqid": reqid,
                "workflow": self.workflow,
                "show_utterances": True,
                "result_type": self.result_type,
                "sequence": 1,
                "end_window_size": self.end_window_size,
                "corpus": {
                    "boosting_table_name": self.boosting_table_name,
                    "correct_table_name": self.correct_table_name,
                },
            },
            "audio": {
                "format": self.format,
                "codec": self.codec,
                "rate": self.rate,
                "bits": self.bits,
                "channel": self.channel,
                "sample_rate": self.rate,
            },
        }

        # Tham số ngôn ngữ chỉ được thêm ở chế độ đa ngôn ngữ
        if self.enable_multilingual and self.language:
            req["audio"]["language"] = self.language

        logger.bind(tag=TAG).debug(
            f"构造yêu cầuTham số: {json.dumps(req, ensure_ascii=False)}"
        )
        return req

    def token_auth(self):
        return {
            "X-Api-App-Key": self.appid,
            "X-Api-Access-Key": self.access_token,
            "X-Api-Resource-Id": self.resource_id,
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }

    def generate_header(
        self,
        version=0x01,
        message_type=0x01,
        message_type_specific_flags=0x00,
        serial_method=0x01,
        compression_type=0x01,
        reserved_data=0x00,
        extension_header: bytes = b"",
    ):
        header = bytearray()
        header_size = int(len(extension_header) / 4) + 1
        header.append((version << 4) | header_size)
        header.append((message_type << 4) | message_type_specific_flags)
        header.append((serial_method << 4) | compression_type)
        header.append(reserved_data)
        header.extend(extension_header)
        return header

    def generate_audio_default_header(self):
        return self.generate_header(
            version=0x01,
            message_type=0x02,
            message_type_specific_flags=0x00,
            serial_method=0x01,
            compression_type=0x01,
        )

    def generate_last_audio_default_header(self):
        return self.generate_header(
            version=0x01,
            message_type=0x02,
            message_type_specific_flags=0x02,
            serial_method=0x01,
            compression_type=0x01,
        )

    def parse_response(self, res: bytes) -> dict:
        try:
            # Kiểm tra độ dài phản hồi
            if len(res) < 4:
                logger.bind(tag=TAG).error(f"Dữ liệu phản hồi quá ngắn: {len(res)}")
                return {"error": "Dữ liệu phản hồi quá ngắn"}

            # Nhận tiêu đề tin nhắn
            header = res[:4]
            message_type = header[1] >> 4

            # Nếu đó là một phản hồi lỗi
            if message_type == 0x0F:  # SERVER_ERROR_RESPONSE
                code = int.from_bytes(res[4:8], "big", signed=False)
                msg_length = int.from_bytes(res[8:12], "big", signed=False)
                error_msg = json.loads(res[12:].decode("utf-8"))
                return {
                    "code": code,
                    "msg_length": msg_length,
                    "payload_msg": error_msg,
                }

            # Nhận dữ liệu JSON
            try:
                # Kiểm tra xem byte 8-11 có phải là trường độ dài JSON hợp lệ không
                # Định dạng: tiêu đề 4 byte + số thứ tự 4 byte + độ dài 4 byte + dữ liệu JSON
                length = int.from_bytes(res[8:12], "big")
                if length > 0 and length <= len(res) - 12:
                    # Có trường độ dài, bắt đầu từ byte 12 để đọc độ dài được chỉ định của JSON
                    json_data = res[12 : 12 + length].decode("utf-8")
                else:
                    # Không có trường độ dài hoặc độ dài không hợp lệ, hãy thử phân tích cú pháp trực tiếp
                    json_data = res[8:].decode("utf-8")
                result = json.loads(json_data)
                logger.bind(tag=TAG).debug(f"thành côngphân tíchJSONphản hồi: {result}")
                return {"payload_msg": result}
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                logger.bind(tag=TAG).error(f"JSONphân tíchthất bại: {str(e)}")
                logger.bind(tag=TAG).error(f"gốcdữ liệu: {res}")
                raise

        except Exception as e:
            logger.bind(tag=TAG).error(f"phân tíchphản hồithất bại: {str(e)}")
            logger.bind(tag=TAG).error(f"gốcphản hồidữ liệu: {res.hex()}")
            raise

    async def speech_to_text(self, opus_data, session_id, artifacts=None):
        result = self.text
        self.text = ""  # văn bản rõ ràng
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
