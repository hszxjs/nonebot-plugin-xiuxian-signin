"""写前快照与轮转（重构计划 R-05）。

存档是本地 JSON，一次坏写就足以丢掉整份数据。``atomic_write_json`` 只保证
「要么旧内容、要么新内容」，但新内容本身是错的（逻辑 bug、误操作、错误的
批量改动）时仍然无解。这里在每次覆盖前把上一版留一份：按文件分目录、按时间
轮转、只保留最近 N 份。

节流是必须的：``users.json`` 在签到、聊天计数、交易等热路径上被频繁改写，
逐次复制会明显拖慢主循环。策略：

- 内容未变（``size`` + ``mtime_ns`` 相同）时直接跳过；
- 同一文件两次自动快照的间隔不小于 :data:`MIN_INTERVAL_SECONDS`；
- 显式来源（后台改配置、手工备份等 ``reason != "auto"``）不受节流限制。

快照失败一律不阻断真实写入——快照是保险，不能让保险本身把游戏写死。
"""

from __future__ import annotations

import contextlib
import os
import threading
import time
from pathlib import Path

from nonebot import logger

SNAPSHOT_DIR_NAME = "snapshots"
DEFAULT_KEEP = 20
MIN_INTERVAL_SECONDS = 300.0
AUTO_REASON = "auto"

_lock = threading.RLock()
# path -> (captured_at_monotonic, (size, mtime_ns))
_last_capture: dict[str, tuple[float, tuple[int, int]]] = {}


def snapshot_dir(path: Path) -> Path:
    """``users.json`` → ``<data_dir>/snapshots/users.json``。"""
    target = Path(path)
    return target.parent / SNAPSHOT_DIR_NAME / target.name


def list_snapshots(path: Path) -> list[Path]:
    """按时间正序返回某文件的快照（旧 → 新）。"""
    directory = snapshot_dir(path)
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix == Path(path).suffix)


def _signature(path: Path) -> tuple[int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_size, stat.st_mtime_ns


def _prune(directory: Path, keep: int) -> None:
    files = sorted(p for p in directory.iterdir() if p.is_file())
    for stale in files[: max(0, len(files) - keep)]:
        with contextlib.suppress(OSError):
            stale.unlink()


def capture_before_write(
    path: Path,
    *,
    reason: str = AUTO_REASON,
    keep: int = DEFAULT_KEEP,
    min_interval: float = MIN_INTERVAL_SECONDS,
) -> Path | None:
    """把 ``path`` 的当前内容留一份快照；返回快照路径，跳过时返回 ``None``。"""
    target = Path(path)
    signature = _signature(target)
    if signature is None or signature[0] == 0:
        # 文件不存在或为空：没有可保护的内容。
        return None

    forced = reason != AUTO_REASON
    key = str(target.resolve()) if target.exists() else str(target)
    now = time.monotonic()
    with _lock:
        last = _last_capture.get(key)
        if last is not None and not forced:
            last_at, last_signature = last
            if last_signature == signature:
                # 自上次快照以来没有变化，不必重复占位。
                return None
            if now - last_at < min_interval:
                return None

    directory = snapshot_dir(target)
    directory.mkdir(parents=True, exist_ok=True)
    # 微秒精度：同一秒内的多次快照（后台连点保存、批量改存档）不能互相覆盖。
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    stamp = f"{stamp}-{time.time_ns() // 1000 % 1_000_000:06d}"
    destination = directory / f"{target.stem}-{stamp}-{reason}{target.suffix}"
    suffix = 1
    while destination.exists():
        destination = directory / f"{target.stem}-{stamp}-{reason}-{suffix}{target.suffix}"
        suffix += 1

    temp_path = directory / f".{destination.name}.tmp"
    try:
        with open(target, "rb") as source, open(temp_path, "wb") as sink:
            while True:
                chunk = source.read(1024 * 256)
                if not chunk:
                    break
                sink.write(chunk)
            sink.flush()
            os.fsync(sink.fileno())
        os.replace(temp_path, destination)
    except OSError as exc:
        with contextlib.suppress(OSError):
            temp_path.unlink()
        logger.warning(f"写前快照失败（已忽略，不阻断写入）：{target}（{exc}）")
        return None

    with _lock:
        _last_capture[key] = (now, signature)
    _prune(directory, max(1, int(keep)))
    return destination


def reset_throttle() -> None:
    """清空节流状态（仅测试与手工排障使用）。"""
    with _lock:
        _last_capture.clear()


def read_snapshot(path: Path, name: str) -> bytes:
    """读取指定快照内容（R-15 回滚用）。

    ``name`` 必须是快照目录内的普通文件名：拒绝任何路径分隔符，且解析后必须
    仍位于快照目录内、后缀与原文件一致——后台会把用户提交的名字直接拼进来，
    这里是防路径穿越的唯一关口。
    """
    target = Path(path)
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ValueError(f"非法快照名：{name!r}")
    directory = snapshot_dir(target).resolve()
    candidate = (directory / name).resolve()
    if candidate.parent != directory or candidate.suffix != target.suffix:
        raise ValueError(f"非法快照名：{name!r}")
    if not candidate.is_file():
        raise FileNotFoundError(f"快照不存在：{name}")
    return candidate.read_bytes()
