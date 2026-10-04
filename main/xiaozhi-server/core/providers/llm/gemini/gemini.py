import os, json, uuid
from types import SimpleNamespace
from typing import Any, Dict, List

import requests
from google import generativeai as genai
from google.generativeai import types, GenerationConfig

from core.providers.llm.base import LLMProviderBase
from core.utils.util import check_model_key
from config.logger import setup_logging
from google.generativeai.types import GenerateContentResponse
from requests import RequestException

log = setup_logging()
TAG = __name__


def test_proxy(proxy_url: str, test_url: str) -> bool:
    try:
        resp = requests.get(test_url, proxies={"http": proxy_url, "https": proxy_url})
        return 200 <= resp.status_code < 400
    except RequestException:
        return False


def setup_proxy_env(http_proxy: str | None, https_proxy: str | None):
    """
    分别测试 HTTP 和 HTTPS 代理是否可用，并设置环境变量。
    如果 HTTPS 代理不可用但 HTTP 可用，会将 HTTPS_PROXY 也指向 HTTP。
    """
    test_http_url = "http://www.google.com"
    test_https_url = "https://www.google.com"

    ok_http = ok_https = False

    if http_proxy:
        ok_http = test_proxy(http_proxy, test_http_url)
        if ok_http:
            os.environ["HTTP_PROXY"] = http_proxy
            log.bind(tag=TAG).info(
                f"cấu hình提供的Gemini HTTPS代理连通thành công: {http_proxy}"
            )
        else:
            log.bind(tag=TAG).warning(
                f"cấu hình提供的Gemini HTTP代理不可用: {http_proxy}"
            )

    if https_proxy:
        ok_https = test_proxy(https_proxy, test_https_url)
        if ok_https:
            os.environ["HTTPS_PROXY"] = https_proxy
            log.bind(tag=TAG).info(
                f"cấu hình提供的Gemini HTTPS代理连通thành công: {https_proxy}"
            )
        else:
            log.bind(tag=TAG).warning(
                f"cấu hình提供的Gemini HTTPS代理不可用: {https_proxy}"
            )

    # Nếu https_proxy không khả dụng, nhưng http_proxy có sẵn và có thể chuyển qua https, hãy sử dụng lại http_proxy dưới dạng https_proxy
    if ok_http and not ok_https:
        if test_proxy(http_proxy, test_https_url):
            os.environ["HTTPS_PROXY"] = http_proxy
            ok_https = True
            log.bind(tag=TAG).info(f"复用HTTP代理作为HTTPS代理: {http_proxy}")

    if not ok_http and not ok_https:
        log.bind(tag=TAG).error(
            f"Gemini 代理设置thất bại: Proxy HTTP và HTTPS đều không khả dụng. Kiểm tra cấu hình"
        )
        raise RuntimeError("Proxy HTTP và HTTPS đều không khả dụng. Kiểm tra cấu hình")


class LLMProvider(LLMProviderBase):
    def __init__(self, cfg: Dict[str, Any]):
        self.model_name = cfg.get("model_name", "gemini-2.0-flash")
        self.api_key = cfg["api_key"]
        http_proxy = cfg.get("http_proxy")
        https_proxy = cfg.get("https_proxy")

        model_key_msg = check_model_key("LLM", self.api_key)
        if model_key_msg:
            log.bind(tag=TAG).error(model_key_msg)

        if http_proxy or https_proxy:
            log.bind(tag=TAG).info(
                f"kiểm tra到Gemini代理cấu hình , 开始测试代理连通性和设置代理环境..."
            )
            setup_proxy_env(http_proxy, https_proxy)
            log.bind(tag=TAG).info(
                f"Gemini 代理设置成功 - HTTP: {http_proxy}, HTTPS: {https_proxy}"
            )
        # Định cấu hình khóa API
        genai.configure(api_key=self.api_key)

        # Đặt thời gian chờ yêu cầu (giây)
        self.timeout = cfg.get("timeout", 120)  # Mặc định 120 giây

        # Tạo phiên bản mô hình
        self.model = genai.GenerativeModel(self.model_name)

        self.gen_cfg = GenerationConfig(
            temperature=0.7,
            top_p=0.9,
            top_k=40,
            max_output_tokens=2048,
        )

    @staticmethod
    def _build_tools(funcs: List[Dict[str, Any]] | None):
        if not funcs:
            return None
        return [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=f["function"]["name"],
                        description=f["function"]["description"],
                        parameters=f["function"]["parameters"],
                    )
                    for f in funcs
                ]
            )
        ]

    # Tài liệu của Gemini đề cập rằng không cần phải duy trì session-id, nó được ghép trực tiếp với đoạn hội thoại.
    def response(self, session_id, dialogue, **kwargs):
        yield from self._generate(dialogue, None)

    def response_with_functions(self, session_id, dialogue, functions=None):
        yield from self._generate(dialogue, self._build_tools(functions))

    def _generate(self, dialogue, tools):
        role_map = {"assistant": "model", "user": "user"}
        contents: list = []
        # đối thoại nối
        for m in dialogue:
            r = m["role"]

            if r == "assistant" and "tool_calls" in m:
                tc = m["tool_calls"][0]
                contents.append(
                    {
                        "role": "model",
                        "parts": [
                            {
                                "function_call": {
                                    "name": tc["function"]["name"],
                                    "args": json.loads(tc["function"]["arguments"]),
                                }
                            }
                        ],
                    }
                )
                continue

            if r == "tool":
                contents.append(
                    {
                        "role": "model",
                        "parts": [{"text": str(m.get("content", ""))}],
                    }
                )
                continue

            contents.append(
                {
                    "role": role_map.get(r, "user"),
                    "parts": [{"text": str(m.get("content", ""))}],
                }
            )

        stream: GenerateContentResponse = self.model.generate_content(
            contents=contents,
            generation_config=self.gen_cfg,
            tools=tools,
            stream=True,
            timeout=self.timeout,
        )

        try:
            for chunk in stream:
                cand = chunk.candidates[0]
                for part in cand.content.parts:
                    # a) Lời gọi hàm - thường đoạn cuối cùng là lời gọi hàm
                    if getattr(part, "function_call", None):
                        fc = part.function_call
                        yield (
                            None,
                            [
                                SimpleNamespace(
                                    id=uuid.uuid4().hex,
                                    type="function",
                                    function=SimpleNamespace(
                                        name=fc.name,
                                        arguments=json.dumps(
                                            dict(fc.args), ensure_ascii=False
                                        ),
                                    ),
                                )
                            ],
                        )
                        return
                    # b) văn bản thuần túy
                    if getattr(part, "text", None):
                        yield part.text if tools is None else (part.text, None)

        finally:
            if tools is not None:
                yield None, None  # chế độ chức năng kết thúc và trả về một gói câm

    # Đóng luồng và bảo lưu phương thức chức năng để làm gián đoạn cuộc trò chuyện sau này. Tài liệu chính thức khuyên bạn nên đóng luồng trước đó để làm gián đoạn cuộc trò chuyện, điều này có thể làm giảm hạn ngạch thanh toán và mức sử dụng tài nguyên một cách hiệu quả.
    @staticmethod
    def _safe_finish_stream(stream: GenerateContentResponse):
        if hasattr(stream, "resolve"):
            stream.resolve()  # Gemini SDK version ≥ 0.5.0
        elif hasattr(stream, "close"):
            stream.close()  # Gemini SDK version < 0.5.0
        else:
            for _ in stream:  # kiệt sức
                pass
