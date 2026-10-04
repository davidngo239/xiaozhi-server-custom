import asyncio
import logging

import websockets
from config.logger import setup_logging


class SuppressInvalidHandshakeFilter(logging.Filter):
    """过滤掉无效握手Lỗinhật ký（如HTTPS访问WS端口）"""

    def filter(self, record):
        msg = record.getMessage()
        suppress_keywords = [
            "opening handshake failed",
            "did not receive a valid HTTP request",
            "connection closed while reading HTTP request",
            "line without CRLF",
        ]
        return not any(keyword in msg for keyword in suppress_keywords)


def _setup_websockets_logger():
    """cấu hình websockets 相关的所有 logger , 过滤无效握手Lỗi"""
    filter_instance = SuppressInvalidHandshakeFilter()
    for logger_name in ["websockets", "websockets.server", "websockets.client"]:
        logger = logging.getLogger(logger_name)
        logger.addFilter(filter_instance)


_setup_websockets_logger()


from core.connection import ConnectionHandler
from config.config_loader import get_config_from_api_async
from core.auth import AuthManager, AuthenticationError
from core.utils.modules_initialize import initialize_modules
from core.utils.util import check_vad_update, check_asr_update

TAG = __name__


class WebSocketServer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging(config)
        self.config_lock = asyncio.Lock()
        modules = initialize_modules(
            self.logger,
            self.config,
            "VAD" in self.config["selected_module"],
            "ASR" in self.config["selected_module"],
            "LLM" in self.config["selected_module"],
            False,
            "Memory" in self.config["selected_module"],
            "Intent" in self.config["selected_module"],
        )
        self._vad = modules["vad"] if "vad" in modules else None
        self._asr = modules["asr"] if "asr" in modules else None
        self._llm = modules["llm"] if "llm" in modules else None
        self._intent = modules["intent"] if "intent" in modules else None
        self._memory = modules["memory"] if "memory" in modules else None

        auth_config = self.config["server"].get("auth", {})
        self.auth_enable = auth_config.get("enabled", False)
        # Danh sách trắng thiết bị
        self.allowed_devices = set(auth_config.get("allowed_devices", []))
        secret_key = self.config["server"]["auth_key"]
        expire_seconds = auth_config.get("expire_seconds", None)
        self.auth = AuthManager(secret_key=secret_key, expire_seconds=expire_seconds)

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("port", 8000))

        async with websockets.serve(
            self._handle_connection,
            host,
            port,
            process_request=self._http_response,
            ping_interval=None,
        ):
            await asyncio.Future()

    async def _handle_connection(self, websocket: websockets.ServerConnection):
        headers = dict(websocket.request.headers)
        if headers.get("device-id", None) is None:
            # Cố gắng lấy id thiết bị từ tham số truy vấn của URL
            from urllib.parse import parse_qs, urlparse

            # Nhận đường dẫn từ yêu cầu WebSocket
            request_path = websocket.request.path
            if not request_path:
                self.logger.bind(tag=TAG).error("Không thể lấy đường dẫn yêu cầu")
                await websocket.close()
                return
            parsed_url = urlparse(request_path)
            query_params = parse_qs(parsed_url.query)
            if "device-id" not in query_params:
                await websocket.send(
                    "Cổng đang hoạt động. Mở digital-human để thử kết nối"
                )
                await websocket.close()
                return
            else:
                websocket.request.headers["device-id"] = query_params["device-id"][0]
            if "client-id" in query_params:
                websocket.request.headers["client-id"] = query_params["client-id"][0]
            if "authorization" in query_params:
                websocket.request.headers["authorization"] = query_params[
                    "authorization"
                ][0]

        """xử lý新kết nối , 每次tạo独立的ConnectionHandler"""
        # Xác thực trước, sau đó thiết lập kết nối
        try:
            await self._handle_auth(websocket)
        except AuthenticationError:
            await websocket.send("Xác thực thất bại")
            await websocket.close()
            return
        # Truyền vào phiên bản máy chủ hiện tại khi tạo ConnectionHandler
        handler = ConnectionHandler(
            self.config,
            self._vad,
            self._asr,
            self._llm,
            self._memory,
            self._intent,
            self,  # Truyền vào phiên bản máy chủ
        )
        try:
            await handler.handle_connection(websocket)
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"Lỗi khi xử lý kết nối: {e}")
        finally:
            # Buộc đóng kết nối (nếu nó chưa được đóng)
            try:
                # Kiểm tra trạng thái WebSocket một cách an toàn và đóng
                if hasattr(websocket, "closed") and not websocket.closed:
                    await websocket.close()
                elif hasattr(websocket, "state") and websocket.state.name != "CLOSED":
                    await websocket.close()
                else:
                    # Nếu không có thuộc tính đóng, hãy thử đóng trực tiếp.
                    await websocket.close()
            except Exception as close_error:
                self.logger.bind(tag=TAG).error(
                    f"Lỗi khi máy chủ buộc đóng kết nối: {close_error}"
                )

    async def _http_response(self, websocket, request_headers):
        # Kiểm tra xem đó có phải là yêu cầu nâng cấp WebSocket không
        if request_headers.headers.get("connection", "").lower() == "upgrade":
            # Nếu đó là yêu cầu WebSocket, hãy trả về Không để cho phép bắt tay tiếp tục.
            return None
        else:
            # Nếu đó là một yêu cầu HTTP bình thường, "máy chủ đang chạy" sẽ được trả về.
            return websocket.respond(200, "Server is running\n")

    async def update_config(self) -> bool:
        """cập nhậtdịch vụ器cấu hình并重新khởi tạo组件

        Returns:
            bool: cập nhật是否thành công
        """
        try:
            async with self.config_lock:
                # Tìm nạp lại cấu hình (sử dụng phiên bản không đồng bộ)
                new_config = await get_config_from_api_async(self.config)
                if new_config is None:
                    self.logger.bind(tag=TAG).error("Không tải được cấu hình mới")
                    return False
                self.logger.bind(tag=TAG).info("Đã tải cấu hình mới")
                # Kiểm tra xem loại VAD và ASR có cần được cập nhật không
                update_vad = check_vad_update(self.config, new_config)
                update_asr = check_asr_update(self.config, new_config)
                self.logger.bind(tag=TAG).info(
                    f"Kiểm tra cập nhật loại VAD và ASR: {update_vad} {update_asr}"
                )
                # Cập nhật cấu hình
                self.config = new_config
                # Khởi tạo lại thành phần
                modules = initialize_modules(
                    self.logger,
                    new_config,
                    update_vad,
                    update_asr,
                    "LLM" in new_config["selected_module"],
                    False,
                    "Memory" in new_config["selected_module"],
                    "Intent" in new_config["selected_module"],
                )

                # Cập nhật phiên bản thành phần
                if "vad" in modules:
                    self._vad = modules["vad"]
                if "asr" in modules:
                    self._asr = modules["asr"]
                if "llm" in modules:
                    self._llm = modules["llm"]
                if "intent" in modules:
                    self._intent = modules["intent"]
                if "memory" in modules:
                    self._memory = modules["memory"]
                self.logger.bind(tag=TAG).info("Đã hoàn tất tác vụ cập nhật cấu hình")
                return True
        except Exception as e:
            self.logger.bind(tag=TAG).error(
                f"Không thể cập nhật cấu hình server: {str(e)}"
            )
            return False

    async def _handle_auth(self, websocket: websockets.ServerConnection):
        # Xác thực trước, sau đó thiết lập kết nối
        if self.auth_enable:
            headers = dict(websocket.request.headers)
            device_id = headers.get("device-id", None)
            client_id = headers.get("client-id", None)
            if self.allowed_devices and device_id in self.allowed_devices:
                # Nếu đó là thiết bị nằm trong danh sách trắng, mã thông báo sẽ không được xác minh và thiết bị sẽ được phát hành trực tiếp.
                return
            else:
                # Nếu không hãy xác minh mã thông báo
                token = headers.get("authorization", "")
                if token.startswith("Bearer "):
                    token = token[7:]  # Xóa tiền tố 'Bearer'
                else:
                    raise AuthenticationError("Missing or invalid Authorization header")
                # Thực hiện chứng nhận
                auth_success = self.auth.verify_token(
                    token, client_id=client_id, username=device_id
                )
                if not auth_success:
                    raise AuthenticationError("Invalid token")
