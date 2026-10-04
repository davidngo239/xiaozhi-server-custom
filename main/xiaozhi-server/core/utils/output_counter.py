import datetime
from typing import Dict, Tuple

# Từ điển toàn cầu lưu trữ số từ đầu ra hàng ngày cho từng thiết bị
_device_daily_output: Dict[Tuple[str, datetime.date], int] = {}
# Ghi lại ngày kiểm tra lần cuối
_last_check_date: datetime.date = None


def reset_device_output():
    """
    重置所有thiết bị的每日输出字数
    每天0点gọi此hàm
    """
    _device_daily_output.clear()


def get_device_output(device_id: str) -> int:
    """
    获取设备当日的输出字数
    """
    current_date = datetime.datetime.now().date()
    return _device_daily_output.get((device_id, current_date), 0)


def add_device_output(device_id: str, char_count: int):
    """
    增加设备的输出字数
    """
    current_date = datetime.datetime.now().date()
    global _last_check_date

    # Nếu là cuộc gọi đầu tiên hoặc ngày thay đổi, hãy xóa bộ đếm
    if _last_check_date is None or _last_check_date != current_date:
        _device_daily_output.clear()
        _last_check_date = current_date

    current_count = _device_daily_output.get((device_id, current_date), 0)
    _device_daily_output[(device_id, current_date)] = current_count + char_count


def check_device_output_limit(device_id: str, max_output_size: int) -> bool:
    """
    检查设备是否超过输出限制
    :return: True 如果超过限制，False 如果未超过
    """
    if not device_id:
        return False
    current_output = get_device_output(device_id)
    return current_output >= max_output_size
