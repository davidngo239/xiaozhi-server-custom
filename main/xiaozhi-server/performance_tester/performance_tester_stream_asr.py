import asyncio
import time
import json
import uuid
import os
import websockets
import gzip
import random
from urllib import parse
from tabulate import tabulate
from config.settings import load_config
import tempfile
import wave
import hmac
import base64
import hashlib
from datetime import datetime
from wsgiref.handlers import format_date_time
from time import mktime

description = "流式ASR首词延迟测试"
try:
    import dashscope
except ImportError:
    dashscope = None


class BaseASRTester:
    def __init__(self, config_key: str, config):
        self.config = config
        self.config_key = config_key
        self.asr_config = self.config.get("ASR", {}).get(config_key, {})
        self.test_audio_files = self._load_test_audio_files()
        self.results = []

    def _load_test_audio_files(self):
        audio_root = os.path.join(os.getcwd(), "config", "assets")
        test_files = []
        if os.path.exists(audio_root):
            for file_name in os.listdir(audio_root):
                if file_name.endswith((".wav", ".pcm")):
                    file_path = os.path.join(audio_root, file_name)
                    with open(file_path, "rb") as f:
                        test_files.append(
                            {"data": f.read(), "path": file_path, "name": file_name}
                        )
        return test_files

    async def test(self, test_count=5):
        raise NotImplementedError

    def _calculate_result(self, service_name, latencies, test_count):
        """计算测试kết quả（修复: 正确xử lýNone值 , 剔除thất bại测试）"""
        # Loại bỏ các giá trị Không có (kiểm tra không thành công) và độ trễ không hợp lệ và chỉ tính độ trễ hiệu quả.
        valid_latencies = [l for l in latencies if l is not None and l > 0]
        if valid_latencies:
            avg_latency = sum(valid_latencies) / len(valid_latencies)
            status = f"成功（{len(valid_latencies)}/{test_count}次有效）"
        else:
            avg_latency = 0
            status = "thất bại: 所有测试均thất bại"
        return {"name": service_name, "latency": avg_latency, "status": status}


class DoubaoStreamASRTester(BaseASRTester):
    def __init__(self, config):
        super().__init__("DoubaoStreamASR", config)
        from core.providers.asr.doubao_stream import ASRProvider as DoubaoStreamProvider

        self.provider = DoubaoStreamProvider(self.asr_config, delete_audio_file=False)

    async def test(self, test_count=5):
        if not self.test_audio_files:
            return {
                "name": "豆包流式ASR",
                "latency": 0,
                "status": "thất bại: không tìm thấy测试âm thanh",
            }
        if not self.asr_config:
            return {
                "name": "豆包流式ASR",
                "latency": 0,
                "status": "thất bại: 未cấu hình",
            }

        latencies = []
        for i in range(test_count):
            try:
                start_time = time.time()

                headers = self.provider.token_auth()

                async with websockets.connect(
                    self.provider.ws_url,
                    additional_headers=headers,
                    max_size=1000000000,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=10,
                ) as ws:
                    request_params = self.provider.construct_request(str(uuid.uuid4()))

                    payload_bytes = str.encode(json.dumps(request_params))
                    payload_bytes = gzip.compress(payload_bytes)
                    full_client_request = bytearray(self.provider.generate_header())
                    full_client_request.extend((len(payload_bytes)).to_bytes(4, "big"))
                    full_client_request.extend(payload_bytes)
                    await ws.send(full_client_request)

                    init_res = await ws.recv()
                    result = self.provider.parse_response(init_res)
                    if "code" in result and result["code"] != 1000:
                        raise Exception(
                            f"Khởi tạo thất bại: {result.get('payload_msg', {}).get('error', 'Lỗi không xác định')}"
                        )

                    audio_data = self.test_audio_files[0]["data"]
                    if audio_data.startswith(b"RIFF"):
                        audio_data = audio_data[44:]

                    # Gửi dữ liệu âm thanh (sử dụng dấu khung cuối cùng để thông báo cho máy chủ rằng âm thanh đã kết thúc)
                    payload = gzip.compress(audio_data)
                    audio_request = bytearray(
                        self.provider.generate_last_audio_default_header()
                    )
                    audio_request.extend(len(payload).to_bytes(4, "big"))
                    audio_request.extend(payload)
                    await ws.send(audio_request)

                    first_chunk = await ws.recv()
                    latency = time.time() - start_time
                    latencies.append(latency)
                    print(f"[豆包ASR] 第{i + 1}次 首词延迟: {latency:.3f}s")
                    await ws.close()

            except Exception as e:
                print(f"[豆包ASR] 第{i + 1}次测试thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("豆包流式ASR", latencies, test_count)


class QwenASRFlashTester(BaseASRTester):
    def __init__(self, config):
        super().__init__("Qwen3ASRFlash", config)

    async def _test_single(self, audio_file_info):
        temp_file_path = None

        try:
            audio_data = audio_file_info["data"]

            # Tối ưu hóa: Di chuyển việc chuẩn bị tệp tạm thời trước thời gian để giảm tác động của IO đĩa khi kiểm tra hiệu suất
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_file_path = f.name

            with wave.open(temp_file_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(audio_data)

            messages = [{"role": "user", "content": [{"audio": temp_file_path}]}]

            api_key = self.asr_config.get("api_key") or os.getenv("DASHSCOPE_API_KEY")
            if not api_key:
                raise ValueError("未cấu hình api_key")

            if dashscope is None:
                raise RuntimeError("未安装 dashscope 库")

            dashscope.api_key = api_key

            # Điểm bắt đầu thời gian thống nhất: bắt đầu tính thời gian trước lệnh gọi API (nhưng việc chuẩn bị tệp đã hoàn tất)
            start_time = time.time()

            response = dashscope.MultiModalConversation.call(
                model="qwen3-asr-flash",
                messages=messages,
                result_format="message",
                asr_options={"enable_lid": True, "enable_itn": False},
                stream=True,
            )

            for chunk in response:
                latency = time.time() - start_time
                return latency

            raise Exception("流式结束 , 未nhận任何phản hồi")

        except Exception as e:
            raise Exception(f"通义ASR流式thất bại: {str(e)}")

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

    async def test(self, test_count=5):
        if not self.test_audio_files:
            return {
                "name": "通义千问ASR",
                "latency": 0,
                "status": "thất bại: không tìm thấy测试âm thanh",
            }
        if not self.asr_config and not os.getenv("DASHSCOPE_API_KEY"):
            return {
                "name": "通义千问ASR",
                "latency": 0,
                "status": "thất bại: 未cấu hình api_key",
            }

        latencies = []
        for i in range(test_count):
            try:
                # print(f"\n[General ASR] bắt đầu bài kiểm tra thứ {i+1}...)
                latency = await self._test_single(self.test_audio_files[0])
                latencies.append(latency)
                print(f"[通义ASR] 第{i + 1}次 首词延迟: {latency:.3f}s")
            except Exception as e:
                # print(f"[General ASR] Thử nghiệm thứ {i+1} không thành công: {str(e)}")
                latencies.append(None)

        return self._calculate_result("通义千问ASR", latencies, test_count)


class XunfeiStreamASRTester(BaseASRTester):
    def __init__(self, config):
        super().__init__("XunfeiStreamASR", config)

    def _create_url(self):
        url = "wss://iat-api.xfyun.cn/v2/iat"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = f"host: iat-api.xfyun.cn\ndate: {date}\nGET /v2/iat HTTP/1.1"
        signature_sha = hmac.new(
            self.asr_config["api_secret"].encode("utf-8"),
            signature_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode()

        authorization_origin = f'api_key="{self.asr_config["api_key"]}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha}"'
        authorization = base64.b64encode(authorization_origin.encode()).decode()

        v = {"authorization": authorization, "date": date, "host": "iat-api.xfyun.cn"}
        return url + "?" + parse.urlencode(v)

    async def test(self, test_count: int = 5):
        if not self.test_audio_files:
            return {
                "name": "讯飞流式ASR",
                "latency": 0,
                "status": "thất bại: không tìm thấy测试âm thanh",
            }
        if not self.asr_config:
            return {
                "name": "讯飞流式ASR",
                "latency": 0,
                "status": "thất bại: 未cấu hình",
            }

        required = ["app_id", "api_key", "api_secret"]
        for k in required:
            if k not in self.asr_config:
                return {
                    "name": "讯飞流式ASR",
                    "latency": 0,
                    "status": f"thất bại: 缺少cấu hình {k}",
                }

        latencies = []
        frame_size = 1280
        audio_raw = self.test_audio_files[0]["data"]
        if audio_raw.startswith(b"RIFF"):
            audio_raw = audio_raw[44:]

        for i in range(test_count):
            try:
                start_time = time.time()
                ws_url = self._create_url()

                async with websockets.connect(
                    ws_url,
                    additional_headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                    },
                    max_size=1 << 30,
                    ping_interval=None,
                    ping_timeout=None,
                    close_timeout=30,
                ) as ws:
                    # Khung đầu tiên: xóa trường punc để tránh lỗi tham số không xác định
                    await ws.send(
                        json.dumps(
                            {
                                "common": {"app_id": self.asr_config["app_id"]},
                                "business": {
                                    "domain": "iat",
                                    "language": "zh_cn",
                                    "accent": "mandarin",
                                    "dwa": "wpgs",
                                    "vad_eos": 5000,
                                    # Đã xóa "punc": Đúng
                                },
                                "data": {
                                    "status": 0,
                                    "format": "audio/L16;rate=16000",
                                    "encoding": "raw",
                                    "audio": base64.b64encode(
                                        audio_raw[:frame_size]
                                    ).decode(),
                                },
                            },
                            ensure_ascii=False,
                        )
                    )

                    # Tất cả các khung tiếp theo
                    pos = frame_size
                    while pos < len(audio_raw):
                        chunk = audio_raw[pos : pos + frame_size]
                        status = 2 if (pos + frame_size >= len(audio_raw)) else 1
                        await ws.send(
                            json.dumps(
                                {
                                    "data": {
                                        "status": status,
                                        "format": "audio/L16;rate=16000",
                                        "encoding": "raw",
                                        "audio": base64.b64encode(chunk).decode(),
                                    }
                                },
                                ensure_ascii=False,
                            )
                        )
                        if status == 2:
                            break
                        pos += frame_size

                    # nhận được lời đầu tiên
                    first_token = True
                    async for message in ws:
                        data = json.loads(message)
                        if data.get("code") != 0:
                            raise Exception(f"讯飞Lỗi: {data.get('message')}")

                        ws_result = data.get("data", {}).get("result", {}).get("ws")
                        if ws_result:
                            text = "".join(
                                cw.get("w", "")
                                for seg in ws_result
                                for cw in seg.get("cw", [])
                            )
                            if text.strip() and first_token:
                                latency = time.time() - start_time
                                latencies.append(latency)
                                print(f"[讯飞ASR] 第{i + 1}次 首词延迟: {latency:.3f}s")
                                first_token = False
                                break

            except Exception as e:
                print(f"[讯飞ASR] 第{i + 1}次测试thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("讯飞流式ASR", latencies, test_count)


class ASRPerformanceSuite:
    def __init__(self, config):
        self.config = config
        self.testers = []
        self.results = []

    def register_tester(self, tester_class):
        try:
            tester = tester_class(self.config)
            self.testers.append(tester)
            print(f"已注册测试器: {tester.config_key}")
        except Exception as e:
            name_map = {
                "DoubaoStreamASRTester": "豆包流式ASR",
                "QwenASRFlashTester": "通义千问ASR",
                "XunfeiStreamASRTester": "讯飞流式ASR",
            }
            name = name_map.get(tester_class.__name__, tester_class.__name__)
            print(f"跳过 {name}: {str(e)}")

    def _print_results(self, test_count):
        if not self.results:
            print("没有有效的ASR测试kết quả")
            return

        print(f"\n{'=' * 60}")
        print("流式ASR首词phản hồikhi间测试kết quả")
        print(f"{'=' * 60}")
        print(f"测试次数: 每个ASRdịch vụ测试 {test_count} lần")

        success_results = sorted(
            [r for r in self.results if "成功" in r["status"]],
            key=lambda x: x["latency"],
        )
        failed_results = [r for r in self.results if "成功" not in r["status"]]

        table_data = [
            [
                r["name"],
                f"{r['latency']:.3f}s" if r["latency"] > 0 else "N/A",
                r["status"],
            ]
            for r in success_results + failed_results
        ]

        print(
            tabulate(
                table_data,
                headers=["ASRdịch vụ", "首词延迟", "trạng thái"],
                tablefmt="grid",
            )
        )
        print("\n测试说明：")
        print(
            "- 计khi起点: thiết lậpkết nối前（包含握手、gửiâm thanh、接收首个nhận dạngkết quả全流程）"
        )
        print("- 通义千问优化: 临时文件准备在计时前完成，减少磁盘IO对测试的影响")
        print("- Lỗixử lý: thất bại的测试不计入平均值 , 只统计thành công测试的延迟")
        print("- 排序规则: thành công的按延迟升序 , thất bại的排在后面")

    async def run(self, test_count=5):
        print(f"开始流式ASR首词phản hồikhi间测试...")
        print(f"每个ASRdịch vụ测试次数: {test_count}次\n")

        self.results = []
        for tester in self.testers:
            print(f"\n--- 测试 {tester.config_key} ---")
            result = await tester.test(test_count)
            self.results.append(result)

        self._print_results(test_count)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="流式ASR首词phản hồikhi间测试công cụ")
    parser.add_argument("--count", type=int, default=5, help="测试次数")
    args = parser.parse_args()

    config = await load_config()
    suite = ASRPerformanceSuite(config)
    suite.register_tester(DoubaoStreamASRTester)
    suite.register_tester(QwenASRFlashTester)
    suite.register_tester(XunfeiStreamASRTester)

    await suite.run(args.count)


if __name__ == "__main__":
    asyncio.run(main())
