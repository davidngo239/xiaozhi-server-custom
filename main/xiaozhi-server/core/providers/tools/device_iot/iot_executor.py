"""thiết bị端IoTcông cụthực thi器"""

import json
import asyncio
from typing import Dict, Any
from ..base import ToolType, ToolDefinition, ToolExecutor
from plugins_func.register import Action, ActionResponse


class DeviceIoTExecutor(ToolExecutor):
    """thiết bị端IoTcông cụthực thi器"""

    def __init__(self, conn):
        self.conn = conn
        self.iot_tools: Dict[str, ToolDefinition] = {}

    async def execute(
        self, conn, tool_name: str, arguments: Dict[str, Any]
    ) -> ActionResponse:
        """thực thithiết bị端IoTcông cụ"""
        if not self.has_tool(tool_name):
            return ActionResponse(
                action=Action.NOTFOUND, response=f"IoTCông cụ {tool_name} không tồn tại"
            )

        try:
            # Phân tích tên công cụ và lấy tên thiết bị cũng như loại hoạt động
            if tool_name.startswith("get_"):
                # Thao tác truy vấn: get_devicename_property
                parts = tool_name.split("_", 2)
                if len(parts) >= 3:
                    device_name = parts[1]
                    property_name = parts[2]

                    value = await self._get_iot_status(device_name, property_name)
                    if value is not None:
                        # Xử lý mẫu phản hồi
                        response_success = arguments.get(
                            "response_success", "Truy vấn thành công: {value}"
                        )
                        response = response_success.replace("{value}", str(value))

                        return ActionResponse(
                            action=Action.RESPONSE,
                            response=response,
                        )
                    else:
                        response_failure = arguments.get(
                            "response_failure",
                            f"Không đọc được trạng thái của {device_name}",
                        )
                        return ActionResponse(
                            action=Action.ERROR, response=response_failure
                        )
            else:
                # Hoạt động điều khiển: devicename_method
                parts = tool_name.split("_", 1)
                if len(parts) >= 2:
                    device_name = parts[0]
                    method_name = parts[1]

                    # Trích xuất các tham số điều khiển (loại trừ các tham số phản hồi)
                    control_params = {
                        k: v
                        for k, v in arguments.items()
                        if k not in ["response_success", "response_failure"]
                    }

                    # Gửi lệnh điều khiển IoT
                    await self._send_iot_command(
                        device_name, method_name, control_params
                    )

                    # Đang chờ cập nhật trạng thái
                    await asyncio.sleep(0.1)

                    response_success = arguments.get(
                        "response_success", "Thao tác thành công"
                    )

                    # Xử lý phần giữ chỗ trong phản hồi
                    for param_name, param_value in control_params.items():
                        placeholder = "{" + param_name + "}"
                        if placeholder in response_success:
                            response_success = response_success.replace(
                                placeholder, str(param_value)
                            )
                        if "{value}" in response_success:
                            response_success = response_success.replace(
                                "{value}", str(param_value)
                            )
                            break

                    return ActionResponse(
                        action=Action.REQLLM,
                        result=response_success,
                    )

            return ActionResponse(
                action=Action.ERROR, response="Không phân tích được tên công cụ IoT"
            )

        except Exception as e:
            response_failure = arguments.get("response_failure", "Thao tác thất bại")
            return ActionResponse(action=Action.ERROR, response=response_failure)

    async def _get_iot_status(self, device_name: str, property_name: str):
        """lấyIoTthiết bịtrạng thái"""
        for key, value in self.conn.iot_descriptors.items():
            if key.lower() == device_name.lower():
                for property_item in value.properties:
                    if property_item["name"].lower() == property_name.lower():
                        return property_item["value"]
        return None

    async def _send_iot_command(
        self, device_name: str, method_name: str, parameters: Dict[str, Any]
    ):
        """发送IoT控制命令"""
        for key, value in self.conn.iot_descriptors.items():
            if key.lower() == device_name.lower():
                for method in value.methods:
                    if method["name"].lower() == method_name.lower():
                        command = {
                            "name": key,
                            "method": method["name"],
                        }

                        if parameters:
                            command["parameters"] = parameters

                        send_message = json.dumps(
                            {"type": "iot", "commands": [command]}
                        )
                        await self.conn.websocket.send(send_message)
                        return

        raise Exception(
            f"Không tìm thấy phương thức {method_name} của thiết bị {device_name}"
        )

    def register_iot_tools(self, descriptors: list):
        """注册IoTcông cụ"""
        for descriptor in descriptors:
            device_name = descriptor["name"]
            device_desc = descriptor["description"]

            # Công cụ truy vấn đăng ký
            if "properties" in descriptor:
                for prop_name, prop_info in descriptor["properties"].items():
                    tool_name = f"get_{device_name.lower()}_{prop_name.lower()}"

                    tool_desc = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": f"Truy vấn {prop_info['description']} của {device_desc}",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "response_success": {
                                        "type": "string",
                                        "description": f"Câu trả lời khi truy vấn thành công; phải dùng {{value}} làm chỗ giữ giá trị nhận được",
                                    },
                                    "response_failure": {
                                        "type": "string",
                                        "description": f"Câu trả lời khi truy vấn thất bại",
                                    },
                                },
                                "required": ["response_success", "response_failure"],
                            },
                        },
                    }

                    self.iot_tools[tool_name] = ToolDefinition(
                        name=tool_name,
                        description=tool_desc,
                        tool_type=ToolType.DEVICE_IOT,
                    )

            # Công cụ kiểm soát đăng ký
            if "methods" in descriptor:
                for method_name, method_info in descriptor["methods"].items():
                    tool_name = f"{device_name.lower()}_{method_name.lower()}"

                    # Xây dựng thông số
                    parameters = {}
                    required_params = []

                    # Thêm các tham số ban đầu của phương thức
                    if "parameters" in method_info:
                        parameters.update(
                            {
                                param_name: {
                                    "type": param_info["type"],
                                    "description": param_info["description"],
                                }
                                for param_name, param_info in method_info[
                                    "parameters"
                                ].items()
                            }
                        )
                        required_params.extend(method_info["parameters"].keys())

                    # Thêm tham số phản hồi
                    parameters.update(
                        {
                            "response_success": {
                                "type": "string",
                                "description": "Câu trả lời thân thiện khi thao tác thành công",
                            },
                            "response_failure": {
                                "type": "string",
                                "description": "Câu trả lời thân thiện khi thao tác thất bại",
                            },
                        }
                    )
                    required_params.extend(["response_success", "response_failure"])

                    tool_desc = {
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "description": f"{device_desc} - {method_info['description']}",
                            "parameters": {
                                "type": "object",
                                "properties": parameters,
                                "required": required_params,
                            },
                        },
                    }

                    self.iot_tools[tool_name] = ToolDefinition(
                        name=tool_name,
                        description=tool_desc,
                        tool_type=ToolType.DEVICE_IOT,
                    )

    def get_tools(self) -> Dict[str, ToolDefinition]:
        """lấy所有thiết bị端IoTcông cụ"""
        return self.iot_tools.copy()

    def has_tool(self, tool_name: str) -> bool:
        """kiểm tra是否有指定的thiết bị端IoTcông cụ"""
        return tool_name in self.iot_tools
