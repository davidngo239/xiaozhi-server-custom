from abc import ABC, abstractmethod
from typing import Optional


class VADProviderBase(ABC):
    @abstractmethod
    def is_vad(self, conn, data) -> bool:
        """kiểm traâm thanhdữ liệutrong的giọng nói活动"""
        pass
