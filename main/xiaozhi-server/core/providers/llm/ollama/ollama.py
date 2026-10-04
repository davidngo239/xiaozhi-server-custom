from config.logger import setup_logging
from typing import Iterable, cast

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
import json
from core.providers.llm.base import LLMProviderBase

TAG = __name__
logger = setup_logging()


class LLMProvider(LLMProviderBase):
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.base_url = config.get("base_url", "http://localhost:11434")
        # Khởi tạo ứng dụng khách OpenAI với URL cơ sở Ollama
        # Nếu không có v1 thì thêm v1
        if not self.base_url.endswith("/v1"):
            self.base_url = f"{self.base_url}/v1"

        self.client = OpenAI(
            base_url=self.base_url,
            api_key="ollama",  # Ollama không cần khóa API nhưng ứng dụng khách OpenAI yêu cầu một khóa
        )

        # Kiểm tra xem đó có phải là mô hình qwen3 không
        self.is_qwen3 = self.model_name and self.model_name.lower().startswith("qwen3")

    def response(self, session_id, dialogue, **kwargs):
        # Nếu đó là mô hình qwen3, hãy thêm lệnh /no_think vào tin nhắn cuối cùng của người dùng
        if self.is_qwen3:
            # Sao chép danh sách cuộc trò chuyện để tránh sửa đổi cuộc trò chuyện gốc
            dialogue_copy = dialogue.copy()

            # Tìm tin nhắn cuối cùng của người dùng
            for i in range(len(dialogue_copy) - 1, -1, -1):
                if dialogue_copy[i]["role"] == "user":
                    # Thêm lệnh /no_think trước tin nhắn của người dùng
                    dialogue_copy[i]["content"] = (
                        "/no_think " + dialogue_copy[i]["content"]
                    )
                    logger.bind(tag=TAG).debug(f"为qwen3模型添加/no_think指令")
                    break

            # Sử dụng đoạn hội thoại đã sửa đổi
            dialogue = dialogue_copy

        logger.bind(tag=TAG).info(
            "LLM INPUT:\n" + json.dumps(dialogue, ensure_ascii=False, indent=2)
        )

        responses = self.client.chat.completions.create(
            model=self.model_name,
            messages=cast(Iterable[ChatCompletionMessageParam], dialogue),
            stream=True,
        )
        is_active = True
        # Được sử dụng để xử lý các thẻ chéo
        buffer = ""

        try:
            for chunk in responses:
                try:
                    delta = (
                        chunk.choices[0].delta
                        if getattr(chunk, "choices", None)
                        else None
                    )
                    if delta is None:
                        continue

                    content = delta.content or ""

                    if content:
                        # Thêm nội dung vào bộ đệm
                        buffer += content

                        # Xử lý thẻ trong bộ đệm
                        while "<think>" in buffer and "</think>" in buffer:
                            # Tìm thẻ <think></think> hoàn chỉnh và xóa nó
                            pre = buffer.split("<think>", 1)[0]
                            post = buffer.split("</think>", 1)[1]
                            buffer = pre + post

                        # Xử lý trường hợp chỉ có thẻ bắt đầu
                        if "<think>" in buffer:
                            is_active = False
                            buffer = buffer.split("<think>", 1)[0]

                        # Xử lý trường hợp chỉ có thẻ đóng
                        if "</think>" in buffer:
                            is_active = True
                            buffer = buffer.split("</think>", 1)[1]

                        # Nếu hiện đang hoạt động và bộ đệm có nội dung, hãy xuất
                        if is_active and buffer:
                            yield buffer
                            buffer = ""  # Xóa bộ đệm

                except Exception as e:
                    logger.bind(tag=TAG).error(f"Error processing chunk: {e}")
        finally:
            responses.close()

    def response_with_functions(self, session_id, dialogue, functions=None):
        # Nếu đó là mô hình qwen3, hãy thêm lệnh /no_think vào tin nhắn cuối cùng của người dùng
        if self.is_qwen3:
            # Sao chép danh sách cuộc trò chuyện để tránh sửa đổi cuộc trò chuyện gốc
            dialogue_copy = dialogue.copy()

            # Tìm tin nhắn cuối cùng của người dùng
            for i in range(len(dialogue_copy) - 1, -1, -1):
                if dialogue_copy[i]["role"] == "user":
                    # Thêm lệnh /no_think trước tin nhắn của người dùng
                    dialogue_copy[i]["content"] = (
                        "/no_think " + dialogue_copy[i]["content"]
                    )
                    logger.bind(tag=TAG).debug(f"为qwen3模型添加/no_think指令")
                    break

            # Sử dụng đoạn hội thoại đã sửa đổi
            dialogue = dialogue_copy

        messages = cast(Iterable[ChatCompletionMessageParam], dialogue)
        if functions is None:
            stream = self.client.chat.completions.create(
                model=self.model_name, messages=messages, stream=True
            )
        else:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                stream=True,
                tools=cast(Iterable[ChatCompletionToolParam], functions),
            )

        is_active = True
        buffer = ""

        try:
            for chunk in stream:
                try:
                    delta = (
                        chunk.choices[0].delta
                        if getattr(chunk, "choices", None)
                        else None
                    )
                    if delta is None:
                        continue

                    content = delta.content
                    tool_calls = delta.tool_calls

                    # Nếu đó là một cuộc gọi công cụ, hãy chuyển nó trực tiếp
                    if tool_calls:
                        yield None, tool_calls
                        continue

                    # Xử lý nội dung văn bản
                    if content:
                        # Thêm nội dung vào bộ đệm
                        buffer += content

                        # Xử lý thẻ trong bộ đệm
                        while "<think>" in buffer and "</think>" in buffer:
                            # Tìm thẻ <think></think> hoàn chỉnh và xóa nó
                            pre = buffer.split("<think>", 1)[0]
                            post = buffer.split("</think>", 1)[1]
                            buffer = pre + post

                        # Xử lý trường hợp chỉ có thẻ bắt đầu
                        if "<think>" in buffer:
                            is_active = False
                            buffer = buffer.split("<think>", 1)[0]

                        # Xử lý trường hợp chỉ có thẻ đóng
                        if "</think>" in buffer:
                            is_active = True
                            buffer = buffer.split("</think>", 1)[1]

                        # Nếu hiện đang hoạt động và bộ đệm có nội dung, hãy xuất
                        if is_active and buffer:
                            yield buffer, None
                            buffer = ""  # Xóa bộ đệm
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Error processing function chunk: {e}")
                    continue
        finally:
            stream.close()
