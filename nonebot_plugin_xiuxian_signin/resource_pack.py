"""外部资源包：秘境背景图不进 wheel（R-09）。

``assets/`` 原始体积 265 MB，其中 ``mystic_maps/backgrounds`` 独占 202 MB——
超过 PyPI 单文件 100 MB 上限，等于装不上。这批背景图在阶段 6 会随秘境推倒
重做、按 Q9 裁切复用，因此只外置它们，其余资源（图标/立绘/字体/后台 SPA）
留在 wheel 里，离线部署改动最小。

三条获取路径，优先级从高到低：

1. ``data_dir/assets/mystic_maps/`` 里已有文件（自动下载或手工放置）；
2. 包内 ``assets/mystic_maps/``（开发环境直接从仓库读，无需下载）；
3. 都没有 → 渲染器用程序化占位背景（``allow_placeholder_background``），
   地图照样能出图，只是没有美术底图。

下载校验用 manifest 里逐图的 sha256：不依赖预先发布整包摘要，且能定位到具体
哪张图坏了；任一图校验失败就整包不落地，避免半截文件把出图变成花屏。
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import zipfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nonebot import logger

PACK_NAME = "mystic_maps"

# 资源包默认地址：仓库不托管大文件，Release 流程会同时产出 mystic_maps.zip。
# 用 latest 是为了跟随版本自动更新；国内网络可用 xiuxian_signin_asset_url
# 指向自建镜像，或直接给一个本地 zip 路径（离线部署）。
DEFAULT_PACK_URL = (
    "https://github.com/hszxjs/nonebot-plugin-xiuxian-signin/releases/latest/download/mystic_maps.zip"
)

# 下载进度日志的间隔（百分比），避免 200 MB 刷屏。
_PROGRESS_STEP = 20

# 由 configure() 设定的数据目录；为空时只用包内资源。
_data_dir: Path | None = None


def configure(data_dir: str | Path | None) -> None:
    """登记数据目录，供 :func:`resolve_background` 优先查找外置资源。"""
    global _data_dir
    _data_dir = Path(data_dir) if data_dir is not None else None


def package_maps_dir() -> Path:
    return Path(__file__).resolve().parent / "assets" / PACK_NAME


def external_maps_dir(data_dir: str | Path | None = None) -> Path:
    root = Path(data_dir) if data_dir is not None else _data_dir
    if root is None:
        return package_maps_dir()
    return root / "assets" / PACK_NAME


def load_manifest(path: Path | None = None) -> dict[str, Any]:
    """读取包内 manifest（主题 → 背景相对路径 + sha256）。"""
    manifest_path = path or (package_maps_dir() / "manifest.json")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"读取秘境资源清单失败：{manifest_path} {exc}")
        return {}
    return data if isinstance(data, dict) else {}


def expected_files(manifest: dict[str, Any]) -> dict[str, str]:
    """返回 {相对路径: sha256}，只包含带摘要的条目。"""
    themes = manifest.get("themes") if isinstance(manifest, dict) else None
    if not isinstance(themes, dict):
        return {}
    files: dict[str, str] = {}
    for theme in themes.values():
        if not isinstance(theme, dict):
            continue
        relative = str(theme.get("background") or "")
        digest = str(theme.get("sha256") or "").lower()
        if relative and len(digest) == 64:
            files[relative] = digest
    return files


@dataclass(frozen=True)
class PackStatus:
    expected: int
    present: int
    source: str

    @property
    def complete(self) -> bool:
        return self.expected > 0 and self.present == self.expected

    def summary(self) -> str:
        return f"{self.present}/{self.expected} 张背景（来源：{self.source}）"


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pack_status(data_dir: str | Path | None = None, manifest: dict[str, Any] | None = None) -> PackStatus:
    files = expected_files(manifest if manifest is not None else load_manifest())
    if not files:
        return PackStatus(expected=0, present=0, source="清单不可用")

    external = external_maps_dir(data_dir)
    present_external = sum(1 for relative in files if (external / relative).is_file())
    if present_external == len(files):
        return PackStatus(len(files), present_external, "外置资源包")

    package = package_maps_dir()
    present_package = sum(1 for relative in files if (package / relative).is_file())
    if present_package == len(files):
        return PackStatus(len(files), present_package, "包内资源")
    if present_external:
        return PackStatus(len(files), present_external, "外置资源包（不完整）")
    if present_package:
        return PackStatus(len(files), present_package, "包内资源（不完整）")
    return PackStatus(len(files), 0, "未安装（使用占位背景）")


def resolve_background(package_path: Path, relative: str) -> Path:
    """背景图定位：外置优先，其次包内，都没有就返回包内路径交给渲染器降级。"""
    if relative:
        external = external_maps_dir() / relative
        if external.is_file():
            return external
    return package_path


class PackError(RuntimeError):
    """资源包下载/校验失败。"""


async def ensure_pack(
    *,
    data_dir: str | Path,
    url: str | None = None,
    manifest: dict[str, Any] | None = None,
    timeout: float = 1800.0,
    progress: Callable[[str], None] | None = None,
) -> bool:
    """确保数据目录里有完整的背景图集合。

    返回 ``True`` 表示可用（原本就有或下载成功）。任何失败都只告警、返回
    ``False``——背景图缺失不影响机器人启动，出图会降级为占位背景。
    """
    manifest = manifest if manifest is not None else load_manifest()
    files = expected_files(manifest)
    if not files:
        logger.warning("秘境资源清单为空或不可用，跳过资源包准备")
        return False

    target = external_maps_dir(data_dir)
    missing = [relative for relative in files if not (target / relative).is_file()]
    if not missing:
        configure(data_dir)
        return True

    source = url or DEFAULT_PACK_URL
    notify = progress or logger.info
    notify(f"秘境背景图缺失 {len(missing)} 张，开始从 {source} 获取")

    staging_root = Path(tempfile.mkdtemp(prefix="xiuxian-assets-"))
    try:
        archive = await _fetch(source, staging_root, timeout=timeout, notify=notify)
        extracted = _extract(archive, staging_root / "unpacked")
        problems = _verify(extracted, files)
        if problems:
            raise PackError("；".join(problems[:3]))
        _install(extracted, target, files)
        configure(data_dir)
        notify(f"秘境资源包就绪：{len(files)} 张背景已安装到 {target}")
        return True
    except Exception as exc:  # noqa: BLE001 - 任何失败都只降级，不影响启动
        logger.warning(f"秘境资源包准备失败，将使用占位背景：{exc}")
        logger.warning(f"可手动下载 {source} 解压到 {target} 后重启，或改用 xiuxian_signin_asset_url 指向镜像")
        return False
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


async def _fetch(source: str, workdir: Path, *, timeout: float, notify: Callable[[str], None]) -> Path:
    """把资源包取到本地：支持 http(s) 与本地路径（离线/内网镜像）。"""
    text = source.removeprefix("file://")
    has_scheme = "://" in source
    local_candidate = Path(text)
    if not has_scheme:
        # 没有协议头一律按本地路径处理：写错时给出的提示要指向具体文件，
        # 而不是 httpx 那句「缺少 http:// 协议」。
        if not local_candidate.is_file():
            raise PackError(f"本地资源包不存在：{local_candidate}")
        notify(f"从本地文件读取资源包：{local_candidate}")
        return local_candidate

    import httpx

    destination = workdir / f"{PACK_NAME}.zip"
    async with (
        httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client,
        client.stream("GET", source) as response,
    ):
        response.raise_for_status()
        total = int(response.headers.get("content-length") or 0)
        downloaded = 0
        next_mark = _PROGRESS_STEP
        with destination.open("wb") as handle:
            async for chunk in response.aiter_bytes(1024 * 512):
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = downloaded * 100 // total
                    if percent >= next_mark:
                        notify(f"资源包下载中 {percent}%（{downloaded // (1024 * 1024)} MB）")
                        next_mark = percent + _PROGRESS_STEP
    return destination

def _extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(destination)
    except (zipfile.BadZipFile, OSError) as exc:
        raise PackError(f"资源包损坏：{exc}") from exc
    return destination


def _candidate_paths(root: Path) -> Iterable[Path]:
    """资源包可能多套一层目录，这里找出 backgrounds 所在层。"""
    if (root / "backgrounds").is_dir():
        yield root
    for child in sorted(root.iterdir()) if root.is_dir() else []:
        if child.is_dir() and (child / "backgrounds").is_dir():
            yield child


def _verify(root: Path, files: dict[str, str]) -> list[str]:
    base = next(iter(_candidate_paths(root)), None)
    if base is None:
        return ["资源包里找不到 backgrounds 目录"]
    problems: list[str] = []
    for relative, digest in files.items():
        path = base / relative
        if not path.is_file():
            problems.append(f"缺少 {relative}")
            continue
        if file_digest(path) != digest:
            problems.append(f"{relative} 校验失败")
    return problems


def _install(root: Path, target: Path, files: dict[str, str]) -> None:
    base = next(iter(_candidate_paths(root)), None)
    if base is None:
        raise PackError("资源包里找不到 backgrounds 目录")
    for relative in files:
        source = base / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # 先复制到同目录临时名再原子替换：下载中断不会留下半截图。
        temporary = destination.with_name(destination.name + ".part")
        shutil.copyfile(source, temporary)
        temporary.replace(destination)
