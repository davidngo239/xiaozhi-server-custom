from aiohttp import web
from config.logger import setup_logging


class BaseHandler:
    def __init__(self, config: dict):
        self.config = config
        self.logger = setup_logging()

    def _add_cors_headers(self, response):
        """添加CORS头信息"""
        response.headers["Access-Control-Allow-Headers"] = (
            "client-id, content-type, device-id, authorization"
        )
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Origin"] = "*"

    async def handle_options(self, request):
        """xử lýOPTIONSyêu cầu , 添加CORS头thông tin"""
        response = web.Response(body=b"", content_type="text/plain")
        self._add_cors_headers(response)
        # Thêm các phương thức được phép
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response
