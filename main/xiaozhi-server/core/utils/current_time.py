"""
khi间công cụmô-đun
提供统一的khi间lấy功能
"""

import cnlunar
from datetime import datetime

WEEKDAY_MAP = {
    "Monday": "Thứ Hai",
    "Tuesday": "Thứ Ba",
    "Wednesday": "Thứ Tư",
    "Thursday": "Thứ Năm",
    "Friday": "Thứ Sáu",
    "Saturday": "Thứ Bảy",
    "Sunday": "Chủ nhật",
}


def get_current_time() -> str:
    """
    lấyhiện tạikhi间字符串 (định dạng: HH:MM)
    """
    return datetime.now().strftime("%H:%M")


def get_current_date() -> str:
    """
    lấy今天日期字符串 (định dạng: YYYY-MM-DD)
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_current_weekday() -> str:
    """
    获取今天星期几
    """
    now = datetime.now()
    return WEEKDAY_MAP[now.strftime("%A")]


def get_current_lunar_date() -> str:
    """
    获取农历日期字符串
    """
    try:
        now = datetime.now()
        today_lunar = cnlunar.Lunar(now, godType="8char")
        return "%s年%s%s" % (
            today_lunar.lunarYearCn,
            today_lunar.lunarMonthCn[:-1],
            today_lunar.lunarDayCn,
        )
    except Exception:
        return "Không thể lấy ngày âm lịch"


def get_current_time_info() -> tuple:
    """
    lấyhiện tạikhi间thông tin
    trả về: (hiện tạikhi间字符串, 今天日期, 今天星期, 农历日期)
    """
    current_time = get_current_time()
    today_date = get_current_date()
    today_weekday = get_current_weekday()
    lunar_date = get_current_lunar_date()

    return current_time, today_date, today_weekday, lunar_date
