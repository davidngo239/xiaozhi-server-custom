from enum import Enum
from typing import Union, Optional


class SentenceType(Enum):
    # sân khấu nói
    FIRST = "FIRST"  # câu đầu tiên
    MIDDLE = "MIDDLE"  # Nói chuyện
    LAST = "LAST"  # câu cuối cùng


class ContentType(Enum):
    # Loại nội dung
    TEXT = "TEXT"  # nội dung văn bản
    FILE = "FILE"  # Nội dung tập tin
    ACTION = "ACTION"  # nội dung hành động


class InterfaceType(Enum):
    # Loại giao diện
    DUAL_STREAM = "DUAL_STREAM"  # Dòng chảy kép
    SINGLE_STREAM = "SINGLE_STREAM"  # luồng đơn
    NON_STREAM = "NON_STREAM"  # không phát trực tuyến


class TTSMessageDTO:
    def __init__(
        self,
        sentence_id: str,
        # sân khấu nói
        sentence_type: SentenceType,
        # Loại nội dung
        content_type: ContentType,
        # Chi tiết nội dung, thường là văn bản hoặc lời bài hát âm thanh cần được chuyển đổi
        content_detail: Optional[str] = None,
        # Nếu loại nội dung là một tệp, bạn cần chuyển vào đường dẫn tệp
        content_file: Optional[str] = None,
    ):
        self.sentence_id = sentence_id
        self.sentence_type = sentence_type
        self.content_type = content_type
        self.content_detail = content_detail
        self.content_file = content_file
