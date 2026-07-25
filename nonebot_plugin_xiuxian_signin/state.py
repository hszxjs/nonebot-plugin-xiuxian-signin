"""插件共享单例与运行时状态。

集中持有所有命令子模块需要的共享对象（config/store/admin_manager/mystic_coordinator）
与可变游戏状态字典。由插件入口 __init__.py 在 NoneBot driver 初始化后导入。

命令子模块通过 ``from ..state import store, config`` 等获取单例，避免循环导入。
"""
from __future__ import annotations

# ruff: noqa: E402

import asyncio
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from nonebot import get_driver, require

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as localstore  # noqa: E402

from .config import Config  # noqa: E402
from .cards import set_font_paths  # noqa: E402
from .storage import JsonStore  # noqa: E402
from .admin import AdminManager  # noqa: E402
from .mystic_dungeon import (  # noqa: E402
    MysticDungeonService,
    MysticTemplateCatalog,
    active_mystic_gameplay_config,
    active_mystic_theme_ids,
    default_mystic_gameplay_config,
)
from .mystic_battle import MysticBattleService  # noqa: E402
from .mystic_cards import MysticMapRenderer  # noqa: E402
from .mystic_runtime import MysticCommandCoordinator  # noqa: E402

driver = get_driver()


def load_config() -> Config:
    data = driver.config.model_dump() if hasattr(driver.config, "model_dump") else driver.config.dict()
    if hasattr(Config, "model_validate"):
        return Config.model_validate(data)
    return Config.parse_obj(data)


config = load_config()
set_font_paths(config.xiuxian_signin_font_path, config.xiuxian_signin_bold_font_path)


def local_now() -> datetime:
    try:
        return datetime.now(ZoneInfo(config.xiuxian_signin_timezone))
    except Exception:
        return datetime.now()


def local_today() -> date:
    return local_now().date()


def get_data_dir() -> Path:
    if config.xiuxian_signin_data_dir:
        return Path(config.xiuxian_signin_data_dir)
    base_data_dir = getattr(localstore, "BASE_DATA_DIR", None)
    if base_data_dir is None:
        return localstore.get_plugin_data_dir()
    data_dir = Path(base_data_dir) / "nonebot_plugin_xiuxian_signin"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


store = JsonStore(get_data_dir())
admin_manager = AdminManager(
    store,
    get_data_dir(),
    config.xiuxian_signin_admin_token or "",
    config.xiuxian_signin_timezone,
)

mystic_catalog = MysticTemplateCatalog.from_files()
mystic_coordinator = MysticCommandCoordinator(
    store=store,
    dungeon_service=MysticDungeonService(
        mystic_catalog,
        now=local_now,
        config_provider=active_mystic_gameplay_config,
        enabled_theme_ids_provider=active_mystic_theme_ids,
    ),
    battle_service=MysticBattleService(
        default_mystic_gameplay_config(),
        now=local_now,
        config_provider=active_mystic_gameplay_config,
    ),
    renderer=MysticMapRenderer(allow_placeholder_background=True),
    now=local_now,
)

# 可变游戏状态字典（各命令子模块共享）。
pending_fishing_users: dict[str, float] = {}
pending_divinations: dict[str, dict[str, Any]] = {}
normal_duel_queue: dict[str, dict[str, Any]] = {}
normal_duel_sessions: dict[str, dict[str, Any]] = {}
doudizhu_tables: dict[str, dict[str, Any]] = {}
beast_realm_tables: dict[str, dict[str, Any]] = {}
beast_realm_private_routes: dict[str, str] = {}

# 生命周期任务句柄（由 __init__.py 的 startup/shutdown hook 赋值）。
rank_scheduler_task: Optional[asyncio.Task] = None
admin_http_server = None
