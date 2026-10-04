import httpx
from typing import Dict, Any, List
from config.logger import setup_logging

TAG = __name__


class ContextDataProvider:
    """dữ liệu上下文填充 , 负责从cấu hình的APIlấydữ liệu"""

    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or setup_logging()
        self.context_data = ""

    def fetch_all(self, device_id: str) -> str:
        """lấy所有cấu hình的上下文dữ liệu"""
        context_providers = self.config.get("context_providers", [])
        if not context_providers:
            return ""

        formatted_lines = []
        for provider in context_providers:
            url = provider.get("url")
            headers = provider.get("headers", {})

            if not url:
                continue

            try:
                headers = headers.copy() if isinstance(headers, dict) else {}
                # Thêm device_id vào tiêu đề yêu cầu
                headers["device-id"] = device_id

                # Gửi yêu cầu
                response = httpx.get(url, headers=headers, timeout=3)

                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, dict):
                        if result.get("code") == 0:
                            data = result.get("data")
                            # Định dạng dữ liệu
                            if isinstance(data, dict):
                                for k, v in data.items():
                                    formatted_lines.append(f"- **{k}：** {v}")
                            elif isinstance(data, list):
                                for item in data:
                                    formatted_lines.append(f"- {item}")
                            else:
                                formatted_lines.append(f"- {data}")
                        else:
                            self.logger.bind(tag=TAG).warning(
                                f"API {url} trả vềLỗi码: {result.get('msg')}"
                            )
                    else:
                        self.logger.bind(tag=TAG).warning(
                            f"API {url} 返回的不是JSON字典"
                        )
                else:
                    self.logger.bind(tag=TAG).warning(
                        f"API {url} Yêu cầu thất bại: {response.status_code}"
                    )
            except Exception as e:
                self.logger.bind(tag=TAG).error(f"lấy上下文dữ liệu {url} thất bại: {e}")

        # Nối tất cả các dòng được định dạng thành một chuỗi
        self.context_data = "\n".join(formatted_lines)
        if self.context_data:
            self.logger.bind(tag=TAG).debug(
                f"đã注入动态上下文dữ liệu:\n{self.context_data}"
            )
        return self.context_data
