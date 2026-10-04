import json
import uuid
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils.dialogue import Message
from core.providers.tts.dto.dto import ContentType
from core.handle.helloHandle import checkWakeupWords
from plugins_func.register import Action, ActionResponse
from core.handle.sendAudioHandle import send_stt_message
from core.handle.reportHandle import enqueue_tool_report
from core.utils.util import remove_punctuation_and_length
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType

TAG = __name__


async def handle_user_intent(conn: "ConnectionHandler", text):
    # Tiền xử lý văn bản đầu vào, xử lý các định dạng JSON có thể
    try:
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                text = parsed_data["content"]  # Trích xuất nội dung để phân tích ý định
                conn.current_speaker = parsed_data.get("speaker")  # Lưu giữ thông tin người nói
    except (json.JSONDecodeError, TypeError):
        pass

    # Kiểm tra xem có lệnh thoát rõ ràng không
    _, filtered_text = remove_punctuation_and_length(text)
    if await check_direct_exit(conn, filtered_text):
        return True

    # Kiểm tra xem đó có phải là từ đánh thức không
    if await checkWakeupWords(conn, filtered_text):
        return True

    if conn.intent_type == "function_call":
        # Sử dụng các phương thức trò chuyện hỗ trợ gọi hàm, không cần phân tích ý định nữa
        return False
    # Phân tích ý định sử dụng LLM
    intent_result = await analyze_intent_with_llm(conn, text)
    if not intent_result:
        return False
    # Sentence_id được tạo khi phiên bắt đầu
    conn.sentence_id = str(uuid.uuid4().hex)
    # Xử lý các ý định khác nhau
    return await process_intent_result(conn, intent_result, text)


async def check_direct_exit(conn: "ConnectionHandler", text):
    """检查是否有明确的退出命令"""
    _, text = remove_punctuation_and_length(text)
    cmd_exit = conn.cmd_exit
    for cmd in cmd_exit:
        if text == cmd:
            conn.logger.bind(tag=TAG).info(f"识别到明确的退出命令: {text}")
            await send_stt_message(conn, text)
            await conn.close()
            return True
    return False


async def analyze_intent_with_llm(conn: "ConnectionHandler", text):
    """使用LLM分析用户意图"""
    if not hasattr(conn, "intent") or not conn.intent:
        conn.logger.bind(tag=TAG).warning("ý địnhnhận dạngdịch vụ未khởi tạo")
        return None

    # Lịch sử cuộc trò chuyện
    dialogue = conn.dialogue
    try:
        intent_result = await conn.intent.detect_intent(conn, dialogue.dialogue, text)
        return intent_result
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"ý địnhnhận dạngthất bại: {str(e)}")

    return None


async def process_intent_result(
    conn: "ConnectionHandler", intent_result, original_text
):
    """xử lýý địnhnhận dạngkết quả"""
    try:
        # Hãy thử phân tích kết quả thành JSON
        intent_data = json.loads(intent_result)

        # Kiểm tra xem có function_call không
        if "function_call" in intent_data:
            # function_call được lấy trực tiếp từ nhận dạng ý định
            conn.logger.bind(tag=TAG).debug(
                f"kiểm tra到function_callđịnh dạng的ý địnhkết quả: {intent_data['function_call']['name']}"
            )
            function_name = intent_data["function_call"]["name"]
            if function_name == "continue_chat":
                return False

            if function_name == "result_for_context":
                await send_stt_message(conn, original_text)
                conn.client_abort = False

                def process_context_result():
                    conn.dialogue.put(Message(role="user", content=original_text))

                    from core.utils.current_time import get_current_time_info

                    current_time, today_date, today_weekday, lunar_date = (
                        get_current_time_info()
                    )

                    # Xây dựng lời nhắc cơ bản theo ngữ cảnh
                    context_prompt = f"""Giờ hiện tại: {current_time}
                                        Ngày hôm nay: {today_date} ({today_weekday})
                                        Ngày âm lịch: {lunar_date}

                                        Dùng thông tin trên để trả lời câu hỏi của người dùng: {original_text}"""

                    # Sử dụng lệnh gọi không đồng bộ để tránh chặn vòng lặp sự kiện và ảnh hưởng đến việc phát lại âm thanh của các thiết bị khác
                    try:
                        response = asyncio.run_coroutine_threadsafe(
                            conn.intent.replyResult(context_prompt, original_text),
                            conn.loop,
                        ).result()
                    except Exception as e:
                        conn.logger.bind(tag=TAG).error(f"LLM生成回复thất bại: {e}")
                        response = None
                    if response:
                        speak_txt(conn, response)

                conn.executor.submit(process_context_result)
                return True

            function_args = {}
            if "arguments" in intent_data["function_call"]:
                function_args = intent_data["function_call"]["arguments"]
                if function_args is None:
                    function_args = {}
            # Đảm bảo tham số là JSON ở định dạng chuỗi
            if isinstance(function_args, dict):
                function_args = json.dumps(function_args)

            function_call_data = {
                "name": function_name,
                "id": str(uuid.uuid4().hex),
                "arguments": function_args,
            }

            await send_stt_message(conn, original_text)
            conn.client_abort = False

            # Chuẩn bị tham số lệnh gọi công cụ
            tool_input = {}
            if function_args:
                if isinstance(function_args, str):
                    tool_input = json.loads(function_args) if function_args else {}
                elif isinstance(function_args, dict):
                    tool_input = function_args

            # Báo cáo cuộc gọi công cụ
            enqueue_tool_report(conn, function_name, tool_input)

            # Sử dụng bộ thực thi để thực hiện lệnh gọi hàm và xử lý kết quả
            def process_function_call():
                conn.dialogue.put(Message(role="user", content=original_text))

                # Hết thời gian gọi công cụ
                tool_call_timeout = int(conn.config.get("tool_call_timeout", 30))
                # Sử dụng bộ xử lý công cụ hợp nhất để xử lý tất cả các lệnh gọi công cụ
                try:
                    result = asyncio.run_coroutine_threadsafe(
                        conn.func_handler.handle_llm_function_call(
                            conn, function_call_data
                        ),
                        conn.loop,
                    ).result(timeout=tool_call_timeout)
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"công cụgọithất bại: {e}")
                    result = ActionResponse(
                        action=Action.ERROR,
                        result="Công cụ phản hồi quá thời gian chờ, bạn thử lại sau nhé",
                        response="Công cụ phản hồi quá thời gian chờ, bạn thử lại sau nhé",
                    )

                # Báo cáo kết quả cuộc gọi công cụ
                if result:
                    enqueue_tool_report(
                        conn,
                        function_name,
                        tool_input,
                        str(result.result) if result.result else None,
                        report_tool_call=False,
                    )

                    if result.action == Action.RESPONSE:  # Trả lời trực tiếp đến giao diện người dùng
                        text = result.response
                        if text is not None:
                            speak_txt(conn, text)
                    elif result.action == Action.REQLLM:  # Sau khi gọi hàm, yêu cầu llm tạo phản hồi
                        text = result.result
                        conn.dialogue.put(Message(role="tool", content=text))
                        # Sử dụng lệnh gọi không đồng bộ để tránh chặn vòng lặp sự kiện và ảnh hưởng đến việc phát lại âm thanh của các thiết bị khác
                        try:
                            llm_result = asyncio.run_coroutine_threadsafe(
                                conn.intent.replyResult(text, original_text),
                                conn.loop,
                            ).result()
                        except Exception as e:
                            conn.logger.bind(tag=TAG).error(f"LLM生成回复thất bại: {e}")
                            llm_result = text
                        if llm_result is None:
                            llm_result = text
                        speak_txt(conn, llm_result)
                    elif (
                        result.action == Action.NOTFOUND
                        or result.action == Action.ERROR
                    ):
                        text = result.response if result.response else result.result
                        if text is not None:
                            speak_txt(conn, text)
                    elif function_name != "play_music":
                        # Để tương thích ngược với mã gốc
                        # Lấy chỉ mục văn bản mới nhất
                        text = result.response
                        if text is None:
                            text = result.result
                        if text is not None:
                            speak_txt(conn, text)

            # Đặt thực thi chức năng trong nhóm luồng
            conn.executor.submit(process_function_call)
            return True
        return False
    except json.JSONDecodeError as e:
        conn.logger.bind(tag=TAG).error(f"xử lýý địnhkết quảkhi出错: {e}")
        return False


def speak_txt(conn: "ConnectionHandler", text):
    # Ghi văn bản vào ánh xạ câu_id
    conn.tts.store_tts_text(conn.sentence_id, text)

    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.FIRST,
            content_type=ContentType.ACTION,
        )
    )
    conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=text)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.LAST,
            content_type=ContentType.ACTION,
        )
    )
    conn.dialogue.put(Message(role="assistant", content=text))
