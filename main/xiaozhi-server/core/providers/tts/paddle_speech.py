import io
import wave
import json
import base64
import asyncio
import websockets
import numpy as np
from datetime import datetime
from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase


TAG = __name__
logger = setup_logging()


class TTSProvider(TTSProviderBase):
    TTS_PARAM_CONFIG = [
        ("ttsVolume", "volume", 0, 3, 1.0, lambda v: round(float(v), 1)),
        ("ttsRate", "speed", 0, 3, 1.0, lambda v: round(float(v), 1)),
    ]

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.url = config.get(
            "url", "ws://192.168.1.10:8092/paddlespeech/tts/streaming"
        )
        self.protocol = config.get("protocol", "websocket")

        if config.get("private_voice"):
            self.spk_id = int(config.get("private_voice"))
        else:
            self.spk_id = int(config.get("spk_id", "0"))

        speed = config.get("speed", 1.0)
        self.speed = float(speed) if speed else 1.0

        volume = config.get("volume", 1.0)
        self.volume = float(volume) if volume else 1.0

        self.delete_audio_file = config.get("delete_audio", True)

        # Áp dụng điều chỉnh tỷ lệ phần trăm nếu có, nếu không thì sử dụng cấu hình công khai
        self._apply_percentage_params(config)

        if not self.delete_audio_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_path = config.get("save_path")
            if save_path:
                if not save_path.endswith(".wav"):
                    save_path = f"{save_path}_{timestamp}.wav"
                else:
                    other_path = save_path[:-4]
                    save_path = f"{other_path}_{timestamp}.wav"
                self.save_path = save_path
            else:
                self.save_path = f"./streaming_tts_{timestamp}.wav"
        else:
            self.save_path = None

    async def pcm_to_wav(
        self,
        pcm_data: bytes,
        sample_rate: int = 24000,
        num_channels: int = 1,
        bits_per_sample: int = 16,
    ) -> bytes:
        """
        sẽ PCM dữ liệu转换为 WAV 文件并trả về字节dữ liệu
        :param pcm_data: PCM dữ liệu（gốc字节流）
        :param sample_rate: âm thanh采样率 , 默认为24000
        :param num_channels: 声道数 , 默认为单声道
        :param bits_per_sample: 每个样本的位数 , 默认为16
        :return: WAV định dạng的字节dữ liệu
        """
        byte_data = np.frombuffer(pcm_data, dtype=np.int16)  # PCM 16-bit
        wav_io = io.BytesIO()

        with wave.open(wav_io, "wb") as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(bits_per_sample // 8)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(byte_data.tobytes())

        return wav_io.getvalue()

    async def text_to_speak(self, text, output_file):
        if self.protocol == "websocket":
            return await self.text_streaming(text, output_file)
        else:
            raise ValueError("Unsupported protocol. Please use 'websocket' or 'http'.")

    async def text_streaming(self, text, output_file):
        try:
            # Kết nối không đồng bộ với máy chủ WebSocket bằng websockets
            async with websockets.connect(self.url) as ws:
                # Gửi yêu cầu bắt đầu
                start_request = {"task": "tts", "signal": "start"}
                await ws.send(json.dumps(start_request))

                # Nhận phản hồi bắt đầu và trích xuất session_id
                start_response = await ws.recv()
                start_response = json.loads(start_response)  # Phân tích phản hồi JSON
                if start_response.get("status") != 0:
                    raise Exception(f"Kết nối thất bại: {start_response.get('signal')}")

                session_id = start_response.get("session")

                # Gửi dữ liệu văn bản được tổng hợp
                data_request = {
                    "text": text,
                    "spk_id": self.spk_id,
                }
                await ws.send(json.dumps(data_request))

                audio_chunks = b""
                timeout_seconds = self.tts_timeout
                try:
                    while True:
                        response = await asyncio.wait_for(
                            ws.recv(), timeout=timeout_seconds
                        )
                        response = json.loads(response)  # Phân tích phản hồi JSON
                        status = response.get("status")

                        if status == 2:  # gói cuối cùng
                            break
                        else:
                            # Nối dữ liệu âm thanh (dữ liệu PCM được mã hóa base64)
                            audio_chunks += base64.b64decode(response.get("audio"))
                except asyncio.TimeoutError:
                    raise Exception(
                        f"WebSocket hết thời gian chờ: chờ âm thanh quá {timeout_seconds} giây"
                    )

                # Chuyển đổi dữ liệu PCM được nối sang định dạng WAV
                wav_data = await self.pcm_to_wav(audio_chunks)

                # yêu cầu kết thúc
                end_request = {
                    "task": "tts",
                    "signal": "end",
                    "session": session_id,  # ID phiên phải khớp với ID trong yêu cầu bắt đầu
                }
                await ws.send(json.dumps(end_request))

                # Nhận phản hồi cuối cùng để tránh ngoại lệ ném dịch vụ
                await ws.recv()

                # Xác định có lưu tập tin dựa trên cấu hình hay không
                if not self.delete_audio_file and self.save_path:
                    with open(self.save_path, "wb") as f:
                        f.write(wav_data)
                    logger.bind(tag=TAG).info(f"âm thanh文件đãlưu到: {self.save_path}")

                # Trả lại hoặc lưu dữ liệu âm thanh
                if output_file:
                    with open(output_file, "wb") as file_to_save:
                        file_to_save.write(wav_data)
                else:
                    return wav_data

        except Exception as e:
            raise Exception(
                f"Error during TTS WebSocket request: {e} while processing text: {text}"
            )
