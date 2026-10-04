import httpx
from config.logger import setup_logging
from plugins_func.register import (
    register_function,
    ToolType,
    ActionResponse,
    Action,
)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

_DEFAULT_DESCRIPTION = "Công cụ tìm kiếm Internet. Chỉ dùng khi người dùng yêu cầu rõ ràng việc tìm kiếm trực tuyến."

WEB_SEARCH_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": _DEFAULT_DESCRIPTION,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Từ khóa hoặc câu hỏi tìm kiếm",
                }
            },
            "required": ["query"],
        },
    },
}


async def _search_metaso(api_key: str, query: str, max_results: int) -> str:
    """gọi秘塔搜索API"""
    url = "https://metaso.cn/api/v1/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "size": max_results,
        "stream": False,
        "scope": "webpage",
        "includeSummary": True,
        "includeRawContent": False,
        "conciseSnippet": False,
    }
    logger.bind(tag=TAG).debug(f"秘塔搜索yêu cầu | URL: {url} | payload: {payload}")
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=3.0)) as client:
        response = await client.post(url, json=payload, headers=headers)
    data = response.json()
    logger.bind(tag=TAG).debug(f"秘塔搜索phản hồi | status: {response.status_code}")

    webpages = data.get("webpages", [])
    if not webpages:
        return "Không tìm thấy kết quả liên quan."

    lines = ["[Kết quả tìm kiếm Internet]"]
    for i, item in enumerate(webpages, 1):
        title = item.get("title", "Không có tiêu đề")
        snippet = item.get("summary", "")
        date = item.get("date", "")
        lines.append(f"{i}. Tiêu đề: {title}")
        if date:
            lines.append(f"   Ngày: {date}")
        if snippet:
            lines.append(f"   Tóm tắt: {snippet}")

    return "\n".join(lines)


async def _search_tavily(api_key: str, query: str, max_results: int) -> str:
    """gọiTavily搜索API"""
    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_answer": "advanced",
    }
    logger.bind(tag=TAG).debug(f"Tavily搜索yêu cầu | URL: {url} | payload: {payload}")
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=3.0)) as client:
        response = await client.post(url, json=payload, headers=headers)
    data = response.json()
    logger.bind(tag=TAG).debug(
        f"Tavily搜索phản hồi | status: {response.status_code} | data: {data}"
    )

    results = data.get("results", [])
    if not results:
        return "Không tìm thấy kết quả liên quan."

    answer = data.get("answer", "")
    lines = [f"[Kết quả tìm kiếm Internet]\nTóm tắt: {answer}"]
    # đối với i, mục trong liệt kê (kết quả, 1):
    #     tiêu đề = item.get("tiêu đề", "Chưa có tiêu đề")
    #     summary = item.get("content", "")
    #     dòng.append(f"{i}.title:{title}")
    #     if summary:
    #         dòng.append(f" tóm tắt: {tóm tắt}")

    return "\n".join(lines)


async def _search_serply(api_key: str, query: str, max_results: int) -> str:
    """gọiSerply搜索API"""
    url = "https://api.serply.io/v1/search"
    headers = {
        "X-Api-Key": api_key,
        "User-Agent": "xiaozhi-esp32-server",
    }
    # Serply có thể trả về tối đa 10 mục trên một trang và số lượng mục được trả về có thể nhiều hơn num một chút, cần được cắt bớt cục bộ.
    params = {"q": query, "num": min(max_results, 10)}
    logger.bind(tag=TAG).debug(f"Serply搜索yêu cầu | URL: {url} | params: {params}")
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=3.0)) as client:
        response = await client.get(url, params=params, headers=headers)
    data = response.json()
    logger.bind(tag=TAG).debug(f"Serply搜索phản hồi | status: {response.status_code}")

    if response.status_code != 200:
        detail = data.get("detail", "") if isinstance(data, dict) else ""
        logger.bind(tag=TAG).error(
            f"Serply搜索thất bại | status: {response.status_code} | detail: {detail}"
        )
        return "Tìm kiếm Internet thất bại. Kiểm tra khóa API."

    results = data.get("results", [])
    if not results:
        return "Không tìm thấy kết quả liên quan."

    lines = ["[Kết quả tìm kiếm Internet]"]
    for i, item in enumerate(results[:max_results], 1):
        title = item.get("title", "Không có tiêu đề")
        snippet = item.get("description", "")
        lines.append(f"{i}. Tiêu đề: {title}")
        if snippet:
            lines.append(f"   Tóm tắt: {snippet}")

    return "\n".join(lines)


@register_function("web_search", WEB_SEARCH_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def web_search(conn: "ConnectionHandler", query: str = None):
    logger.bind(tag=TAG).info(f"web_search 被gọi | query={query}")
    if not query:
        return ActionResponse(
            Action.REQLLM, "Vui lòng cung cấp từ khóa tìm kiếm.", None
        )

    web_search_config = conn.config.get("plugins", {}).get("web_search", {})
    provider = web_search_config.get("provider", "").lower()
    max_results = int(web_search_config.get("max_results", 3))
    logger.bind(tag=TAG).info(
        f"web_search cấu hình | provider={provider} | max_results={max_results} | config_keys={list(web_search_config.keys())}"
    )

    api_key = web_search_config.get("api_key", "")
    if not api_key:
        return ActionResponse(
            Action.REQLLM,
            "Chưa cấu hình khóa API tìm kiếm Internet. Vui lòng điền trong tệp cấu hình.",
            None,
        )

    try:
        if provider == "metaso":
            result_text = await _search_metaso(api_key, query, max_results)
        elif provider == "tavily":
            result_text = await _search_tavily(api_key, query, max_results)
        elif provider == "serply":
            result_text = await _search_serply(api_key, query, max_results)
        else:
            return ActionResponse(
                Action.REQLLM,
                f"Tìm kiếm Internet chưa cấu hình hoặc nguồn tìm kiếm không hợp lệ (hiện tại: {provider}). Vui lòng kiểm tra cấu hình.",
                None,
            )
        logger.bind(tag=TAG).info(f"搜索kết quả组装hoàn tất:\n{result_text}")
    except httpx.TimeoutException:
        logger.bind(tag=TAG).error("Yêu cầu tìm kiếm trực tuyến đã quá thời gian chờ")
        result_text = "Tìm kiếm Internet quá thời gian chờ. Vui lòng thử lại sau."
    except httpx.HTTPStatusError as e:
        logger.bind(tag=TAG).error(f"Yêu cầu tìm kiếm trực tuyến thất bại: {e}")
        result_text = "Tìm kiếm Internet thất bại. Vui lòng thử lại sau."
    except Exception as e:
        logger.bind(tag=TAG).error(f"Lỗi tìm kiếm trực tuyến: {e}")
        result_text = "Tìm kiếm Internet gặp lỗi. Vui lòng thử lại sau."

    return ActionResponse(Action.REQLLM, result_text, None)
