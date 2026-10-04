"""
bộ nhớ đệm策略和dữ liệu结构定义
"""

import time
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass


class CacheStrategy(Enum):
    """缓存策略枚举"""

    TTL = "ttl"  # Hết hạn dựa trên thời gian
    LRU = "lru"  # Ít được sử dụng gần đây nhất
    FIXED_SIZE = "fixed_size"  # kích thước cố định
    TTL_LRU = "ttl_lru"  # Chiến lược lai TTL + LRU


@dataclass
class CacheEntry:
    """bộ nhớ đệm条目dữ liệu结构"""

    value: Any
    timestamp: float
    ttl: Optional[float] = None  # Thời gian sống (giây)
    access_count: int = 0
    last_access: float = None

    def __post_init__(self):
        if self.last_access is None:
            self.last_access = self.timestamp

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def touch(self):
        """更新访问时间和计数"""
        self.last_access = time.time()
        self.access_count += 1
