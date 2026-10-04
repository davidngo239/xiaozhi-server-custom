Tài liệu này hướng dẫn phát triển mô-đun người ảo. Nếu cần triển khai máy chủ Xiaozhi, hãy xem [hướng dẫn triển khai](../../README.md#%E9%83%A8%E7%BD%B2%E6%96%87%E6%A1%A3).

Để triển khai người ảo trên máy tất cả trong một, khởi chạy Kiosk toàn màn hình hoặc cấu hình môi trường hệ thống, xem [hướng dẫn triển khai máy tất cả trong một](../../docs/all-in-one-digital-human-setup.md).

Để tải mô hình từ khóa đánh thức, cấu hình thời gian chạy và xem hướng dẫn sử dụng, xem [tài liệu về từ khóa đánh thức](../../docs/digital-human-wakeword.md).

# Giới thiệu dự án

`digital-human` là mô-đun thử nghiệm người ảo độc lập. Mô-đun cung cấp trang thử nghiệm cục bộ, tài nguyên giao diện, bộ chạy từ khóa đánh thức và cầu nối sự kiện để kiểm tra toàn bộ luồng tương tác.

# Khởi chạy nhanh

Cài đặt các gói phụ thuộc:

```bash
pip install -r wakeword_runtime/requirements.txt
```

Khởi chạy mô-đun:

```bash
python start.py
```

# Địa chỉ truy cập

Sau khi khởi chạy, có thể truy cập:

- Trang web: http://127.0.0.1:8006/index.html
- WebSocket cầu nối sự kiện: ws://127.0.0.1:8006/wakeword-ws
- Kiểm tra trạng thái: http://127.0.0.1:8006/health

# Cấu trúc thư mục

- `start.py`: điểm khởi chạy mô-đun
- `index.html`: trang thử nghiệm người ảo
- `wakeword_runtime`: bộ chạy và cấu hình từ khóa đánh thức cục bộ
- `js`, `css`: mã giao diện và kiểu hiển thị
- `images`, `resources`: tài nguyên giao diện

# Tài liệu liên quan

- [Hướng dẫn triển khai máy tất cả trong một](../../docs/all-in-one-digital-human-setup.md): triển khai trên thiết bị x86, trình chiếu Kiosk và cấu hình tự khởi động.
- [Tài liệu về từ khóa đánh thức](../../docs/digital-human-wakeword.md): tải mô hình, cấu hình bộ chạy và gỡ lỗi cục bộ.
