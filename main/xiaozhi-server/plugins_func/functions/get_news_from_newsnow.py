import random
import httpx
from io import BytesIO
from markitdown import MarkItDown, StreamInfo
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler


TAG = __name__
logger = setup_logging()

CHANNEL_MAP = {
    "Báo The Paper": "thepaper",
    "Xu hướng Baidu": "baidu",
    "Tài Liên Xã": "cls-depth",
    "V2EX": "v2ex-share",
    "知乎": "zhihu",
    "微博": "weibo",
    "联合早报": "zaobao",
    "酷安": "coolapk",
    "MKTNews": "mktnews-flash",
    "华尔街见闻": "wallstreetcn-quick",
    "36氪": "36kr-quick",
    "抖音": "douyin",
    "虎扑": "hupu",
    "百度贴吧": "tieba",
    "今日头条": "toutiao",
    "IT之家": "ithome",
    "澎湃新闻": "thepaper",
    "卫星通讯社": "sputniknewscn",
    "参考消息": "cankaoxiaoxi",
    "远景论坛": "pcbeta-windows11",
    "财联社": "cls-depth",
    "雪球": "xueqiu-hotstock",
    "格隆汇": "gelonghui",
    "法布财经": "fastbull-express",
    "Solidot": "solidot",
    "Hacker News": "hackernews",
    "Product Hunt": "producthunt",
    "Github": "github-trending-today",
    "哔哩哔哩": "bilibili-hot-search",
    "快手": "kuaishou",
    "靠谱新闻": "kaopu",
    "金十数据": "jin10",
    "百度热搜": "baidu",
    "牛客": "nowcoder",
    "少数派": "sspai",
    "稀土掘金": "juejin",
    "凤凰网": "ifeng",
    "虫部落": "chongbuluo-latest",
}

# Từ điển nguồn tin tức mặc định, được sử dụng khi không được chỉ định trong cấu hình
DEFAULT_NEWS_SOURCES = "Báo The Paper;Xu hướng Baidu;Tài Liên Xã"


def _get_newsnow_config(conn):
    # Nhận từ cấu hình kết nối
    plugins = conn.config.get("plugins", {})
    newsnow = plugins.get("get_news_from_newsnow", {})
    sources = newsnow.get("news_sources", "")
    if isinstance(sources, str) and sources.strip():
        return sources

    return ""


def get_news_sources_from_config(conn):
    """从cấu hìnhtronglấy新闻源字符串"""
    try:
        result = _get_newsnow_config(conn)
        if result:
            logger.bind(tag=TAG).debug(f"使用cấu hình的新闻源: {result}")
            return result

        logger.bind(tag=TAG).debug("không tìm thấy新闻源cấu hình , 使用默认cấu hình")
        return DEFAULT_NEWS_SOURCES

    except Exception as e:
        logger.bind(tag=TAG).error(f"lấy新闻源cấu hìnhthất bại: {e} , 使用默认cấu hình")
        return DEFAULT_NEWS_SOURCES


# Nhận tên nguồn tin tức có sẵn từ cấu hình mặc định (được lấy động trong thời gian chạy bởi get_news_sources_from_config)
example_sources_str = DEFAULT_NEWS_SOURCES.replace(";", "、")

GET_NEWS_FROM_NEWSNOW_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_news_from_newsnow",
        "description": "Dùng khi người dùng muốn xem hoặc nghe tin tức, chẳng hạn hỏi tin mới hoặc tin hôm nay.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": f"Tên nguồn tin, ví dụ {example_sources_str}. Tùy chọn; nếu bỏ trống sẽ dùng các nguồn mặc định",
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


async def fetch_news_from_api(conn: "ConnectionHandler", source="thepaper"):
    """从API获取新闻列表"""
    try:
        api_url = f"https://newsnow.busiyi.world/api/s?id={source}"

        news_config = conn.config.get("plugins", {}).get("get_news_from_newsnow", {})
        if news_config.get("url"):
            api_url = news_config["url"] + source

        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=3.0)
        ) as client:
            response = await client.get(api_url, headers=headers)

        data = response.json()

        if "items" in data:
            return data["items"]
        else:
            logger.bind(tag=TAG).error(f"lấy新闻APIphản hồiđịnh dạngLỗi: {data}")
            return []

    except Exception as e:
        logger.bind(tag=TAG).error(f"lấy新闻APIthất bại: {e}")
        return []


async def fetch_news_detail(url):
    """lấy新闻详情页nội dung并使用MarkItDown清理HTML"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=3.0)
        ) as client:
            response = await client.get(url, headers=headers)

        # Sử dụng MarkItDown để dọn dẹp nội dung HTML
        md = MarkItDown(enable_plugins=False)
        result = md.convert_stream(
            BytesIO(response.content),
            stream_info=StreamInfo(
                mimetype="text/html",
                extension=".html",
                charset=response.encoding or "utf-8",
            ),
        )

        # Nhận nội dung văn bản đã được làm sạch
        clean_text = result.text_content

        # Nếu nội dung đã được xóa trống, một thông báo nhắc nhở sẽ được trả về.
        if not clean_text or len(clean_text.strip()) == 0:
            logger.bind(tag=TAG).warning(f"清理后的新闻nội dung为空: {url}")
            return "Không thể đọc chi tiết tin tức, có thể do cấu trúc trang đặc biệt hoặc nội dung bị hạn chế."

        return clean_text
    except Exception as e:
        logger.bind(tag=TAG).error(f"lấy新闻详情thất bại: {e}")
        return "Không thể lấy nội dung chi tiết"


@register_function(
    "get_news_from_newsnow",
    GET_NEWS_FROM_NEWSNOW_FUNCTION_DESC,
    ToolType.SYSTEM_CTL,
)
async def get_news_from_newsnow(
    conn: "ConnectionHandler",
    source: str = "澎湃新闻",
    detail: bool = False,
    lang: str = "vi_VN",
):
    """lấy新闻并随机选择一条tiến hành播报 , 或lấy上一条新闻的详细nội dung"""
    try:
        # Nhận nguồn tin tức hiện được cấu hình
        news_sources = get_news_sources_from_config(conn)

        # Nếu chi tiết là Đúng, hãy lấy chi tiết của tin tức trước đó
        detail = str(detail).lower() == "true"
        if detail:
            if (
                not hasattr(conn, "last_newsnow_link")
                or not conn.last_newsnow_link
                or "url" not in conn.last_newsnow_link
            ):
                return ActionResponse(
                    Action.REQLLM,
                    "Chưa có tin tức vừa tra cứu. Hãy lấy một tin trước nhé.",
                    None,
                )

            url = conn.last_newsnow_link.get("url")
            title = conn.last_newsnow_link.get("title", "Tiêu đề chưa xác định")
            source_id = conn.last_newsnow_link.get("source_id", "thepaper")
            source_name = CHANNEL_MAP.get(source_id, "Nguồn chưa xác định")

            if not url or url == "#":
                return ActionResponse(
                    Action.REQLLM,
                    "Tin này không có liên kết hợp lệ để lấy nội dung chi tiết.",
                    None,
                )

            logger.bind(tag=TAG).debug(
                f"获取新闻详情: {title}, 来源: {source_name}, URL={url}"
            )

            # Nhận chi tiết tin tức
            detail_content = await fetch_news_detail(url)

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
                # f"Nguồn tin: {source_name}\n"
                f"详细nội dung: {detail_content}\n\n"
                f"(请对上述新闻nội dungtiến hành总结 , 提取关键thông tin , 以自然、流畅的方式向người dùng播报 , "
                f"不要提及这是总结，就像是在讲述一个完整的新闻)"
            )

            return ActionResponse(Action.REQLLM, detail_report, None)

        # Nếu không, hãy lấy danh sách tin tức và chọn ngẫu nhiên một
        # Chuyển đổi tên tiếng Trung sang ID tiếng Anh
        english_source_id = None

        # Kiểm tra xem tên tiếng Trung đã nhập có trong nguồn tin đã định cấu hình hay không
        news_sources_list = [
            name.strip() for name in news_sources.split(";") if name.strip()
        ]
        if source in news_sources_list:
            # Nếu tên tiếng Trung đã nhập có trong nguồn tin tức được định cấu hình, hãy tìm kiếm ID tiếng Anh tương ứng trong CHANNEL_MAP
            english_source_id = CHANNEL_MAP.get(source)

        # Nếu không tìm thấy ID tiếng Anh tương ứng, hãy sử dụng nguồn mặc định
        if not english_source_id:
            logger.bind(tag=TAG).warning(f"无效的新闻源: {source}，使用默认源澎湃新闻")
            english_source_id = "thepaper"
            source = "澎湃新闻"

        logger.bind(tag=TAG).info(f"获取新闻: 新闻源={source}({english_source_id})")

        # Nhận danh sách tin tức
        news_items = await fetch_news_from_api(conn, english_source_id)

        if not news_items:
            return ActionResponse(
                Action.REQLLM,
                f"Xin lỗi, chưa lấy được tin từ {source}. Bạn thử lại sau hoặc chọn nguồn khác nhé.",
                None,
            )

        # Chọn ngẫu nhiên một mẩu tin tức
        selected_news = random.choice(news_items)

        # Lưu liên kết tin tức hiện tại vào đối tượng kết nối để biết chi tiết truy vấn tiếp theo
        if not hasattr(conn, "last_newsnow_link"):
            conn.last_newsnow_link = {}
        conn.last_newsnow_link = {
            "url": selected_news.get("url", "#"),
            "title": selected_news.get("title", "Tiêu đề chưa xác định"),
            "source_id": english_source_id,
        }

        # Xây dựng một báo cáo tin tức
        news_report = (
            f"根据下列dữ liệu , 用{lang}回应người dùng的新闻查询yêu cầu: \n\n"
            f"新闻标题: {selected_news['title']}\n"
            # f"Nguồn tin: {source}\n"
            f"(请以自然、流畅的方式向用户播报这条新闻标题，"
            f"hướng dẫnngười dùng可以要求lấy详细nội dung , 此khisẽlấy新闻的详细nội dung.)"
        )

        return ActionResponse(Action.REQLLM, news_report, None)

    except Exception as e:
        logger.bind(tag=TAG).error(f"获取新闻出错: {e}")
        return ActionResponse(
            Action.REQLLM, "Xin lỗi, có lỗi khi lấy tin tức. Bạn thử lại sau nhé.", None
        )
