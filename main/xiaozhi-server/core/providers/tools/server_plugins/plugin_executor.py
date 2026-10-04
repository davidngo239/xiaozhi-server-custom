"""dịch vụ端插件công cụthực thi器"""

import asyncio
from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import (
    all_function_registry,
    module_func_map,
    Action,
    ActionResponse,
)


class ServerPluginExecutor(ToolExecutor):
    """dịch vụ端插件công cụthực thi器"""

    def __init__(self, conn: "ConnectionHandler"):
        self.conn = conn
        self.config = conn.config

    async def execute(
        self, conn: "ConnectionHandler", tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """thực thidịch vụ端插件công cụ"""
        func_item = all_function_registry.get(tool_name)
        if not func_item:
            return ActionResponse(
                action=Action.NOTFOUND, response=f"Hàm plugin {tool_name} không tồn tại"
            )

        try:
            # Xác định cách gọi dựa trên loại công cụ
            if hasattr(func_item, "type"):
                func_type = func_item.type
                if func_type.code in [4, 5]:  # SYSTEM_CTL và IOT_CTL cần tham số conn
                    result = func_item.func(conn, **arguments)
                elif func_type.code == 2:  # WAIT
                    result = func_item.func(**arguments)
                elif func_type.code == 3:  # CHANGE_SYS_PROMPT
                    result = func_item.func(conn, **arguments)
                else:
                    result = func_item.func(**arguments)
            else:
                # Tham số conn không được truyền theo mặc định
                result = func_item.func(**arguments)

            # Tương thích với chức năng tiện ích def async
            if asyncio.iscoroutine(result):
                result = await result

            return result

        except Exception as e:
            return ActionResponse(
                action=Action.ERROR,
                response=str(e),
            )

    def _expand_plugin_names(self, config_functions):
        """sẽmô-đun级别的插件名展开为cụ thểhàm名.

        在一个 function 文件trong可能注册多个 @register_function ,
        cấu hìnhtrong如果使用的是mô-đun名（文件名） , 需要展开为cụ thể的hàm名列表.
        """
        if not isinstance(config_functions, list):
            try:
                config_functions = list(config_functions)
            except TypeError:
                return []

        expanded = []
        for name in config_functions:
            if name in module_func_map:
                # Tên mô-đun, được mở rộng cho tất cả các tên chức năng đã đăng ký trong mô-đun
                expanded.extend(module_func_map[name])
            elif name in all_function_registry:
                # Khớp chính xác với tên hàm và giữ nó trực tiếp
                expanded.append(name)
            else:
                # Tên không xác định, hãy để nguyên (có thể là MCP hoặc công cụ khác)
                expanded.append(name)
        return expanded

    def _get_plugin_description(self, func_name):
        """获取插件函数的描述，优先精确匹配函数名，其次匹配模块名。"""
        plugins = self.config.get("plugins", {})
        # Tên hàm khớp chính xác
        if func_name in plugins:
            return plugins[func_name].get("description", "")
        # Tìm kiếm ngược tên mô-đun thông qua module_func_map
        for module_name, func_names in module_func_map.items():
            if func_name in func_names and module_name in plugins:
                return plugins[module_name].get("description", "")
        return ""

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """lấy所有注册的dịch vụ端插件công cụ"""
        tools = {}

        # Nhận các chức năng cần thiết
        necessary_functions = ["handle_exit_intent", "get_lunar"]

        # Nhận các chức năng trong cấu hình
        config_functions = self.config["Intent"][
            self.config["selected_module"]["Intent"]
        ].get("functions", [])

        # Mở rộng tên trình cắm cấp mô-đun thành tên chức năng cụ thể (cơ chế che phủ)
        config_functions = self._expand_plugin_names(config_functions)

        # Kết hợp tất cả các chức năng cần thiết
        all_required_functions = list(set(necessary_functions + config_functions))

        for func_name in all_required_functions:
            func_item = all_function_registry.get(func_name)
            if func_item:
                # Nhận mô tả từ đăng ký chức năng (hỗ trợ tìm kiếm hai cấp tên mô-đun và tên chức năng)
                fun_description = self._get_plugin_description(func_name)
                if fun_description is not None and len(fun_description) > 0:
                    if "function" in func_item.description and isinstance(
                        func_item.description["function"], dict
                    ):
                        func_item.description["function"]["description"] = (
                            fun_description
                        )

                # Plug-in tin tức: Cập nhật mô tả tham số nguồn tin tức theo cấu hình
                if func_name == "get_news_from_newsnow":
                    self._init_news_source_description(func_item, func_name)

                tools[func_name] = ToolDefinition(
                    name=func_name,
                    description=func_item.description,
                    tool_type=ToolType.SERVER_PLUGIN,
                )

        return tools

    def has_tool(self, tool_name: str) -> bool:
        """kiểm tra是否有指定的dịch vụ端插件công cụ"""
        return tool_name in all_function_registry

    def _init_news_source_description(self, func_item, func_name):
        """根据kết nốicấu hìnhkhởi tạo新闻công cụ的tham số描述"""
        news_sources = (
            self.config.get("plugins", {}).get(func_name, {}).get("news_sources", "")
        )
        if not news_sources:
            news_sources = "Báo The Paper;Xu hướng Baidu;Tài Liên Xã"
        sources_str = news_sources.replace(";", "、")
        try:
            func_item.description["function"]["parameters"]["properties"]["source"][
                "description"
            ] = f"Tên nguồn tin hợp lệ, ví dụ {sources_str}. Tham số tùy chọn; bỏ trống để dùng nguồn mặc định"
        except (KeyError, TypeError):
            pass
