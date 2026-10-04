import httpx
from bs4 import BeautifulSoup
from config.logger import setup_logging
from plugins_func.register import register_function, ToolType, ActionResponse, Action
from core.utils.util import get_ip_info
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()

GET_WEATHER_FUNCTION_DESC = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "Tra cứu thời tiết tại địa điểm người dùng nêu. Nếu người dùng nêu tỉnh, hãy dùng thành phố thủ phủ; "
            "nếu nêu địa danh khác, hãy dùng thủ phủ của tỉnh đó. Dự báo địa phương bảy ngày đã có trong ngữ cảnh; "
            "chỉ gọi công cụ khi người dùng hỏi thời tiết ở thành phố khác."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Tên địa điểm, ví dụ Hà Nội. Tùy chọn; bỏ qua nếu không có",
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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    )
}

# Mã thời tiết https://dev.qweather.com/docs/resource/icons/#weather-icons
WEATHER_CODE_MAP = {
    "100": "Trời nắng",
    "101": "Nhiều mây",
    "102": "Ít mây",
    "103": "Nắng xen mây",
    "104": "Trời âm u",
    "150": "Trời nắng",
    "151": "Nhiều mây",
    "152": "Ít mây",
    "153": "Nắng xen mây",
    "300": "Mưa rào",
    "301": "Mưa rào lớn",
    "302": "Mưa dông",
    "303": "Dông mạnh",
    "304": "Dông kèm mưa đá",
    "305": "Mưa nhỏ",
    "306": "Mưa vừa",
    "307": "Mưa lớn",
    "308": "Mưa cực lớn",
    "309": "Mưa phùn",
    "310": "Mưa rất lớn",
    "311": "Mưa cực lớn",
    "312": "Mưa đặc biệt lớn",
    "313": "Mưa đóng băng",
    "314": "Mưa nhỏ đến vừa",
    "315": "Mưa vừa đến lớn",
    "316": "Mưa lớn đến rất lớn",
    "317": "Mưa rất lớn đến cực lớn",
    "318": "Mưa cực lớn đến đặc biệt lớn",
    "350": "Mưa rào",
    "351": "Mưa rào lớn",
    "399": "Mưa",
    "400": "Tuyết nhẹ",
    "401": "Tuyết vừa",
    "402": "Tuyết dày",
    "403": "Bão tuyết",
    "404": "Mưa tuyết",
    "405": "Thời tiết mưa tuyết",
    "406": "Mưa rào tuyết",
    "407": "Tuyết rào",
    "408": "Tuyết nhẹ đến vừa",
    "409": "Tuyết vừa đến dày",
    "410": "Tuyết dày đến bão tuyết",
    "456": "Mưa rào tuyết",
    "457": "Tuyết rào",
    "499": "Tuyết",
    "500": "Sương mỏng",
    "501": "Sương mù",
    "502": "Khói mù",
    "503": "Cát bay",
    "504": "Bụi lơ lửng",
    "507": "Bão cát",
    "508": "Bão cát mạnh",
    "509": "Sương mù dày",
    "510": "Sương mù rất dày",
    "511": "Khói mù vừa",
    "512": "Khói mù dày",
    "513": "Khói mù nghiêm trọng",
    "514": "Sương mù dày đặc",
    "515": "Sương mù cực dày",
    "900": "Nóng",
    "901": "Lạnh",
    "999": "Chưa xác định",
}


async def fetch_city_info(location, api_key, api_host):
    url = f"https://{api_host}/geo/v2/city/lookup?key={api_key}&location={location}&lang=vi"
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
        response = await client.get(url, headers=HEADERS)
    data = response.json()
    if data.get("error") is not None:
        logger.bind(tag=TAG).error(
            f"Lấy thông tin thời tiết thất bại, lý do: {data.get('error', {}).get('detail')}"
        )
        return None
    return data.get("location", [])[0] if data.get("location") else None


async def fetch_weather_page(url):
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
        response = await client.get(url, headers=HEADERS)
    return (
        BeautifulSoup(response.text, "html.parser")
        if response.status_code == 200
        else None
    )


def parse_weather_info(soup):
    city_name = soup.select_one("h1.c-submenu__location").get_text(strip=True)

    current_abstract = soup.select_one(".c-city-weather-current .current-abstract")
    current_abstract = (
        current_abstract.get_text(strip=True) if current_abstract else "Chưa xác định"
    )

    current_basic = {}
    for item in soup.select(
        ".c-city-weather-current .current-basic .current-basic___item"
    ):
        parts = item.get_text(strip=True, separator=" ").split(" ")
        if len(parts) == 2:
            key, value = parts[1], parts[0]
            current_basic[key] = value

    temps_list = []
    for row in soup.select(".city-forecast-tabs__row")[:7]:  # Lấy dữ liệu của 7 ngày trước đó
        date = row.select_one(".date-bg .date").get_text(strip=True)
        weather_code = (
            row.select_one(".date-bg .icon")["src"].split("/")[-1].split(".")[0]
        )
        weather = WEATHER_CODE_MAP.get(weather_code, "Chưa xác định")
        temps = [span.get_text(strip=True) for span in row.select(".tmp-cont .temp")]
        high_temp, low_temp = (temps[0], temps[-1]) if len(temps) >= 2 else (None, None)
        temps_list.append((date, weather, high_temp, low_temp))

    return city_name, current_abstract, current_basic, temps_list


@register_function("get_weather", GET_WEATHER_FUNCTION_DESC, ToolType.SYSTEM_CTL)
async def get_weather(
    conn: "ConnectionHandler", location: str = None, lang: str = "vi_VN"
):
    from core.utils.cache.manager import cache_manager, CacheType

    weather_config = conn.config.get("plugins", {}).get("get_weather", {})
    api_host = weather_config.get("api_host", "mj7p3y7naa.re.qweatherapi.com")
    api_key = weather_config.get("api_key", "a861d0d5e7bf4ee1a83d9a9e4f96d4da")
    default_location = weather_config.get("default_location", "Hồ Chí Minh")
    client_ip = conn.client_ip

    # Ưu tiên sử dụng thông số vị trí do người dùng cung cấp
    if not location:
        # Xác định thành phố theo IP của máy khách
        if client_ip:
            # Trước tiên hãy lấy thông tin thành phố tương ứng với IP từ bộ đệm
            cached_ip_info = cache_manager.get(CacheType.IP_INFO, client_ip)
            if cached_ip_info:
                location = cached_ip_info.get("city")
            else:
                # Thiếu bộ nhớ đệm, hãy gọi API để lấy
                ip_info = get_ip_info(client_ip, logger)
                if ip_info:
                    cache_manager.set(CacheType.IP_INFO, client_ip, ip_info)
                    location = ip_info.get("city")

            if not location:
                location = default_location
        else:
            # Nếu không có IP thì sử dụng vị trí mặc định
            location = default_location
    # Cố gắng lấy báo cáo thời tiết đầy đủ từ bộ nhớ đệm
    weather_cache_key = f"full_weather_{location}_{lang}"
    cached_weather_report = cache_manager.get(CacheType.WEATHER, weather_cache_key)
    if cached_weather_report:
        return ActionResponse(Action.REQLLM, cached_weather_report, None)

    # Thiếu bộ nhớ đệm, nhận dữ liệu thời tiết theo thời gian thực
    city_info = await fetch_city_info(location, api_key, api_host)
    if not city_info:
        return ActionResponse(
            Action.REQLLM,
            f"Không tìm thấy thành phố: {location}. Vui lòng kiểm tra lại địa điểm",
            None,
        )
    soup = await fetch_weather_page(city_info["fxLink"])
    if not soup:
        return ActionResponse(Action.REQLLM, None, "Yêu cầu thất bại")
    city_name, current_abstract, current_basic, temps_list = parse_weather_info(soup)

    weather_report = (
        f"Vị trí bạn hỏi: {city_name}\n\nThời tiết hiện tại: {current_abstract}\n"
    )

    # Thêm các thông số thời tiết hiện tại hợp lệ
    if current_basic:
        weather_report += "Thông số chi tiết:\n"
        for key, value in current_basic.items():
            if value != "0":  # Lọc các giá trị không hợp lệ
                weather_report += f"  · {key}: {value}\n"

    # Thêm dự báo 7 ngày
    weather_report += "\nDự báo 7 ngày tới:\n"
    for date, weather, high, low in temps_list:
        weather_report += f"{date}: {weather}, nhiệt độ {low}~{high}\n"

    # nhắc nhở
    weather_report += (
        "\n(Nếu cần thời tiết một ngày cụ thể, hãy cho mình biết ngày nhé)"
    )

    # Báo cáo thời tiết đầy đủ trong bộ nhớ đệm
    cache_manager.set(CacheType.WEATHER, weather_cache_key, weather_report)

    return ActionResponse(Action.REQLLM, weather_report, None)
