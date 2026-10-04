import asyncio
import time
import aiohttp
import requests
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict
from config.logger import setup_logging
from core.utils.cache.manager import cache_manager
from core.utils.cache.config import CacheType

TAG = __name__
logger = setup_logging()


class VoiceprintProvider:
    """声纹nhận dạngdịch vụ提供者"""

    def __init__(self, config: dict):
        self.original_url = config.get("url", "")
        self.speakers = config.get("speakers", [])
        self.speaker_map = self._parse_speakers()
        # Ngưỡng tương tự nhận dạng giọng nói, mặc định 0,4
        self.similarity_threshold = float(config.get("similarity_threshold", 0.4))

        # Phân tích địa chỉ và khóa API
        self.api_url = None
        self.api_key = None
        self.speaker_ids = []

        if not self.original_url:
            logger.bind(tag=TAG).warning(
                "声纹nhận dạngURL未cấu hình , 声纹nhận dạngsẽ被禁用"
            )
            self.enabled = False
        else:
            # Phân tích URL và khóa
            parsed_url = urlparse(self.original_url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # Trích xuất khóa từ tham số truy vấn
            query_params = parse_qs(parsed_url.query)
            self.api_key = query_params.get("key", [""])[0]

            if not self.api_key:
                logger.bind(tag=TAG).error(
                    "URLtrongkhông tìm thấykeytham số , 声纹nhận dạngsẽ被禁用"
                )
                self.enabled = False
            else:
                # Xây dựng địa chỉ giao diện nhận dạng
                self.api_url = f"{base_url}/voiceprint/identify"

                # Trích xuất loa_ids
                for speaker_str in self.speakers:
                    try:
                        parts = speaker_str.split(",", 2)
                        if len(parts) >= 1:
                            speaker_id = parts[0].strip()
                            self.speaker_ids.append(speaker_id)
                    except Exception:
                        continue

                # Kiểm tra xem có cấu hình loa hợp lệ không
                if not self.speaker_ids:
                    logger.bind(tag=TAG).warning(
                        "未cấu hình有效的người nói , 声纹nhận dạngsẽ被禁用"
                    )
                    self.enabled = False
                else:
                    # Thực hiện kiểm tra tình trạng để xác minh rằng máy chủ có sẵn
                    if self._check_server_health():
                        self.enabled = True
                        logger.bind(tag=TAG).info(
                            f"声纹识别已启用: API={self.api_url}, 说话人={len(self.speaker_ids)}个, 相似度阈值={self.similarity_threshold}"
                        )
                    else:
                        self.enabled = False
                        logger.bind(tag=TAG).warning(
                            f"声纹nhận dạngdịch vụ器不可用 , 声纹nhận dạngđã禁用: {self.api_url}"
                        )

    def _parse_speakers(self) -> Dict[str, Dict[str, str]]:
        """phân tíchngười nóicấu hình"""
        speaker_map = {}
        for speaker_str in self.speakers:
            try:
                parts = speaker_str.split(",", 2)
                if len(parts) >= 3:
                    speaker_id, name, description = (
                        parts[0].strip(),
                        parts[1].strip(),
                        parts[2].strip(),
                    )
                    speaker_map[speaker_id] = {"name": name, "description": description}
            except Exception as e:
                logger.bind(tag=TAG).warning(
                    f"phân tíchngười nóicấu hìnhthất bại: {speaker_str}, Lỗi: {e}"
                )
        return speaker_map

    def _check_server_health(self) -> bool:
        """kiểm tra声纹nhận dạngdịch vụ器健康trạng thái"""
        if not self.api_url or not self.api_key:
            return False

        cache_key = f"{self.api_url}:{self.api_key}"

        # Kiểm tra bộ đệm
        cached_result = cache_manager.get(CacheType.VOICEPRINT_HEALTH, cache_key)
        if cached_result is not None:
            logger.bind(tag=TAG).debug(
                f"使用bộ nhớ đệm的健康trạng thái: {cached_result}"
            )
            return cached_result

        # Bộ nhớ đệm hết hạn hoặc không tồn tại
        logger.bind(tag=TAG).info("thực thi声纹dịch vụ器健康kiểm tra")

        try:
            # URL kiểm tra sức khỏe
            parsed_url = urlparse(self.api_url)
            health_url = f"{parsed_url.scheme}://{parsed_url.netloc}/voiceprint/health?key={self.api_key}"

            # Gửi yêu cầu kiểm tra sức khỏe
            response = requests.get(health_url, timeout=3)

            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "healthy":
                    logger.bind(tag=TAG).info("声纹nhận dạngdịch vụ器健康kiểm tra通过")
                    is_healthy = True
                else:
                    logger.bind(tag=TAG).warning(
                        f"声纹nhận dạngdịch vụ器trạng tháisự cố: {result}"
                    )
                    is_healthy = False
            else:
                logger.bind(tag=TAG).warning(
                    f"声纹nhận dạngdịch vụ器健康kiểm trathất bại: HTTP {response.status_code}"
                )
                is_healthy = False

        except requests.exceptions.ConnectTimeout:
            logger.bind(tag=TAG).warning(
                "声纹nhận dạngdịch vụ器kết nốiquá thời gian chờ"
            )
            is_healthy = False
        except requests.exceptions.ConnectionError:
            logger.bind(tag=TAG).warning("声纹nhận dạngdịch vụ器kết nối被拒绝")
            is_healthy = False
        except Exception as e:
            logger.bind(tag=TAG).warning(
                f"声纹nhận dạngdịch vụ器健康kiểm trasự cố: {e}"
            )
            is_healthy = False

        # Kết quả lưu vào bộ đệm bằng trình quản lý bộ đệm chung
        cache_manager.set(CacheType.VOICEPRINT_HEALTH, cache_key, is_healthy)
        logger.bind(tag=TAG).info(f"健康kiểm trakết quảđãbộ nhớ đệm: {is_healthy}")

        return is_healthy

    async def identify_speaker(
        self, audio_data: bytes, session_id: str
    ) -> Optional[str]:
        """识别说话人"""
        if not self.enabled or not self.api_url or not self.api_key:
            logger.bind(tag=TAG).debug(
                "声纹nhận dạng功能đã禁用或未cấu hình , bỏ quanhận dạng"
            )
            return None

        try:
            api_start_time = time.monotonic()

            # Chuẩn bị tiêu đề yêu cầu
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            }

            # Chuẩn bị dữ liệu nhiều phần/biểu mẫu dữ liệu
            data = aiohttp.FormData()
            data.add_field("speaker_ids", ",".join(self.speaker_ids))
            data.add_field(
                "file", audio_data, filename="audio.wav", content_type="audio/wav"
            )

            timeout = aiohttp.ClientTimeout(total=10)

            # yêu cầu mạng
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    self.api_url, headers=headers, data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        speaker_id = result.get("speaker_id")
                        score = result.get("score", 0)
                        total_elapsed_time = time.monotonic() - api_start_time

                        logger.bind(tag=TAG).info(
                            f"声纹识别耗时: {total_elapsed_time:.3f}s"
                        )

                        # Kiểm tra ngưỡng tương tự
                        if score < self.similarity_threshold:
                            logger.bind(tag=TAG).warning(
                                f"声纹识别相似度{score:.3f}低于阈值{self.similarity_threshold}"
                            )
                            return "Người nói chưa xác định"

                        if speaker_id and speaker_id in self.speaker_map:
                            result_name = self.speaker_map[speaker_id]["name"]
                            logger.bind(tag=TAG).info(
                                f"声纹识别成功: {result_name} (相似度: {score:.3f})"
                            )
                            return result_name
                        else:
                            logger.bind(tag=TAG).warning(
                                f"未识别的说话人ID: {speaker_id}"
                            )
                            return "Người nói chưa xác định"
                    else:
                        logger.bind(tag=TAG).error(
                            f"声纹nhận dạngAPILỗi: HTTP {response.status}"
                        )
                        return None

        except asyncio.TimeoutError:
            elapsed = time.monotonic() - api_start_time
            logger.bind(tag=TAG).error(
                f"声纹nhận dạngquá thời gian chờ: {elapsed:.3f}s"
            )
            return None
        except Exception as e:
            elapsed = time.monotonic() - api_start_time
            logger.bind(tag=TAG).error(f"声纹nhận dạngthất bại: {e}")
            return None
