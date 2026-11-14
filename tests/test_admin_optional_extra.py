"""后台 HTTP 层可选依赖的降级契约（R-23）。

`fastapi` / `starlette` / `uvicorn` 只服务于后台 Web 界面（`/xiuxian-admin`），
已被移出核心依赖、放进 `admin` extra。没装 extra 的部署必须满足：

1. 插件本体照常导入、照常初始化（命令、渲染、存储都不受影响）；
2. `AdminManager` 仍可用（配置读写/审计/备份不依赖 HTTP 层）；
3. 只有 `create_admin_app` / `install_admin_routes` / `start_admin_server` 报错，
   且报错信息直接告诉用户该装什么。

用子进程验证，避免把「屏蔽 fastapi」的 import hook 留在当前进程里污染其它测试。
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_plugin_imports_without_admin_http_dependencies() -> None:
    code = textwrap.dedent(
        """
        import sys, importlib.abc

        BLOCKED = ("fastapi", "uvicorn", "starlette")


        class _Blocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".")[0] in BLOCKED:
                    raise ModuleNotFoundError(f"blocked {fullname}")
                return None


        sys.meta_path.insert(0, _Blocker())

        import nonebot
        nonebot.init(driver="~httpx")  # 非 fastapi driver：证明核心不依赖 fastapi

        from nonebot_plugin_xiuxian_signin import domain  # noqa: F401  领域层可用
        from nonebot_plugin_xiuxian_signin import admin

        assert admin.ADMIN_HTTP_AVAILABLE is False
        assert "[admin]" in admin.ADMIN_HTTP_MISSING_HINT
        assert admin.AdminManager is not None  # 管理器的非 HTTP 能力仍在
        try:
            admin.create_admin_app(manager=None)
        except RuntimeError as exc:
            assert "[admin]" in str(exc)
        else:
            raise AssertionError("缺 fastapi 时 create_admin_app 必须报错而不是静默返回")
        # start_admin_server 自身不查标志位，而是靠第一行就调用 create_admin_app 兜住。
        # 这里锁住该行为：顺序一旦被调换，用户会看到 AttributeError 而不是安装指引。
        try:
            admin.start_admin_server(manager=None)
        except RuntimeError as exc:
            assert "[admin]" in str(exc)
        except (AttributeError, TypeError) as exc:
            raise AssertionError(f"start_admin_server 应沿用安装指引，实际抛 {type(exc).__name__}: {exc}")
        else:
            raise AssertionError("缺 fastapi 时 start_admin_server 必须报错")
        print("OK")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "OK" in result.stdout
