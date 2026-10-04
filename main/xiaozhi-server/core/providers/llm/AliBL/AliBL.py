from config.logger import setup_logging
from http import HTTPStatus
import dashscope
from dashscope import Application
from core.providers.llm.base import LLMProviderBase
from core.utils.util import check_model_key
import time

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.api_key = config["api_key"]
        self.app_id = config["app_id"]
        self.base_url = config.get("base_url")
        self.is_No_prompt = config.get("is_no_prompt")
        self.memory_id = config.get("ali_memory_id")
        self.streaming_chunk_size = config.get(
            "streaming_chunk_size", 3
        )  # Số ký tự được trả về trên mỗi luồng
        check_model_key("AliBLLLM", self.api_key)

    def response(self, session_id, dialogue):
        # xử lý đối thoại
        if self.is_No_prompt:
            dialogue.pop(0)
            logger.bind(tag=TAG).debug(
                f"【阿里百练APIdịch vụ】xử lý后的dialogue: {dialogue}"
            )

        # Xây dựng tham số cuộc gọi
        call_params = {
            "api_key": self.api_key,
            "app_id": self.app_id,
            "session_id": session_id,
            "messages": dialogue,
            # Bật tính năng phát trực tuyến gốc SDK
            "stream": True,
        }
        if self.memory_id != False:
            # Bộ nhớ Bailian yêu cầu các tham số nhắc nhở
            prompt = dialogue[-1].get("content")
            call_params["memory_id"] = self.memory_id
            call_params["prompt"] = prompt
            logger.bind(tag=TAG).debug(
                f"【阿里百练APIdịch vụ】xử lý后的prompt: {prompt}"
            )

        # Tùy chọn đặt địa chỉ cơ sở API tùy chỉnh (bỏ qua nếu được định cấu hình làm URL chế độ tương thích)
        if self.base_url and ("/api/" in self.base_url):
            dashscope.base_http_api_url = self.base_url

        responses = Application.call(**call_params)

        # Xử lý truyền trực tuyến (SDK trả về một đối tượng có thể lặp lại khi stream=True; nếu không thì trả về một đối tượng phản hồi duy nhất)
        logger.bind(tag=TAG).debug(
            f"【阿里百练APIdịch vụ】构造Tham số: {dict(call_params, api_key='***')}"
        )

        last_text = ""
        try:
            for resp in responses:
                if resp.status_code != HTTPStatus.OK:
                    logger.bind(tag=TAG).error(
                        f"code={resp.status_code}, message={resp.message}, 请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code"
                    )
                    continue
                current_text = getattr(getattr(resp, "output", None), "text", None)
                if current_text is None:
                    continue
                # Truyền phát SDK là phạm vi bao phủ gia tăng và tính toán đầu ra chênh lệch
                if len(current_text) >= len(last_text):
                    delta = current_text[len(last_text) :]
                else:
                    # Tránh tình trạng rollback ngẫu nhiên
                    delta = current_text
                if delta:
                    yield delta
                last_text = current_text
        except TypeError:
            # Dự phòng không phát trực tuyến (trả lại một lần)
            if responses.status_code != HTTPStatus.OK:
                logger.bind(tag=TAG).error(
                    f"code={responses.status_code}, message={responses.message}, 请参考文档：https://help.aliyun.com/zh/model-studio/developer-reference/error-code"
                )
                yield "[Dịch vụ API Alibaba Bailian phản hồi bất thường]"
            else:
                full_text = getattr(getattr(responses, "output", None), "text", "")
                logger.bind(tag=TAG).info(
                    f"【阿里百练APIdịch vụ】完整phản hồi长度: {len(full_text)}"
                )
                for i in range(0, len(full_text), self.streaming_chunk_size):
                    chunk = full_text[i : i + self.streaming_chunk_size]
                    if chunk:
                        yield chunk

    def response_with_functions(self, session_id, dialogue, functions=None):
        # Alibaba Bailian hiện không hỗ trợ các lệnh gọi hàm gốc. Để duy trì khả năng tương thích, điều này sẽ quay trở lại đầu ra truyền phát văn bản thông thường.
        # Lớp trên sẽ sử dụng ở dạng (nội dung, tool_calls) và ở đây luôn trả về (mã thông báo, Không có)
        logger.bind(tag=TAG).warning(
            "阿里百练未实现原生 function call，已回退为纯文本流式输出"
        )
        for token in self.response(session_id, dialogue):
            yield token, None
