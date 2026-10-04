import json
import copy
from aiohttp import web
from config.logger import setup_logging
from core.api.base_handler import BaseHandler
from core.utils.util import get_vision_url, is_valid_image_file
from core.utils.vllm import create_instance
from config.config_loader import get_private_config_from_api
from core.utils.auth import AuthToken
import base64
from typing import Tuple, Optional
from plugins_func.register import Action

TAG = __name__

# Đặt kích thước tệp tối đa thành 5 MB
MAX_FILE_SIZE = 5 * 1024 * 1024


class VisionHandler(BaseHandler):
    def __init__(self, config: dict):
        super().__init__(config)
        # Công cụ xác thực khởi tạo
        self.auth = AuthToken(config["server"]["auth_key"])

    def _create_error_response(self, message: str) -> dict:
        """tạo统一的Lỗiphản hồiđịnh dạng"""
        return {"success": False, "message": message}

    def _verify_auth_token(self, request) -> Tuple[bool, Optional[str]]:
        """验证认证token"""
        # Chế độ kiểm tra: cho phép mã thông báo kiểm tra cụ thể hoặc bỏ qua xác minh
        auth_header = request.headers.get("Authorization", "")
        client_id = request.headers.get("Client-Id", "")

        # Cho phép máy khách thử nghiệm bỏ qua bước xác thực
        if client_id == "web_test_client":
            device_id = request.headers.get("Device-Id", "test_device")
            return True, device_id

        if not auth_header.startswith("Bearer "):
            return False, None

        token = auth_header[7:]  # Xóa tiền tố "Bearer"
        return self.auth.verify_token(token)

    async def handle_post(self, request):
        """xử lý MCP Vision POST yêu cầu"""
        response = None  # Khởi tạo biến phản hồi
        try:
            # Mã thông báo xác minh
            is_valid, token_device_id = self._verify_auth_token(request)
            if not is_valid:
                response = web.Response(
                    text=json.dumps(
                        self._create_error_response(
                            "Token xác thực không hợp lệ hoặc đã hết hạn"
                        )
                    ),
                    content_type="application/json",
                    status=401,
                )
                return response

            # Nhận thông tin tiêu đề yêu cầu
            device_id = request.headers.get("Device-Id", "")
            client_id = request.headers.get("Client-Id", "")
            if device_id != token_device_id:
                raise ValueError("ID thiết bị không khớp với token")
            # Phân tích các yêu cầu nhiều phần/biểu mẫu dữ liệu
            reader = await request.multipart()

            # Đọc trường câu hỏi
            question_field = await reader.next()
            if question_field is None:
                raise ValueError("Thiếu trường câu hỏi")
            question = await question_field.text()
            self.logger.bind(tag=TAG).debug(f"Question: {question}")

            # Đọc tập tin hình ảnh
            image_field = await reader.next()
            if image_field is None:
                raise ValueError("Thiếu tệp hình ảnh")

            # Đọc dữ liệu hình ảnh
            image_data = await image_field.read()
            if not image_data:
                raise ValueError("Dữ liệu hình ảnh trống")

            # Kiểm tra kích thước tập tin
            if len(image_data) > MAX_FILE_SIZE:
                raise ValueError(
                    f"Hình ảnh vượt giới hạn, kích thước tối đa là {MAX_FILE_SIZE / 1024 / 1024}MB"
                )

            # Kiểm tra định dạng tập tin
            if not is_valid_image_file(image_data):
                raise ValueError(
                    "Định dạng không được hỗ trợ. Tải lên hình ảnh hợp lệ: JPEG, PNG, GIF, BMP, TIFF hoặc WEBP"
                )

            # Chuyển đổi hình ảnh sang mã hóa base64
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Nếu bảng điều khiển thông minh được bật, hãy lấy cấu hình mô hình từ bảng điều khiển thông minh
            current_config = copy.deepcopy(self.config)
            read_config_from_api = current_config.get("read_config_from_api", False)
            if read_config_from_api:
                current_config = await get_private_config_from_api(
                    current_config,
                    device_id,
                    client_id,
                )

            select_vllm_module = current_config["selected_module"].get("VLLM")
            if not select_vllm_module:
                raise ValueError("Bạn chưa chọn mô-đun phân tích hình ảnh mặc định")

            vllm_type = (
                select_vllm_module
                if "type" not in current_config["VLLM"][select_vllm_module]
                else current_config["VLLM"][select_vllm_module]["type"]
            )

            if not vllm_type:
                raise ValueError(
                    f"Không tìm thấy nhà cung cấp cho mô-đun VLLM {vllm_type}"
                )

            vllm = create_instance(
                vllm_type, current_config["VLLM"][select_vllm_module]
            )

            result = vllm.response(question, image_base64)

            return_json = {
                "success": True,
                "action": Action.RESPONSE.name,
                "response": result,
            }

            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except ValueError as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision POSTyêu cầusự cố: {e}")
            return_json = self._create_error_response(str(e))
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision POSTyêu cầusự cố: {e}")
            return_json = self._create_error_response("Lỗi khi xử lý yêu cầu")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            if response:
                self._add_cors_headers(response)
            return response

    async def handle_get(self, request):
        """xử lý MCP Vision GET yêu cầu"""
        try:
            vision_explain = get_vision_url(self.config)
            if vision_explain and len(vision_explain) > 0 and "null" != vision_explain:
                message = f"API MCP Vision đang hoạt động. Địa chỉ phân tích hình ảnh: {vision_explain}"
            else:
                message = "API MCP Vision chưa hoạt động đúng. Mở data/.config.yaml và cấu hình địa chỉ server.vision_explain"

            response = web.Response(text=message, content_type="text/plain")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"MCP Vision GETyêu cầusự cố: {e}")
            return_json = self._create_error_response("Lỗi nội bộ server")
            response = web.Response(
                text=json.dumps(return_json, separators=(",", ":")),
                content_type="application/json",
            )
        finally:
            self._add_cors_headers(response)
            return response
