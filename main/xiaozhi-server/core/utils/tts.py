import os
import re
import sys
import importlib

from config.logger import setup_logging
from core.utils.textUtils import check_emoji

logger = setup_logging()

punctuation_set = {
    "，",
    ",",  # Dấu phẩy tiếng Trung + dấu phẩy tiếng Anh
    "。",
    ".",  # Thời kỳ Trung Quốc + thời kỳ Anh
    "！",
    "!",  # Dấu chấm than tiếng Trung + dấu chấm than tiếng Anh
    "“",
    "”",
    '"',  # Dấu ngoặc kép tiếng Trung + dấu ngoặc kép tiếng Anh
    "：",
    ":",  # Dấu hai chấm tiếng Trung + dấu hai chấm tiếng Anh
    "-",
    "－",  # Dấu gạch ngang tiếng Anh + dòng ngang có độ rộng tối đa của tiếng Trung
    "、",  # Số Trung Quốc
    "[",
    "]",  # dấu ngoặc vuông
    "【",
    "】",  # Dấu ngoặc vuông của Trung Quốc
    "~",  # dấu ngã
}


def create_instance(class_name, *args, **kwargs):
    # Tạo phiên bản TTS
    if os.path.exists(os.path.join("core", "providers", "tts", f"{class_name}.py")):
        lib_name = f"core.providers.tts.{class_name}"
        if lib_name not in sys.modules:
            sys.modules[lib_name] = importlib.import_module(f"{lib_name}")
        return sys.modules[lib_name].TTSProvider(*args, **kwargs)

    raise ValueError(
        f"Loại TTS không được hỗ trợ: {class_name}. Vui lòng kiểm tra trường type trong cấu hình"
    )


class MarkdownCleaner:
    """
    封装 Markdown 清理逻辑：直接用 MarkdownCleaner.clean_markdown(text) 即可
    """

    # ký tự công thức
    NORMAL_FORMULA_CHARS = re.compile(r"[a-zA-Z\\^_{}\+\-\(\)\[\]=]")

    @staticmethod
    def _replace_inline_dollar(m: re.Match) -> str:
        """
        只要捕获到完整的 "$...$":
          - 如果内部有典型公式字符 => 去掉两侧 $
          - 否则 (纯数字/货币等) => 保留 "$...$"
        """
        content = m.group(1)
        if MarkdownCleaner.NORMAL_FORMULA_CHARS.search(content):
            return content
        else:
            return m.group(0)

    @staticmethod
    def _replace_table_block(match: re.Match) -> str:
        """
        当匹配到一个整段表格块时，回调该函数。
        """
        block_text = match.group("table_block")
        lines = block_text.strip("\n").split("\n")

        parsed_table = []
        for line in lines:
            line_stripped = line.strip()
            if re.match(r"^\|\s*[-:]+\s*(\|\s*[-:]+\s*)+\|?$", line_stripped):
                continue
            columns = [
                col.strip() for col in line_stripped.split("|") if col.strip() != ""
            ]
            if columns:
                parsed_table.append(columns)

        if not parsed_table:
            return ""

        headers = parsed_table[0]
        data_rows = parsed_table[1:] if len(parsed_table) > 1 else []

        lines_for_tts = []
        if len(parsed_table) == 1:
            # chỉ có một dòng
            only_line_str = ", ".join(parsed_table[0])
            lines_for_tts.append(f"Bảng một hàng: {only_line_str}")
        else:
            lines_for_tts.append(f"Tiêu đề cột: {', '.join(headers)}")
            for i, row in enumerate(data_rows, start=1):
                row_str_list = []
                for col_index, cell_val in enumerate(row):
                    if col_index < len(headers):
                        row_str_list.append(f"{headers[col_index]} = {cell_val}")
                    else:
                        row_str_list.append(cell_val)
                lines_for_tts.append(f"Hàng {i}: {', '.join(row_str_list)}")

        return "\n".join(lines_for_tts) + "\n"

    # Biên dịch trước tất cả các biểu thức chính quy (sắp xếp theo tần suất thực hiện)
    # Ở đây, các phương thức tĩnh của thay thế_xxx phải được xác định trước để chúng có thể được tham chiếu chính xác trong danh sách.
    REGEXES = [
        (re.compile(r"```.*?```", re.DOTALL), ""),  # khối mã
        (re.compile(r"^#+\s*", re.MULTILINE), ""),  # Tiêu đề
        (re.compile(r"(\*\*|__)(.*?)\1"), r"\2"),  # Đậm
        (re.compile(r"(\*|_)(?=\S)(.*?)(?<=\S)\1"), r"\2"),  # chữ nghiêng
        (re.compile(r"!\[.*?\]\(.*?\)"), ""),  # hình ảnh
        (re.compile(r"\[(.*?)\]\(.*?\)"), r"\1"),  # liên kết
        (re.compile(r"^\s*>+\s*", re.MULTILINE), ""),  # Trích dẫn
        (
            re.compile(r"(?P<table_block>(?:^[^\n]*\|[^\n]*\n)+)", re.MULTILINE),
            _replace_table_block,
        ),
        (re.compile(r"^\s*[*+-]\s*", re.MULTILINE), "- "),  # danh sách
        (re.compile(r"\$\$.*?\$\$", re.DOTALL), ""),  # công thức cấp khối
        (
            re.compile(r"(?<![A-Za-z0-9])\$([^\n$]+)\$(?![A-Za-z0-9])"),
            _replace_inline_dollar,
        ),
        (re.compile(r"\n{2,}"), "\n"),  # thêm dòng trống
    ]

    @staticmethod
    def clean_markdown(text: str) -> str:
        """
        主入口方法：依序执行所有正则，移除或替换 Markdown 元素
        """
        for regex, replacement in MarkdownCleaner.REGEXES:
            text = regex.sub(replacement, text)

        # Xóa biểu thức biểu tượng cảm xúc
        text = check_emoji(text)

        # Kiểm tra xem văn bản có hoàn toàn bằng tiếng Anh và có dấu câu cơ bản không
        if text and all(
            (c.isascii() or c.isspace() or c in punctuation_set) for c in text
        ):
            # Giữ nguyên không gian ban đầu và trả lại trực tiếp
            return text

        return text.strip()


def convert_percentage_to_range(percentage, min_val, max_val, base_val=None):
    """
    将百分比(-100~100)转换为指定范围的值

    Args:
        percentage: 百分比值 (-100 到 100)
        min_val: 目标范围最小值
        max_val: 目标范围最大值
        base_val: 基准值（可选，默认为范围中点）

    Returns:
        转换后的值
    """
    percentage, min_val, max_val = float(percentage), float(min_val), float(max_val)
    base_val = float(base_val) if base_val is not None else (min_val + max_val) / 2

    if percentage < 0:
        # Tỷ lệ phần trăm âm: nội suy tuyến tính từ base_val đến min_val
        result = base_val + (base_val - min_val) * (percentage / 100)
    else:
        # Tỷ lệ phần trăm dương: nội suy tuyến tính từ base_val đến max_val
        result = base_val + (max_val - base_val) * (percentage / 100)

    # Đảm bảo kết quả nằm trong phạm vi hợp lệ
    return max(min_val, min(max_val, result))
