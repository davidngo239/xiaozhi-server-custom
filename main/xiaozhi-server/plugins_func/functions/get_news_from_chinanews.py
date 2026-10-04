import random
import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler


TAG = __name__
logger = setup_logging()

GET_NEWS_FROM_CHINANEWS_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news_from_chinanews",
        "description": "Dùng khi người dùng muốn xem hoặc nghe tin tức. Có thể chọn loại tin xã hội, công nghệ, quốc tế hoặc kinh tế. Mặc định là tin xã hội.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Loại tin, ví dụ xã hội, công nghệ hoặc quốc tế. Tùy chọn; mặc định là tin xã hội",
                },
                "detail": {
                    "type": "boolean",
                    "description": "Có lấy nội dung chi tiết hay không; mặc định false. Nếu true, lấy chi tiết tin vừa truy vấn",
                },
                "lang": {
                    "type": "string",
                    "description": "Mã ngôn ngữ phản hồi, ví dụ vi_VN, zh_CN, en_US hoặc ja_JP; mặc định vi_VN",
                },
            },
            "required": ["lang"],
        },
    },
}


async def fetch_news_from_rss(rss_url):
    """从RSS源获取新闻列表"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
            response = await client.get(rss_url)

        # Phân tích cú pháp XML
        root = ET.fromstring(response.content)

        # Tìm tất cả các thành phần mục (mục tin tức)
        news_items = []
        for item in root.findall(".//item"):
            title = (
                item.find("title").text
                if item.find("title") is not None
                else "Không có tiêu đề"
            )
            link = item.find("link").text if item.find("link") is not None else "#"
            description = (
                item.find("description").text
                if item.find("description") is not None
                else "Không có mô tả"
            )
            pubDate = (
                item.find("pubDate").text
                if item.find("pubDate") is not None
                else "Thời gian chưa xác định"
            )

            news_items.append(
                {
                    "title": title,
                    "link": link,
                    "description": description,
                    "pubDate": pubDate,
                }
            )

        return news_items
    except Exception as e:
        logger.bind(tag=TAG).error(f"lấyRSS新闻thất bại: {e}")
        return []


async def fetch_news_detail(url):
    """lấy新闻详情页nội dung并总结"""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=3.0)
        ) as client:
            response = await client.get(url)

        soup = BeautifulSoup(response.content, "html.parser")

        # Cố gắng trích xuất nội dung nội dung (bộ chọn ở đây cần được điều chỉnh theo cấu trúc trang web thực tế)
        content_div = soup.select_one(
            ".content_desc, .content, article, .article-content"
        )
        if content_div:
            paragraphs = content_div.find_all("p")
            content = "\n".join(
                [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
            )
            return content
        else:
            # Nếu không tìm thấy một khu vực nội dung cụ thể, hãy thử lấy tất cả các đoạn văn
            paragraphs = soup.find_all("p")
            content = "\n".join(
                [p.get_text().strip() for p in paragraphs if p.get_text().strip()]
            )
            return content[:2000]  # Giới hạn độ dài
    except Exception as e:
        logger.bind(tag=TAG).error(f"lấy新闻详情thất bại: {e}")
        return "Không thể lấy nội dung chi tiết"


def map_category(category_text):
    """sẽngười dùng输入的trong文类别映射到cấu hình文件trong的类别键"""
    if not category_text:
        return None

    # Từ điển lập bản đồ danh mục, hiện hỗ trợ tin tức xã hội, quốc tế và tài chính. Để biết thêm các loại, hãy xem tệp cấu hình
    category_map = {
        "xã hội": "society_rss_url",
        "công nghệ": "society_rss_url",
        "quốc tế": "world_rss_url",
        "kinh tế": "finance_rss_url",
        "tài chính": "finance_rss_url",
        # tin tức xã hội
        "社会": "society_rss_url",
        "社会新闻": "society_rss_url",
        # tin tức quốc tế
        "国际": "world_rss_url",
        "国际新闻": "world_rss_url",
        # tin tức tài chính
        "财经": "finance_rss_url",
        "财经新闻": "finance_rss_url",
        "金融": "finance_rss_url",
        "经济": "finance_rss_url",
    }

    # Chuyển đổi sang chữ thường và loại bỏ khoảng trắng
    normalized_category = category_text.lower().strip()

    # Trả về kết quả ánh xạ hoặc đầu vào ban đầu nếu không khớp
    return category_map.get(normalized_category, category_text)


@register_function(
    "get_news_from_chinanews",
    GET_NEWS_FROM_CHINANEWS_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
async def get_news_from_chinanews(
    conn: "ConnectionHandler",
    category: str = None,
    detail: bool = False,
    lang: str = "zh_CN",
):
    """lấy新闻并随机选择一条tiến hành播报 , 或lấy上一条新闻的详细nội dung"""
    try:
        # Nếu chi tiết là Đúng, hãy lấy chi tiết của tin tức trước đó
        if detail:
            if (
                not hasattr(conn, "last_news_link")
                or not conn.last_news_link
                or "link" not in conn.last_news_link
            ):
                return ActionResponse(
                    Action.REQLLM,
                    "Chưa có tin tức vừa tra cứu. Hãy lấy một tin trước nhé.",
                    None,
                )

            link = conn.last_news_link.get("link")
            title = conn.last_news_link.get("title", "Tiêu đề chưa xác định")

            if link == "#":
                return ActionResponse(
                    Action.REQLLM,
                    "Tin này không có liên kết hợp lệ để lấy nội dung chi tiết.",
                    None,
                )

            logger.bind(tag=TAG).debug(f"获取新闻详情: {title}, URL={link}")

            # Nhận chi tiết tin tức
            detail_content = await fetch_news_detail(link)

            if (
                not detail_content
                or detail_content == "Không thể lấy nội dung chi tiết"
            ):
                return ActionResponse(
                    Action.REQLLM,
                    f"Xin lỗi, không thể lấy chi tiết tin “{title}”, có thể do liên kết hết hiệu lực hoặc trang đã đổi cấu trúc.",
                    None,
                )

            # Báo cáo chi tiết bản dựng
            detail_report = (
                f"根据下列dữ liệu , 用{lang}回应người dùng的新闻详情查询yêu cầu: \n\n"
                f"新闻标题: {title}\n"
                f"详细nội dung: {detail_content}\n\n"
                f"(请对上述新闻nội dungtiến hành总结 , 提取关键thông tin , 以自然、流畅的方式向người dùng播报 , "
                f"不要提及这是总结，就像是在讲述一个完整的新闻故事)"
            )

            return ActionResponse(Action.REQLLM, detail_report, None)

        # Nếu không, hãy lấy danh sách tin tức và chọn ngẫu nhiên một
        # Nhận URL RSS từ cấu hình
        rss_config = conn.config.get("plugins", {}).get("get_news_from_chinanews", {})
        default_rss_url = rss_config.get(
            "default_rss_url", "https://www.chinanews.com.cn/rss/society.xml"
        )

        # Ánh xạ các danh mục do người dùng nhập vào các khóa danh mục trong cấu hình
        mapped_category = map_category(category)

        # Nếu một danh mục được cung cấp, hãy thử lấy URL tương ứng từ cấu hình
        rss_url = default_rss_url
        if mapped_category and mapped_category in rss_config:
            rss_url = rss_config[mapped_category]

        logger.bind(tag=TAG).info(
            f"lấy新闻: gốc类别={category}, 映射类别={mapped_category}, URL={rss_url}"
        )

        # Nhận danh sách tin tức
        news_items = await fetch_news_from_rss(rss_url)

        if not news_items:
            return ActionResponse(
                Action.REQLLM,
                "Xin lỗi, chưa lấy được tin tức. Bạn thử lại sau nhé.",
                None,
            )

        # Chọn ngẫu nhiên một mẩu tin tức
        selected_news = random.choice(news_items)

        # Lưu liên kết tin tức hiện tại vào đối tượng kết nối để biết chi tiết truy vấn tiếp theo
        if not hasattr(conn, "last_news_link"):
            conn.last_news_link = {}
        conn.last_news_link = {
            "link": selected_news.get("link", "#"),
            "title": selected_news.get("title", "Tiêu đề chưa xác định"),
        }

        # Xây dựng một báo cáo tin tức
        news_report = (
            f"根据下列dữ liệu , 用{lang}回应người dùng的新闻查询yêu cầu: \n\n"
            f"新闻标题: {selected_news['title']}\n"
            f"发布时间: {selected_news['pubDate']}\n"
            f"新闻nội dung: {selected_news['description']}\n"
            f"(请以自然、流畅的方式向người dùng播报这条新闻 , 可以适当总结nội dung , "
            f"直接读出新闻即可 , 不需要额外多余的nội dung."
            f"如果người dùng询问更多详情 , 告知người dùng可以说'请详细介绍这条新闻'lấy更多nội dung)"
        )

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"获取新闻出错: {e}")
        return ActionResponse(
            Action.REQLLM, "Xin lỗi, có lỗi khi lấy tin tức. Bạn thử lại sau nhé.", None
        )
