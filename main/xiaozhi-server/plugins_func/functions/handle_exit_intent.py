from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

handle_exit_intent_function_desc = {
    "type": "function",
    "function": {
        "name": "handle_exit_intent",
        "description": "Gọi khi người dùng muốn kết thúc hội thoại hoặc thoát hệ thống",
        "parameters": {
            "type": "object",
            "properties": {
                "say_goodbye": {
                    "type": "string",
                    "description": "Lời tạm biệt thân thiện để kết thúc hội thoại",
                }
            },
            "required": ["say_goodbye"],
        },
    },
}


@register_function(
    "handle_exit_intent", handle_exit_intent_function_desc, ToolType.SYSTEM_CTL
)
def handle_exit_intent(conn: "ConnectionHandler", say_goodbye: str | None = None):
    # Xử lý ý định thoát
    try:
        if say_goodbye is None:
            say_goodbye = "Tạm biệt, chúc bạn một ngày vui vẻ!"
        if not conn.close_after_chat:
            conn.close_after_chat = True
        logger.bind(tag=TAG).info(f"Đã xử lý yêu cầu kết thúc:{say_goodbye}")
        return ActionResponse(
            action=Action.RESPONSE,
            result="Đã xử lý yêu cầu kết thúc",
            response=say_goodbye,
        )
    except Exception as e:
        logger.bind(tag=TAG).error(f"xử lý退出ý địnhLỗi: {e}")
        return ActionResponse(
            action=Action.NONE, result="Không thể xử lý yêu cầu kết thúc", response=""
        )
