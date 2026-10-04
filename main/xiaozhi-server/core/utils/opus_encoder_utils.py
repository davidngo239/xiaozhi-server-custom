"""
Opus编码công cụ类
sẽPCMâm thanhdữ liệu编码为Opusđịnh dạng
"""

import logging
import traceback
import numpy as np
from opuslib_next import Encoder
from opuslib_next import constants
from typing import Optional, Callable, Any


class OpusEncoderUtils:
    """PCM到Opus的编码器"""

    def __init__(self, sample_rate: int, channels: int, frame_size_ms: int):
        """
        初始化Opus编码器

        Args:
            sample_rate: 采样率 (Hz)
            channels: 通道数 (1=单声道, 2=立体声)
            frame_size_ms: 帧大小 (毫秒)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.frame_size_ms = frame_size_ms
        # Tính số lượng mẫu trên mỗi khung = tốc độ lấy mẫu * kích thước khung (ms) / 1000
        self.frame_size = (sample_rate * frame_size_ms) // 1000
        # Tổng kích thước khung hình = mẫu trên mỗi khung hình * số kênh
        self.total_frame_size = self.frame_size * channels

        # Cài đặt tốc độ bit và độ phức tạp
        self.bitrate = 24000  # bps
        self.complexity = 10  # chất lượng cao nhất

        # Bộ đệm được khởi tạo trống
        self.buffer = np.array([], dtype=np.int16)

        try:
            # Tạo bộ mã hóa Opus
            self.encoder = Encoder(
                sample_rate,
                channels,
                constants.APPLICATION_AUDIO,  # Chế độ tối ưu hóa âm thanh
            )
            self.encoder.bitrate = self.bitrate
            self.encoder.complexity = self.complexity
            self.encoder.signal = constants.SIGNAL_VOICE  # Tối ưu hóa tín hiệu thoại
        except Exception as e:
            logging.error(f"khởi tạoOpus编码器thất bại: {e}")
            raise RuntimeError("Khởi tạo thất bại") from e

    def reset_state(self):
        """重置编码器trạng thái"""
        self.encoder.reset_state()
        self.buffer = np.array([], dtype=np.int16)

    def encode_pcm_to_opus_stream(
        self, pcm_data: bytes, end_of_stream: bool, callback: Callable[[Any], Any]
    ):
        """
        sẽPCMdữ liệu编码为Opusđịnh dạng , 以流式方式tiến hànhxử lý

        Args:
            pcm_data: PCM字节dữ liệu
            end_of_stream: 是否为流的结束,
            callback: opusxử lý方法

        Returns:
            Opusdữ liệu包列表
        """
        # Chuyển đổi dữ liệu byte thành mảng ngắn
        new_samples = self._convert_bytes_to_shorts(pcm_data)

        # Xác minh dữ liệu PCM
        self._validate_pcm_data(new_samples)

        # Nối dữ liệu mới vào bộ đệm
        self.buffer = np.append(self.buffer, new_samples)

        offset = 0

        # Xử lý tất cả các khung hoàn chỉnh
        while offset <= len(self.buffer) - self.total_frame_size:
            frame = self.buffer[offset : offset + self.total_frame_size]
            output = self._encode(frame)
            if output:
                callback(output)
            offset += self.total_frame_size

        # Giữ các mẫu chưa được xử lý
        self.buffer = self.buffer[offset:]

        # Xử lý dữ liệu còn lại ở cuối luồng
        if end_of_stream and len(self.buffer) > 0:
            # Tạo khung cuối cùng và điền nó bằng số 0
            last_frame = np.zeros(self.total_frame_size, dtype=np.int16)
            last_frame[: len(self.buffer)] = self.buffer

            output = self._encode(last_frame)
            if output:
                callback(output)
            self.buffer = np.array([], dtype=np.int16)

    def _encode(self, frame: np.ndarray) -> Optional[bytes]:
        """编码一帧âm thanhdữ liệu"""
        try:
            # Bộ mã hóa được giải phóng, mã hóa bị bỏ qua
            if not hasattr(self, "encoder") or self.encoder is None:
                return None
            # Chuyển đổi mảng numpy thành byte
            frame_bytes = frame.tobytes()
            # opuslib yêu cầu số byte đầu vào phải là bội số của các kênh*2
            encoded = self.encoder.encode(frame_bytes, self.frame_size)
            return encoded
        except Exception as e:
            logging.error(f"Opus编码thất bại: {e}")
            traceback.print_exc()
            return None

    def _convert_bytes_to_shorts(self, bytes_data: bytes) -> np.ndarray:
        """将字节数组转换为short数组 (16位PCM)"""
        # Giả sử đầu vào là PCM 16 bit theo thứ tự endian nhỏ
        return np.frombuffer(bytes_data, dtype=np.int16)

    def _validate_pcm_data(self, pcm_shorts: np.ndarray) -> None:
        """验证PCMdữ liệu是否有效"""
        # Phạm vi dữ liệu PCM 16 bit là -32768 đến 32767
        if np.any((pcm_shorts < -32768) | (pcm_shorts > 32767)):
            invalid_samples = pcm_shorts[(pcm_shorts < -32768) | (pcm_shorts > 32767)]
            logging.warning(f"发现无效PCM样本: {invalid_samples[:5]}...")
            # Trong các ứng dụng thực tế, bạn có thể chọn cắt thay vì ném ngoại lệ.
            # np.clip(pcm_shorts, -32768, 32767, out=pcm_shorts)

    def close(self):
        """đóng编码器并释放资源"""
        if hasattr(self, "encoder") and self.encoder:
            try:
                del self.encoder
                self.encoder = None
            except Exception as e:
                logging.error(f"Error releasing Opus encoder: {e}")
