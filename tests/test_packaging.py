"""打包契约（R-19）：wheel 里到底带了什么。

发布是硬门禁（D2=是），而打包问题不会在任何单元测试里暴露：

1. 新增资源忘登记 ``package-data`` → 本地开发有图、用户装完没图；
2. 秘境背景图（约 202 MB）被 ``include-package-data`` 顺带塞进 wheel → 超过 PyPI 单文件
   100 MB 上限，发布直接失败；
3. ``fastapi`` 被误加回核心依赖 → 只想跑机器人、不开后台的用户被迫装一整条 HTTP 栈。

本文件用静态比对代替真的构建 wheel（构建要几十秒且依赖本地 setuptools 行为），
把「清单与磁盘实际文件是否一致」这件事变成一次秒级断言。
"""
from __future__ import annotations

import pathlib
import tomllib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "nonebot_plugin_xiuxian_signin"
PYPROJECT = ROOT / "pyproject.toml"

ASSET_SUFFIXES = {".png", ".json", ".ttf", ".txt", ".html", ".js", ".css", ".svg", ".webp"}
# PyPI 单文件上限 100 MB，留 5 MB 余量。
MAX_SINGLE_FILE_BYTES = 95 * 1024 * 1024


@pytest.fixture(scope="module")
def project() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _package_data(project: dict) -> list[str]:
    return project["tool"]["setuptools"]["package-data"]["nonebot_plugin_xiuxian_signin"]


def _excluded(project: dict) -> list[str]:
    return (
        project["tool"]["setuptools"]
        .get("exclude-package-data", {})
        .get("nonebot_plugin_xiuxian_signin", [])
    )


def _matches(relative: str, patterns: list[str]) -> bool:
    return any(pathlib.PurePath(relative).match(pattern) for pattern in patterns)


def _shipped_assets() -> list[pathlib.Path]:
    return [
        path
        for path in PACKAGE_DIR.rglob("*")
        if path.is_file() and (path.suffix in ASSET_SUFFIXES or "admin_web" in path.parts)
    ]


def test_every_runtime_asset_is_declared_in_package_data(project: dict) -> None:
    """磁盘上每个运行期资源都必须被 package-data 或 exclude 命中。"""
    patterns = _package_data(project)
    excluded = _excluded(project)
    undeclared: list[str] = []
    for path in _shipped_assets():
        relative = path.relative_to(PACKAGE_DIR).as_posix()
        if _matches(relative, excluded):
            continue
        if not _matches(relative, patterns):
            undeclared.append(relative)
    assert not undeclared, (
        "这些资源既没有被 package-data 收进 wheel，也没有被显式排除，"
        f"用户装完会缺文件：{sorted(undeclared)[:20]}（共 {len(undeclared)} 个）"
    )


def test_mystic_backgrounds_are_excluded(project: dict) -> None:
    """202 MB 背景图必须走 Release 资源包，不能进 wheel。"""
    excluded = _excluded(project)
    assert any("backgrounds" in pattern for pattern in excluded), (
        "exclude-package-data 必须排除 assets/mystic_maps/backgrounds，否则 wheel 会超 PyPI 限制"
    )
    backgrounds = list((PACKAGE_DIR / "assets" / "mystic_maps" / "backgrounds").glob("*"))
    if backgrounds:
        assert all(_matches(f"assets/mystic_maps/backgrounds/{p.name}", excluded) for p in backgrounds)


def test_no_single_file_exceeds_pypi_limit() -> None:
    oversized = [
        (path.relative_to(PACKAGE_DIR).as_posix(), path.stat().st_size)
        for path in PACKAGE_DIR.rglob("*")
        if path.is_file() and path.stat().st_size > MAX_SINGLE_FILE_BYTES
    ]
    assert not oversized, f"单文件超过 95 MB，无法发布到 PyPI：{oversized}"


def test_http_stack_is_not_a_core_dependency(project: dict) -> None:
    """fastapi/starlette/uvicorn 只能在 admin extra 里（R-23）。"""
    core = [dep.lower() for dep in project["project"]["dependencies"]]
    for name in ("fastapi", "starlette", "uvicorn"):
        assert not any(dep.startswith(name) for dep in core), f"{name} 不应出现在核心依赖"

    extras = project["project"]["optional-dependencies"]
    admin = " ".join(extras.get("admin", [])).lower()
    for name in ("fastapi", "starlette", "uvicorn"):
        assert name in admin, f"{name} 必须出现在 admin extra，否则后台无法安装"
    dev = " ".join(extras.get("dev", [])).lower()
    assert "fastapi" in dev, "测试直接打后台路由，dev extra 必须带 fastapi"


def test_pydantic_floor_is_v2(project: dict) -> None:
    """config_schema 用 v2 API，装 v1 会在导入期直接崩。"""
    core = [dep.lower().replace(" ", "") for dep in project["project"]["dependencies"]]
    pydantic_deps = [dep for dep in core if dep.startswith("pydantic")]
    assert pydantic_deps, "核心依赖必须声明 pydantic"
    assert any(">=2" in dep for dep in pydantic_deps), f"pydantic 下限必须是 2.0：{pydantic_deps}"


def test_package_marker_file_exists() -> None:
    """py.typed 缺失会让下游类型检查直接放弃本包。"""
    assert (PACKAGE_DIR / "py.typed").is_file()
    assert "py.typed" in _package_data(tomllib.loads(PYPROJECT.read_text(encoding="utf-8")))
