import os
import io
import sys
import time
import shutil
import psutil
import asyncio

from funasr import AutoModel
from config.logger import setup_logging
from typing import Optional, Tuple, List
from core.providers.asr.utils import lang_tag_filter
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType

TAG = __name__
logger = setup_logging()

MAX_RETRIES = 2
RETRY_DELAY = 1  # Độ trễ thử lại (giây)


# chụp đầu ra tiêu chuẩn
class CaptureOutput:
    def __enter__(self):
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        # Xuất nội dung đã chụp thông qua logger
        if self.output:
            logger.bind(tag=TAG).info(self.output.strip())


class ASRProvider(ASRProviderBase):
    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()

        # Phát hiện bộ nhớ, yêu cầu nhiều hơn 2G
        min_mem_bytes = 2 * 1024 * 1024 * 1024
        try:
            total_mem = psutil.virtual_memory().total
        except RuntimeError as e:
            logger.bind(tag=TAG).warning(
                f"lấyhệ thống内存thông tinthất bại , bỏ quaFunASR内存kiểm tra: {e}"
            )
        else:
            if total_mem < min_mem_bytes:
                logger.bind(tag=TAG).error(
                    f"可用内存不足2G , hiện tại仅有 {total_mem / (1024 * 1024):.2f} MB , 可能không thểkhởi độngFunASR"
                )

        self.interface_type = InterfaceType.LOCAL
        self.model_dir = config.get("model_dir")
        self.output_dir = config.get("output_dir")  # Tên khóa cấu hình đúng
        self.language = config.get("language", "auto")
        self.delete_audio_file = delete_audio_file

        # Đảm bảo thư mục đầu ra tồn tại
        os.makedirs(self.output_dir, exist_ok=True)
        with CaptureOutput():
            self.model = AutoModel(
                model=self.model_dir,
                vad_kwargs={"max_single_segment_time": 30000},
                disable_update=True,
                hub="hf",
                # device="cuda:0", # Kích hoạt khả năng tăng tốc GPU
            )

    async def speech_to_text(
        self, opus_data: List[bytes], session_id: str, artifacts=None
    ) -> Tuple[Optional[str], Optional[str]]:
        """语音转文本主处理逻辑"""
        retry_count = 0

        while retry_count < MAX_RETRIES:
            try:
                if artifacts is None:
                    return "", None

                # Nhận dạng giọng nói - sử dụng nhóm luồng để tránh chặn vòng lặp sự kiện
                start_time = time.time()
                result = await asyncio.to_thread(
                    self.model.generate,
                    input=artifacts.pcm_bytes,
                    cache={},
                    language=self.language,
                    use_itn=True,
                    batch_size_s=60,
                )
                text = lang_tag_filter(result[0]["text"])
                logger.bind(tag=TAG).debug(
                    f"giọng nóinhận dạng耗khi: {time.time() - start_time:.3f}s | kết quả: {text['content']}"
                )

                return text, artifacts.file_path

            except OSError as e:
                retry_count += 1
                if retry_count >= MAX_RETRIES:
                    logger.bind(tag=TAG).error(
                        f"giọng nóinhận dạngthất bại（đãthử lại{retry_count}次）: {e}",
                        exc_info=True,
                    )
                    return "", None
                logger.bind(tag=TAG).warning(
                    f"giọng nóinhận dạngthất bại , đangthử lại（{retry_count}/{MAX_RETRIES}）: {e}"
                )
                time.sleep(RETRY_DELAY)

            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"giọng nóinhận dạngthất bại: {e}", exc_info=True
                )
                return "", None
