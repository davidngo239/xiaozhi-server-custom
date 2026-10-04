import os
import base64
import functools
import threading
from typing import Optional, Dict

import httpx

TAG = __name__


class DeviceNotFoundException(Exception):
    pass


class DeviceBindException(Exception):
    def __init__(self, bind_code):
        self.bind_code = bind_code
        super().__init__(f"Lỗi liên kết thiết bị, mã liên kết: {bind_code}")


class ManageApiClient:
    _instance = None
    _instance_lock = threading.Lock()  # Bảo vệ việc đọc và ghi của _instance và _closed
    _async_clients = {}  # Lưu trữ các ứng dụng khách riêng biệt cho từng vòng lặp sự kiện
    _secret = None
    _closed = False  # safe_close() được đặt thành True và sẽ không có kết nối mới nào được tạo sau khi đóng.

    def __new__(cls, config):
        """单例模式确保全局唯一实例 , 并支持传入cấu hìnhtham số"""
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._init_client(config)
            return cls._instance

    @classmethod
    def _init_client(cls, config):
        """khởi tạocấu hình（延迟tạomáy khách）"""
        cls.config = config.get("manager-api")

        if not cls.config:
            raise Exception("Cấu hình manager-api không hợp lệ")

        if not cls.config.get("url") or not cls.config.get("secret"):
            raise Exception("URL hoặc secret của manager-api không hợp lệ")

        if "你" in cls.config.get("secret") or "YOUR_" in cls.config.get("secret"):
            raise Exception("Vui lòng cấu hình secret của manager-api trước")

        cls._secret = cls.config.get("secret")
        cls.max_retries = cls.config.get("max_retries", 6)  # Số lần thử lại tối đa
        cls.retry_delay = cls.config.get("retry_delay", 10)  # Độ trễ thử lại ban đầu (giây)
        # Không tạo AsyncClient ở đây, trì hoãn việc tạo cho đến khi sử dụng thực tế
        cls._async_clients = {}
        cls._closed = False

    @classmethod
    async def _ensure_async_client(cls):
        """确保异步客户端已创建（为每个事件循环创建独立的客户端）"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)

            # Việc kiểm tra trạng thái đóng và tạo nhóm kết nối phải nằm trong cùng một phần quan trọng để tránh safe_close()
            # Sau khi xóa nhóm kết nối, sẽ có yêu cầu ghi lại ứng dụng khách mới.
            with cls._instance_lock:
                if cls._closed:
                    raise Exception(
                        "ManageApiClient đã đóng, không tạo thêm máy khách HTTP"
                    )

                if loop_id not in cls._async_clients:
                    # Máy chủ có thể chủ động đóng kết nối và nhóm kết nối httpx không thể phát hiện và dọn dẹp chính xác
                    limits = httpx.Limits(
                        max_keepalive_connections=0,  # Vô hiệu hóa tính năng duy trì và tạo kết nối mới mỗi lần
                    )
                    cls._async_clients[loop_id] = httpx.AsyncClient(
                        base_url=cls.config.get("url"),
                        headers={
                            "User-Agent": f"PythonClient/2.0 (PID:{os.getpid()})",
                            "Accept": "application/json",
                            "Authorization": "Bearer " + cls._secret,
                        },
                        timeout=cls.config.get("timeout", 30),
                        limits=limits,  # Hạn chế sử dụng
                        trust_env=False,
                    )
                return cls._async_clients[loop_id]
        except RuntimeError:
            # Nếu không có vòng lặp sự kiện đang chạy, hãy tạo một vòng lặp sự kiện tạm thời
            raise Exception("Phải gọi trong ngữ cảnh bất đồng bộ")

    @classmethod
    async def _async_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """gửi单次异步HTTPyêu cầu并xử lýphản hồi"""
        # Đảm bảo rằng ứng dụng khách đã được tạo
        client = await cls._ensure_async_client()
        endpoint = endpoint.lstrip("/")
        response = None
        try:
            response = await client.request(method, endpoint, **kwargs)
            response.raise_for_status()

            result = response.json()

            # Xử lý các lỗi nghiệp vụ do API trả về
            if result.get("code") == 10041:
                raise DeviceNotFoundException(result.get("msg"))
            elif result.get("code") == 10042:
                raise DeviceBindException(result.get("msg"))
            elif result.get("code") != 0:
                raise Exception(
                    f"API trả về lỗi: {result.get('msg', 'Lỗi không xác định')}"
                )

            # Trả về dữ liệu thành công
            return result.get("data") if result.get("code") == 0 else None
        finally:
            # Đảm bảo các phản hồi được đóng lại (sẽ được thực thi ngay cả khi xảy ra ngoại lệ)
            if response is not None:
                await response.aclose()

    @classmethod
    def _should_retry(cls, exception: Exception) -> bool:
        """判断sự cố是否应该thử lại"""
        # Lỗi liên quan đến kết nối mạng
        if isinstance(
            exception, (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)
        ):
            return True

        # Lỗi mã trạng thái HTTP
        if isinstance(exception, httpx.HTTPStatusError):
            status_code = exception.response.status_code
            return status_code in [408, 429, 500, 502, 503, 504]

        return False

    @classmethod
    async def _execute_async_request(cls, method: str, endpoint: str, **kwargs) -> Dict:
        """带thử lại机制的异步yêu cầuthực thi器"""
        import asyncio

        retry_count = 0

        while retry_count <= cls.max_retries:
            try:
                # Thực hiện các yêu cầu không đồng bộ
                return await cls._async_request(method, endpoint, **kwargs)
            except Exception as e:
                # Xác định xem bạn có nên thử lại không
                if retry_count < cls.max_retries and cls._should_retry(e):
                    retry_count += 1
                    print(
                        f"{method} {endpoint} 异步Yêu cầu thất bại , sẽ在 {cls.retry_delay:.1f} giây后tiến hành第 {retry_count} lầnthử lại"
                    )
                    await asyncio.sleep(cls.retry_delay)
                    continue
                else:
                    # Nếu không thử lại, một ngoại lệ sẽ được ném trực tiếp.
                    raise

    @classmethod
    def _get_instance(cls):
        """线程安全地lấy单例实例引用

        gọi方应使用trả về的局部引用 , 而不是判空后再次读取
        ManageApiClient._instance: 即使随后 safe_close() sẽ _instance
        置为 None , đãlấy的引用仍指向原对象 , 从而消除"判空之后、
        使用之前实例被置空"的 TOCTOU 竞态窗口.
        """
        with cls._instance_lock:
            return cls._instance

    @classmethod
    def safe_close(cls):
        """安全đóng所有异步kết nối池"""
        import asyncio

        with cls._instance_lock:
            cls._closed = True
            clients = list(cls._async_clients.values())
            cls._async_clients.clear()
            cls._instance = None

        for client in clients:
            try:
                asyncio.run(client.aclose())
            except Exception:
                pass


def api_guard(error_msg: str = None, raise_when_closed: bool = False):
    """装饰器: 统一lấy单例实例、判空与sự cố兜底

    - 通过 _get_instance() 一次性lấy实例局部引用 , 注入为被装饰hàm的
      第一个tham số , 消除与 safe_close() 之间的 TOCTOU 竞态窗口;
    - 实例未khởi tạo或đãđóngkhi: raise_when_closed=True 抛出明确sự cố
      （用于khởi động路径hàm） , 否则静默trả về None（用于守护线程路径）;
    - error_msg 不为 None khi捕获yêu cầusự cố、打印nhật ký并trả về None;
      为 None khisự cố原样抛出 , 由gọi方xử lý.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            instance = ManageApiClient._get_instance()
            if instance is None:
                if raise_when_closed:
                    raise Exception("ManageApiClient chưa khởi tạo hoặc đã đóng")
                return None
            if error_msg is None:
                return await func(instance, *args, **kwargs)
            try:
                return await func(instance, *args, **kwargs)
            except Exception as e:
                print(f"{error_msg}: {e}")
                return None

        return wrapper

    return decorator


@api_guard(raise_when_closed=True)
async def get_server_config(instance) -> Optional[Dict]:
    """lấydịch vụ器基础cấu hình"""
    return await instance._execute_async_request("POST", "/config/server-base")


@api_guard(raise_when_closed=True)
async def get_agent_models(
    instance, mac_address: str, client_id: str, selected_module: Dict
) -> Optional[Dict]:
    """lấy代理模型cấu hình"""
    return await instance._execute_async_request(
        "POST",
        "/config/agent-models",
        json={
            "macAddress": mac_address,
            "clientId": client_id,
            "selectedModule": selected_module,
        },
    )


@api_guard("Không thể lấy từ thay thế")
async def get_correct_words(instance, mac_address: str) -> Optional[Dict]:
    """获取智能体替换词"""
    return await instance._execute_async_request(
        "POST", "/config/correct-words", json={"macAddress": mac_address}
    )


@api_guard("Không thể tạo và lưu tóm tắt trò chuyện")
async def generate_and_save_chat_summary(instance, session_id: str) -> Optional[Dict]:
    """生成并lưu聊天记录总结（守护线程tronggọi , dịch vụđãđóngkhi静默trả về None）"""
    return await instance._execute_async_request(
        "POST",
        f"/agent/chat-summary/{session_id}/save",
    )


@api_guard("Không thể tạo và lưu tiêu đề trò chuyện")
async def generate_and_save_chat_title(instance, session_id: str) -> Optional[Dict]:
    """生成并lưu聊天标题（守护线程tronggọi , dịch vụđãđóngkhi静默trả về None）"""
    return await instance._execute_async_request(
        "POST",
        f"/agent/chat-title/{session_id}/generate",
    )


@api_guard("Báo cáo TTS thất bại")
async def report(
    instance,
    mac_address: str,
    session_id: str,
    chat_type: int,
    content: str,
    audio,
    report_time,
) -> Optional[Dict]:
    """异步聊天记录上报"""
    if not content:
        return None
    return await instance._execute_async_request(
        "POST",
        f"/agent/chat-history/report",
        json={
            "macAddress": mac_address,
            "sessionId": session_id,
            "chatType": chat_type,
            "content": content,
            "reportTime": report_time,
            "audioBase64": (base64.b64encode(audio).decode("utf-8") if audio else None),
        },
    )


@api_guard("Tra cứu danh bạ thất bại")
async def lookup_address_book(
    instance, caller_mac: str, nickname: str
) -> Optional[Dict]:
    """根据昵称查找目标设备"""
    return await instance._execute_async_request(
        "GET",
        f"/device/address-book/lookup?callerMac={caller_mac}&nickname={nickname}",
    )


def init_service(config):
    ManageApiClient(config)


def manage_api_http_safe_close():
    ManageApiClient.safe_close()
