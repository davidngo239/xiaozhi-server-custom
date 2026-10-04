import asyncio
import logging
import os
import time
import threading
from typing import Dict
import yaml
from tabulate import tabulate

# Đảm bảo nhập create_tts_instance từ core.utils.tts
from core.utils.tts import create_instance as create_tts_instance
from config.settings import load_config

# Đặt mức nhật ký chung thành CẢNH BÁO
logging.basicConfig(level=logging.WARNING)

description = "非流式语音合成性能测试"


class TTSPerformanceTester:
    def __init__(self, config):
        self.config = config
        self.test_sentences = self.config.get("module_test", {}).get(
            "test_sentences",
            [
                "永和九年，岁在癸丑，暮春之初；",
                "夫人之相与，俯仰一世，或取诸怀抱，悟言一室之内；或因寄所托，放浪形骸之外。虽趣舍万殊，静躁不同，",
                "每览昔人兴感之由，若合一契，未尝不临文嗟悼，不能喻之于怀。固知一死生为虚诞，齐彭殇为妄作。",
            ],
        )
        self.results = {}

    async def _test_tts(self, tts_name: str, config: Dict) -> Dict:
        """测试单个TTS模块的性能"""
        try:
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and any(x in config[field] for x in ["你的", "placeholder"])
                for field in token_fields
            ):
                print(f"TTS {tts_name} 未cấu hìnhaccess_token/api_key , đãbỏ qua")
                return {"name": tts_name, "errors": 1}

            module_type = config.get("type", tts_name)
            tts = create_tts_instance(module_type, config, delete_audio_file=True)

            # Đặt đối tượng mô phỏng conn để ngăn việc triển khai TTS truy cập vào self.conn.sample_rate là Không có
            class MockConn:
                sample_rate = 16000
                audio_format = "pcm"
                stop_event = threading.Event()  # Cần phải là một đối tượng Sự kiện thực sự
                client_abort = False
                headers = {}

            tts.conn = MockConn()

            # Đặt mô phỏng opus_encoding để tránh một số TTS nhất định truy cập self.opus_encoding là Không có
            class MockOpusEncoder:
                pass

            if not hasattr(tts, "opus_encoder") or tts.opus_encoder is None:
                tts.opus_encoder = MockOpusEncoder()

            print(f"测试 TTS: {tts_name}")

            # Kiểm tra kết nối
            tmp_file = tts.generate_filename()
            await tts.text_to_speak("kết nối测试", tmp_file)

            if not tmp_file or not os.path.exists(tmp_file):
                print(f"{tts_name} kết nốithất bại")
                return {"name": tts_name, "errors": 1}

            total_time = 0
            test_count = len(self.test_sentences[:3])

            for i, sentence in enumerate(self.test_sentences[:2], 1):
                start = time.time()
                tmp_file = tts.generate_filename()
                await tts.text_to_speak(sentence, tmp_file)
                duration = time.time() - start
                total_time += duration

                if tmp_file and os.path.exists(tmp_file):
                    print(f"{tts_name} [{i}/{test_count}] 测试成功")
                else:
                    print(f"{tts_name} [{i}/{test_count}] 测试thất bại")
                    return {"name": tts_name, "errors": 1}

            return {
                "name": tts_name,
                "avg_time": total_time / test_count,
                "errors": 0,
            }

        except Exception as e:
            print(f"{tts_name} 测试thất bại: {str(e)}")
            return {"name": tts_name, "errors": 1}

    def _print_results(self):
        """打印测试kết quả"""
        if not self.results:
            print("没有有效的TTS测试kết quả")
            return

        headers = ["TTS模块", "平均耗时(秒)", "测试句子数", "trạng thái"]
        table_data = []

        # Thu thập tất cả dữ liệu và phân loại nó
        valid_results = []
        error_results = []

        for name, data in self.results.items():
            if data["errors"] == 0:
                # kết quả bình thường
                avg_time = f"{data['avg_time']:.3f}"
                test_count = len(self.test_sentences[:3])
                status = "✅ 正常"

                # Lưu giá trị được sử dụng để sắp xếp
                valid_results.append(
                    {
                        "name": name,
                        "avg_time": avg_time,
                        "test_count": test_count,
                        "status": status,
                        "sort_key": data["avg_time"],
                    }
                )
            else:
                # Kết quả sai
                avg_time = "-"
                test_count = "0/3"

                # Loại lỗi mặc định là lỗi mạng
                error_type = "网络Lỗi"
                status = f"❌ {error_type}"

                error_results.append([name, avg_time, test_count, status])

        # Sắp xếp theo thời gian trung bình tăng dần
        valid_results.sort(key=lambda x: x["sort_key"])

        # Chuyển đổi các kết quả hợp lệ được sắp xếp thành dữ liệu dạng bảng
        for result in valid_results:
            table_data.append(
                [
                    result["name"],
                    result["avg_time"],
                    result["test_count"],
                    result["status"],
                ]
            )

        # Thêm kết quả lỗi vào cuối dữ liệu bảng
        table_data.extend(error_results)

        print("\nTTS性能测试kết quả:")
        print(
            tabulate(
                table_data,
                headers=headers,
                tablefmt="grid",
                colalign=("left", "right", "right", "left"),
            )
        )
        print("\n测试说明:")
        print("- quá thời gian chờ控制: 单个yêu cầu最大chờkhi间为10秒")
        print("- Lỗixử lý: không thểkết nối和quá thời gian chờ的列为网络Lỗi")
        print("- 排序规则: 按平均耗时从快到慢排序")

    async def run(self):
        """执行测试"""
        print("开始TTS性能测试...")

        if not self.config.get("TTS"):
            print("cấu hình文件trongkhông tìm thấyTTScấu hình")
            return

        # Duyệt qua tất cả các cấu hình TTS
        tasks = []
        for tts_name, config in self.config.get("TTS", {}).items():
            tasks.append(self._test_tts(tts_name, config))

        # Thực hiện đồng thời các thử nghiệm
        results = await asyncio.gather(*tasks)

        # Lưu tất cả kết quả, bao gồm cả lỗi
        for result in results:
            self.results[result["name"]] = result

        # In kết quả
        self._print_results()


# Đối với các yêu cầu gọi của performance_tester.py
async def main():
    config = await load_config()
    tester = TTSPerformanceTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
