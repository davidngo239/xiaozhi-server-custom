import os
import asyncio
from config.config_loader import read_config, get_project_dir, load_config


default_config_file = "config.yaml"
config_file_valid = False


def check_config_file():
    global config_file_valid
    if config_file_valid:
        return
    """
    简化的cấu hìnhkiểm tra , 仅hướng dẫnngười dùngcấu hình文件的使用情况
    """
    custom_config_file = get_project_dir() + "data/." + default_config_file
    if not os.path.exists(custom_config_file):
        raise FileNotFoundError(
            "Không tìm thấy data/.config.yaml. Kiểm tra tệp cấu hình theo hướng dẫn"
        )

    # Kiểm tra xem cấu hình có được đọc từ API không
    config = asyncio.run(load_config())
    if config.get("read_config_from_api", False):
        print("Đọc cấu hình từ API")
        old_config_origin = read_config(custom_config_file)
        if old_config_origin.get("selected_module") is not None:
            error_msg = (
                "Tệp cấu hình đang chứa cả cấu hình bảng quản lý và cấu hình cục bộ:\n"
            )
            error_msg += "\nBạn nên:\n"
            error_msg += "1. Sao chép config_from_api.yaml từ thư mục gốc vào data và đổi tên thành .config.yaml\n"
            error_msg += "2. Cấu hình địa chỉ API và khóa theo hướng dẫn\n"
            raise ValueError(error_msg)
    config_file_valid = True
