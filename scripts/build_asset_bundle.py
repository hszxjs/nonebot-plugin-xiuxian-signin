"""把秘境背景图打成资源包 zip（R-09）。

背景图 202 MB，超过 PyPI 单文件 100 MB 上限，因此不进 wheel：构建时用本脚本
生成 ``mystic_maps.zip`` 挂到 GitHub Release，插件首次启动按需下载。

包内布局保持 ``backgrounds/<名称>.png``，解压到
``<data_dir>/assets/mystic_maps/`` 即可被 :mod:`resource_pack` 直接命中。

用法::

    python scripts/build_asset_bundle.py --output dist/mystic_maps.zip

可选 ``--verify-only``：只按 manifest 校验仓库里现有的图，不产出 zip
（发布前检查素材有没有被误改）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = REPO_ROOT / "nonebot_plugin_xiuxian_signin" / "assets" / "mystic_maps"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest() -> dict:
    return json.loads((ASSET_ROOT / "manifest.json").read_text(encoding="utf-8"))


def theme_backgrounds(manifest: dict) -> dict[str, str]:
    themes = manifest.get("themes") or {}
    return {
        str(theme["background"]): str(theme.get("sha256") or "").lower()
        for theme in themes.values()
        if isinstance(theme, dict) and theme.get("background")
    }


def verify(manifest: dict) -> list[str]:
    problems: list[str] = []
    for relative, expected in theme_backgrounds(manifest).items():
        path = ASSET_ROOT / relative
        if not path.is_file():
            problems.append(f"缺少 {relative}")
        elif expected and sha256_of(path) != expected:
            problems.append(f"{relative} 与 manifest 里的 sha256 不一致")
    return problems


def build(output: Path, manifest: dict) -> int:
    backgrounds = theme_backgrounds(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as bundle:
        # 背景图已是 PNG，再压缩几乎没有收益，用 STORED 换取更快的解包。
        for relative in backgrounds:
            bundle.write(ASSET_ROOT / relative, arcname=relative)
        bundle.write(ASSET_ROOT / "manifest.json", arcname="manifest.json")
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"已生成 {output}（{len(backgrounds)} 张背景，{size_mb:.1f} MB）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="构建秘境背景图资源包")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dist" / "mystic_maps.zip")
    parser.add_argument("--verify-only", action="store_true", help="只校验素材完整性")
    args = parser.parse_args()

    manifest = load_manifest()
    problems = verify(manifest)
    if problems:
        print("素材校验失败：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    if args.verify_only:
        print(f"素材校验通过：{len(theme_backgrounds(manifest))} 张背景与 manifest 一致")
        return 0
    return build(args.output, manifest)


if __name__ == "__main__":
    raise SystemExit(main())
