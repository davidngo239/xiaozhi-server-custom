import asyncio
import logging
import os
import statistics
import time
import concurrent.futures
from typing import Dict, Optional
import yaml
import aiohttp
from tabulate import tabulate
from core.utils.llm import create_instance as create_llm_instance
from config.settings import load_config

# Đặt cấp độ nhật ký chung thành CẢNH BÁO và chặn nhật ký cấp độ THÔNG TIN
logging.basicConfig(level=logging.WARNING)

description = "大语言模型性能测试"


class LLMPerformanceTester:
    def __init__(self, config):
        self.config = config
        # Sử dụng nội dung thử nghiệm phù hợp hơn với kịch bản của tổng đài viên, bao gồm cả các từ nhắc nhở của hệ thống
        self.system_prompt = self._load_system_prompt()
        self.test_sentences = self.config.get("module_test", {}).get(
            "test_sentences",
            [
                "你好，我今天心情不太好，能安慰一下我吗？",
                "帮我查一下明天的天气如何？",
                "我想听一个有趣的故事，你能给我讲一个吗？",
                "现在几点了？今天是星期几？",
                "我想设置一个明天早上8点的闹钟提醒我开会",
            ],
        )
        self.results = {}

    def _load_system_prompt(self) -> str:
        """tảihệ thốnghướng dẫn词"""
        try:
            prompt_file = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                self.config.get("prompt_template", "agent-base-prompt.txt"),
            )
            with open(prompt_file, "r", encoding="utf-8") as f:
                content = f.read()
                # Thay thế các biến mẫu bằng các giá trị kiểm tra
                content = content.replace(
                    "{{base_prompt}}", "你是小智，一个聪明可爱的AI助手"
                )
                content = content.replace(
                    "{{emojiList}}", "😀,😃,😄,😁,😊,😍,🤔,😮,😱,😢,😭,😴,😵,🤗,🙄"
                )
                content = content.replace("{{current_time}}", "2024年8月17日 12:30:45")
                content = content.replace("{{today_date}}", "2024年8月17日")
                content = content.replace("{{today_weekday}}", "Thứ Bảy")
                content = content.replace("{{lunar_date}}", "甲辰年七月十四")
                content = content.replace("{{local_address}}", "北京市")
                content = content.replace("{{weather_info}}", "今天Nắng , 25-32℃")
                return content
        except Exception as e:
            print(f"không thểtảihệ thốnghướng dẫn词文件: {e}")
            return "你是小智，一个聪明可爱的AI助手。请用温暖友善的语气回复用户。"

    def _collect_response_sync(self, llm, messages, llm_name, sentence_start):
        """同步收集phản hồidữ liệu的辅助方法"""
        chunks = []
        first_token_received = False
        first_token_time = None

        try:
            response_generator = llm.response("perf_test", messages)
            chunk_count = 0
            for chunk in response_generator:
                chunk_count += 1
                # Mỗi khi một số khối nhất định được xử lý, hãy kiểm tra xem nó có bị gián đoạn hay không.
                if chunk_count % 10 == 0:
                    # Thoát sớm bằng cách kiểm tra xem luồng hiện tại có bị đánh dấu là bị gián đoạn không
                    import threading

                    if (
                        threading.current_thread().ident
                        != threading.main_thread().ident
                    ):
                        # Nếu không phải luồng chính, kiểm tra xem có cần dừng luồng không
                        pass

                # Kiểm tra xem đoạn có chứa thông tin lỗi không
                chunk_str = str(chunk)
                if (
                    "sự cố" in chunk_str
                    or "Lỗi" in chunk_str
                    or "502" in chunk_str.lower()
                ):
                    error_msg = chunk_str.lower()
                    print(f"{llm_name} phản hồi包含Lỗithông tin: {error_msg}")
                    # Ném ra một ngoại lệ có chứa thông báo lỗi
                    raise Exception(chunk_str)

                if not first_token_received and chunk.strip() != "":
                    first_token_time = time.time() - sentence_start
                    first_token_received = True
                    print(f"{llm_name} 首个 Token: {first_token_time:.3f}s")
                chunks.append(chunk)
        except Exception as e:
            # Thông báo lỗi chi tiết hơn
            error_msg = str(e).lower()
            print(f"{llm_name} phản hồi收集sự cố: {error_msg}")
            # Đối với lỗi 502 hoặc lỗi mạng, hãy ném trực tiếp các ngoại lệ và để lớp trên xử lý chúng.
            if (
                "502" in error_msg
                or "bad gateway" in error_msg
                or "error code: 502" in error_msg
                or "sự cố" in str(e)
                or "Lỗi" in str(e)
            ):
                raise e
            # Đối với các lỗi khác, kết quả một phần có thể được trả về
            return chunks, first_token_time

        return chunks, first_token_time

    async def _check_ollama_service(self, base_url: str, model_name: str) -> bool:
        """异步kiểm tra Ollama dịch vụtrạng thái"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{base_url}/api/version") as response:
                    if response.status != 200:
                        print(f"Ollama dịch vụ未khởi động或không thể访问: {base_url}")
                        return False
                async with session.get(f"{base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        if not any(model["name"] == model_name for model in models):
                            print(
                                f"Ollama 模型 {model_name} 未找到，请先使用 `ollama pull {model_name}` 下载"
                            )
                            return False
                    else:
                        print("không thểlấy Ollama 模型列表")
                        return False
                return True
            except Exception as e:
                print(f"không thểkết nối到 Ollama dịch vụ: {str(e)}")
                return False

    async def _test_single_sentence(
        self, llm_name: str, llm, sentence: str
    ) -> Optional[Dict]:
        """测试单个句子的性能"""
        try:
            print(f"{llm_name} 开始测试: {sentence[:20]}...")
            sentence_start = time.time()
            first_token_received = False
            first_token_time = None

            # Xây dựng một thông báo chứa các từ nhắc nhở của hệ thống
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": sentence},
            ]

            # Sử dụng asyncio.wait_for để kiểm soát thời gian chờ
            try:
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    # Tạo tác vụ thu thập phản hồi
                    future = executor.submit(
                        self._collect_response_sync,
                        llm,
                        messages,
                        llm_name,
                        sentence_start,
                    )

                    # Sử dụng asyncio.wait_for để triển khai kiểm soát thời gian chờ
                    try:
                        response_chunks, first_token_time = await asyncio.wait_for(
                            asyncio.wrap_future(future), timeout=10.0
                        )
                    except asyncio.TimeoutError:
                        print(f"{llm_name} 测试quá thời gian chờ（10秒） , bỏ qua")
                        # Buộc hủy bỏ tương lai
                        future.cancel()
                        # Đợi một khoảng thời gian ngắn để đảm bảo rằng tác vụ nhóm luồng có thể phản hồi việc hủy
                        try:
                            await asyncio.wait_for(
                                asyncio.wrap_future(future), timeout=1.0
                            )
                        except (
                            asyncio.TimeoutError,
                            concurrent.futures.CancelledError,
                            Exception,
                        ):
                            # Bỏ qua tất cả các ngoại lệ và đảm bảo việc thực hiện chương trình tiếp tục
                            pass
                        return None

            except Exception as timeout_error:
                print(f"{llm_name} xử lýsự cố: {timeout_error}")
                return None

            response_time = time.time() - sentence_start
            print(f"{llm_name} hoàn tấtphản hồi: {response_time:.3f}s")

            return {
                "name": llm_name,
                "type": "llm",
                "first_token_time": first_token_time,
                "response_time": response_time,
            }
        except Exception as e:
            error_msg = str(e).lower()
            # Kiểm tra xem đó là lỗi 502 hay lỗi mạng
            if (
                "502" in error_msg
                or "bad gateway" in error_msg
                or "error code: 502" in error_msg
            ):
                print(f"{llm_name} 遇到502Lỗi , bỏ qua测试")
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "502网络Lỗi",
                }
            print(f"{llm_name} 句子测试thất bại: {str(e)}")
            return None

    async def _test_llm(self, llm_name: str, config: Dict) -> Dict:
        """异步测试单个 LLM 性能"""
        try:
            # Đối với Ollama, bỏ qua kiểm tra api_key và xử lý đặc biệt
            if llm_name == "Ollama":
                base_url = config.get("base_url", "http://localhost:11434")
                model_name = config.get("model_name")
                if not model_name:
                    print("Ollama 未cấu hình model_name")
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "网络Lỗi",
                    }

                if not await self._check_ollama_service(base_url, model_name):
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "网络Lỗi",
                    }
            else:
                if "api_key" in config and any(
                    x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]
                ):
                    print(f"bỏ qua未cấu hình的 LLM: {llm_name}")
                    return {
                        "name": llm_name,
                        "type": "llm",
                        "errors": 1,
                        "error_type": "cấu hìnhLỗi",
                    }

            # Lấy loại thực tế (tương thích với cấu hình cũ)
            module_type = config.get("type", llm_name)
            llm = create_llm_instance(module_type, config)

            # Sử dụng thống nhất mã hóa UTF-8
            test_sentences = [
                s.encode("utf-8").decode("utf-8") for s in self.test_sentences
            ]

            # Tạo một nhiệm vụ kiểm tra cho tất cả các câu
            sentence_tasks = []
            for sentence in test_sentences:
                sentence_tasks.append(
                    self._test_single_sentence(llm_name, llm, sentence)
                )

            # Thực hiện đồng thời tất cả các bài kiểm tra câu và xử lý các trường hợp ngoại lệ có thể xảy ra
            sentence_results = await asyncio.gather(
                *sentence_tasks, return_exceptions=True
            )

            # Xử lý kết quả, lọc ra các ngoại lệ và giá trị Không có
            valid_results = []
            for result in sentence_results:
                if isinstance(result, dict) and result is not None:
                    valid_results.append(result)
                elif isinstance(result, Exception):
                    error_msg = str(result).lower()
                    if "502" in error_msg or "bad gateway" in error_msg:
                        print(f"{llm_name} 遇到502Lỗi , bỏ qua该句子测试")
                        return {
                            "name": llm_name,
                            "type": "llm",
                            "errors": 1,
                            "error_type": "502网络Lỗi",
                        }
                    else:
                        print(f"{llm_name} 句子测试sự cố: {result}")

            if not valid_results:
                print(f"{llm_name} 无有效dữ liệu , 可能遇到网络问题或cấu hìnhLỗi")
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "网络Lỗi",
                }

            # Kiểm tra số lượng kết quả hợp lệ và coi như thử nghiệm thất bại nếu quá ít
            if len(valid_results) < len(test_sentences) * 0.3:  # Phải có ít nhất tỷ lệ thành công 30%
                print(
                    f"{llm_name} 成功测试句子过少({len(valid_results)}/{len(test_sentences)})，可能网络不稳定或接口有问题"
                )
                return {
                    "name": llm_name,
                    "type": "llm",
                    "errors": 1,
                    "error_type": "网络Lỗi",
                }

            first_token_times = [
                r["first_token_time"]
                for r in valid_results
                if r.get("first_token_time")
            ]
            response_times = [r["response_time"] for r in valid_results]

            # Lọc dữ liệu ngoại lệ (dữ liệu vượt quá 3 độ lệch chuẩn)
            if len(response_times) > 1:
                mean = statistics.mean(response_times)
                stdev = statistics.stdev(response_times)
                filtered_times = [t for t in response_times if t <= mean + 3 * stdev]
            else:
                filtered_times = response_times

            return {
                "name": llm_name,
                "type": "llm",
                "avg_response": sum(response_times) / len(response_times),
                "avg_first_token": (
                    sum(first_token_times) / len(first_token_times)
                    if first_token_times
                    else 0
                ),
                "success_rate": f"{len(valid_results)}/{len(test_sentences)}",
                "errors": 0,
            }
        except Exception as e:
            error_msg = str(e).lower()
            if "502" in error_msg or "bad gateway" in error_msg:
                print(f"LLM {llm_name} 遇到502Lỗi , bỏ qua测试")
            else:
                print(f"LLM {llm_name} 测试thất bại: {str(e)}")
            error_type = "网络Lỗi"
            if "timeout" in str(e).lower():
                error_type = "quá thời gian chờkết nối"
            return {
                "name": llm_name,
                "type": "llm",
                "errors": 1,
                "error_type": error_type,
            }

    def _print_results(self):
        """打印测试kết quả"""
        print("\n" + "=" * 50)
        print("LLM 性能测试kết quả")
        print("=" * 50)

        if not self.results:
            print("没有可用的测试kết quả")
            return

        headers = [
            "模型名称",
            "平均phản hồikhi间(s)",
            "首Token时间(s)",
            "成功率",
            "trạng thái",
        ]
        table_data = []

        # Thu thập tất cả dữ liệu và phân loại nó
        valid_results = []
        error_results = []

        for name, data in self.results.items():
            if data["errors"] == 0:
                # kết quả bình thường
                avg_response = f"{data['avg_response']:.3f}"
                avg_first_token = (
                    f"{data['avg_first_token']:.3f}"
                    if data["avg_first_token"] > 0
                    else "-"
                )
                success_rate = data.get("success_rate", "N/A")
                status = "✅ 正常"

                # Lưu giá trị được sử dụng để sắp xếp
                first_token_value = (
                    data["avg_first_token"]
                    if data["avg_first_token"] > 0
                    else float("inf")
                )

                valid_results.append(
                    {
                        "name": name,
                        "avg_response": avg_response,
                        "avg_first_token": avg_first_token,
                        "success_rate": success_rate,
                        "status": status,
                        "sort_key": first_token_value,
                    }
                )
            else:
                # Kết quả sai
                avg_response = "-"
                avg_first_token = "-"
                success_rate = "0/5"

                # Nhận loại lỗi cụ thể
                error_type = data.get("error_type", "网络Lỗi")
                status = f"❌ {error_type}"

                error_results.append(
                    [name, avg_response, avg_first_token, success_rate, status]
                )

        # Sắp xếp theo thời gian mã thông báo đầu tiên theo thứ tự tăng dần
        valid_results.sort(key=lambda x: x["sort_key"])

        # Chuyển đổi các kết quả hợp lệ được sắp xếp thành dữ liệu dạng bảng
        for result in valid_results:
            table_data.append(
                [
                    result["name"],
                    result["avg_response"],
                    result["avg_first_token"],
                    result["success_rate"],
                    result["status"],
                ]
            )

        # Thêm kết quả lỗi vào cuối dữ liệu bảng
        table_data.extend(error_results)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print("\n测试说明:")
        print("- 测试nội dung: 包含完整hệ thốnghướng dẫn词的智能体对话场景")
        print("- quá thời gian chờ控制: 单个yêu cầu最大chờkhi间为10秒")
        print("- Lỗixử lý: 自动bỏ qua502Lỗi和网络sự cố的模型")
        print("- thành công率: thành côngphản hồi的句子数量/总测试句子数量")
        print("\n测试完成！")

    async def run(self):
        """执行全量异步测试"""
        print("开始筛选可用 LLM 模块...")

        # Tạo tất cả các nhiệm vụ kiểm tra
        all_tasks = []

        # Nhiệm vụ kiểm tra LLM
        if self.config.get("LLM") is not None:
            for llm_name, config in self.config.get("LLM", {}).items():
                # Kiểm tra tính hợp lệ của cấu hình
                if llm_name == "CozeLLM":
                    if any(x in config.get("bot_id", "") for x in ["你的"]) or any(
                        x in config.get("user_id", "") for x in ["你的"]
                    ):
                        print(f"LLM {llm_name} 未cấu hình bot_id/user_id , đãbỏ qua")
                        continue
                elif "api_key" in config and any(
                    x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]
                ):
                    print(f"LLM {llm_name} 未cấu hình api_key , đãbỏ qua")
                    continue

                # Đối với Ollama, trước tiên hãy kiểm tra trạng thái dịch vụ
                if llm_name == "Ollama":
                    base_url = config.get("base_url", "http://localhost:11434")
                    model_name = config.get("model_name")
                    if not model_name:
                        print("Ollama 未cấu hình model_name")
                        continue

                    if not await self._check_ollama_service(base_url, model_name):
                        continue

                print(f"添加 LLM 测试tác vụ: {llm_name}")
                all_tasks.append(self._test_llm(llm_name, config))

        print(f"\n找到 {len(all_tasks)} 个可用 LLM 模块")
        print("\n开始并发测试所有模块...\n")

        # Thực hiện đồng thời tất cả các tác vụ kiểm tra nhưng đặt thời gian chờ độc lập cho từng tác vụ
        async def test_with_timeout(task, timeout=30):
            """为每个测试tác vụ添加quá thời gian chờ保护"""
            try:
                return await asyncio.wait_for(task, timeout=timeout)
            except asyncio.TimeoutError:
                print(f"测试tác vụquá thời gian chờ（{timeout}秒） , bỏ qua")
                return {
                    "name": "Unknown",
                    "type": "llm",
                    "errors": 1,
                    "error_type": "quá thời gian chờkết nối",
                }
            except Exception as e:
                print(f"测试tác vụsự cố: {str(e)}")
                return {
                    "name": "Unknown",
                    "type": "llm",
                    "errors": 1,
                    "error_type": "网络Lỗi",
                }

        # Bảo vệ thời gian chờ cho mỗi tác vụ
        protected_tasks = [test_with_timeout(task) for task in all_tasks]

        # Thực hiện đồng thời tất cả các nhiệm vụ kiểm tra
        all_results = await asyncio.gather(*protected_tasks, return_exceptions=True)

        # Xử lý kết quả
        for result in all_results:
            if isinstance(result, dict):
                if result.get("errors") == 0:
                    self.results[result["name"]] = result
                else:
                    # Ghi nhật ký ngay cả khi có lỗi, dùng để hiển thị trạng thái lỗi
                    if result.get("name") != "Unknown":
                        self.results[result["name"]] = result
            elif isinstance(result, Exception):
                print(f"测试kết quảxử lýsự cố: {str(result)}")

        # In kết quả
        print("\n生成测试报告...")
        self._print_results()


async def main():
    config = await load_config()
    tester = LLMPerformanceTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
