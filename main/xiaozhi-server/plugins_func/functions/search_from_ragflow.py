import json
import httpx
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

# Xác định các mẫu mô tả chức năng cơ bản
SEARCH_FROM_RAGFLOW_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "search_from_ragflow",
        "description": "Tra cứu thông tin trong kho tri thức",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "Câu hỏi cần tra cứu"}
            },
            "required": ["question"],
        },
    },
}


@register_function(
    "search_from_ragflow", SEARCH_FROM_RAGFLOW_FUNCTION_DESC, ToolType.SYSTEM_CTL
)
async def search_from_ragflow(conn: "ConnectionHandler", question=None):
    # Đảm bảo các tham số chuỗi xử lý mã hóa chính xác
    if question and isinstance(question, str):
        # Đảm bảo tham số câu hỏi là chuỗi được mã hóa UTF-8
        pass
    else:
        question = str(question) if question is not None else ""

    ragflow_config = conn.config.get("plugins", {}).get("search_from_ragflow", {})
    base_url = ragflow_config.get("base_url", "")
    api_key = ragflow_config.get("api_key", "")
    dataset_ids = ragflow_config.get("dataset_ids", [])

    url = base_url + "/api/v1/retrieval"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # Đảm bảo rằng các chuỗi trong tải trọng được mã hóa UTF-8
    payload = {"question": question, "dataset_ids": dataset_ids}

    try:
        # Sử dụng Ensure_ascii=False để đảm bảo xử lý chính xác tiếng Trung khi tuần tự hóa JSON
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(5.0, connect=3.0), verify=False
        ) as client:
            response = await client.post(url, json=payload, headers=headers)

        # Đặt rõ ràng mã hóa phản hồi thành utf-8
        response.encoding = "utf-8"

        response.raise_for_status()

        # Lấy nội dung văn bản trước, sau đó xử lý giải mã JSON theo cách thủ công
        response_text = response.text

        result = json.loads(response_text)

        if result.get("code") != 0:
            error_detail = result.get("error", {}).get("detail", "Lỗi không xác định")
            error_message = result.get("error", {}).get("message", "")
            error_code = result.get("code", "")

            # Ghi lại thông báo lỗi một cách an toàn
            logger.bind(tag=TAG).error(
                f"RAGFlow APIgọithất bại , phản hồi码: {error_code} , Chi tiết lỗi: {error_detail} , 完整phản hồi: {result}"
            )

            # Xây dựng phản hồi lỗi chi tiết
            error_response = f"API RAG trả về lỗi (mã lỗi: {error_code}）"

            if error_message:
                error_response += f"：{error_message}"
            if error_detail:
                error_response += f"\nChi tiết: {error_detail}"

            return ActionResponse(Action.RESPONSE, None, error_response)

        chunks = result.get("data", {}).get("chunks", [])
        contents = []
        for chunk in chunks:
            content = chunk.get("content", "")
            if content:
                # Xử lý an toàn chuỗi nội dung
                if isinstance(content, str):
                    contents.append(content)
                elif isinstance(content, bytes):
                    contents.append(content.decode("utf-8", errors="replace"))
                else:
                    contents.append(str(content))

        if contents:
            # Sắp xếp nội dung cơ sở kiến thức vào chế độ tham chiếu
            context_text = f"# Với câu hỏi “{question}”, tìm được nội dung sau trong kho tri thức\n"
            context_text += "```\n\n\n".join(contents[:5])
            context_text += "\n```"
        else:
            context_text = "Không có thông tin liên quan trong kho tri thức."
        return ActionResponse(Action.REQLLM, context_text, None)

    except httpx.TimeoutException as e:
        error_response = "API RAG phản hồi quá thời gian chờ"
        error_response += "\nCó thể do RAGflow phản hồi chậm hoặc mạng có độ trễ"
        error_response += "\nThử lại sau hoặc kiểm tra hiệu năng RAGflow"
        return ActionResponse(Action.RESPONSE, None, error_response)

    except httpx.HTTPStatusError as e:
        if hasattr(e.response, "status_code"):
            status_code = e.response.status_code
            error_response = f"Lỗi HTTP API RAG (mã trạng thái: {status_code}）"
            try:
                error_detail = e.response.json().get("error", {}).get("message", "")
                if error_detail:
                    error_response += f"\nChi tiết lỗi: {error_detail}"
            except:
                pass
        else:
            error_response = f"Lỗi HTTP API RAG: {str(e)}"
        return ActionResponse(Action.RESPONSE, None, error_response)

    except httpx.HTTPError as e:
        error_response = "Không thể kết nối API RAG"
        error_response += (
            "\nCó thể do địa chỉ RAGflow không đúng hoặc dịch vụ chưa chạy"
        )
        error_response += "\nKiểm tra địa chỉ và trạng thái dịch vụ RAGflow"
        return ActionResponse(Action.RESPONSE, None, error_response)

    except Exception as e:
        # Các trường hợp ngoại lệ khác
        error_type = type(e).__name__
        logger.bind(tag=TAG).error(
            f"RAGflowxử lýsự cố , sự cốloại: {error_type} , Chi tiết: {str(e)}"
        )

        # Cung cấp thông tin lỗi chi tiết
        error_response = f"Lỗi xử lý API RAG ({error_type}）：{str(e)}"
        return ActionResponse(Action.RESPONSE, None, error_response)
