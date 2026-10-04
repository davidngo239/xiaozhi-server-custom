"""công cụthực thi器基类定义"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from .tool_types import ToolDefinition
from plugins_func.register import ActionResponse


class ToolExecutor(ABC):
    """công cụthực thi器抽象基类"""

    @abstractmethod
    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """thực thicông cụgọi"""
        pass

    @abstractmethod
    def get_tools(self) -> Dict[str, ToolDefinition]:
        """lấy该thực thi器管理的所有công cụ"""
        pass

    @abstractmethod
    def has_tool(self, tool_name: str) -> bool:
        """kiểm tra是否有指定công cụ"""
        pass
