"""关键操作的审计日志（重构计划 R-05）。

用 JSON Lines 追加到 ``<data_dir>/audit.log``：一行一条，便于 grep 与后续
导入分析。写入量很小（登录、改密、改配置、改存档、备份），因此每条都 fsync，
确保进程被杀后仍能追溯到底发生了什么。

超过 :data:`MAX_BYTES` 时滚动成 ``audit.log.1``（只保留上一代），避免长期
运行把磁盘写满。
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

AUDIT_FILE_NAME = "audit.log"
MAX_BYTES = 5 * 1024 * 1024

_lock = threading.RLock()


def audit_path(data_dir: Path) -> Path:
    return Path(data_dir) / AUDIT_FILE_NAME


def _rotate(path: Path) -> None:
    try:
        if not path.exists() or path.stat().st_size < MAX_BYTES:
            return
    except OSError:
        return
    with contextlib.suppress(OSError):
        os.replace(path, path.with_name(f"{path.name}.1"))


def audit(data_dir: Path, event: str, /, **fields: Any) -> None:
    """追加一条审计记录；任何失败都只记日志，不影响业务。"""
    directory = Path(data_dir)
    entry: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "event": str(event),
    }
    entry.update({key: value for key, value in fields.items() if value is not None})
    line = json.dumps(entry, ensure_ascii=False, default=str)

    with _lock:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            path = audit_path(directory)
            _rotate(path)
            with open(path, "a", encoding="utf-8") as fp:
                fp.write(line + "\n")
                fp.flush()
                os.fsync(fp.fileno())
        except OSError:
            # 审计不可用不能阻断业务；调用方会同时在常规日志里看到操作结果。
            from nonebot import logger

            logger.warning(f"审计日志写入失败：{line}")


def read_audit(data_dir: Path, *, limit: int = 200) -> list[dict[str, Any]]:
    """读最近 ``limit`` 条审计记录（新的在前），用于排障与后续后台展示。"""
    path = audit_path(data_dir)
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    entries: list[dict[str, Any]] = []
    for line in reversed(lines[-max(0, limit) :]):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            entries.append(parsed)
    return entries
