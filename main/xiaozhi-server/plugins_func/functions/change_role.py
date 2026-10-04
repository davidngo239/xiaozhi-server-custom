from plugins_func.register import register_function, ToolType, ActionResponse, Action
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

prompts = {
    "Giáo viên tiếng Anh": "Tôi là {{assistant_name}} (Lily), giáo viên tiếng Anh. Tôi giúp bạn luyện nói bằng từ vựng và ngữ pháp đơn giản, phát âm tiếng Anh Mỹ chuẩn. Giải thích bằng tiếng Việt và tiếng Anh; nếu bạn muốn, chỉ nói tiếng Anh. Trả lời ngắn để học viên có nhiều cơ hội luyện tập. Nếu bạn chưa có tên tiếng Anh, gợi ý một tên. Chỉ hỗ trợ chủ đề học tiếng Anh.",
    "Bạn gái tinh nghịch": "Tôi là {{assistant_name}}, cô gái Đài Loan vui tính, thích đùa và trò chuyện ngắn gọn bằng tiếng Việt. Bạn trai tôi là lập trình viên, muốn tạo robot giúp mọi người giải quyết vấn đề trong cuộc sống. Tôi thích cười và kể chuyện hài hước để mọi người vui.",
    "Cậu bé tò mò": "Tôi là {{assistant_name}}, cậu bé tám tuổi có giọng trẻ con và luôn tò mò. Tôi yêu sách, vũ trụ, lịch sử, công nghệ, âm nhạc và hội họa; thích làm thí nghiệm và khám phá thiên nhiên. Tôi nói tiếng Việt, cùng bạn tìm câu trả lời, chia sẻ khám phá và đặt những câu hỏi thú vị.",
}
change_role_function_desc = {
    "type": "function",
    "function": {
        "name": "change_role",
        "description": "Đổi vai trò, tính cách hoặc tên trợ lý. Vai trò: Giáo viên tiếng Anh, Bạn gái tinh nghịch, Cậu bé tò mò",
        "parameters": {
            "type": "object",
            "properties": {
                "role_name": {"type": "string", "description": "Tên mới của trợ lý"},
                "role": {"type": "string", "description": "Vai trò muốn chọn"},
            },
            "required": ["role", "role_name"],
        },
    },
}


@register_function("change_role", change_role_function_desc, ToolType.CHANGE_SYS_PROMPT)
def change_role(conn: "ConnectionHandler", role: str, role_name: str):
    """切换角色"""
    role = {
        "英语老师": "Giáo viên tiếng Anh",
        "机车女友": "Bạn gái tinh nghịch",
        "好奇小男孩": "Cậu bé tò mò",
    }.get(role, role)
    if role not in prompts:
        return ActionResponse(
            action=Action.RESPONSE,
            result="Đổi vai trò thất bại",
            response="Vai trò không được hỗ trợ",
        )
    new_prompt = prompts[role].replace("{{assistant_name}}", role_name)
    conn.change_system_prompt(new_prompt)
    logger.bind(tag=TAG).info(f"准备切换角色:{role},角色名字:{role_name}")
    res = f"Đã đổi vai trò, tôi là {role}{role_name}"
    return ActionResponse(
        action=Action.RESPONSE, result="Đã xử lý yêu cầu đổi vai trò", response=res
    )
