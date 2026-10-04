from enum import Enum


class TextMessageType(Enum):
    """thông điệploại枚举"""

    HELLO = "hello"
    ABORT = "abort"
    LISTEN = "listen"
    IOT = "iot"
    MCP = "mcp"
    SERVER = "server"
    PING = "ping"
