"""
hệ thốnghướng dẫn词管理器mô-đun
负责管理和cập nhậthệ thốnghướng dẫn词 , 包括快速khởi tạo和异步增强功能
"""

import os
import asyncio
import threading
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from config.logger import setup_logging
from jinja2 import Template

TAG = __name__

WEEKDAY_MAP = {
    "Monday": "Thứ Hai",
    "Tuesday": "Thứ Ba",
    "Wednesday": "Thứ Tư",
    "Thursday": "Thứ Năm",
    "Friday": "Thứ Sáu",
    "Saturday": "Thứ Bảy",
    "Sunday": "Chủ nhật",
}

EMOJI_List = [
    "😶",
    "🙂",
    "😆",
    "😂",
    "😔",
    "😠",
    "😭",
    "😍",
    "😳",
    "😲",
    "😱",
    "🤔",
    "😉",
    "😎",
    "😌",
    "🤤",
    "😘",
    "😏",
    "😴",
    "😜",
    "🙄",
]


class PromptManager:
    """hệ thốnghướng dẫn词管理器 , 负责管理和cập nhậthệ thốnghướng dẫn词"""

    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger or setup_logging()
        self.base_prompt_template = None
        self.last_update_time = 0

        # Nhập trình quản lý bộ đệm chung
        from core.utils.cache.manager import cache_manager, CacheType

        self.cache_manager = cache_manager
        self.CacheType = CacheType

        # Khởi tạo nguồn ngữ cảnh
        from core.utils.context_provider import ContextDataProvider

        self.context_provider = ContextDataProvider(config, self.logger)
        self.context_data = {}

        self._load_base_template()

    def _load_base_template(self):
        """tải基础hướng dẫn词模板"""
        try:
            template_path = self.config.get("prompt_template", None)
            if not template_path:
                template_path = "agent-base-prompt.txt"
            cache_key = f"prompt_template:{template_path}"

            # Lấy nó từ bộ đệm trước
            cached_template = self.cache_manager.get(self.CacheType.CONFIG, cache_key)
            if cached_template is not None:
                self.base_prompt_template = cached_template
                self.logger.bind(tag=TAG).debug("从bộ nhớ đệmtải基础hướng dẫn词模板")
                return

            # Thiếu bộ nhớ đệm, đọc từ tập tin
            if os.path.exists(template_path):
                with open(template_path, "r", encoding="utf-8") as f:
                    template_content = f.read()

                # Lưu trữ trong bộ đệm (loại CONFIG không tự động hết hạn theo mặc định và cần được vô hiệu hóa theo cách thủ công)
                self.cache_manager.set(
                    self.CacheType.CONFIG, cache_key, template_content
                )
                self.base_prompt_template = template_content
                self.logger.bind(tag=TAG).debug(
                    "thành côngtải基础hướng dẫn词模板并bộ nhớ đệm"
                )
            else:
                self.logger.bind(tag=TAG).warning(f"未找到{template_path}文件")
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"tảihướng dẫn词模板thất bại: {e}")

    def get_quick_prompt(self, user_prompt: str, device_id: str = None) -> str:
        """快速lấyhệ thốnghướng dẫn词（使用người dùngcấu hình）"""
        device_cache_key = f"device_prompt:{device_id}"
        cached_device_prompt = self.cache_manager.get(
            self.CacheType.DEVICE_PROMPT, device_cache_key
        )
        if cached_device_prompt is not None:
            self.logger.bind(tag=TAG).debug(f"使用设备 {device_id} 的缓存提示词")
            return cached_device_prompt
        else:
            self.logger.bind(tag=TAG).debug(
                f"设备 {device_id} 无缓存提示词，使用传入的提示词"
            )

        # Sử dụng từ nhắc nhở đến và lưu vào bộ đệm (nếu có ID thiết bị)
        if device_id:
            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(
                self.CacheType.DEVICE_PROMPT, device_cache_key, user_prompt
            )
            self.logger.bind(tag=TAG).debug(f"设备 {device_id} 的提示词已缓存")

        self.logger.bind(tag=TAG).info(f"使用快速提示词: {user_prompt[:50]}...")
        return user_prompt

    def _get_current_time_info(self) -> tuple:
        """lấyhiện tạikhi间thông tin"""
        from .current_time import (
            get_current_date,
            get_current_weekday,
            get_current_lunar_date,
        )

        today_date = get_current_date()
        today_weekday = get_current_weekday()
        lunar_date = get_current_lunar_date() + "\n"

        return today_date, today_weekday, lunar_date

    def _get_location_info(self, client_ip: str) -> str:
        """获取位置信息"""
        try:
            # Lấy nó từ bộ đệm trước
            cached_location = self.cache_manager.get(self.CacheType.LOCATION, client_ip)
            if cached_location is not None:
                return cached_location

            # Thiếu bộ nhớ đệm, hãy gọi API để lấy
            from core.utils.util import get_ip_info

            ip_info = get_ip_info(client_ip, self.logger)
            city = ip_info.get("city", "Vị trí chưa xác định")
            location = f"{city}"

            # bộ nhớ đệm
            self.cache_manager.set(self.CacheType.LOCATION, client_ip, location)
            return location
        except Exception as e:
            self.logger.bind(tag=TAG).error(f"lấy位置thông tinthất bại: {e}")
            return "Vị trí chưa xác định"

    def _get_weather_info(self, conn: "ConnectionHandler", location: str) -> str:
        """获取天气信息"""
        try:
            # Lấy nó từ bộ đệm trước
            cached_weather = self.cache_manager.get(self.CacheType.WEATHER, location)
            if cached_weather is not None:
                return cached_weather

            # Thiếu bộ nhớ đệm, gọi hàm async get_weather
            # Windows ProactorEventLoop không hỗ trợ run_coroutine_threadsafe().result()
            # Vì vậy hãy sử dụng call_soon_threadsafe để gửi task + threading.Event để chờ kết quả
            # Lưu ý: Event.wait() chỉ chặn luồng nhóm luồng hiện tại và không chặn vòng lặp sự kiện chính
            from plugins_func.functions.get_weather import get_weather
            from plugins_func.register import ActionResponse

            result_holder = []
            exception_holder = []

            async def _call():
                try:
                    result_holder.append(
                        await get_weather(conn, location=location, lang="zh_CN")
                    )
                except Exception as e:
                    exception_holder.append(e)
                finally:
                    event.set()

            event = threading.Event()
            conn.loop.call_soon_threadsafe(lambda: asyncio.ensure_future(_call()))
            if not event.wait(timeout=10):
                raise TimeoutError("Lấy thông tin thời tiết quá thời gian chờ")
            if exception_holder:
                raise exception_holder[0]
            result = result_holder[0]
            if isinstance(result, ActionResponse):
                weather_report = result.result
                self.cache_manager.set(self.CacheType.WEATHER, location, weather_report)
                return weather_report
            return "Không thể lấy thông tin thời tiết"

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"lấy天气thông tinthất bại: {e}")
            return "Không thể lấy thông tin thời tiết"

    def update_context_info(self, conn, client_ip: str):
        """同步更新上下文信息"""
        try:
            local_address = ""
            if (
                client_ip
                and self.base_prompt_template
                and (
                    "local_address" in self.base_prompt_template
                    or "weather_info" in self.base_prompt_template
                )
            ):
                # Nhận thông tin vị trí (sử dụng bộ đệm chung)
                local_address = self._get_location_info(client_ip)

            if (
                self.base_prompt_template
                and "weather_info" in self.base_prompt_template
                and local_address
            ):
                # Nhận thông tin thời tiết (sử dụng bộ đệm chung)
                self._get_weather_info(conn, local_address)

            # Nhận dữ liệu ngữ cảnh cấu hình
            if hasattr(conn, "device_id") and conn.device_id:
                if (
                    self.base_prompt_template
                    and "dynamic_context" in self.base_prompt_template
                ):
                    self.context_data = self.context_provider.fetch_all(conn.device_id)
                else:
                    self.context_data = ""

            self.logger.bind(tag=TAG).debug(f"上下文信息更新完成")

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"cập nhật上下文thông tinthất bại: {e}")

    def build_enhanced_prompt(
        self, user_prompt: str, device_id: str, client_ip: str = None, *args, **kwargs
    ) -> str:
        """构建增强的hệ thốnghướng dẫn词"""
        if not self.base_prompt_template:
            return user_prompt

        try:
            # Nhận thông tin thời gian mới nhất (không cần lưu vào bộ nhớ đệm)
            today_date, today_weekday, lunar_date = self._get_current_time_info()

            # Nhận thông tin ngữ cảnh được lưu trong bộ nhớ đệm
            local_address = ""
            weather_info = ""

            if client_ip:
                # Nhận thông tin vị trí (từ bộ đệm chung)
                local_address = (
                    self.cache_manager.get(self.CacheType.LOCATION, client_ip) or ""
                )

                # Nhận thông tin thời tiết (từ bộ đệm chung)
                if local_address:
                    weather_info = (
                        self.cache_manager.get(self.CacheType.WEATHER, local_address)
                        or ""
                    )

            # Lấy ngôn ngữ do TTS chọn, giá trị mặc định là tiếng Trung
            language = (
                self.config.get("TTS", {})
                .get(self.config.get("selected_module", {}).get("TTS", ""), {})
                .get("language")
                or "Tiếng Việt"
            )
            self.logger.bind(tag=TAG).debug(f"获取到选择的语言: {language}")

            # Thay thế các biến mẫu
            template = Template(self.base_prompt_template)
            enhanced_prompt = template.render(
                base_prompt=user_prompt,
                current_time="{{current_time}}",
                today_date=today_date,
                today_weekday=today_weekday,
                lunar_date=lunar_date,
                local_address=local_address,
                weather_info=weather_info,
                emojiList=EMOJI_List,
                device_id=device_id,
                client_ip=client_ip,
                dynamic_context=self.context_data,
                language=language,
                *args,
                **kwargs,
            )
            device_cache_key = f"device_prompt:{device_id}"
            self.cache_manager.set(
                self.CacheType.DEVICE_PROMPT, device_cache_key, enhanced_prompt
            )
            self.logger.bind(tag=TAG).info(
                f"构建增强提示词成功，长度: {len(enhanced_prompt)}"
            )
            return enhanced_prompt

        except Exception as e:
            self.logger.bind(tag=TAG).error(f"构建增强hướng dẫn词thất bại: {e}")
            return user_prompt
