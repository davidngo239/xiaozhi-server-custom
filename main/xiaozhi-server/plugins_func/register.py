from config.logger import setup_logging
from enum import Enum

TAG = __name__

logger = setup_logging()


class ToolType(Enum):
    NONE = (1, "Không thực hiện thêm thao tác sau khi gọi công cụ")
    WAIT = (2, "Gọi công cụ và chờ hàm trả về")
    CHANGE_SYS_PROMPT = (3, "Đổi prompt hệ thống, tính cách hoặc vai trò trợ lý")
    SYSTEM_CTL = (
        4,
        "Điều khiển hệ thống như thoát hoặc phát nhạc; cần truyền tham số conn",
    )
    IOT_CTL = (5, "Điều khiển thiết bị IoT; cần truyền tham số conn")
    MCP_CLIENT = (6, "Máy khách MCP")

    def __init__(self, code, message):
        self.code = code
        self.message = message


class Action(Enum):
    ERROR = (-1, "Lỗi")
    NOTFOUND = (0, "Không tìm thấy hàm")
    NONE = (1, "Không thực hiện thao tác")
    RESPONSE = (2, "Trả lời trực tiếp")
    REQLLM = (3, "Gọi hàm rồi yêu cầu LLM tạo câu trả lời")
    RECORD = (4, "Ghi việc gọi công cụ vào lịch sử hội thoại")

    def __init__(self, code, message):
        self.code = code
        self.message = message


class ActionResponse:
    def __init__(self, action: Action, result=None, response=None):
        self.action = action  # kiểu hành động
        self.result = result  # kết quả của một hành động
        self.response = response  # Nội dung trả lời trực tiếp


class FunctionItem:
    def __init__(self, name, description, func, type):
        self.name = name
        self.description = description
        self.func = func
        self.type = type


class DeviceTypeRegistry:
    """thiết bịloại注册表 , 用于管理IOTthiết bịloại及其hàm"""

    def __init__(self):
        self.type_functions = {}  # type_signature -> {func_name: FunctionItem}

    def generate_device_type_id(self, descriptor):
        """通过thiết bị能力描述生成loạiID"""
        properties = sorted(descriptor["properties"].keys())
        methods = sorted(descriptor["methods"].keys())
        # Sử dụng kết hợp các thuộc tính và phương thức làm mã định danh duy nhất cho loại thiết bị
        type_signature = (
            f"{descriptor['name']}:{','.join(properties)}:{','.join(methods)}"
        )
        return type_signature

    def get_device_functions(self, type_id):
        """lấythiết bịloại对应的所有hàm"""
        return self.type_functions.get(type_id, {})

    def register_device_type(self, type_id, functions):
        """注册thiết bịloại及其hàm"""
        if type_id not in self.type_functions:
            self.type_functions[type_id] = functions


# Từ điển đăng ký hàm khởi tạo
all_function_registry = {}
# Tên mô-đun -> ánh xạ danh sách tên chức năng, được sử dụng để mở rộng tên trình cắm cấp mô-đun thành tên chức năng cụ thể
module_func_map = {}


def register_function(name, desc, type=None):
    """注册函数到函数注册字典的装饰器"""

    def decorator(func):
        all_function_registry[name] = FunctionItem(name, desc, func, type)
        # Ghi lại ánh xạ tên mô-đun thành tên chức năng, được sử dụng để mở rộng cấu hình trình cắm cấp mô-đun
        module_name = func.__module__.split(".")[-1]
        module_func_map.setdefault(module_name, []).append(name)
        logger.bind(tag=TAG).debug(f"Đã tải hàm '{name}', có thể đăng ký sử dụng")
        return func

    return decorator


def register_device_function(name, desc, type=None):
    """注册设备级别的函数到函数注册字典的装饰器"""

    def decorator(func):
        logger.bind(tag=TAG).debug(f"thiết bịhàm '{name}' đãtải")
        return func

    return decorator


class FunctionRegistry:
    def __init__(self):
        self.function_registry = {}
        self.logger = setup_logging()

    def register_function(self, name, func_item=None):
        # Nếu cung cấp func_item thì đăng ký trực tiếp
        if func_item:
            self.function_registry[name] = func_item
            self.logger.bind(tag=TAG).debug(f"函数 '{name}' 直接注册成功")
            return func_item

        # Nếu không thì tìm kiếm từ all_function_registry
        func = all_function_registry.get(name)
        if not func:
            self.logger.bind(tag=TAG).error(f"函数 '{name}' 未找到")
            return None
        self.function_registry[name] = func
        self.logger.bind(tag=TAG).debug(f"函数 '{name}' 注册成功")
        return func

    def unregister_function(self, name):
        # Chức năng hủy đăng ký để kiểm tra xem nó có tồn tại không
        if name not in self.function_registry:
            self.logger.bind(tag=TAG).error(f"函数 '{name}' 未找到")
            return False
        self.function_registry.pop(name, None)
        self.logger.bind(tag=TAG).info(f"函数 '{name}' 注销成功")
        return True

    def get_function(self, name):
        return self.function_registry.get(name)

    def get_all_functions(self):
        return self.function_registry

    def get_all_function_desc(self):
        return [func.description for _, func in self.function_registry.items()]
