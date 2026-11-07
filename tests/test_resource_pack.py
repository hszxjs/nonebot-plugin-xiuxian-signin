"""R-09：秘境背景图外置包（下载、校验、定位、降级）。

核心约束是「坏包不能落地」：校验失败必须整包丢弃，否则半截文件会让出图花屏，
而且玩家看不出是资源问题还是渲染 bug。
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from nonebot_plugin_xiuxian_signin import resource_pack


@pytest.fixture(autouse=True)
def _reset_configure():
    yield
    resource_pack.configure(None)


def _write_png(path: Path, color: tuple[int, int, int]) -> str:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), color).save(path, format="PNG")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_bundle(tmp: Path, *, corrupt: bool = False, nested: bool = False) -> tuple[Path, dict]:
    source = tmp / "source"
    first = _write_png(source / "backgrounds" / "alpha.png", (10, 20, 30))
    second = _write_png(source / "backgrounds" / "beta.png", (40, 50, 60))
    manifest = {
        "schema_version": 1,
        "themes": {
            "alpha": {"background": "backgrounds/alpha.png", "sha256": first},
            "beta": {"background": "backgrounds/beta.png", "sha256": second},
        },
    }
    archive = tmp / "mystic_maps.zip"
    prefix = "mystic_maps/" if nested else ""
    with zipfile.ZipFile(archive, "w") as bundle:
        for name in ("alpha.png", "beta.png"):
            bundle.write(source / "backgrounds" / name, arcname=f"{prefix}backgrounds/{name}")
        bundle.write(source / "backgrounds" / "alpha.png", arcname=f"{prefix}backgrounds/alpha.png.copy")
    if corrupt:
        # 覆盖其中一个文件，使 sha256 与 manifest 不符。
        with zipfile.ZipFile(archive, "a") as bundle:
            bundle.writestr(f"{prefix}backgrounds/beta.png", b"not a real png")
    return archive, manifest


def test_ensure_pack_installs_and_configures(tmp_path: Path) -> None:
    archive, manifest = _build_bundle(tmp_path)
    data_dir = tmp_path / "data"

    ok = __import__("asyncio").run(
        resource_pack.ensure_pack(data_dir=data_dir, url=str(archive), manifest=manifest)
    )

    assert ok is True
    target = data_dir / "assets" / "mystic_maps"
    assert (target / "backgrounds" / "alpha.png").is_file()
    assert (target / "backgrounds" / "beta.png").is_file()
    # 安装完成后应把外置目录登记给渲染层。
    assert resource_pack.external_maps_dir() == target
    status = resource_pack.pack_status(data_dir, manifest)
    assert status.complete and status.source == "外置资源包"


def test_ensure_pack_accepts_nested_directory(tmp_path: Path) -> None:
    archive, manifest = _build_bundle(tmp_path, nested=True)
    data_dir = tmp_path / "data"

    ok = __import__("asyncio").run(
        resource_pack.ensure_pack(data_dir=data_dir, url=str(archive), manifest=manifest)
    )

    assert ok is True
    assert (data_dir / "assets" / "mystic_maps" / "backgrounds" / "alpha.png").is_file()


def test_corrupt_pack_is_rejected_entirely(tmp_path: Path) -> None:
    archive, manifest = _build_bundle(tmp_path, corrupt=True)
    data_dir = tmp_path / "data"

    ok = __import__("asyncio").run(
        resource_pack.ensure_pack(data_dir=data_dir, url=str(archive), manifest=manifest)
    )

    assert ok is False
    # 一张图坏了就整包不落地：宁可继续用占位背景，也不要半套真图。
    assert not (data_dir / "assets" / "mystic_maps" / "backgrounds" / "alpha.png").exists()


def test_missing_source_only_warns(tmp_path: Path) -> None:
    _, manifest = _build_bundle(tmp_path)
    ok = __import__("asyncio").run(
        resource_pack.ensure_pack(
            data_dir=tmp_path / "data", url=str(tmp_path / "nope.zip"), manifest=manifest
        )
    )
    assert ok is False


def test_resolve_background_prefers_external(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    external = data_dir / "assets" / "mystic_maps" / "backgrounds" / "alpha.png"
    external.parent.mkdir(parents=True)
    external.write_bytes(b"external")
    package = tmp_path / "pkg" / "backgrounds" / "alpha.png"
    package.parent.mkdir(parents=True)
    package.write_bytes(b"package")

    resource_pack.configure(data_dir)
    assert resource_pack.resolve_background(package, "backgrounds/alpha.png") == external

    # 外置缺失时回落到包内路径（交给渲染器的占位降级）。
    resource_pack.configure(None)
    assert resource_pack.resolve_background(package, "backgrounds/alpha.png") == package


def test_manifest_digests_cover_all_backgrounds() -> None:
    """仓库里的 manifest 必须覆盖全部背景图，否则下载包会漏图。"""
    manifest = resource_pack.load_manifest()
    files = resource_pack.expected_files(manifest)
    assert files, "manifest 里没有可用的 sha256 条目"

    package = resource_pack.package_maps_dir()
    on_disk = {path.relative_to(package).as_posix() for path in (package / "backgrounds").glob("*.png")}
    assert on_disk == set(files), "manifest 与实际背景图不一致（新增/删除主题后忘了更新 sha256？）"


def test_catalog_builds_when_backgrounds_are_absent(tmp_path: Path) -> None:
    """wheel 里没有背景图时插件必须能正常加载（R-09 的核心前提）。

    原先 ``_validate_background_hashes`` 读不到文件就抛 ValueError，导致一旦
    把背景图移出 wheel，插件导入即失败、机器人根本起不来。
    """
    from nonebot_plugin_xiuxian_signin.mystic_dungeon import MysticTemplateCatalog

    package = resource_pack.package_maps_dir()
    manifest_path = tmp_path / "manifest.json"
    templates_path = tmp_path / "templates.json"
    manifest_path.write_text((package / "manifest.json").read_text(encoding="utf-8"), encoding="utf-8")
    templates_path.write_text((package / "templates.json").read_text(encoding="utf-8"), encoding="utf-8")
    # 不复制 backgrounds 目录，模拟 wheel 安装后的状态。
    catalog = MysticTemplateCatalog.from_files(manifest_path, templates_path)

    assert catalog.themes
    assert all(not theme.background_path.is_file() for theme in catalog.themes.values())


def test_manifest_json_is_packaged_but_backgrounds_are_not() -> None:
    """wheel 里必须保留 manifest/templates，且不含背景图（R-09 的封装契约）。"""
    import tomllib

    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    patterns = pyproject["tool"]["setuptools"]["package-data"]["nonebot_plugin_xiuxian_signin"]

    assert "assets/mystic_maps/manifest.json" in patterns
    assert "assets/mystic_maps/templates.json" in patterns
    assert not any("mystic_maps/backgrounds" in pattern for pattern in patterns)
    assert json.loads((resource_pack.package_maps_dir() / "manifest.json").read_text(encoding="utf-8"))
