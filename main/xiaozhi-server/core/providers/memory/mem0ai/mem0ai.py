import json
import asyncio
import traceback

from ..base import MemoryProviderBase, logger
from mem0 import MemoryClient
from core.utils.util import check_model_key

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        self.api_key = config.get("api_key", "")
        self.api_version = config.get("api_version", "v1.1")
        model_key_msg = check_model_key("Mem0ai", self.api_key)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)
            self.use_mem0 = False
            return
        else:
            self.use_mem0 = True

        try:
            self.client = MemoryClient(api_key=self.api_key)
            logger.bind(tag=TAG).info("thành côngkết nối到 Mem0ai dịch vụ")
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"kết nối到 Mem0ai dịch vụkhixảy raLỗi: {str(e)}"
            )
            logger.bind(tag=TAG).error(f"详细Lỗi: {traceback.format_exc()}")
            self.use_mem0 = False

    async def save_memory(self, msgs, session_id=None):
        try:
            if self.use_mem0 and len(msgs) >= 2:
                # Định dạng nội dung dưới dạng danh sách tin nhắn cho mem0
                messages = []
                for message in msgs:
                    if message.role == "system":
                        continue

                    if message.role == "tool":
                        continue

                    content = message.content

                    if content is None:
                        continue

                    # Trích xuất nội dung từ định dạng JSON nếu có (đối với ASR có thẻ cảm xúc/ngôn ngữ)
                    # Same logic as in query_memory method
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

                    messages.append({"role": message.role, "content": content})

                result = await asyncio.to_thread(
                    self.client.add, messages, user_id=self.role_id
                )
                logger.bind(tag=TAG).debug(f"Save memory result: {result}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"lưu记忆thất bại: {str(e)}")

        return None

    async def query_memory(self, query: str) -> str:
        if not self.use_mem0:
            return ""
        try:
            if not getattr(self, "role_id", None):
                return ""

            filters = {"user_id": self.role_id}

            search_query = query
            try:
                if query.strip().startswith("{") and query.strip().endswith("}"):
                    data = json.loads(query)
                    if "content" in data:
                        search_query = data["content"]
            except (json.JSONDecodeError, KeyError):
                pass

            results = await asyncio.to_thread(
                self.client.search, search_query, filters=filters
            )
            if not results or "results" not in results:
                return ""

            # Định dạng từng mục bộ nhớ với thời gian cập nhật lên tới vài phút
            memories = []
            for entry in results["results"]:
                timestamp = entry.get("updated_at", "")
                if timestamp:
                    try:
                        # Phân tích và định dạng lại dấu thời gian
                        dt = timestamp.split(".")[0]  # Remove milliseconds
                        formatted_time = dt.replace("T", " ")
                    except:
                        formatted_time = timestamp
                memory = entry.get("memory", "")
                if timestamp and memory:
                    # Lưu trữ bộ dữ liệu (dấu thời gian, chuỗi định dạng) để sắp xếp
                    memories.append((timestamp, f"[{formatted_time}] {memory}"))

            # Sort by timestamp in descending order (newest first)
            memories.sort(key=lambda x: x[0], reverse=True)

            # Chỉ trích xuất các chuỗi được định dạng
            memories_str = "\n".join(f"- {memory[1]}" for memory in memories)
            logger.bind(tag=TAG).debug(f"Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆thất bại: {str(e)}")
            return ""
