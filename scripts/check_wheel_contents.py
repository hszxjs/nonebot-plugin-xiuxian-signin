"""校验 wheel 内容（R-10）。

之所以单独校验而不是只看「构建成功」：``package-data`` 漏一条 glob，构建照样
成功、测试照样全绿，装到用户机器上才会发现资源缺失。R-08 就是这种情况
（``assets/mystic_events/*.json`` 与 ``assets/signin_calendar/*.png`` 都漏了）。

用法::

    python scripts/check_wheel_contents.py dist/*.whl [--max-size-mb 100]

体积超限默认只告警：``assets/`` 265 MB 超过 PyPI 单文件 100 MB 上限，需要
R-09（资源出 wheel）才能解决；在 R-09 完成前把它设成硬失败会卡住所有 PR。
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
import zipfile
from pathlib import Path

# (glob 模式, 最少命中数量, 说明)
REQUIRED: list[tuple[str, int, str]] = [
    ("nonebot_plugin_xiuxian_signin/assets/admin_web/index.html", 1, "后台 SPA 入口"),
    ("nonebot_plugin_xiuxian_signin/assets/admin_web/assets/*", 1, "后台静态资源"),
    ("nonebot_plugin_xiuxian_signin/assets/mystic_events/*.json", 1, "秘境事件表"),
    ("nonebot_plugin_xiuxian_signin/assets/signin_calendar/*.png", 1, "签到日历图"),
    ("nonebot_plugin_xiuxian_signin/assets/item_icons/*.png", 1, "物品图标"),
    ("nonebot_plugin_xiuxian_signin/config_schema.py", 1, "配置契约"),
    ("nonebot_plugin_xiuxian_signin/admin_auth.py", 1, "后台鉴权"),
    ("nonebot_plugin_xiuxian_signin/storage/snapshots.py", 1, "写前快照"),
    ("nonebot_plugin_xiuxian_signin/storage/audit.py", 1, "审计日志"),
]

FORBIDDEN: list[tuple[str, str]] = [
    ("*/__pycache__/*", "字节码缓存不应进包"),
    ("*.pyc", "字节码缓存不应进包"),
    ("tests/*", "测试不应进包"),
    ("*/.pytest_cache/*", "测试缓存不应进包"),
    (
        "*/assets/mystic_maps/backgrounds/*",
        "秘境背景图应走外置资源包（R-09），进了 wheel 会把体积顶过 PyPI 上限",
    ),
]


def check_wheel(path: Path, max_size_mb: float | None) -> list[str]:
    problems: list[str] = []
    size_mb = path.stat().st_size / (1024 * 1024)

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()

    for pattern, minimum, label in REQUIRED:
        hits = [name for name in names if fnmatch.fnmatch(name, pattern)]
        if len(hits) < minimum:
            problems.append(f"缺少{label}（{pattern}），实际命中 {len(hits)} 个")

    for pattern, reason in FORBIDDEN:
        hits = [name for name in names if fnmatch.fnmatch(name, pattern)]
        if hits:
            problems.append(f"{reason}：{hits[:3]}")

    print(f"{path.name}: {size_mb:.1f} MB, {len(names)} 个文件")
    if max_size_mb is not None and size_mb > max_size_mb:
        problems.append(f"体积 {size_mb:.1f} MB 超过上限 {max_size_mb:.0f} MB")
    elif max_size_mb is None and size_mb > 100:
        print(
            f"  WARN 体积 {size_mb:.1f} MB 超过 PyPI 单文件 100 MB 上限，"
            "需 R-09（资源出 wheel）解决；当前不阻断 CI。"
        )
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 wheel 内容完整性")
    parser.add_argument("wheels", nargs="+", type=Path)
    parser.add_argument(
        "--max-size-mb",
        type=float,
        default=None,
        help="体积上限（MB）；不给则只告警不失败",
    )
    args = parser.parse_args()

    problems: list[str] = []
    for wheel in args.wheels:
        if not wheel.exists():
            problems.append(f"找不到 {wheel}")
            continue
        problems.extend(check_wheel(wheel, args.max_size_mb))

    if problems:
        print("\nwheel 内容校验失败：", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print("wheel 内容校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
