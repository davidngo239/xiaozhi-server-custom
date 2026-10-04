import struct


def decode_opus_from_file(input_file):
    """
    从p3文件trong解码 Opus dữ liệu , 并trả về一个 Opus dữ liệu包的列表以及总khi长.
    """
    opus_datas = []
    total_frames = 0
    sample_rate = 16000  # tốc độ lấy mẫu tập tin
    frame_duration_ms = 60  # Thời lượng khung hình
    frame_size = int(sample_rate * frame_duration_ms / 1000)

    with open(input_file, "rb") as f:
        while True:
            # Đọc tiêu đề (4 byte): [loại 1 byte, dành riêng 1 byte, độ dài 2 byte]
            header = f.read(4)
            if not header:
                break

            # Giải nén thông tin tiêu đề
            _, _, data_len = struct.unpack(">BBH", header)

            # Đọc dữ liệu Opus theo độ dài được chỉ định bởi tiêu đề
            opus_data = f.read(data_len)
            if len(opus_data) != data_len:
                raise ValueError(
                    f"Data length({len(opus_data)}) mismatch({data_len}) in the file."
                )

            opus_datas.append(opus_data)
            total_frames += 1

    # Tính tổng thời lượng
    total_duration = (total_frames * frame_duration_ms) / 1000.0
    return opus_datas, total_duration


def decode_opus_from_bytes(input_bytes):
    """
    从p3二进制dữ liệutrong解码 Opus dữ liệu , 并trả về一个 Opus dữ liệu包的列表以及总khi长.
    """
    import io

    opus_datas = []
    total_frames = 0
    sample_rate = 16000  # tốc độ lấy mẫu tập tin
    frame_duration_ms = 60  # Thời lượng khung hình
    frame_size = int(sample_rate * frame_duration_ms / 1000)

    f = io.BytesIO(input_bytes)
    while True:
        header = f.read(4)
        if not header:
            break
        _, _, data_len = struct.unpack(">BBH", header)
        opus_data = f.read(data_len)
        if len(opus_data) != data_len:
            raise ValueError(
                f"Data length({len(opus_data)}) mismatch({data_len}) in the bytes."
            )
        opus_datas.append(opus_data)
        total_frames += 1

    total_duration = (total_frames * frame_duration_ms) / 1000.0
    return opus_datas, total_duration
