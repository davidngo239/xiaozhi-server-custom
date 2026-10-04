import asyncio
import time
import json
import uuid
import aiohttp
import websockets
import hmac
import base64
import hashlib
import asyncio
from urllib.parse import urlparse, urlencode
from tabulate import tabulate
from config.settings import load_config
from core.utils.alibl_endpoint import (
    build_ws_connect_options as build_alibl_ws_connect_options,
    resolve_ws_url as resolve_alibl_ws_url,
)

description = "流式TTS语音合成首词耗时测试"


class StreamTTSPerformanceTester:
    def __init__(self, config):
        self.config = config
        self.test_texts = ["你好，这是一句话。"]
        self.results = []

    async def test_aliyun_tts(self, text=None, test_count=5):
        """测试阿里云流式TTS首词延迟（测试多次取平均）"""
        text = text or self.test_texts[0]
        latencies = []

        for i in range(test_count):
            try:
                tts_config = self.config["TTS"]["AliyunStreamTTS"]
                appkey = tts_config["appkey"]
                token = tts_config["token"]
                voice = tts_config["voice"]
                host = tts_config["host"]
                ws_url = f"wss://{host}/ws/v1"

                # Điểm bắt đầu định giờ thống nhất: bắt đầu định giờ trước khi thiết lập kết nối
                start_time = time.time()
                async with websockets.connect(
                    ws_url, extra_headers={"X-NLS-Token": token}
                ) as ws:
                    task_id = str(uuid.uuid4())
                    message_id = str(uuid.uuid4())

                    start_request = {
                        "header": {
                            "message_id": message_id,
                            "task_id": task_id,
                            "namespace": "FlowingSpeechSynthesizer",
                            "name": "StartSynthesis",
                            "appkey": appkey,
                        },
                        "payload": {
                            "voice": voice,
                            "format": "pcm",
                            "sample_rate": 16000,
                            "volume": 50,
                            "speech_rate": 0,
                            "pitch_rate": 0,
                            "enable_subtitle": True,
                        },
                    }
                    await ws.send(json.dumps(start_request))

                    start_response = json.loads(await ws.recv())
                    if start_response["header"]["name"] != "SynthesisStarted":
                        raise Exception("khởi động合成thất bại")

                    run_request = {
                        "header": {
                            "message_id": str(uuid.uuid4()),
                            "task_id": task_id,
                            "namespace": "FlowingSpeechSynthesizer",
                            "name": "RunSynthesis",
                            "appkey": appkey,
                        },
                        "payload": {"text": text},
                    }
                    await ws.send(json.dumps(run_request))

                    while True:
                        response = await ws.recv()
                        if isinstance(response, bytes):
                            latency = time.time() - start_time
                            latencies.append(latency)
                            print(f"[阿里云TTS] 第{i + 1}次 首词延迟: {latency:.3f}s")
                            break
                        elif isinstance(response, str):
                            data = json.loads(response)
                            if data["header"]["name"] == "TaskFailed":
                                raise Exception(
                                    f"Tổng hợp giọng nói thất bại: {data['payload']['error_info']}"
                                )

            except Exception as e:
                print(f"[阿里云TTS] 第{i + 1}次测试thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("阿里云TTS", latencies, test_count)

    async def test_alibl_tts(self, text=None, test_count=5):
        """测试阿里云百炼CosyVoice流式TTS首词延迟"""
        text = text or self.test_texts[0]
        latencies = []

        for i in range(test_count):
            try:
                tts_config = self.config["TTS"]["AliBLTTS"]
                api_key = tts_config["api_key"]
                model = tts_config.get("model", "cosyvoice-v2")
                voice = tts_config.get("voice", "longxiaochun_v2")
                format_type = tts_config.get("format", "pcm")
                sample_rate = int(tts_config.get("sample_rate", "24000"))
                connect_options = build_alibl_ws_connect_options(
                    float(self.config.get("tts_timeout", 15))
                )

                ws_url = resolve_alibl_ws_url(tts_config.get("ws_url"))
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "X-DashScope-DataInspection": "enable",
                }

                start_time = time.time()

                async with websockets.connect(
                    ws_url,
                    additional_headers=headers,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                    max_size=10 * 1024 * 1024,
                    **connect_options,
                ) as ws:
                    session_id = uuid.uuid4().hex

                    # 1. Gửi run-task (bắt đầu tác vụ)
                    run_task_message = {
                        "header": {
                            "action": "run-task",
                            "task_id": session_id,
                            "streaming": "duplex",
                        },
                        "payload": {
                            "task_group": "audio",
                            "task": "tts",
                            "function": "SpeechSynthesizer",
                            "model": model,
                            "parameters": {
                                "text_type": "PlainText",
                                "voice": voice,
                                "format": format_type,
                                "sample_rate": sample_rate,
                                "volume": 50,
                                "rate": 1.0,
                                "pitch": 1.0,
                            },
                            "input": {},
                        },
                    }
                    await ws.send(json.dumps(run_task_message))

                    # 2. Đợi sự kiện bắt đầu tác vụ (chìa khóa! Bạn phải đợi sự kiện này trước khi gửi văn bản)
                    task_started = False
                    while not task_started:
                        msg = await ws.recv()
                        if isinstance(msg, str):
                            data = json.loads(msg)
                            header = data.get("header", {})
                            event = header.get("event")
                            if event == "task-started":
                                task_started = True
                                print(
                                    f"[阿里云百炼TTS] 第{i + 1}次 tác vụkhởi độngthành công"
                                )
                            elif event == "task-failed":
                                raise Exception(
                                    f"khởi độngthất bại: {header.get('error_message', 'Lỗi không xác định')}"
                                )

                    # 3. Gửi nhiệm vụ tiếp tục (Gửi văn bản! Đây là điều nên làm)
                    continue_task_message = {
                        "header": {
                            "action": "continue-task",  # Thay đổi trở lại nhiệm vụ tiếp tục
                            "task_id": session_id,
                            "streaming": "duplex",
                        },
                        "payload": {"input": {"text": text}},
                    }
                    await ws.send(json.dumps(continue_task_message))

                    # 4. Gửi kết thúc nhiệm vụ (end task)
                    finish_task_message = {
                        "header": {
                            "action": "finish-task",
                            "task_id": session_id,
                            "streaming": "duplex",
                        },
                        "payload": {"input": {}},
                    }
                    await ws.send(json.dumps(finish_task_message))

                    # 5. Đợi đoạn dữ liệu âm thanh đầu tiên
                    while True:
                        msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                        if isinstance(msg, (bytes, bytearray)) and len(msg) > 0:
                            latency = time.time() - start_time
                            print(
                                f"[阿里云百炼TTS] 第{i + 1}次 首词延迟: {latency:.3f}s"
                            )
                            latencies.append(latency)
                            break
                        elif isinstance(msg, str):
                            data = json.loads(msg)
                            event = data.get("header", {}).get("event")
                            if event == "task-failed":
                                raise Exception(f"Tổng hợp giọng nói thất bại: {data}")
                            elif event == "task-finished":
                                if not latencies or latencies[-1] is None:
                                    raise Exception("tác vụ结束但未nhậnâm thanh")

            except Exception as e:
                print(f"[阿里云百炼TTS] 第{i + 1}次thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("阿里云百炼TTS", latencies, test_count)

    async def test_doubao_tts(self, text=None, test_count=5):
        """测试火山引擎流式TTS首词延迟（测试多次取平均）"""
        text = text or self.test_texts[0]
        latencies = []

        for i in range(test_count):
            try:
                tts_config = self.config["TTS"]["HuoshanDoubleStreamTTS"]
                ws_url = tts_config["ws_url"]
                app_id = tts_config["appid"]
                access_token = tts_config["access_token"]
                resource_id = tts_config["resource_id"]
                speaker = tts_config["speaker"]

                start_time = time.time()
                ws_header = {
                    "X-Api-App-Key": app_id,
                    "X-Api-Access-Key": access_token,
                    "X-Api-Resource-Id": resource_id,
                    "X-Api-Connect-Id": str(uuid.uuid4()),
                }
                async with websockets.connect(
                    ws_url, additional_headers=ws_header, max_size=1000000000
                ) as ws:
                    session_id = uuid.uuid4().hex

                    # Gửi yêu cầu bắt đầu phiên
                    header = bytes(
                        [
                            (0b0001 << 4) | 0b0001,
                            0b0001 << 4 | 0b1011,
                            0b0001 << 4 | 0b0000,
                        ]
                    )
                    optional = bytearray()
                    optional.extend((1).to_bytes(4, "big", signed=True))
                    session_id_bytes = session_id.encode()
                    optional.extend(
                        len(session_id_bytes).to_bytes(4, "big", signed=True)
                    )
                    optional.extend(session_id_bytes)
                    payload = json.dumps({"speaker": speaker}).encode()
                    await ws.send(
                        header
                        + optional
                        + len(payload).to_bytes(4, "big", signed=True)
                        + payload
                    )

                    # Gửi văn bản
                    header = bytes(
                        [
                            (0b0001 << 4) | 0b0001,
                            0b0001 << 4 | 0b1011,
                            0b0001 << 4 | 0b0000,
                            0,
                        ]
                    )
                    optional = bytearray()
                    optional.extend((200).to_bytes(4, "big", signed=True))
                    session_id_bytes = session_id.encode()
                    optional.extend(
                        len(session_id_bytes).to_bytes(4, "big", signed=True)
                    )
                    optional.extend(session_id_bytes)
                    payload = json.dumps({"text": text, "speaker": speaker}).encode()
                    await ws.send(
                        header
                        + optional
                        + len(payload).to_bytes(4, "big", signed=True)
                        + payload
                    )

                    first_chunk = await ws.recv()
                    latency = time.time() - start_time
                    latencies.append(latency)
                    print(f"[火山引擎TTS] 第{i + 1}次 首词延迟: {latency:.3f}s")

            except Exception as e:
                print(f"[火山引擎TTS] 第{i + 1}次测试thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("火山引擎TTS", latencies, test_count)

    async def test_paddlespeech_tts(self, text=None, test_count=5):
        """测试PaddleSpeech流式TTS首词延迟（测试多次取平均）"""
        text = text or self.test_texts[0]
        latencies = []

        for i in range(test_count):
            try:
                tts_config = self.config["TTS"]["PaddleSpeechTTS"]
                tts_url = tts_config["url"]
                spk_id = tts_config["spk_id"]
                speed = tts_config["speed"]
                volume = tts_config["volume"]

                start_time = time.time()
                async with websockets.connect(tts_url) as ws:
                    # Gửi yêu cầu bắt đầu
                    await ws.send(json.dumps({"task": "tts", "signal": "start"}))

                    start_response = json.loads(await ws.recv())
                    if start_response.get("status") != 0:
                        raise Exception("kết nốithất bại")

                    # Gửi dữ liệu văn bản
                    await ws.send(
                        json.dumps(
                            {
                                "text": text,
                                "spk_id": spk_id,
                                "speed": speed,
                                "volume": volume,
                            }
                        )
                    )

                    # Nhận khối dữ liệu đầu tiên
                    first_chunk = await ws.recv()
                    latency = time.time() - start_time
                    latencies.append(latency)
                    print(f"[PaddleSpeechTTS] 第{i + 1}次 首词延迟: {latency:.3f}s")

                    # Gửi yêu cầu kết thúc
                    end_request = {"task": "tts", "signal": "end"}
                    await ws.send(json.dumps(end_request))

                    # Đảm bảo kết nối được đóng một cách duyên dáng
                    try:
                        await ws.recv()
                    except websockets.exceptions.ConnectionClosedOK:
                        pass

            except Exception as e:
                print(f"[PaddleSpeechTTS] 第{i + 1}次测试thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("PaddleSpeechTTS", latencies, test_count)

    async def test_indexstream_tts(self, text=None, test_count=5):
        """测试IndexStream流式TTS首词延迟（测试多次取平均）"""
        text = text or self.test_texts[0]
        latencies = []

        for i in range(test_count):
            try:
                tts_config = self.config["TTS"]["IndexStreamTTS"]
                api_url = tts_config.get("api_url")
                voice = tts_config.get("voice")

                # Điểm bắt đầu định giờ thống nhất: bắt đầu định giờ trước khi thiết lập kết nối
                start_time = time.time()

                async with aiohttp.ClientSession() as session:
                    payload = {"text": text, "character": voice}
                    async with session.post(api_url, json=payload, timeout=10) as resp:
                        if resp.status != 200:
                            raise Exception(
                                f"Yêu cầu thất bại: {resp.status}, {await resp.text()}"
                            )

                        async for chunk in resp.content.iter_any():
                            data = (
                                chunk[0] if isinstance(chunk, (list, tuple)) else chunk
                            )
                            if not data:
                                continue

                            latency = time.time() - start_time
                            latencies.append(latency)
                            print(
                                f"[IndexStreamTTS] 第{i + 1}次 首词延迟: {latency:.3f}s"
                            )
                            resp.close()
                            break
                        else:
                            latencies.append(None)

            except Exception as e:
                print(f"[IndexStreamTTS] 第{i + 1}次测试thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("IndexStreamTTS", latencies, test_count)

    async def test_linkerai_tts(self, text=None, test_count=5):
        """测试Linkerai流式TTS首词延迟（测试多次取平均）"""
        text = text or self.test_texts[0]
        latencies = []

        for i in range(test_count):
            try:
                tts_config = self.config["TTS"]["LinkeraiTTS"]
                api_url = tts_config["api_url"]
                access_token = tts_config["access_token"]
                voice = tts_config["voice"]

                # Điểm bắt đầu định giờ thống nhất: bắt đầu định giờ trước khi thiết lập kết nối
                start_time = time.time()
                async with aiohttp.ClientSession() as session:
                    params = {
                        "tts_text": text,
                        "spk_id": voice,
                        "frame_durition": 60,
                        "stream": "true",
                        "target_sr": 16000,
                        "audio_format": "pcm",
                        "instruct_text": "请生成一段自然流畅的语音",
                    }
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    }

                    async with session.get(
                        api_url, params=params, headers=headers, timeout=10
                    ) as resp:
                        if resp.status != 200:
                            raise Exception(
                                f"Yêu cầu thất bại: {resp.status}, {await resp.text()}"
                            )

                        # Nhận khối dữ liệu đầu tiên
                        async for _ in resp.content.iter_any():
                            latency = time.time() - start_time
                            latencies.append(latency)
                            print(f"[LinkeraiTTS] 第{i + 1}次 首词延迟: {latency:.3f}s")
                            break
                        else:
                            latencies.append(None)

            except Exception as e:
                print(f"[LinkeraiTTS] 第{i + 1}次测试thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("LinkeraiTTS", latencies, test_count)

    async def test_xunfei_tts(self, text=None, test_count=5):
        """测试讯飞流式TTS首词延迟（测试多次取平均）"""
        text = text or self.test_texts[0]
        latencies = []

        for i in range(test_count):
            try:
                # Đã sửa tên nút cấu hình để khớp với XunFeiTTS trong tệp cấu hình
                tts_config = self.config["TTS"]["XunFeiTTS"]
                app_id = tts_config["app_id"]
                api_key = tts_config["api_key"]
                api_secret = tts_config["api_secret"]
                api_url = tts_config.get(
                    "api_url", "wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/mcd9m97e6"
                )
                voice = tts_config.get("voice", "x5_lingxiaoxuan_flow")
                # Tạo URL xác thực
                auth_url = self._create_xunfei_auth_url(api_key, api_secret, api_url)
                start_time = time.time()
                async with websockets.connect(
                    auth_url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=10,
                    max_size=1000000000,
                ) as ws:
                    # Xây dựng yêu cầu
                    request = self._build_xunfei_request(app_id, text, voice)
                    await ws.send(json.dumps(request))
                    # Đợi đoạn dữ liệu âm thanh đầu tiên
                    first_audio_received = False
                    while not first_audio_received:
                        msg = await asyncio.wait_for(ws.recv(), timeout=10)
                        data = json.loads(msg)
                        header = data.get("header", {})
                        code = header.get("code")

                        if code != 0:
                            message = header.get("message", "Lỗi không xác định")
                            raise Exception(
                                f"Tổng hợp giọng nói thất bại: {code} - {message}"
                            )

                        payload = data.get("payload", {})
                        audio_payload = payload.get("audio", {})

                        if audio_payload:
                            status = audio_payload.get("status", 0)
                            audio_data = audio_payload.get("audio", "")
                            if status == 1 and audio_data:
                                # Đoạn dữ liệu âm thanh đầu tiên được nhận
                                latency = time.time() - start_time
                                latencies.append(latency)
                                print(f"[讯飞TTS] 第{i + 1}次 首词延迟: {latency:.3f}s")
                                first_audio_received = True
                                break
            except Exception as e:
                print(f"[讯飞TTS] 第{i + 1}次测试thất bại: {str(e)}")
                latencies.append(None)

        return self._calculate_result("讯飞TTS", latencies, test_count)

    def _create_xunfei_auth_url(self, api_key, api_secret, api_url):
        """生成讯飞WebSocket认证URL"""
        parsed_url = urlparse(api_url)
        host = parsed_url.netloc
        path = parsed_url.path

        # Để có được thời gian UTC, iFlytek yêu cầu sử dụng định dạng RFC1123
        now = time.gmtime()
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", now)

        # Xây dựng chuỗi chữ ký
        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"

        # Tính chữ ký
        signature_sha = hmac.new(
            api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha_base64 = base64.b64encode(signature_sha).decode(encoding="utf-8")

        # Xây dựng ủy quyền
        authorization_origin = f'api_key="{api_key}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature_sha_base64}"'
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode(
            encoding="utf-8"
        )

        # Xây dựng URL WebSocket cuối cùng
        v = {"authorization": authorization, "date": date, "host": host}
        url = api_url + "?" + urlencode(v)
        return url

    def _build_xunfei_request(self, app_id, text, voice):
        """构建讯飞TTSyêu cầu结构"""
        return {
            "header": {
                "app_id": app_id,
                "status": 2,
            },
            "parameter": {
                "oral": {
                    "oral_level": "mid",
                    "spark_assist": 1,
                    "stop_split": 0,
                    "remain": 0,
                },
                "tts": {
                    "vcn": voice,
                    "speed": 50,
                    "volume": 50,
                    "pitch": 50,
                    "bgs": 0,
                    "reg": 0,
                    "rdn": 0,
                    "rhy": 0,
                    "audio": {
                        "encoding": "raw",
                        "sample_rate": 24000,
                        "channels": 1,
                        "bit_depth": 16,
                        "frame_size": 0,
                    },
                },
            },
            "payload": {
                "text": {
                    "encoding": "utf8",
                    "compress": "raw",
                    "format": "plain",
                    "status": 2,
                    "seq": 1,
                    "text": base64.b64encode(text.encode("utf-8")).decode("utf-8"),
                }
            },
        }

    def _calculate_result(self, service_name, latencies, test_count):
        """计算测试kết quả（正确xử lýNone值 , 剔除thất bại测试）"""
        # Loại bỏ các thử nghiệm không thành công (Không có giá trị và độ trễ <= 0) và chỉ tính độ trễ hiệu quả
        valid_latencies = [l for l in latencies if l is not None and l > 0]
        if valid_latencies:
            avg_latency = sum(valid_latencies) / len(valid_latencies)
            status = f"成功（{len(valid_latencies)}/{test_count}次有效）"
        else:
            avg_latency = 0
            status = "thất bại: 所有测试均thất bại"
        return {"name": service_name, "latency": avg_latency, "status": status}

    def _print_results(self, test_text, test_count):
        """打印测试kết quả"""
        if not self.results:
            print("没有有效的TTS测试kết quả")
            return

        print(f"\n{'=' * 60}")
        print("流式TTS首词延迟测试kết quả")
        print(f"{'=' * 60}")
        print(f"测试文本: {test_text}")
        print(f"测试次数: 每个TTSdịch vụ测试 {test_count} lần")

        # Sắp xếp kết quả: thành công trước, thứ tự tăng dần theo độ trễ
        success_results = sorted(
            [r for r in self.results if "成功" in r["status"]],
            key=lambda x: x["latency"],
        )
        failed_results = [r for r in self.results if "成功" not in r["status"]]

        table_data = [
            [r["name"], f"{r['latency']:.3f}", r["status"]]
            for r in success_results + failed_results
        ]

        print(
            tabulate(
                table_data,
                headers=["TTSdịch vụ", "首词延迟(秒)", "trạng thái"],
                tablefmt="grid",
            )
        )
        print(
            "\n测试说明: 测量从thiết lậpkết nối到接收第一个âm thanhdữ liệu块的khi间（包含握手、鉴权、gửivăn bản） , 取多次测试平均值"
        )
        print(
            "- 计khi起点: thiết lậpWebSocket/HTTPkết nối前（统一包含网络建连、握手、gửivăn bản全流程）"
        )
        print("- quá thời gian chờ控制: 单个yêu cầu最大chờkhi间为10秒")
        print("- Lỗixử lý: thất bại的测试不计入平均值 , 只统计thành công测试的延迟")
        print("- 排序规则: 按平均耗时从快到慢排序")

    async def run(self, test_text=None, test_count=5):
        """thực thi测试

        Args:
            test_text: 要测试的văn bản , 如果为None则使用默认văn bản
            test_count: 每个TTSdịch vụ的测试次数
        """
        test_text = test_text or self.test_texts[0]
        print(f"开始流式TTS首词延迟测试...")
        print(f"测试文本: {test_text}")
        print(f"每个TTSdịch vụ测试次数: {test_count}次")

        if not self.config.get("TTS"):
            print("cấu hình文件trongkhông tìm thấyTTScấu hình")
            return

        # Kiểm tra từng dịch vụ TTS
        self.results = []

        # Kiểm tra TTS đám mây của Alibaba
        result = await self.test_aliyun_tts(test_text, test_count)
        self.results.append(result)

        # Kiểm tra TTS trên nền tảng đám mây của Alibaba Bailian
        if self.config.get("TTS", {}).get("AliBLTTS"):
            result = await self.test_alibl_tts(test_text, test_count)
            self.results.append(result)

        # Kiểm tra động cơ núi lửa TTS
        result = await self.test_doubao_tts(test_text, test_count)
        self.results.append(result)

        # Kiểm tra PaddleSpeech TTS
        result = await self.test_paddlespeech_tts(test_text, test_count)
        self.results.append(result)

        # Kiểm tra Linkerai TTS
        result = await self.test_linkerai_tts(test_text, test_count)
        self.results.append(result)

        # Kiểm tra IndexStreamTTS
        result = await self.test_indexstream_tts(test_text, test_count)
        self.results.append(result)

        # Kiểm tra iFlytek TTS
        if self.config.get("TTS", {}).get("XunFeiTTS"):
            result = await self.test_xunfei_tts(test_text, test_count)
            self.results.append(result)

        # In kết quả
        self._print_results(test_text, test_count)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="流式TTS首词延迟测试công cụ")
    parser.add_argument("--text", help="要测试的văn bảnnội dung")
    parser.add_argument("--count", type=int, default=5, help="每个TTSdịch vụ的测试次数")

    args = parser.parse_args()
    config = await load_config()
    await StreamTTSPerformanceTester(config).run(args.text, args.count)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
