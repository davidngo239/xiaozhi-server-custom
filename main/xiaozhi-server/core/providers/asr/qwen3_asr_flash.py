import os
from typing import Optional, Tuple, List
import dashscope
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

tag = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        # Loại tải lên tệp âm thanh, phát trực tiếp đầu ra nhận dạng văn bản
        self.interface_type = InterfaceType.NON_STREAM
        """Qwen3-ASR-Flash ASR初始化"""

        # Thông số cấu hình
        self.api_key = config.get("api_key")
        if not self.api_key:
            raise ValueError("Qwen3-ASR-Flash cần cấu hình api_key")

        self.model_name = config.get("model_name", "qwen3-asr-flash")
        self.output_dir = config.get("output_dir", "./audio_output")
        self.delete_audio_file = delete_audio_file

        # Cấu hình tùy chọn ASR
        self.enable_lid = config.get("enable_lid", True)  # Tự động phát hiện ngôn ngữ
        self.enable_itn = config.get("enable_itn", True)  # Chuẩn hóa văn bản nghịch đảo
        self.language = config.get("language", None)  # Chỉ định ngôn ngữ, được phát hiện tự động theo mặc định
        self.context = config.get("context", "")  # Thông tin ngữ cảnh để cải thiện độ chính xác nhận dạng

        # Đảm bảo thư mục đầu ra tồn tại
        os.makedirs(self.output_dir, exist_ok=True)

    def prefers_temp_file(self) -> bool:
        return True

    def requires_file(self) -> bool:
        return True

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, artifacts=None
    ) -> Tuple[Optional[str], Optional[str]]:
        """sẽgiọng nóidữ liệu转换为văn bản"""
        temp_file_path = None
        file_path = None
        try:
            if artifacts is None:
                return "", None
            temp_file_path = artifacts.temp_path
            file_path = artifacts.file_path
            if not temp_file_path:
                return "", file_path
            # Xây dựng thông báo yêu cầu
            messages = [{"role": "user", "content": [{"audio": temp_file_path}]}]

            # Nếu có thông tin ngữ cảnh, hãy thêm thông báo hệ thống
            if self.context:
                messages.insert(
                    0, {"role": "system", "content": [{"text": self.context}]}
                )

            # Chuẩn bị cho các tùy chọn ASR
            asr_options = {"enable_lid": self.enable_lid, "enable_itn": self.enable_itn}

            # Nếu một ngôn ngữ được chỉ định, hãy thêm nó vào các tùy chọn
            if self.language:
                asr_options["language"] = self.language

            # Đặt khóa API
            dashscope.api_key = self.api_key

            # Gửi yêu cầu phát trực tuyến
            response = dashscope.MultiModalConversation.call(
                model=self.model_name,
                messages=messages,
                result_format="message",
                asr_options=asr_options,
                stream=True,
            )

            # Xử lý phản hồi phát trực tuyến
            full_text = ""
            for chunk in response:
                try:
                    text = chunk["output"]["choices"][0]["message"].content[0]["text"]
                    # Cập nhật toàn văn mới nhất
                    full_text = text.strip()
                except:
                    pass

            return full_text, file_path

        except Exception as e:
            logger.bind(tag=tag).error(f"giọng nóinhận dạngthất bại: {e}")
            return "", file_path
