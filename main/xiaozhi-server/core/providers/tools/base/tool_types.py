"""công cụhệ thống的loại定义"""

from enum import Enum

from dataclasses import dataclass
from typing import Any, Dict, Optional
from plugins_func.register import Action


class ToolType(Enum):
    """công cụloại枚举"""

    SERVER_PLUGIN = "server_plugin"  # Plugin phía máy chủ
    SERVER_MCP = "server_mcp"  # MCP phía máy chủ
    DEVICE_IOT = "device_iot"  # IoT phía thiết bị
    DEVICE_MCP = "device_mcp"  # MCP phía thiết bị
    MCP_ENDPOINT = "mcp_endpoint"  # MCP là một công cụ


@dataclass
class ToolDefinition:
    """công cụ定义"""

    name: str  # Tên công cụ
    description: Dict[str, Any]  # Mô tả công cụ theo định dạng gọi hàm OpenAI
    tool_type: ToolType  # Loại công cụ
    parameters: Optional[Dict[str, Any]] = None  # Tham số bổ sung
