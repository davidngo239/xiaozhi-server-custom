"""
bộ nhớ đệmcấu hình管理
"""

from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass
from .strategies import CacheStrategy


class CacheType(Enum):
    """bộ nhớ đệmloại枚举"""

    LOCATION = "location"
    WEATHER = "weather"
    LUNAR = "lunar"
    INTENT = "intent"
    IP_INFO = "ip_info"
    CONFIG = "config"
    DEVICE_PROMPT = "device_prompt"
    VOICEPRINT_HEALTH = "voiceprint_health"  # Kiểm tra sức khỏe nhận dạng giọng nói
    AUDIO_DATA = "audio_data"  # Bộ đệm dữ liệu âm thanh


@dataclass
class CacheConfig:
    """bộ nhớ đệmcấu hình类"""

    strategy: CacheStrategy = CacheStrategy.TTL
    ttl: Optional[float] = 300  # Mặc định 5 phút
    max_size: Optional[int] = 1000  # Tối đa mặc định là 1000 mục
    cleanup_interval: float = 60  # Khoảng thời gian dọn dẹp (giây)

    @classmethod
    def for_type(cls, cache_type: CacheType) -> "CacheConfig":
        """根据bộ nhớ đệmloạitrả về预设cấu hình"""
        configs = {
            CacheType.LOCATION: cls(
                strategy=CacheStrategy.TTL,
                ttl=None,
                max_size=1000,  # Vô hiệu hóa thủ công
            ),
            CacheType.IP_INFO: cls(
                strategy=CacheStrategy.TTL,
                ttl=86400,
                max_size=1000,  # 24 giờ
            ),
            CacheType.WEATHER: cls(
                strategy=CacheStrategy.TTL,
                ttl=28800,
                max_size=1000,  # 8 giờ
            ),
            CacheType.LUNAR: cls(
                strategy=CacheStrategy.TTL,
                ttl=2592000,
                max_size=365,  # Hết hạn sau 30 ngày
            ),
            CacheType.INTENT: cls(
                strategy=CacheStrategy.TTL_LRU,
                ttl=600,
                max_size=1000,  # 10 phút
            ),
            CacheType.CONFIG: cls(
                strategy=CacheStrategy.FIXED_SIZE,
                ttl=None,
                max_size=20,  # Vô hiệu hóa thủ công
            ),
            CacheType.DEVICE_PROMPT: cls(
                strategy=CacheStrategy.TTL,
                ttl=None,
                max_size=1000,  # Vô hiệu hóa thủ công
            ),
            CacheType.VOICEPRINT_HEALTH: cls(
                strategy=CacheStrategy.TTL,
                ttl=600,
                max_size=100,  # Hết hạn sau 10 phút
            ),
            CacheType.AUDIO_DATA: cls(
                strategy=CacheStrategy.TTL,
                ttl=600,
                max_size=100,  # Hết hạn sau 10 phút
            ),
        }
        return configs.get(cache_type, cls())
