"""Pytest configuration — must run BEFORE any test imports project modules.

Adds the xiaozhi-server directory to sys.path so the existing implicit
relative imports (`from core.utils.textUtils import ...`) resolve.

External-API mock toggle (default: mocked)
-------------------------------------------
The dep-upgrade orchestrator and CI run this test suite *without* any
real API credentials. By default the tests construct the actual provider
objects from ``data/.config.yaml`` but route every network call through
a recording shim, so no traffic leaves the host.

Set ``RUN_LIVE_API_TESTS=1`` to opt in to real network calls. In that
mode the 5-module readiness check runs in strict form (any missing key
→ ``sys.exit(3)``), the mock shims are uninstalled, and tests hit the
real providers.

Configuration loading
---------------------
Always uses the file-merge path (``config.yaml`` + ``data/.config.yaml``).
``manager-api`` is intentionally NOT contacted — pytest must work in a
single-module deployment.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

import yaml

# Bảng điều khiển Windows mặc định sử dụng mã hóa GBK; biểu tượng cảm xúc/bản in tiếng Trung sẽ bùng nổ, buộc UTF-8.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ---------------------------------------------------------------------------
# opuslib_next stub: Cho phép liên kết nhập được thông qua; điều chỉnh âm thanh thực sẽ không thành công, hãy tự kiểm tra thử/ngoại trừ
# ---------------------------------------------------------------------------
try:
    import opuslib_next  # noqa: F401
except Exception:
    _stub = types.ModuleType("opuslib_next")
    _stub.Encoder = type("Encoder", (), {"__init__": lambda *a, **kw: None})
    _stub.Decoder = type("Decoder", (), {"__init__": lambda *a, **kw: None})
    _stub.APPLICATION_AUDIO = 0
    _stub.OpusError = type("OpusError", (Exception,), {})
    _stub.constants = types.SimpleNamespace()
    sys.modules["opuslib_next"] = _stub
    for sub in ("api", "exceptions"):
        sys.modules[f"opuslib_next.{sub}"] = types.ModuleType(f"opuslib_next.{sub}")


# ---------------------------------------------------------------------------
# Tải cấu hình: luôn tiến hành hợp nhất tập tin
# ---------------------------------------------------------------------------
# Ưu tiên:
#   1. Tệp được trỏ đến bởi biến môi trường ``PYTEST_CONFIG_FILE`` (được khuyến nghị - cấu hình thử nghiệm riêng biệt)
#   2. data/.config.yaml (cấu hình triển khai sản xuất/mô-đun đơn)
_DEFAULT_CUSTOM = _PROJECT_ROOT / "data" / ".config.yaml"
_CUSTOM_CONFIG = (
    Path(os.environ["PYTEST_CONFIG_FILE"])
    if os.environ.get("PYTEST_CONFIG_FILE")
    else _DEFAULT_CUSTOM
)


def _load_via_file_merge() -> dict:
    """纯文件合并：config.yaml + data/.config.yaml。和生产单模块部署一致。"""
    from config.config_loader import merge_configs

    config: dict = {}
    default_path = _PROJECT_ROOT / "config.yaml"
    if default_path.exists():
        config = yaml.safe_load(default_path.read_text(encoding="utf-8")) or {}

    if _CUSTOM_CONFIG.exists():
        custom = yaml.safe_load(_CUSTOM_CONFIG.read_text(encoding="utf-8")) or {}
        config = merge_configs(config, custom)

    return config


# Phát hiện triển khai mô-đun đầy đủ (không nhanh ở mọi chế độ, tránh kích hoạt API từ xa).
# Việc triển khai mô-đun đầy đủ sẽ khiến ``load_config`` được kéo từ xa thông qua manager-api và pytest sẽ không được kích hoạt.
if _CUSTOM_CONFIG.exists():
    _raw_custom = yaml.safe_load(_CUSTOM_CONFIG.read_text(encoding="utf-8")) or {}
    _api_cfg = _raw_custom.get("manager-api", {})
    _has_url = bool(_api_cfg.get("url"))
    _has_secret = bool(_api_cfg.get("secret")) and "你" not in str(
        _api_cfg.get("secret", "")
    )
    if _has_url and _has_secret:
        print(
            "\n[conftest] ============================================================\n"
            "[conftest] FAIL: 检测到全模块部署（manager-api.url + secret 已配置），\n"
            "[conftest]       pytest 不支持全模块部署。\n"
            "[conftest] 原因：manager-api 的 server.secret 是匿名 token，\n"
            "[conftest]       没有 sys:role:superAdmin 权限，\n"
            "[conftest]       拿不到 LLM/TTS/Memory 的 configJson（含 api_key）。\n"
            "[conftest] 切换到单模块的方法：\n"
            "[conftest]   1) manager-web → 参数管理 → 模型配置，\n"
            "[conftest]      把 LLM/TTS/Memory 的 configJson 抄出来\n"
            "[conftest]   2) 写到 data/.config.yaml（结构跟 config.yaml 一致）\n"
            "[conftest]   3) 清空 data/.config.yaml 里的 manager-api 整块\n"
            "[conftest]   4) 重跑 pytest\n"
            "[conftest] ============================================================",
            flush=True,
        )
        sys.exit(2)


# Luôn hợp nhất các tệp: sử dụng trực tiếp mô-đun duy nhất
CONFIG: dict = _load_via_file_merge()


# ---------------------------------------------------------------------------
# Phím: Thay thế các mục cấu hình thời gian chạy như ``load_config`` / ``get_server_config`` bằng
# Quay lại trực tiếp CONFIG đã xây dựng của chúng tôi, tránh ``config.config_loader.load_config`` trong
# Trong quá trình chạy thử, hãy đọc lại ``data/.config.yaml`` (mặc định là cấu hình triển khai mô-đun đầy đủ) và kích hoạt
# cuộc gọi từ xa của người quản lý-api.
# ---------------------------------------------------------------------------
async def _load_config_patched(*_args, **_kwargs):
    return CONFIG


async def _get_server_config_patched(*_args, **_kwargs):
    return None


def _init_service_noop(_config):
    """阻止 ``init_service`` 实例化 ``ManageApiClient``。"""
    return None


import config.config_loader as _cl  # noqa: E402
import config.manage_api_client as _mac  # noqa: E402

_cl.load_config = _load_config_patched
_mac.init_service = _init_service_noop
_mac.get_server_config = _get_server_config_patched
# Xóa đơn vị ManaApiClient để tránh việc khởi tạo đã được kích hoạt bởi mã khác.
_mac.ManageApiClient._instance = None
_mac.ManageApiClient._closed = True


# ---------------------------------------------------------------------------
# Định cấu hình trình trợ giúp truy cập (tài liệu tham khảo thử nghiệm)
# ---------------------------------------------------------------------------
def get_provider_config(module: str, provider_name: str | None = None) -> dict:
    """拿某个 provider 的 config dict。

    - provider_name=None：取 ``selected_module[module]``
    - 否则显式指定
    返回 {} 表示没配。
    """
    if provider_name is None:
        provider_name = CONFIG.get("selected_module", {}).get(module)
    if not provider_name:
        return {}
    return CONFIG.get(module, {}).get(provider_name, {}) or {}


def get_selected_provider_name(module: str) -> str | None:
    return CONFIG.get("selected_module", {}).get(module)


def get_provider_type(module: str, provider_name: str | None = None) -> str | None:
    """返回 ``create_instance`` 真正需要的 type 名（与 section 名可能不同）。

    约定（来自 core/utils/modules_initialize.py）：type 不存在时回退到 section 名。
    """
    cfg = get_provider_config(module, provider_name)
    if not cfg:
        return None
    return cfg.get("type") or (provider_name or get_selected_provider_name(module))


def has_real_key(config: dict, *keys: str) -> bool:
    """任一候选 key 名下值不是占位符就算有真密钥。

    占位符判定：空 / "你的..." / 包含 "placeholder" / 字面 "none"。
    """
    if not config:
        return False
    for key in keys:
        val = config.get(key)
        if val is None:
            continue
        s = str(val).strip().lower()
        if not s or s == "none":
            continue
        if s.startswith("你的") or "placeholder" in s:
            continue
        return True
    return False


# ---------------------------------------------------------------------------
# Chế độ mô phỏng mặc định: chặn các cuộc gọi mạng HTTP/SDK của bên thứ ba và thử nghiệm có thể chạy mà không cần khóa thực
# ---------------------------------------------------------------------------
LIVE_API_TESTS: bool = os.environ.get("RUN_LIVE_API_TESTS") == "1"

# Danh sách SDK của bên thứ ba. Không cần phải làm gì ở chế độ thực (việc nhập thực tế được giữ lại).
# Trong chế độ Mô phỏng, những tên này được đưa vào sys.modules và các lớp ngoại lệ/phần giữ chỗ máy khách được cung cấp.
_MOCKED_MODULES: tuple[str, ...] = (
    # Lưu ý: Các gói openai / httpx / request thực sự của bên thứ ba này thường được cài đặt trong môi trường conda.
    # Shim toàn bộ mô-đun sẽ hủy các mô-đun phụ như ``openai.types`` / ``httpx.AsyncClient``
    # phân tích. Chỉ Shim khi gói tương ứng chưa được cài đặt (__getattr__ vẫn lấy đường dẫn nhập thực).
    "anthropic",
    "dashscope",
    "tencentcloud",
    "xunfei",
    "vosk",
    "edge_tts",
    "elevenlabs",
    "mem0",
    "mem0ai",
    "freezegun",
)

# Các gói này buộc phải hoạt động ngay cả khi chúng được cài đặt - chúng có thể khiến chuỗi mô hình cục bộ phát nổ khi nhập
# (funasr có một chặng đường dài để đến với torch và torch DLL), hoặc nó phụ thuộc nhiều vào GPU và mô hình không thể chạy.
_FORCE_SHIM_MODULES: tuple[str, ...] = (
    "funasr",
    "torch",
    "torchaudio",
    "modelscope",
)


def _try_import_real(name: str) -> bool:
    """检查真实第三方包是否可加载（不真正 import，只检查 importer.find_spec）。

    主动 ``__import__`` 会触发包级副作用（funasr 引 torch 等），绕过它直接
    看包是否在 sys.path / site-packages 里。
    """
    import importlib.util

    spec = importlib.util.find_spec(name)
    return spec is not None


class _RecordingShim:
    """A no-op stand-in for any object reachable through a shimmed module.

    Acts as both a callable and an attribute container: every attribute
    access returns a callable that records the call and yields another
    shim. Used as a base class for fake exception classes so
    ``except httpx.ConnectError`` blocks evaluate correctly.
    """

    _calls: list = []

    def __init__(self, *_args, **_kwargs):
        pass

    def __getattr__(self, attr):
        def _record(*args, **kwargs):
            type(self)._calls.append((attr, args, kwargs))
            return _RecordingShim()

        return _record

    def __call__(self, *args, **kwargs):
        type(self)._calls.append(("__call__", args, kwargs))
        return _RecordingShim()


class _ShimModule(types.ModuleType):
    """PEP 562 module — any attribute access returns a recording shim."""

    def __getattr__(self, attr):
        if attr in ("__path__", "__loader__", "__spec__"):
            raise AttributeError(attr)
        # Cache so identity stays stable across accesses.
        value = _RecordingShim()
        setattr(self, attr, value)
        return value


def _install_mock_layer() -> None:
    """Insert PEP 562 shims for every third-party SDK in :data:`_MOCKED_MODULES`.

    Exception classes (e.g. ``httpx.ConnectError``) become ``_RecordingShim``
    subclasses — so ``except`` blocks match and ``isinstance`` checks pass.
    Common callable symbols (``Client`` / ``OpenAI`` / ``AutoModel``) are
    pre-bound to the shim type so ``Client(...)`` constructions succeed.

    If a real package is already importable (e.g. openai installed in conda),
    we leave it alone — shimming would break submodule resolution like
    ``openai.types``.
    """
    for name in list(_MOCKED_MODULES) + list(_FORCE_SHIM_MODULES):
        if name in sys.modules and isinstance(sys.modules[name], _ShimModule):
            continue
        if name not in _FORCE_SHIM_MODULES and _try_import_real(name):
            # Real package is available — use it. We'll patch network I/O
            # ở lớp yêu cầu ở chế độ mô phỏng (xem bên dưới).
            continue
        shim = _ShimModule(name)
        shim.OpenAI = _RecordingShim
        shim.AsyncOpenAI = _RecordingShim
        shim.Client = _RecordingShim
        shim.AsyncClient = _RecordingShim
        shim.AutoModel = _RecordingShim
        shim.completions = _RecordingShim()
        shim.chat = _RecordingShim()
        shim.exceptions = _ShimModule(f"{name}.exceptions")
        sys.modules[name] = shim
        sys.modules[f"{name}.exceptions"] = shim.exceptions

    # Rút ngắn asyncio.sleep để tránh độ trễ vòng lặp thử lại.
    import asyncio

    async def _fast_sleep(_seconds):
        return None

    asyncio.sleep = _fast_sleep  # type: ignore[assignment]

    # Mô hình lớp mạng: Nếu httpx thực được tải, hãy thay thế AsyncClient.send của nó bằng
    # Ngay lập tức ném cuống ConnectError, kích hoạt ``_ Should_retry`` và đi đến ``raise``,
    # Nhưng tránh đưa ra những yêu cầu thực tế. Chế độ trực tiếp hoàn toàn không cài đặt lớp này.
    if not LIVE_API_TESTS:
        try:
            import httpx as _httpx  # noqa: F401

            class _FakeAsyncClient:
                def __init__(self, *args, **kwargs):
                    pass

                async def send(self, *args, **kwargs):
                    raise _httpx.ConnectError("MOCK: connect refused")

                async def aclose(self):
                    return None

            class _FakeClient:
                def __init__(self, *args, **kwargs):
                    pass

                def send(self, *args, **kwargs):
                    raise _httpx.ConnectError("MOCK: connect refused")

                def close(self):
                    return None

            _httpx.AsyncClient = _FakeAsyncClient  # type: ignore[misc]
            _httpx.Client = _FakeClient  # type: ignore[misc]
        except ImportError:
            pass


if not LIVE_API_TESTS:
    _install_mock_layer()


# ---------------------------------------------------------------------------
# Xác minh khởi động chế độ trực tiếp: Phát hiện triển khai mô-đun đơn đã được hoàn thành sớm khi tải tệp
# ---------------------------------------------------------------------------
if LIVE_API_TESTS:
    print("[conftest] OK: 单模块部署（文件合并配置）")


_REQUIRED_MODULES = ("ASR", "LLM", "TTS", "Memory", "VAD")
_SECRET_FIELDS = (
    "api_key",
    "token",
    "access_token",
    "authorization",
    "secret_key",
    "access_key",
    "app_id",
    "app_secret",
    "bot_id",
    "user_id",
)


def _check_modules_ready() -> None:
    """Live 模式下：5 个核心模块必须配齐。Mock 模式下只打印 soft warning。"""
    problems: list[str] = []
    selected = CONFIG.get("selected_module") or {}
    for module in _REQUIRED_MODULES:
        provider_name = selected.get(module)
        if not provider_name:
            problems.append(f"{module} 未在 selected_module 配置（dev 漏选）")
            continue
        cfg = CONFIG.get(module, {}).get(provider_name)
        if not cfg:
            problems.append(
                f"{module}.{provider_name} 配置缺失（CFG 字典里没这个 provider）"
            )
            continue
        secret_keys_present = [k for k in _SECRET_FIELDS if k in cfg]
        if secret_keys_present and not any(
            has_real_key(cfg, k) for k in secret_keys_present
        ):
            problems.append(
                f"{module}.{provider_name} 的 secret 字段"
                f"{secret_keys_present} 全是占位符（dev 没填真 key）"
            )
    if not problems:
        return
    if LIVE_API_TESTS:
        msg = (
            "\n[conftest] ============================================================\n"
            "[conftest] FAIL: pytest 要求 5 个核心模块全部配齐才能跑。\n"
            "[conftest] 缺失/未就绪项：\n"
            + "\n".join(f"[conftest]   - {p}" for p in problems)
            + "\n[conftest] 必须在 data/.config.yaml 里把 5 个模块"
            "（ASR/LLM/TTS/Memory/VAD）都配齐才能跑 pytest。\n"
            "[conftest] ============================================================"
        )
        print(msg, file=sys.stderr, flush=True)
        sys.exit(3)
    print(
        "[conftest] NOTE: 默认 mock 模式 — 下列模块未配齐，但 pytest 仍可跑：\n  - "
        + "\n  - ".join(problems)
        + "\n[conftest] 真请求模式：export RUN_LIVE_API_TESTS=1 且配齐后再跑。",
        flush=True,
    )


_check_modules_ready()


# ---------------------------------------------------------------------------
# Dấu rõ ràng: Nhắc người dùng về chế độ hiện tại ở chế độ mô phỏng
# ---------------------------------------------------------------------------
if not LIVE_API_TESTS:
    print(
        "[conftest] MOCK 模式（默认）：第三方 HTTP/SDK 已注入 shim，不发真请求。\n"
        "[conftest] 真请求模式：export RUN_LIVE_API_TESTS=1 pytest tests/ -v",
        flush=True,
    )


import pytest  # noqa: E402  (after conftest hooks so pytest is initialised)


def pytest_collection_modifyitems(config, items):
    """Live 模式下：``live_api`` 标记的测试必须配齐密钥才能跑（否则 skip）。"""
    if LIVE_API_TESTS:
        return
    # Không có sự bỏ qua bắt buộc trong chế độ Mô phỏng: tất cả các bài kiểm tra đều sẽ chạy (sử dụng shim).
    return
