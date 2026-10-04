import asyncio
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from ..base import IntentProviderBase
from plugins_func.functions.play_music import initialize_music_handler
from config.logger import setup_logging
from core.utils.util import get_system_error_response
import re
import json
import hashlib
import time


TAG = __name__
logger = setup_logging()


class IntentProvider(IntentProviderBase):
    def __init__(self, config):
        super().__init__(config)
        self.llm = None
        self.promot = ""
        # Nhập trình quản lý bộ đệm chung
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType
        self.history_count = 4  # Theo mặc định, 4 bản ghi cuộc trò chuyện cuối cùng sẽ được sử dụng.

    def get_intent_system_prompt(self, functions_list: str) -> str:
        """
        根据cấu hình的ý định选项和可用hàm动态生成hệ thốnghướng dẫn词
        Args:
            functions: 可用的hàm列表 , JSONđịnh dạng字符串
        Returns:
            định dạng化后的hệ thốnghướng dẫn词
        """

        # Phần mô tả chức năng xây dựng
        functions_desc = "Danh sách hàm có thể sử dụng:\n"
        for func in functions_list:
            func_info = func.get("function", {})
            name = func_info.get("name", "")
            desc = func_info.get("description", "")
            params = func_info.get("parameters", {})

            functions_desc += f"\nTên hàm: {name}\n"
            functions_desc += f"Mô tả: {desc}\n"

            if params:
                functions_desc += "Tham số:\n"
                for param_name, param_info in params.get("properties", {}).items():
                    param_desc = param_info.get("description", "")
                    param_type = param_info.get("type", "")
                    functions_desc += f"- {param_name} ({param_type}): {param_desc}\n"

            functions_desc += "---\n"

        prompt = f"""Bạn là trợ lý nhận diện ý định. Phân tích câu cuối của người dùng và chọn hàm phù hợp.
Chỉ trả về JSON hợp lệ, không thêm văn bản, giải thích hay biểu tượng cảm xúc.
Với câu hỏi về giờ, ngày, thứ, âm lịch hoặc vị trí hiện tại, trả về {{"function_call": {{"name": "result_for_context"}}}}. Hàm này không cần arguments; hệ thống lấy thông tin từ ngữ cảnh.
Nếu người dùng hỏi tại sao hoặc làm thế nào cuộc trò chuyện kết thúc, chọn continue_chat. Chỉ chọn handle_exit_intent khi người dùng yêu cầu rõ ràng kết thúc hoặc thoát.
{functions_desc}
Chọn hàm phù hợp nhất trong danh sách. Nếu không có hàm phù hợp, trả về {{"function_call": {{"name": "continue_chat"}}}}.
Kết quả phải có function_call và name, cùng arguments nếu hàm cần tham số.
Ví dụ:
- Hỏi mức pin: {{"function_call": {{"name": "get_battery_level", "arguments": {{"response_success": "Mức pin hiện tại là {{value}}%", "response_failure": "Không đọc được mức pin"}}}}}}
- Hỏi độ sáng: {{"function_call": {{"name": "self_screen_get_brightness"}}}}
- Đặt độ sáng 50%: {{"function_call": {{"name": "self_screen_set_brightness", "arguments": {{"brightness": 50}}}}}}
- Kết thúc trò chuyện: {{"function_call": {{"name": "handle_exit_intent", "arguments": {{"say_goodbye": "Tạm biệt"}}}}}}
- Chào hỏi: {{"function_call": {{"name": "continue_chat"}}}}
Nếu một câu chứa nhiều lệnh, trả về function_calls với các lệnh theo thứ tự, ví dụ {{"function_calls": [{{"name": "light_on"}}, {{"name": "volume_up"}}]}}.
Tuyệt đối chỉ xuất JSON hợp lệ.
"""
        return prompt

    async def replyResult(self, text: str, original_text: str):
        """使用 asyncio.to_thread 避免阻塞事件循环"""
        try:
            user_prompt = (
                "Dựa trên nội dung trên, trả lời người dùng tự nhiên bằng tiếng Việt, ngắn gọn và trực tiếp. Người dùng nói: "
                + original_text
            )
            # Sử dụng to_thread để đặt các lệnh gọi chặn đồng bộ vào nhóm luồng để thực thi mà không chặn vòng lặp sự kiện.
            llm_result = await asyncio.to_thread(
                self.llm.response_no_stream,
                system_prompt=text,
                user_prompt=user_prompt,
            )
            return llm_result
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in generating reply result: {e}")
            return get_system_error_response(self.config)

    async def detect_intent(
        self, conn: "ConnectionHandler", dialogue_history: List[Dict], text: str
    ) -> str:
        if not self.llm:
            raise ValueError("LLM provider not set")
        if conn.func_handler is None:
            return '{"function_call": {"name": "continue_chat"}}'

        # Ghi lại tổng thời gian bắt đầu
        total_start_time = time.time()

        # In thông tin model đã sử dụng
        model_info = getattr(self.llm, "model_name", str(self.llm.__class__.__name__))
        logger.bind(tag=TAG).debug(f"使用意图识别模型: {model_info}")

        # Tính toán khóa bộ đệm
        cache_key = hashlib.md5((conn.device_id + text).encode()).hexdigest()

        # Kiểm tra bộ đệm
        cached_intent = self.cache_manager.get(self.CacheType.INTENT, cache_key)
        if cached_intent is not None:
            cache_time = time.time() - total_start_time
            logger.bind(tag=TAG).debug(
                f"使用缓存的意图: {cache_key} -> {cached_intent}, 耗时: {cache_time:.4f}秒"
            )
            return cached_intent

        if self.promot == "":
            functions = conn.func_handler.get_functions()
            if hasattr(conn, "mcp_client"):
                mcp_tools = conn.mcp_client.get_available_tools()
                if mcp_tools is not None and len(mcp_tools) > 0:
                    if functions is None:
                        functions = []
                    functions.extend(mcp_tools)

            self.promot = self.get_intent_system_prompt(functions)

        music_config = initialize_music_handler(conn)
        music_file_names = music_config["music_file_names"]
        prompt_music = f"{self.promot}\n<musicNames>{music_file_names}\n</musicNames>"

        home_assistant_cfg = conn.config["plugins"].get("home_assistant")
        if home_assistant_cfg:
            devices = home_assistant_cfg.get("devices", [])
        else:
            devices = []
        if len(devices) > 0:
            hass_prompt = "\nDanh sách thiết bị thông minh trong nhà (vị trí, tên thiết bị, entity_id), có thể điều khiển qua Home Assistant:\n"
            for device in devices:
                hass_prompt += device + "\n"
            prompt_music += hass_prompt

        logger.bind(tag=TAG).debug(f"User prompt: {prompt_music}")

        # Mẹo xây dựng lịch sử trò chuyện của người dùng
        msgStr = ""

        # Nhận lịch sử cuộc trò chuyện gần đây
        start_idx = max(0, len(dialogue_history) - self.history_count)
        for i in range(start_idx, len(dialogue_history)):
            msgStr += f"{dialogue_history[i].role}: {dialogue_history[i].content}\n"

        msgStr += f"User: {text}\n"
        user_prompt = f"current dialogue:\n{msgStr}"

        # Ghi lại thời gian hoàn thành tiền xử lý
        preprocess_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(f"意图识别预处理耗时: {preprocess_time:.4f}秒")

        # Sử dụng LLM để nhận dạng ý định
        llm_start_time = time.time()
        logger.bind(tag=TAG).debug(f"开始LLMý địnhnhận dạnggọi, 模型: {model_info}")

        try:
            # Sử dụng to_thread để đặt các cuộc gọi chặn đồng bộ vào nhóm luồng nhằm tránh chặn vòng lặp sự kiện
            intent = await asyncio.to_thread(
                self.llm.response_no_stream,
                system_prompt=prompt_music,
                user_prompt=user_prompt,
            )
        except Exception as e:
            logger.bind(tag=TAG).error(f"Error in intent detection LLM call: {e}")
            return '{"function_call": {"name": "continue_chat"}}'

        # Ghi lại thời gian hoàn thành cuộc gọi LLM
        llm_time = time.time() - llm_start_time
        logger.bind(tag=TAG).debug(
            f"外挂的大模型ý địnhnhận dạnghoàn tất, 模型: {model_info}, gọi耗khi: {llm_time:.4f}秒"
        )

        # Ghi lại thời gian bắt đầu xử lý hậu kỳ
        postprocess_start_time = time.time()

        # Làm sạch và phân tích phản hồi
        intent = intent.strip()
        # Hãy thử trích xuất phần JSON
        match = re.search(r"\{.*\}", intent, re.DOTALL)
        if match:
            intent = match.group(0)

        # Ghi lại tổng thời gian xử lý
        total_time = time.time() - total_start_time
        logger.bind(tag=TAG).debug(
            f"【ý địnhnhận dạng性能】模型: {model_info}, 总耗khi: {total_time:.4f}秒, LLMgọi: {llm_time:.4f}秒, 查询: '{text[:20]}...'"
        )

        # Hãy thử phân tích cú pháp thành JSON
        try:
            intent_data = json.loads(intent)
            # Nếu bao gồm function_call, hãy định dạng nó thành định dạng phù hợp để xử lý
            if "function_call" in intent_data:
                function_data = intent_data["function_call"]
                function_name = function_data.get("name")
                function_args = function_data.get("arguments", {})

                # Ghi lại cuộc gọi chức năng được công nhận
                logger.bind(tag=TAG).info(
                    f"llm nhận dạng到ý định: {function_name}, Tham số: {function_args}"
                )

                # Xử lý các loại ý định khác nhau
                if function_name == "result_for_context":
                    # Xử lý các truy vấn thông tin cơ bản và xây dựng kết quả trực tiếp từ ngữ cảnh
                    logger.bind(tag=TAG).info(
                        "kiểm tra到result_for_contextý định , sẽ使用上下文thông tin直接回答"
                    )

                elif function_name == "continue_chat":
                    # Xử lý các cuộc trò chuyện bình thường
                    # Giữ các tin nhắn không liên quan đến công cụ
                    clean_history = [
                        msg
                        for msg in conn.dialogue.dialogue
                        if msg.role not in ["tool", "function"]
                    ]
                    conn.dialogue.dialogue = clean_history

                else:
                    # Xử lý các cuộc gọi hàm
                    logger.bind(tag=TAG).info(
                        f"kiểm tra到hàmgọiý định: {function_name}"
                    )

            # Xử lý và trả về bộ đệm thống nhất
            self.cache_manager.set(self.CacheType.INTENT, cache_key, intent)
            postprocess_time = time.time() - postprocess_start_time
            logger.bind(tag=TAG).debug(f"意图后处理耗时: {postprocess_time:.4f}秒")
            return intent
        except json.JSONDecodeError:
            # thời gian xử lý bài viết
            postprocess_time = time.time() - postprocess_start_time
            logger.bind(tag=TAG).error(
                f"không thểphân tíchý địnhJSON: {intent}, 后xử lý耗khi: {postprocess_time:.4f}秒"
            )
            # Nếu phân tích cú pháp không thành công, ý định tiếp tục trò chuyện mặc định sẽ được trả về.
            return '{"function_call": {"name": "continue_chat"}}'
