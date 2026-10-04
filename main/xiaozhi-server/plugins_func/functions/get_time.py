from datetime import datetime
import cnlunar
from plugins_func.register import register_function, ToolType, ActionResponse, Action

get_lunar_function_desc = {
    "type": "function",
    "function": {
        "name": "get_lunar",
        "description": (
            "Tra cứu âm lịch và lịch truyền thống cho một ngày cụ thể, gồm ngày âm, can chi, tiết khí, con giáp, "
            "cung hoàng đạo, bát tự và ngày tốt xấu. Nếu không nêu nội dung, mặc định tra cứu năm can chi và ngày âm. "
            "Với câu hỏi cơ bản về ngày âm hôm nay, hãy dùng thông tin trong ngữ cảnh, không gọi công cụ này."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "Ngày cần tra cứu theo định dạng YYYY-MM-DD, ví dụ 2024-01-01. Mặc định là ngày hiện tại",
                },
                "query": {
                    "type": "string",
                    "description": "Nội dung cần tra cứu, ví dụ ngày âm, can chi, ngày lễ, tiết khí, con giáp, cung hoàng đạo, bát tự hoặc ngày tốt xấu",
                },
            },
            "required": [],
        },
    },
}


@register_function("get_lunar", get_lunar_function_desc, ToolType.WAIT)
def get_lunar(date=None, query=None):
    """
    Dùng để tra cứu âm lịch hiện tại, can chi, tiết khí, con giáp, cung hoàng đạo, bát tự và ngày tốt xấu
    """
    from core.utils.cache.manager import cache_manager, CacheType

    # Nếu một đối số ngày được cung cấp thì ngày đã chỉ định sẽ được sử dụng; nếu không thì ngày hiện tại sẽ được sử dụng
    if date:
        try:
            now = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return ActionResponse(
                Action.REQLLM,
                "Định dạng ngày không hợp lệ; hãy dùng YYYY-MM-DD, ví dụ: 2024-01-01",
                None,
            )
    else:
        now = datetime.now()

    current_date = now.strftime("%Y-%m-%d")

    # Nếu truy vấn là Không, văn bản mặc định sẽ được sử dụng
    if query is None:
        query = "Mặc định tra cứu năm can chi và ngày âm"

    # Cố gắng lấy thông tin lịch âm từ bộ đệm
    lunar_cache_key = f"lunar_info_{current_date}"
    cached_lunar_info = cache_manager.get(CacheType.LUNAR, lunar_cache_key)
    if cached_lunar_info:
        return ActionResponse(Action.REQLLM, cached_lunar_info, None)

    response_text = f"Dựa trên thông tin sau để trả lời yêu cầu của người dùng về {query} và nội dung liên quan:\n"

    lunar = cnlunar.Lunar(now, godType="8char")
    response_text += (
        "Thông tin âm lịch:\n"
        "Năm âm lịch %s, tháng %s, ngày %s\n"
        % (lunar.lunarYearCn, lunar.lunarMonthCn[:-1], lunar.lunarDayCn)
        + "Can chi: năm %s, tháng %s, ngày %s\n"
        % (lunar.year8Char, lunar.month8Char, lunar.day8Char)
        + "Con giáp: %s\n" % (lunar.chineseYearZodiac)
        + "Bát tự: %s\n"
        % (
            " ".join(
                [lunar.year8Char, lunar.month8Char, lunar.day8Char, lunar.twohour8Char]
            )
        )
        + "Ngày lễ hôm nay: %s\n"
        % (
            ",".join(
                filter(
                    None,
                    (
                        lunar.get_legalHolidays(),
                        lunar.get_otherHolidays(),
                        lunar.get_otherLunarHolidays(),
                    ),
                )
            )
        )
        + "Tiết khí hôm nay: %s\n" % (lunar.todaySolarTerms)
        + "Tiết khí tiếp theo: %s, ngày %s/%s/%s\n"
        % (
            lunar.nextSolarTerm,
            lunar.nextSolarTermYear,
            lunar.nextSolarTermDate[0],
            lunar.nextSolarTermDate[1],
        )
        + "Các tiết khí trong năm nay: %s\n"
        % (
            ", ".join(
                [
                    f"{term} ({date[0]}/{date[1]})"
                    for term, date in lunar.thisYearSolarTermsDic.items()
                ]
            )
        )
        + "Xung khắc theo con giáp: %s\n" % (lunar.chineseZodiacClash)
        + "Cung hoàng đạo: %s\n" % (lunar.starZodiac)
        + "Nạp âm: %s\n" % lunar.get_nayin()
        + "Điều kiêng kỵ theo Bành Tổ: %s\n" % (lunar.get_pengTaboo(delimit=", "))
        + "Trực ngày: %s\n" % lunar.get_today12DayOfficer()[0]
        + "Thần trực: %s (%s)\n"
        % (lunar.get_today12DayOfficer()[1], lunar.get_today12DayOfficer()[2])
        + "Nhị thập bát tú: %s\n" % lunar.get_the28Stars()
        + "Hướng thần tốt: %s\n" % " ".join(lunar.get_luckyGodsDirection())
        + "Thai thần hôm nay: %s\n" % lunar.get_fetalGod()
        + "Nên làm: %s\n" % "、".join(lunar.goodThing[:10])
        + "Nên tránh: %s\n" % "、".join(lunar.badThing[:10])
        + "(Mặc định trả về năm can chi và ngày âm; chỉ bổ sung ngày tốt xấu nếu người dùng yêu cầu.)"
    )

    # Lưu trữ thông tin âm lịch
    cache_manager.set(CacheType.LUNAR, lunar_cache_key, response_text)

    return ActionResponse(Action.REQLLM, response_text, None)
