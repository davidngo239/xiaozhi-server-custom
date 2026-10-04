import time
import asyncio
from collections import deque
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()


class AudioRateController:
    """
    音频速率控制器 - 按照60ms帧时长精确控制音频发送
    解决高并发下的时间累积误差问题
    """

    def __init__(self, frame_duration=60, send_delay=0):
        """
        Args:
            frame_duration: 单个音频帧时长（毫秒），默认60ms
            send_delay: 自定义发送间隔（毫秒）。
                        0 = 按 frame_duration 节奏发；
                        >0 = 按 send_delay 节奏发（主线程不入队延迟，无预缓冲）
        """
        # Khoảng thời gian kiểm soát luồng (mili giây): sử dụng giá trị cấu hình khi send_delay > 0, nếu không thì sử dụng frame_duration
        self.interval_ms = send_delay if send_delay > 0 else frame_duration
        self.queue = deque()
        self.play_position = 0  # Vị trí chơi ảo (mili giây)
        self.start_timestamp = None  # Dấu thời gian bắt đầu (chỉ đọc, không sửa đổi)
        self.pending_send_task = None
        self.logger = logger
        self.queue_empty_event = asyncio.Event()  # Sự kiện xóa hàng đợi
        self.queue_empty_event.set()  # Trạng thái trống ban đầu
        self.queue_has_data_event = asyncio.Event()  # Xếp hàng sự kiện dữ liệu
        self._last_queue_empty_time = 0  # Lần cuối cùng hàng đợi được làm trống (giây)

    def reset(self):
        """重置控制器trạng thái"""
        if self.pending_send_task and not self.pending_send_task.done():
            self.pending_send_task.cancel()
            # Sau khi hủy tác vụ, tác vụ sẽ được dọn sạch ở vòng lặp sự kiện tiếp theo mà không bị chặn và chờ đợi.

        self.queue.clear()
        self.play_position = 0
        self.start_timestamp = None  # Đặt theo gói âm thanh đầu tiên
        self._last_queue_empty_time = 0  # đặt lại thời gian
        # Xử lý sự kiện liên quan
        self.queue_empty_event.set()
        self.queue_has_data_event.clear()

    def add_audio(self, opus_packet):
        """添加音频包到队列"""
        # Nếu hàng đợi trước đó trống, dấu thời gian cần được điều chỉnh để giữ thời gian phát lại liên tục
        # Bằng cách này, trong khi công cụ đang gọi và chờ, âm thanh mới được thêm vào sẽ không được phát trước.
        # Nếu khoảng thời gian ngắn (<1 khung hình), điều đó có nghĩa là phát trực tuyến bình thường và không cần thiết lập lại.
        if len(self.queue) == 0 and self.play_position > 0:
            elapsed_since_empty = (
                time.monotonic() - self._last_queue_empty_time
            ) * 1000
            # Chỉ khi khoảng thời gian vượt quá 1 khung hình thì nó mới được coi là "tạm dừng và tiếp tục" thực sự
            if elapsed_since_empty >= self.interval_ms:
                self.start_timestamp = time.monotonic() - (self.play_position / 1000)
                self.logger.bind(tag=TAG).debug(
                    f"队列从空恢复 , 重置khi间戳 , hiện tại播放位置: {self.play_position}ms , 间隔: {elapsed_since_empty:.0f}ms"
                )

        self.queue.append(("audio", opus_packet))
        # Xử lý sự kiện liên quan
        self.queue_empty_event.clear()
        self.queue_has_data_event.set()

    def add_message(self, message_callback):
        """
        添加thông điệp到队列（立即gửi , 不占用播放khi间）

        Args:
            message_callback: thông điệpgửi回调hàm async def()
        """
        if len(self.queue) == 0 and self.play_position > 0:
            elapsed_since_empty = (
                time.monotonic() - self._last_queue_empty_time
            ) * 1000
            if elapsed_since_empty >= self.interval_ms:
                self.start_timestamp = time.monotonic() - (self.play_position / 1000)
                self.logger.bind(tag=TAG).debug(
                    f"队列从空恢复 , 重置khi间戳 , hiện tại播放位置: {self.play_position}ms , 间隔: {elapsed_since_empty:.0f}ms"
                )

        self.queue.append(("message", message_callback))
        # Xử lý sự kiện liên quan
        self.queue_empty_event.clear()
        self.queue_has_data_event.set()

    def _get_elapsed_ms(self):
        """获取已经过的时间（毫秒）"""
        if self.start_timestamp is None:
            return 0
        return (time.monotonic() - self.start_timestamp) * 1000

    async def check_queue(self, send_audio_callback):
        """
        kiểm tra队列并按khigửiâm thanh/thông điệp

        Args:
            send_audio_callback: gửiâm thanh的回调hàm async def(opus_packet)
        """
        while self.queue:
            item = self.queue[0]
            item_type = item[0]

            if item_type == "message":
                # Kiểu tin nhắn: Gửi ngay, không chiếm thời gian chơi
                _, message_callback = item
                self.queue.popleft()
                try:
                    await message_callback()
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"gửithông điệpthất bại: {e}")
                    raise

            elif item_type == "audio":
                if self.start_timestamp is None:
                    self.start_timestamp = time.monotonic()

                _, opus_packet = item

                # Chờ trong một vòng lặp cho đến khi thời gian đến
                while True:
                    # Tính chênh lệch thời gian
                    elapsed_ms = self._get_elapsed_ms()
                    output_ms = self.play_position

                    if elapsed_ms < output_ms:
                        # Chưa tới giờ gửi, hãy tính thời gian chờ
                        wait_ms = output_ms - elapsed_ms

                        # Tiếp tục kiểm tra sau khi chờ đợi (cho phép ngắt quãng)
                        try:
                            await asyncio.sleep(wait_ms / 1000)
                        except asyncio.CancelledError:
                            self.logger.bind(tag=TAG).debug("âm thanhgửitác vụ被hủy")
                            raise
                        # Kiểm tra lại thời gian sau khi chờ đợi (lặp lại while True)
                    else:
                        # Đã hết thời gian, hãy thoát khỏi vòng chờ đợi
                        break

                # Đã hết thời gian, hãy xóa khỏi hàng đợi và gửi
                self.queue.popleft()
                self.play_position += self.interval_ms
                try:
                    await send_audio_callback(opus_packet)
                except Exception as e:
                    self.logger.bind(tag=TAG).error(f"gửiâm thanhthất bại: {e}")
                    raise

        # Xóa sự kiện sau khi hàng đợi được xử lý
        self.queue_empty_event.set()
        self.queue_has_data_event.clear()
        self._last_queue_empty_time = time.monotonic()  # Ghi lại thời gian trống hàng đợi

    def start_sending(self, send_audio_callback):
        """
        khởi động异步gửitác vụ

        Args:
            send_audio_callback: gửiâm thanh的回调hàm

        Returns:
            asyncio.Task: gửitác vụ
        """

        async def _send_loop():
            try:
                while True:
                    # Chờ đợi các sự kiện dữ liệu xếp hàng, không thăm dò và chờ chiếm CPU
                    await self.queue_has_data_event.wait()

                    await self.check_queue(send_audio_callback)
            except asyncio.CancelledError:
                self.logger.bind(tag=TAG).debug("音频发送循环已停止")
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"âm thanhgửi循环sự cố: {e}")

        self.pending_send_task = asyncio.create_task(_send_loop())
        return self.pending_send_task

    def stop_sending(self):
        """停止gửitác vụ"""
        if self.pending_send_task and not self.pending_send_task.done():
            self.pending_send_task.cancel()
            self.logger.bind(tag=TAG).debug("đãhủyâm thanhgửitác vụ")
