import os
import sys
import asyncio
from loguru import logger
from config.config_loader import load_config
from config.settings import check_config_file
from core.utils.cache.manager import cache_manager, CacheType

SERVER_VERSION = "0.9.7"
_logger_initialized = False


def get_module_abbreviation(module_name, module_dict):
    """获取模块名称的缩写，如果为空则返回00
    如果名称中包含下划线，则返回下划线后面的前两个字符
    """
    module_value = module_dict.get(module_name, "")
    if not module_value:
        return "00"
    if "_" in module_value:
        parts = module_value.split("_")
        return parts[-1][:2] if parts[-1] else "00"
    return module_value[:2]


def build_module_string(selected_module):
    """构建模块字符串"""
    return (
        get_module_abbreviation("VAD", selected_module)
        + get_module_abbreviation("ASR", selected_module)
        + get_module_abbreviation("LLM", selected_module)
        + get_module_abbreviation("TTS", selected_module)
        + get_module_abbreviation("Memory", selected_module)
        + get_module_abbreviation("Intent", selected_module)
        + get_module_abbreviation("VLLM", selected_module)
    )


def formatter(record):
    """为没有 tag 的日志添加默认值，并处理动态模块字符串"""
    record["extra"].setdefault("tag", record["name"])
    # Nếu selected_module không được đặt, giá trị mặc định sẽ được sử dụng
    record["extra"].setdefault("selected_module", "00000000000000")
    # Trích xuất selected_module từ cấp cao nhất đến cấp cao nhất để hỗ trợ định dạng {selected_module}
    record["selected_module"] = record["extra"]["selected_module"]
    return record["message"]


def setup_logging(config=None):
    """从cấu hình文件trong读取nhật kýcấu hình , 并设置nhật ký输出định dạng和级别"""
    if config is None:
        check_config_file()
        # Trước tiên hãy kiểm tra bộ nhớ đệm để tránh lặp lại chờ đợi tải_config trong ngữ cảnh không đồng bộ
        config = cache_manager.get(CacheType.CONFIG, "main_config")
        if config is None:
            # Không có bộ nhớ đệm (về mặt lý thuyết là không nên xảy ra) trước khi sử dụng asyncio.run
            config = asyncio.run(load_config())
    log_config = config["log"]
    global _logger_initialized

    # Định cấu hình nhật ký trong lần khởi tạo đầu tiên
    if not _logger_initialized:
        # Khởi tạo với chuỗi mô-đun mặc định
        logger.configure(
            extra={
                "selected_module": log_config.get("selected_module", "00000000000000"),
            }
        )

        log_format = log_config.get(
            "log_format",
            "<green>{time:YYMMDD HH:mm:ss}</green>[{version}_{extra[selected_module]}][<light-blue>{extra[tag]}</light-blue>]-<level>{level}</level>-<light-green>{message}</light-green>",
        )
        log_format_file = log_config.get(
            "log_format_file",
            "{time:YYYY-MM-DD HH:mm:ss} - {version}_{extra[selected_module]} - {name} - {level} - {extra[tag]} - {message}",
        )
        log_format = log_format.replace("{version}", SERVER_VERSION)
        log_format_file = log_format_file.replace("{version}", SERVER_VERSION)

        log_level = log_config.get("log_level", "INFO")
        log_dir = log_config.get("log_dir", "tmp")
        log_file = log_config.get("log_file", "server.log")
        data_dir = log_config.get("data_dir", "data")

        os.makedirs(log_dir, exist_ok=True)
        os.makedirs(data_dir, exist_ok=True)

        # Định cấu hình đầu ra nhật ký
        logger.remove()

        # xuất ra bàn điều khiển
        logger.add(sys.stdout, format=log_format, level=log_level, filter=formatter)

        # Xuất ra tệp - thư mục thống nhất, xoay theo kích thước
        # Đường dẫn đầy đủ của tệp nhật ký
        log_file_path = os.path.join(log_dir, log_file)

        # Thêm trình xử lý nhật ký
        logger.add(
            log_file_path,
            format=log_format_file,
            level=log_level,
            filter=formatter,
            rotation="10 MB",  # Tối đa 10 MB mỗi tệp
            retention="30 days",  # Giữ trong 30 ngày
            compression=None,
            encoding="utf-8",
            enqueue=True,  # An toàn không đồng bộ
            backtrace=True,
            diagnose=True,
        )
        _logger_initialized = True  # Đánh dấu là đã khởi tạo

    return logger


def create_connection_logger(selected_module_str):
    """为kết nốitạo独立的nhật ký器 , 绑定特定的mô-đun字符串"""
    return logger.bind(selected_module=selected_module_str)
