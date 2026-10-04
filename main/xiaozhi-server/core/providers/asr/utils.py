import re
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

EMOTION_EMOJI_MAP = {
    "HAPPY": "🙂",
    "SAD": "😔",
    "ANGRY": "😡",
    "NEUTRAL": "😶",
    "FEARFUL": "😰",
    "DISGUSTED": "🤢",
    "SURPRISED": "😲",
    "EMO_UNKNOWN": "😶",  # Những cảm xúc không xác định sử dụng các biểu thức trung tính theo mặc định
}
# EVENT_EMOJI_MAP = {
#     "<|BGM|>": "🎼",
#     "<|Speech|>": "",
#     "<|Applause|>": "👏",
#     "<|Laughter|>": "😀",
#     "<|Cry|>": "😭",
#     "<|Sneeze|>": "🤧",
#     "<|Breath|>": "",
#     "<|Cough|>": "🤧",
# }


def lang_tag_filter(text: str) -> dict:
    """
    phân tích FunASR nhận dạngkết quả , 按顺序提取标签和纯văn bảnnội dung

    Args:
        text: ASR nhận dạng的gốcvăn bản , 可能包含多种标签

    Returns:
        dict: {"language": "zh", "emotion": "SAD", "emoji": "😔", "content": "你好"} 如果有标签 ,
              {"content": "纯văn bản"} 如果没有标签

    Examples:
        FunASR 输出định dạng: <|语种|><|情绪|><|事件|><|其他选项|>原文
        >>> lang_tag_filter("<|zh|><|SAD|><|Speech|><|withitn|>你好啊 , 测试测试.")
        {"language": "zh", "emotion": "SAD", "emoji": "😔", "content": "你好啊 , 测试测试."}
        >>> lang_tag_filter("<|en|><|HAPPY|><|Speech|><|withitn|>Hello hello.")
        {"language": "en", "emotion": "HAPPY", "emoji": "🙂", "content": "Hello hello."}
        >>> lang_tag_filter("plain text")
        {"content": "plain text"}
    """
    # Trích xuất tất cả các thẻ (theo thứ tự)
    tag_pattern = r"<\|([^|]+)\|>"
    all_tags = re.findall(tag_pattern, text)

    # Xóa tất cả các thẻ định dạng <|...|> và nhận văn bản thuần túy
    clean_text = re.sub(tag_pattern, "", text).strip()

    # Giữ cấu trúc trả về nhất quán để ngăn người gọi nhầm văn bản thuần túy với truy cập từ điển.
    if not all_tags:
        return {"content": clean_text}

    # Trích xuất các thẻ theo thứ tự cố định của FunASR và trả về dict
    language = all_tags[0] if len(all_tags) > 0 else "zh"
    emotion = all_tags[1] if len(all_tags) > 1 else "NEUTRAL"
    # sự kiện = all_tags[2] if len(all_tags) > 2 else "Speech" # Thẻ sự kiện chưa được sử dụng

    result = {
        "content": clean_text,
        "language": language,
        "emotion": emotion,
        # "sự kiện": sự kiện,
    }

    # Thêm ánh xạ biểu tượng cảm xúc
    if emotion in EMOTION_EMOJI_MAP:
        result["emotion"] = EMOTION_EMOJI_MAP[emotion]
    # Thẻ sự kiện chưa được sử dụng
    # nếu sự kiện trong EVENT_EMOJI_MAP:
    #     kết quả["sự kiện"] = EVENT_EMOJI_MAP[sự kiện]

    return result
