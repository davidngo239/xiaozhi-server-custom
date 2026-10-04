from enum import Enum
from typing import Union, Optional


class InterfaceType(Enum):
    # Loại giao diện
    STREAM = "STREAM"  # giao diện phát trực tuyến
    NON_STREAM = "NON_STREAM"  # giao diện không phát trực tuyến
    LOCAL = "LOCAL"  # dịch vụ địa phương
