from ..base import MemoryProviderBase, logger
import time
import json
import os
import yaml
from config.config_loader import get_project_dir
from config.manage_api_client import generate_and_save_chat_summary
import asyncio
from core.utils.util import check_model_key


short_term_memory_prompt = 'Bạn quản lý bộ nhớ hội thoại để cá nhân hóa những cuộc trò chuyện sau.\nChỉ ghi thông tin thực sự có trong hội thoại, không đưa dữ liệu ví dụ vào bộ nhớ.\nĐánh giá mỗi thông tin theo độ mới 40%, cường độ cảm xúc hoặc mức độ nhắc lại 35%, và liên hệ với thông tin khác 25%.\nKhi người dùng đổi tên, lưu tên cũ, tên mới và thời điểm thay đổi. Giữ lịch sử cập nhật của thông tin quan trọng.\nNén thông tin ngắn gọn. Khi tổng độ dài đạt 900 ký tự, xóa mục có điểm dưới 60 và không được nhắc trong ba lượt; gộp mục tương tự, giữ thời điểm mới nhất.\nChỉ trả về chuỗi JSON hợp lệ, không giải thích hay chú thích. Nội dung bằng tiếng Việt.\nCấu trúc JSON: {"profile": {"current_name": "", "previous_names": [], "traits": []}, "memories": [{"event": "", "timestamp": "", "emotion": 0, "connections": [], "freshness": 0}], "relationships": {"frequent_topics": {}, "connections": []}, "pending": {"urgent_tasks": [], "care": []}, "quotes": []}.\n'


def extract_json_data(json_code):
    start = json_code.find("```json")
    # Tìm phần cuối ``` tiếp theo bắt đầu từ đầu
    end = json_code.find("```", start + 1)
    # print("start:", start, "end:", end)
    if start == -1 or end == -1:
        try:
            jsonData = json.loads(json_code)
            return json_code
        except Exception as e:
            print("Error:", e)
        return ""
    jsonData = json_code[start + 7 : end]
    return jsonData


TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory):
        super().__init__(config)
        self.short_memory = ""
        self.save_to_file = True
        self.memory_path = get_project_dir() + "data/.memory.yaml"
        self.load_memory(summary_memory)

    def init_memory(
        self, role_id, llm, summary_memory=None, save_to_file=True, **kwargs
    ):
        super().init_memory(role_id, llm, **kwargs)
        self.save_to_file = save_to_file
        self.load_memory(summary_memory)

    def load_memory(self, summary_memory):
        # API trả về trực tiếp sau khi lấy được bộ nhớ tóm tắt
        if summary_memory or not self.save_to_file:
            self.short_memory = summary_memory
            return

        all_memory = {}
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                all_memory = yaml.safe_load(f) or {}
        if self.role_id in all_memory:
            self.short_memory = all_memory[self.role_id]

    def save_memory_to_file(self):
        all_memory = {}
        if os.path.exists(self.memory_path):
            with open(self.memory_path, "r", encoding="utf-8") as f:
                all_memory = yaml.safe_load(f) or {}
        all_memory[self.role_id] = self.short_memory
        with open(self.memory_path, "w", encoding="utf-8") as f:
            yaml.dump(all_memory, f, allow_unicode=True)

    async def save_memory(self, msgs, session_id=None):
        # In thông tin model đã sử dụng
        model_info = getattr(self.llm, "model_name", str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(f"使用记忆lưu模型: {model_info}")
        api_key = getattr(self.llm, "api_key", None)
        memory_key_msg = check_model_key("LLM tóm tắt bộ nhớ", api_key)
        if memory_key_msg:
            logger.bind(tag=TAG).error(memory_key_msg)
        if self.llm is None:
            logger.bind(tag=TAG).error("LLM is not set for memory provider")
            return None

        if len(msgs) < 2:
            return None

        msgStr = ""
        for msg in msgs:
            content = msg.content

            # Trích xuất nội dung từ định dạng JSON nếu có (đối với ASR có thẻ cảm xúc/ngôn ngữ)
            try:
                if (
                    content
                    and content.strip().startswith("{")
                    and content.strip().endswith("}")
                ):
                    data = json.loads(content)
                    if "content" in data:
                        content = data["content"]
            except (json.JSONDecodeError, KeyError, TypeError):
                # Nếu phân tích thất bại, dùng nội dung ban đầu
                pass

            if msg.role == "user":
                msgStr += f"User: {content}\n"
            elif msg.role == "assistant":
                msgStr += f"Assistant: {content}\n"
        if self.short_memory and len(self.short_memory) > 0:
            msgStr += "Bộ nhớ trước đây: \n"
            msgStr += self.short_memory

        # thời điểm hiện tại
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        msgStr += f"Giờ hiện tại: {time_str}"

        if self.save_to_file:
            try:
                result = self.llm.response_no_stream(
                    short_term_memory_prompt,
                    msgStr,
                    max_tokens=2000,
                    temperature=0.2,
                )
                json_str = extract_json_data(result)
                json.loads(json_str)  # Kiểm tra xem định dạng json có đúng không
                self.short_memory = json_str
                self.save_memory_to_file()
            except Exception as e:
                logger.bind(tag=TAG).error(f"Error in saving memory: {e}")
        else:
            # Khi save_to_file là Sai, giao diện tóm tắt bản ghi trò chuyện ở phía Java sẽ được gọi.
            summary_id = session_id if session_id else self.role_id
            await generate_and_save_chat_summary(summary_id)
        logger.bind(tag=TAG).info(
            f"Save memory successful - Role: {self.role_id}, Session: {session_id}"
        )

        return self.short_memory

    async def query_memory(self, query: str) -> str:
        return self.short_memory
