from abc import ABC, abstractmethod
from typing import List, Dict
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class IntentProviderBase(ABC):
    def __init__(self, config):
        self.config = config

    def set_llm(self, llm):
        self.llm = llm
        # Nhận tên model và thông tin loại
        model_name = getattr(llm, "model_name", str(llm.__class__.__name__))
        # Giữ nhật ký chi tiết hơn
        logger.bind(tag=TAG).info(f"意图识别设置LLM: {model_name}")

    @abstractmethod
    async def detect_intent(self, conn, dialogue_history: List[Dict], text: str) -> str:
        """
        kiểm trangười dùng最后一句话的ý định
        Args:
            dialogue_history: 对话历史记录列表 , 每条记录包含role和content
        Returns:
            trả vềnhận dạng出的ý định , định dạng为:
            - "继续聊天"
            - "结束聊天"
            - "播放音乐 歌名" 或 "随机播放音乐"
            - "查询天气 地点名" 或 "查询天气 [hiện tại位置]"
        """
        pass
