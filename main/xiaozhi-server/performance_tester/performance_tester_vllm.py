import time
import asyncio
import logging
import statistics
import base64
from typing import Dict
from tabulate import tabulate
from core.utils.vllm import create_instance
from config.settings import load_config

# Đặt cấp độ nhật ký chung thành CẢNH BÁO và chặn nhật ký cấp độ THÔNG TIN
logging.basicConfig(level=logging.WARNING)

description = "视觉识别模型性能测试"


class AsyncVisionPerformanceTester:
    def __init__(self, config):
        self.config = config

        self.test_images = [
            "../../docs/images/demo1.png",
            "../../docs/images/demo2.png",
        ]
        self.test_questions = [
            "这张图片里有什么？",
            "请详细描述这张图片的nội dung",
        ]

        # Tải hình ảnh thử nghiệm
        self.results = {"vllm": {}}

    async def _test_vllm(self, vllm_name: str, config: Dict) -> Dict:
        """异步测试单个视觉大模型性能"""
        try:
            # Kiểm tra cấu hình khóa API
            if "api_key" in config and any(
                x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]
            ):
                print(f"⏭️  VLLM {vllm_name} 未cấu hìnhapi_key , đãbỏ qua")
                return {"name": vllm_name, "type": "vllm", "errors": 1}

            # Lấy loại thực tế (tương thích với cấu hình cũ)
            module_type = config.get("type", vllm_name)
            vllm = create_instance(module_type, config)

            print(f"🖼️ 测试 VLLM: {vllm_name}")

            # Tạo tất cả các nhiệm vụ kiểm tra
            test_tasks = []
            for question in self.test_questions:
                for image in self.test_images:
                    test_tasks.append(
                        self._test_single_vision(vllm_name, vllm, question, image)
                    )

            # Thực hiện đồng thời tất cả các thử nghiệm
            test_results = await asyncio.gather(*test_tasks)

            # Xử lý kết quả
            valid_results = [r for r in test_results if r is not None]
            if not valid_results:
                print(f"⚠️  {vllm_name} 无有效dữ liệu , 可能cấu hìnhLỗi")
                return {"name": vllm_name, "type": "vllm", "errors": 1}

            response_times = [r["response_time"] for r in valid_results]

            # Lọc dữ liệu bất thường
            mean = statistics.mean(response_times)
            stdev = statistics.stdev(response_times) if len(response_times) > 1 else 0
            filtered_times = [t for t in response_times if t <= mean + 3 * stdev]

            if len(filtered_times) < len(test_tasks) * 0.5:
                print(f"⚠️  {vllm_name} 有效dữ liệu不足 , 可能网络不稳定")
                return {"name": vllm_name, "type": "vllm", "errors": 1}

            return {
                "name": vllm_name,
                "type": "vllm",
                "avg_response": sum(response_times) / len(response_times),
                "std_response": (
                    statistics.stdev(response_times) if len(response_times) > 1 else 0
                ),
                "errors": 0,
            }

        except Exception as e:
            print(f"⚠️ VLLM {vllm_name} 测试thất bại: {str(e)}")
            return {"name": vllm_name, "type": "vllm", "errors": 1}

    async def _test_single_vision(
        self, vllm_name: str, vllm, question: str, image: str
    ) -> Dict:
        """测试单个视觉问题的性能"""
        try:
            print(f"📝 {vllm_name} 开始测试: {question[:20]}...")
            start_time = time.time()

            # Đọc hình ảnh và chuyển đổi sang base64
            with open(image, "rb") as image_file:
                image_data = image_file.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")

            # Nhận phản hồi trực tiếp
            response = vllm.response(question, image_base64)
            response_time = time.time() - start_time
            print(f"✓ {vllm_name} hoàn tấtphản hồi: {response_time:.3f}s")

            return {
                "name": vllm_name,
                "type": "vllm",
                "response_time": response_time,
            }
        except Exception as e:
            print(f"⚠️ {vllm_name} 测试thất bại: {str(e)}")
            return None

    def _print_results(self):
        """打印测试kết quả"""
        vllm_table = []
        for name, data in self.results["vllm"].items():
            if data["errors"] == 0:
                stability = data["std_response"] / data["avg_response"]
                vllm_table.append(
                    [
                        name,
                        f"{data['avg_response']:.3f}秒",
                        f"{stability:.3f}",
                    ]
                )

        if vllm_table:
            print("\n视觉大模型性能排行:\n")
            print(
                tabulate(
                    vllm_table,
                    headers=["模型名称", "phản hồi耗khi", "稳定性"],
                    tablefmt="github",
                    colalign=("left", "right", "right"),
                    disable_numparse=True,
                )
            )
        else:
            print("\n⚠️ 没有可用的视觉大模型进行测试。")

    async def run(self):
        """执行全量异步测试"""
        print("🔍 开始筛选可用视觉大模型...")

        if not self.test_images:
            print(f"\n⚠️  {self.image_root} 路径下没有图片文件 , không thểtiến hành测试")
            return

        # Tạo tất cả các nhiệm vụ kiểm tra
        all_tasks = []

        # Nhiệm vụ kiểm tra VLLM
        if self.config.get("VLLM") is not None:
            for vllm_name, config in self.config.get("VLLM", {}).items():
                if "api_key" in config and any(
                    x in config["api_key"] for x in ["你的", "placeholder", "sk-xxx"]
                ):
                    print(f"⏭️  VLLM {vllm_name} 未cấu hìnhapi_key , đãbỏ qua")
                    continue
                print(f"🖼️ 添加VLLM测试tác vụ: {vllm_name}")
                all_tasks.append(self._test_vllm(vllm_name, config))

        print(f"\n✅ 找到 {len(all_tasks)} 个可用视觉大模型")
        print(f"✅ 使用 {len(self.test_images)} 张测试图片")
        print(f"✅ 使用 {len(self.test_questions)} 个测试问题")
        print("\n⏳ 开始并发测试所有模型...\n")

        # Thực hiện đồng thời tất cả các nhiệm vụ kiểm tra
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Xử lý kết quả
        for result in all_results:
            if isinstance(result, dict) and result["errors"] == 0:
                self.results["vllm"][result["name"]] = result

        # In kết quả
        print("\n📊 生成测试报告...")
        self._print_results()


async def main():
    config = await load_config()
    tester = AsyncVisionPerformanceTester(config)
    await tester.run()


if __name__ == "__main__":
    asyncio.run(main())
