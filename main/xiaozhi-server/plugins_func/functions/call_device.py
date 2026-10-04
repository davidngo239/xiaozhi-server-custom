"""呼叫thiết bịcông cụ"""

import httpx
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

call_device_function_desc = {
    "type": "function",
    "function": {
        "name": "call_device",
        "description": (
            "Thiết lập cuộc gọi thoại giữa các thiết bị. Khi người dùng yêu cầu gọi hoặc kết nối với một người, nickname là tên người đó. Khi hệ thống báo có cuộc gọi đến, chỉ gọi công cụ nếu người dùng đồng ý nhận cuộc gọi rõ ràng; nickname lấy từ thông báo cuộc gọi. Nếu ý định nhận hay từ chối chưa rõ, hỏi lại trước khi gọi công cụ."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "nickname": {
                    "type": "string",
                    "description": "Tên ghi chú của thiết bị cần gọi, ví dụ: Minh, An",
                },
            },
            "required": ["nickname"],
        },
    },
}


async def _request_api(url: str, params: dict, headers: dict):
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        return await client.get(url, params=params, headers=headers)


def _failed_reply(msg: str) -> ActionResponse:
    return ActionResponse(action=Action.RESPONSE, response=msg)


def _is_answering(conn: "ConnectionHandler") -> bool:
    """检查是否为接听模式（conn.incoming_call 不为空）"""
    return hasattr(conn, "incoming_call") and conn.incoming_call is not None


@register_function("call_device", call_device_function_desc, ToolType.SYSTEM_CTL)
async def call_device(conn: "ConnectionHandler", nickname: str):
    caller_mac = conn.headers.get("device-id")
    if not caller_mac:
        return _failed_reply("Không lấy được địa chỉ MAC của thiết bị")

    api_config = conn.config.get("manager-api", {})
    api_url = api_config.get("url")
    api_secret = api_config.get("secret")
    if not api_url or not api_secret:
        logger.bind(tag=TAG).error("Thiếu cấu hình API quản lý thiết bị")
        return _failed_reply("Lỗi cấu hình, vui lòng thử lại sau")

    headers = {"Authorization": f"Bearer {api_secret}"}

    # Phân biệt xem đó là cuộc gọi đang hoạt động hay cuộc gọi đến
    is_answer = _is_answering(conn)
    params = {"callerMac": caller_mac, "nickname": nickname}
    if is_answer:
        params["answer"] = "true"

    # Tìm kiếm sổ địa chỉ của bạn và thực hiện cuộc gọi
    try:
        resp = await _request_api(
            f"{api_url}/device/address-book/call",
            params=params,
            headers=headers,
        )
        result = resp.json()
    except httpx.HTTPError as e:
        logger.bind(tag=TAG).error(f"Yêu cầu gọi thất bại: {e}")
        return _failed_reply("Gọi thất bại, vui lòng thử lại sau")

    if result.get("code") != 0:
        return _failed_reply(result.get("msg", "Gọi thất bại"))

    data = result.get("data", {})
    if data.get("status") == "error":
        return _failed_reply(data.get("message"))

    if is_answer:
        return ActionResponse(action=Action.NONE, response="Đã nhận cuộc gọi")
    else:
        conn.calling = True
        return ActionResponse(
            action=Action.NONE,
            response=f"Đang gọi {nickname}, vui lòng chờ bên kia trả lời",
        )
