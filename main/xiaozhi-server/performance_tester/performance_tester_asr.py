import asyncio
import logging
import os
import time
import concurrent.futures
from typing import Dict, Optional
import aiohttp
from tabulate import tabulate
from core.utils.asr import create_instance as create_stt_instance

# Đặt cấp độ nhật ký chung thành CẢNH BÁO và chặn nhật ký cấp độ THÔNG TIN
logging.basicConfig(level=logging.WARNING)

description = "语音识别模型性能测试"


class ASRPerformanceTester:
    def __init__(self):
        self.config = self._load_config_from_data_dir()
        self.test_wav_list = self._load_test_wav_files()
        self.results = {"stt": {}}

        # nhật ký gỡ lỗi
        print(f"[DEBUG] tải的ASRcấu hình: {self.config.get('ASR', {})}")
        print(f"[DEBUG] 音频文件数量: {len(self.test_wav_list)}")

    def _load_config_from_data_dir(self) -> Dict:
        """从 data 目录tải所有 .config.yaml 文件的cấu hình"""
        config = {"ASR": {}}
        data_dir = os.path.join(os.getcwd(), "data")
        print(f"[DEBUG] 扫描cấu hình文件目录: {data_dir}")

        for root, _, files in os.walk(data_dir):
            for file in files:
                if file.endswith(".config.yaml"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            import yaml

                            file_config = yaml.safe_load(f)
                            # Cấu hình ASR/asr tương thích với trường hợp
                            asr_config = file_config.get("ASR") or file_config.get(
                                "asr"
                            )
                            if asr_config:
                                config["ASR"].update(asr_config)
                                print(
                                    f"[DEBUG] 从 {file_path} tải ASR cấu hìnhthành công"
                                )
                    except Exception as e:
                        print(f" tảicấu hình文件 {file_path} thất bại: {str(e)}")
        return config

    def _load_test_wav_files(self) -> list:
        """tải测试用的âm thanh文件（添加路径调试）"""
        wav_root = os.path.join(os.getcwd(), "config", "assets")
        print(f"[DEBUG] 音频文件目录: {wav_root}")
        test_wav_list = []

        if os.path.exists(wav_root):
            file_list = os.listdir(wav_root)
            print(f"[DEBUG] 找到音频文件: {file_list}")
            for file_name in file_list:
                file_path = os.path.join(wav_root, file_name)
                if os.path.getsize(file_path) > 300 * 1024:  # 300KB
                    with open(file_path, "rb") as f:
                        test_wav_list.append(f.read())
        else:
            print(f" 目录不存在: {wav_root}")
        return test_wav_list

    async def _test_single_audio(
        self, stt_name: str, stt, audio_data: bytes
    ) -> Optional[float]:
        """测试单个音频文件的性能"""
        try:
            start_time = time.time()
            text, _ = await stt.speech_to_text_wrapper(
                [audio_data], "1", stt.audio_format
            )
            if text is None:
                return None

            duration = time.time() - start_time

            # Phát hiện thời gian bất thường 0,000s
            if abs(duration) < 0.001:  # Dưới 1 mili giây được coi là ngoại lệ
                print(f"{stt_name} kiểm tra到sự cốkhi间: {duration:.6f}s (视为Lỗi)")
                return None

            return duration
        except Exception as e:
            error_msg = str(e).lower()
            if "502" in error_msg or "bad gateway" in error_msg:
                print(f"{stt_name} 遇到502Lỗi")
                return None
            return None

    async def _test_stt_with_timeout(self, stt_name: str, config: Dict) -> Dict:
        """异步测试单个STT性能 , 带quá thời gian chờ控制"""
        try:
            # Kiểm tra tính hợp lệ của cấu hình
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and str(config[field]).lower()
                in ["你的", "placeholder", "none", "null", ""]
                for field in token_fields
            ):
                print(f"  STT {stt_name} 未cấu hình有效access_token/api_key , đãbỏ qua")
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "cấu hìnhLỗi",
                }

            module_type = config.get("type", stt_name)
            stt = create_stt_instance(module_type, config, delete_audio_file=True)
            stt.audio_format = "pcm"

            print(f" 测试 STT: {stt_name}")

            # Sử dụng nhóm luồng và kiểm soát thời gian chờ
            loop = asyncio.get_event_loop()

            # Kiểm tra tệp âm thanh đầu tiên để kiểm tra kết nối
            try:
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            self._test_single_audio(
                                stt_name, stt, self.test_wav_list[0]
                            )
                        )
                    )
                    first_result = await asyncio.wait_for(
                        asyncio.wrap_future(future), timeout=10.0
                    )

                    if first_result is None:
                        print(f" {stt_name} kết nốithất bại")
                        return {
                            "name": stt_name,
                            "type": "stt",
                            "errors": 1,
                            "error_type": "网络Lỗi",
                        }
            except asyncio.TimeoutError:
                print(f" {stt_name} kết nốiquá thời gian chờ（10秒） , bỏ qua")
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "quá thời gian chờkết nối",
                }
            except Exception as e:
                error_msg = str(e).lower()
                if "502" in error_msg or "bad gateway" in error_msg:
                    print(f" {stt_name} 遇到502Lỗi , bỏ qua")
                    return {
                        "name": stt_name,
                        "type": "stt",
                        "errors": 1,
                        "error_type": "502网络Lỗi",
                    }
                print(f" {stt_name} kết nốisự cố: {str(e)}")
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "网络Lỗi",
                }

                # Kiểm tra đầy đủ với kiểm soát thời gian chờ
            total_time = 0
            valid_tests = 0
            test_count = len(self.test_wav_list)

            for i, audio_data in enumerate(self.test_wav_list, 1):
                try:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            lambda: asyncio.run(
                                self._test_single_audio(stt_name, stt, audio_data)
                            )
                        )
                        duration = await asyncio.wait_for(
                            asyncio.wrap_future(future), timeout=10.0
                        )

                        if duration is not None and duration > 0.001:
                            total_time += duration
                            valid_tests += 1
                            print(
                                f" {stt_name} [{i}/{test_count}] 耗时: {duration:.2f}s"
                            )
                        else:
                            print(
                                f" {stt_name} [{i}/{test_count}] 测试thất bại(含0.000ssự cố)"
                            )

                except asyncio.TimeoutError:
                    print(
                        f" {stt_name} [{i}/{test_count}] quá thời gian chờ（10秒） , bỏ qua"
                    )
                    continue
                except Exception as e:
                    error_msg = str(e).lower()
                    if "502" in error_msg or "bad gateway" in error_msg:
                        print(f" {stt_name} [{i}/{test_count}] 502Lỗi , bỏ qua")
                        return {
                            "name": stt_name,
                            "type": "stt",
                            "errors": 1,
                            "error_type": "502网络Lỗi",
                        }
                    print(f" {stt_name} [{i}/{test_count}] sự cố: {str(e)}")
                    continue
            # Kiểm tra số lượng bài kiểm tra hợp lệ
            if valid_tests < test_count * 0.3:  # Tỷ lệ thành công ít nhất 30%
                print(
                    f" {stt_name} 成功测试过少({valid_tests}/{test_count})，可能网络不稳定"
                )
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "网络Lỗi",
                }

            if valid_tests == 0:
                return {
                    "name": stt_name,
                    "type": "stt",
                    "errors": 1,
                    "error_type": "网络Lỗi",
                }

            avg_time = total_time / valid_tests
            return {
                "name": stt_name,
                "type": "stt",
                "avg_time": avg_time,
                "success_rate": f"{valid_tests}/{test_count}",
                "errors": 0,
            }

        except Exception as e:
            error_msg = str(e).lower()
            if "502" in error_msg or "bad gateway" in error_msg:
                error_type = "502网络Lỗi"
            elif "timeout" in error_msg:
                error_type = "quá thời gian chờkết nối"
            else:
                error_type = "网络Lỗi"
            print(f"⚠️ {stt_name} 测试thất bại: {str(e)}")
            return {
                "name": stt_name,
                "type": "stt",
                "errors": 1,
                "error_type": error_type,
            }

    def _print_results(self):
        """打印测试kết quả , 按phản hồikhi间排序"""
        print("\n" + "=" * 50)
        print("ASR 性能测试kết quả")
        print("=" * 50)

        if not self.results.get("stt"):
            print("没有可用的测试kết quả")
            return

        headers = ["模型名称", "平均耗时(s)", "成功率", "trạng thái"]
        table_data = []

        # Thu thập tất cả dữ liệu và phân loại nó
        valid_results = []
        error_results = []

        for name, data in self.results["stt"].items():
            if data["errors"] == 0:
                # kết quả bình thường
                avg_time = f"{data['avg_time']:.3f}"
                success_rate = data.get("success_rate", "N/A")
                status = "✅ 正常"

                # Lưu giá trị được sử dụng để sắp xếp
                sort_key = data["avg_time"]

                valid_results.append(
                    {
                        "name": name,
                        "avg_time": avg_time,
                        "success_rate": success_rate,
                        "status": status,
                        "sort_key": sort_key,
                    }
                )
            else:
                # Kết quả sai
                avg_time = "-"
                success_rate = "0/N"

                # Nhận loại lỗi cụ thể
                error_type = data.get("error_type", "网络Lỗi")
                status = f"❌ {error_type}"

                error_results.append([name, avg_time, success_rate, status])

        # Sắp xếp theo thời gian phản hồi theo thứ tự tăng dần (nhanh nhất đến chậm nhất)
        valid_results.sort(key=lambda x: x["sort_key"])

        # Chuyển đổi các kết quả hợp lệ được sắp xếp thành dữ liệu dạng bảng
        for result in valid_results:
            table_data.append(
                [
                    result["name"],
                    result["avg_time"],
                    result["success_rate"],
                    result["status"],
                ]
            )

        # Thêm kết quả lỗi vào cuối dữ liệu bảng
        table_data.extend(error_results)

        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        print("\n测试说明:")
        print("- quá thời gian chờ控制: 单个âm thanh最大chờkhi间为10秒")
        print("- Lỗixử lý: 自动bỏ qua502Lỗi、quá thời gian chờ和网络sự cố的模型")
        print("- 成功率：成功识别的音频数量/总测试音频数量")
        print("- 排序规则: 按平均耗khi从快到慢排序 , Lỗi模型排最后")
        print("\n测试完成！")

    async def run(self):
        """执行全量异步测试"""
        print("开始筛选可用ASR模块...")
        if not self.config.get("ASR"):
            print("cấu hìnhtrongkhông tìm thấy ASR mô-đun")
            return

        all_tasks = []
        for stt_name, config in self.config["ASR"].items():
            # Kiểm tra tính hợp lệ của cấu hình
            token_fields = ["access_token", "api_key", "token"]
            if any(
                field in config
                and str(config[field]).lower()
                in ["你的", "placeholder", "none", "null", ""]
                for field in token_fields
            ):
                print(f"ASR {stt_name} 未cấu hình有效access_token/api_key , đãbỏ qua")
                continue

            print(f"添加 ASR 测试tác vụ: {stt_name}")
            all_tasks.append(self._test_stt_with_timeout(stt_name, config))

        if not all_tasks:
            print("没有可用的ASR模块进行测试。")
            return

        print(f"\n找到 {len(all_tasks)} 个可用ASR模块")
        print("\n开始并发测试所有ASR模块...")
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Xử lý kết quả
        for result in all_results:
            if isinstance(result, dict) and result.get("type") == "stt":
                self.results["stt"][result["name"]] = result

        # In kết quả
        self._print_results()


async def main():
    tester = ASRPerformanceTester()
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
