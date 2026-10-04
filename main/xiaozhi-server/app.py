import sys
import uuid
import signal
import asyncio
from aioconsole import ainput
from config.settings import load_config
from config.logger import setup_logging
from core.utils.util import get_local_ip, validate_mcp_endpoint
from core.http_server import SimpleHttpServer
from core.websocket_server import WebSocketServer
from core.utils.util import check_ffmpeg_installed
from core.utils.gc_manager import get_gc_manager

TAG = __name__
logger = setup_logging()


async def wait_for_exit() -> None:
    """
    阻塞直到nhận Ctrl‑C / SIGTERM.
    - Unix: 使用 add_signal_handler
    - Windows: 依赖 KeyboardInterrupt
    """
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    if sys.platform != "win32":  # Unix / macOS
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await stop_event.wait()
    else:
        # Windows: chờ đợi một tương lai luôn chờ đợi,
        # Hãy để KeyboardInterrupt bong bóng lên asyncio.run để loại bỏ vấn đề thoát khỏi quá trình chặn các luồng thông thường kế thừa
        try:
            await asyncio.Future()
        except KeyboardInterrupt:  # Ctrl‑C
            pass


async def monitor_stdin():
    """监控标准输入，消费回车键"""
    while True:
        await ainput()  # Chờ nhập bất đồng bộ và nhận phím Enter


async def main():
    check_ffmpeg_installed()
    config = await load_config()

    # ưu tiên auth_key: Tệp cấu hình server.auth_key > manager-api.secret > được tạo tự động
    # auth_key được sử dụng để xác thực jwt, chẳng hạn như xác thực jwt của giao diện phân tích trực quan, tạo mã thông báo và xác thực websocket của giao diện ota
    # Lấy auth_key trong tệp cấu hình
    auth_key = config["server"].get("auth_key", "")

    # Xác minh auth_key, nếu không hợp lệ, hãy thử sử dụng manager-api.secret
    if not auth_key or len(auth_key) == 0 or "你" in auth_key or "YOUR_" in auth_key:
        auth_key = config.get("manager-api", {}).get("secret", "")
        # Xác minh bí mật, nếu không hợp lệ, tạo khóa ngẫu nhiên
        if (
            not auth_key
            or len(auth_key) == 0
            or "你" in auth_key
            or "YOUR_" in auth_key
        ):
            auth_key = str(uuid.uuid4().hex)

    config["server"]["auth_key"] = auth_key

    # Thêm nhiệm vụ giám sát stdin
    stdin_task = asyncio.create_task(monitor_stdin())

    # Khởi động trình quản lý GC toàn cầu (dọn dẹp 5 phút một lần)
    gc_manager = get_gc_manager(interval_seconds=300)
    await gc_manager.start()

    # Khởi động máy chủ WebSocket
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())
    # Bắt đầu máy chủ http đơn giản
    ota_server = SimpleHttpServer(config)
    ota_task = asyncio.create_task(ota_server.start())

    read_config_from_api = config.get("read_config_from_api", False)
    port = int(config["server"].get("http_port", 8003))
    if not read_config_from_api:
        logger.bind(tag=TAG).info(
            "Địa chỉ OTA:\t\thttp://{}:{}/xiaozhi/ota/",
            get_local_ip(),
            port,
        )
    logger.bind(tag=TAG).info(
        "Địa chỉ phân tích hình ảnh:\thttp://{}:{}/mcp/vision/explain",
        get_local_ip(),
        port,
    )
    mcp_endpoint = config.get("mcp_endpoint", None)
    if (
        mcp_endpoint is not None
        and "你" not in mcp_endpoint
        and "YOUR_" not in mcp_endpoint
    ):
        # Xác minh định dạng điểm truy cập MCP
        if validate_mcp_endpoint(mcp_endpoint):
            logger.bind(tag=TAG).info("Điểm MCP:\t{}", mcp_endpoint)
            # Chuyển đổi địa chỉ điểm đếm mcp thành điểm gọi
            mcp_endpoint = mcp_endpoint.replace("/mcp/", "/call/")
            config["mcp_endpoint"] = mcp_endpoint
        else:
            logger.bind(tag=TAG).error("Địa chỉ điểm MCP không đúng định dạng")
            config["mcp_endpoint"] = "YOUR_MCP_WEBSOCKET_ENDPOINT"

    # Nhận cấu hình WebSocket, sử dụng các giá trị mặc định an toàn
    websocket_port = 8000
    server_config = config.get("server", {})
    if isinstance(server_config, dict):
        websocket_port = int(server_config.get("port", 8000))

    logger.bind(tag=TAG).info(
        "Địa chỉ WebSocket:\tws://{}:{}/xiaozhi/v1/",
        get_local_ip(),
        websocket_port,
    )

    logger.bind(tag=TAG).info(
        "======= Địa chỉ trên dùng giao thức WebSocket, không mở bằng trình duyệt ======="
    )
    logger.bind(tag=TAG).info(
        "Để thử WebSocket, hãy khởi động mô-đun digital-human và mở trang tương tác trong trình duyệt"
    )
    logger.bind(tag=TAG).info(
        "=============================================================\n"
    )

    try:
        await wait_for_exit()  # Chờ đến khi nhận tín hiệu thoát
    except asyncio.CancelledError:
        print("Tác vụ đã bị hủy, đang dọn tài nguyên...")
    finally:
        # Dừng trình quản lý GC toàn cầu
        await gc_manager.stop()

        # Hủy tất cả tác vụ (điểm sửa lỗi chính)
        stdin_task.cancel()
        ws_task.cancel()
        if ota_task:
            ota_task.cancel()

        # Chờ kết thúc nhiệm vụ (phải thêm thời gian chờ)
        await asyncio.wait(
            [stdin_task, ws_task, ota_task] if ota_task else [stdin_task, ws_task],
            timeout=3.0,
            return_when=asyncio.ALL_COMPLETED,
        )
        print("Server đã đóng, chương trình kết thúc.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Đã dừng thủ công, chương trình kết thúc.")
