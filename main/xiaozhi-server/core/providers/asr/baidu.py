import time
import os
from typing import Optional, Tuple, List
from aip import AipSpeech
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool = True):
        super().__init__()
        self.interface_type = InterfaceType.NON_STREAM
        self.app_id = config.get("app_id")
        self.api_key = config.get("api_key")
        self.secret_key = config.get("secret_key")

        dev_pid = config.get("dev_pid", "1537")
        self.dev_pid = int(dev_pid) if dev_pid else 1537

        self.output_dir = config.get("output_dir")
        self.delete_audio_file = delete_audio_file

        self.client = AipSpeech(str(self.app_id), self.api_key, self.secret_key)

        # Đảm bảo thư mục đầu ra tồn tại
        os.makedirs(self.output_dir, exist_ok=True)

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, artifacts=None
    ) -> Tuple[Optional[str], Optional[str]]:
        """sẽgiọng nóidữ liệu转换为văn bản"""
        if not opus_data:
            logger.bind(tag=TAG).warning("âm thanhdữ liệu为空！")
            return None, None

        try:
            # Kiểm tra xem cấu hình đã được đặt chưa
            if not self.app_id or not self.api_key or not self.secret_key:
                logger.bind(tag=TAG).error(
                    "百度giọng nóinhận dạngcấu hình未设置 , không thểtiến hànhnhận dạng"
                )
                return None, None

            if artifacts is None:
                return "", None

            start_time = time.time()
            # Xác định các tập tin cục bộ
            result = self.client.asr(
                artifacts.pcm_bytes,
                "pcm",
                16000,
                {
                    "dev_pid": str(self.dev_pid),
                },
            )

            if result and result["err_no"] == 0:
                logger.bind(tag=TAG).debug(
                    f"百度giọng nóinhận dạng耗khi: {time.time() - start_time:.3f}s | kết quả: {result}"
                )
                result = result["result"][0]
                return result, artifacts.file_path
            else:
                raise Exception(
                    f"Nhận dạng giọng nói Baidu thất bại, mã lỗi: {result['err_no']}, thông báo lỗi: {result['err_msg']}"
                )
                return None, artifacts.file_path

        except Exception as e:
            logger.bind(tag=TAG).error(f"xử lýâm thanhkhixảy raLỗi！{e}", exc_info=True)
            return None, None
