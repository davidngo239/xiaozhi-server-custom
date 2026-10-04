import requests
from requests.exceptions import RequestException
from config.logger import setup_logging
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.agent_id = config.get("agent_id")  # Tương ứng với Agent_id
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", config.get("url"))  # Sử dụng base_url theo mặc định
        self.api_url = f"{self.base_url}/api/conversation/process"  # Ghép nối URL API hoàn chỉnh

    def response(self, session_id, dialogue, **kwargs):
        # Trợ lý giọng nói tại nhà có ý định riêng. Không cần sử dụng xiaozhi ai tích hợp sẵn. Nó chỉ cần chuyển những gì người dùng nói cho trợ lý tại nhà.

        # Trích xuất nội dung cuối cùng có vai trò là 'người dùng'
        input_text = None
        if isinstance(dialogue, list):  # Đảm bảo cuộc đối thoại là một danh sách
            # Duyệt theo thứ tự ngược lại và tìm tin nhắn cuối cùng có vai trò 'người dùng'
            for message in reversed(dialogue):
                if message.get("role") == "user":  # Đã tìm thấy thư có vai trò 'người dùng'
                    input_text = message.get("content", "")
                    break  # Thoát khỏi vòng lặp ngay sau khi tìm thấy nó

        # Xây dựng dữ liệu yêu cầu
        payload = {
            "text": input_text,
            "agent_id": self.agent_id,
            "conversation_id": session_id,  # Sử dụng session_id làm cuộc trò chuyện_id
        }
        # Đặt tiêu đề yêu cầu
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Thực hiện yêu cầu POST
        with requests.post(self.api_url, json=payload, headers=headers) as response:
            # Kiểm tra xem yêu cầu có thành công không
            response.raise_for_status()

            # Phân tích dữ liệu trả về
            data = response.json()
        speech = (
            data.get("response", {})
            .get("speech", {})
            .get("plain", {})
            .get("speech", "")
        )

        # Trả về nội dung đã tạo
        if speech:
            yield speech
        else:
            logger.bind(tag=TAG).warning("API trả vềdữ liệutrong没有 speech nội dung")

    def response_with_functions(self, session_id, dialogue, functions=None):
        logger.bind(tag=TAG).error(
            f"homeassistant不支持（function call），建议使用其他意图识别"
        )
