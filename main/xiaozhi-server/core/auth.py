import hmac
import base64
import hashlib
import time


class AuthenticationError(Exception):
    """认证sự cố"""

    pass


class AuthManager:
    """
    统一授权认证管理器
    生成与验证 client_id device_id token（HMAC-SHA256）认证三元组
    token trong不含明文 client_id/device_id , 只携带签名 + khi间戳; client_id/device_id在kết nốikhi传递
    在 MQTT trong client_id: client_id, username: device_id, password: token
    在 Websocket trong , header:{Device-ID: device_id, Client-ID: client_id, Authorization: Bearer token, ......}
    """

    def __init__(self, secret_key: str, expire_seconds: int = 60 * 60 * 24 * 30):
        if not expire_seconds or expire_seconds < 0:
            self.expire_seconds = 60 * 60 * 24 * 30
        else:
            self.expire_seconds = expire_seconds
        self.secret_key = secret_key

    def _sign(self, content: str) -> str:
        """HMAC-SHA256签名并Base64编码"""
        sig = hmac.new(
            self.secret_key.encode("utf-8"), content.encode("utf-8"), hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")

    def generate_token(self, client_id: str, username: str) -> str:
        """
        生成 token
        Args:
            client_id: thiết bịkết nốiID
            username: thiết bịngười dùng名（通常为deviceId）
        Returns:
            str: token字符串
        """
        ts = int(time.time())
        content = f"{client_id}|{username}|{ts}"
        signature = self._sign(content)
        # Mã thông báo chỉ chứa chữ ký và dấu thời gian và không chứa thông tin văn bản thuần túy.
        token = f"{signature}.{ts}"
        return token

    def verify_token(self, token: str, client_id: str, username: str) -> bool:
        """
        验证token有效性
        Args:
            token: máy khách传入的token
            client_id: kết nối使用的client_id
            username: kết nối使用的username
        """
        try:
            sig_part, ts_str = token.split(".")
            ts = int(ts_str)
            if int(time.time()) - ts > self.expire_seconds:
                return False  # Đã hết hạn

            expected_sig = self._sign(f"{client_id}|{username}|{ts}")
            if not hmac.compare_digest(sig_part, expected_sig):
                return False

            return True
        except Exception:
            return False
