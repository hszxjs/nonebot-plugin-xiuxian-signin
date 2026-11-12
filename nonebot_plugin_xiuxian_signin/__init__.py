from __future__ import annotations

# NoneBot plugins must be required before importing their dependent modules.
# ruff: noqa: E402

import asyncio
import sys
from collections import Counter
import random
import re
import time
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

try:
    import httpx
except ImportError:
    httpx = None

from nonebot import get_bot, get_driver, logger, on_message, require

require("nonebot_plugin_localstore")
import nonebot_plugin_localstore as localstore
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent, MessageSegment, PrivateMessageEvent
from nonebot.exception import ActionFailed, IgnoredException, NetworkError
from nonebot.matcher import Matcher
from nonebot.message import event_preprocessor
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from . import beast_realm as beast_realm_game
from .cards import render_adventure_card, render_battle_card, render_fishing_card, render_in_thread, render_signin_calendar_card, render_signin_card, render_text_panel, set_font_paths
from .config import Config
from .domain import (
    CANCEL_WORDS,
    CONFIRM_WORDS,
    ARTIFACT_REFINING_RECIPES,
    IMMORTAL_SEED_INFOS,
    BREAKTHROUGH_REQUIREMENTS,
    FISHING_REWARDS,
    REALMS,
    RankReward,
    SigninResult,
    acquired_root_summary,
    acquired_root_text,
    alchemy_text,

    apply_chat_cultivation,

    apply_dual_cultivation,
    apply_fishing,
    apply_rank_reward,
    apply_signin,
    artifact_power,
    artifact_realm_catalog_summary_text,
    item_required_realm_index,
    array_layer,
    array_layer_cap_text,
    array_multiplier,
    array_proficiency_cap,
    array_proficiency_value,
    available_arrays,
    available_artifacts,

    available_materials,
    available_special_ability_items,
    available_curios,
    available_foods,
    available_methods,
    available_misc_items,
    available_pills,
    available_plants,
    available_puppets,
    available_spirit_stones,
    available_talismans,
    available_battle_techniques,
    battle_power,
    battle_summary,
    breakthrough_realm,
    breakthrough_requirement_key_for_realm_index,
    breakthrough_source_realm_index,
    breakthrough_target_realm,
    breakthrough_target_realm_index,
    breakthrough_item_quality_cap_text,
    breakthrough_quality_relation_text,
    breakthrough_status,
    catalog_item_detail_text,

    buy_shop_item,

    choose_cultivation_route,

    choose_evil_cultivation,

    choose_faction_identity,
    combat_max_mana,

    complete_daily_task,

    daily_tasks_text,
    draw_talisman_by_index,
    duel_records,
    equip_array,
    equip_artifact,
    equip_method,
    equip_puppet,
    equip_talisman,
    simulate_normal_duel,
    method_profile,
    format_method_detail,
    ensure_combat_profile,
    fishing_count_from_text,
    identify_misc_item,
    learn_special_ability,
    market_offer_price,
    method_power,
    technique_cooldown,
    technique_mana_cost,
    plant_spirit_plant,
    pop_reward_by_category_index,
    puppet_power,
    rank_reward_for,

    array_deduction_text,
    batch_sell_rewards,
    batch_sell_low_realm_artifacts,
    deduce_array,
    emperor_artifact_catalog_text,
    equip_immortal_seed,
    immortal_seed_text,
    is_unique_reward,
    make_unique_replica,
    refine_artifact_by_recipe,
    refining_text,
    set_life_artifact,
    refine_pill_by_recipe,
    refine_dan_root,
    refine_artifact_root,
    regress_cultivation,
    refine_spirit_stone,
    refine_demon_core,
    refine_spirit_stones_batch,
    refine_demon_cores_batch,
    refine_spirit_liquid,
    reward_display_name,

    route_status_text,

    sell_reward,

    shop_items_for_date,

    special_ability_catalog_text,
    special_ability_list_text,
    spirit_stone_text,
    makeup_price,
    makeup_sign,
    makeup_used_this_month,
    signin_streak,
    talisman_draw_text,
    unequip_artifact,
    unequip_talisman,
    use_curio,
    use_food,
    use_foods_batch,
    use_pill,
    use_pills_batch,
    use_talisman,
)
from .admin import AdminManager, install_admin_routes, start_admin_server
from .mystic_battle import MysticBattleService
from .mystic_cards import MysticMapRenderer, render_no_token_panel
from .mystic_dungeon import (
    DungeonMode,
    DungeonPhase,
    DungeonRisk,
    MysticDungeonService,
    MysticTemplateCatalog,
    active_mystic_gameplay_config,
    active_mystic_theme_ids,
    default_mystic_gameplay_config,
)
from .domain.rewards import reward_count_by_names
from .mystic_menu import MYSTIC_HELP_SUMMARY, MYSTIC_PICMENU_ENTRY
from .mystic_runtime import (
    DungeonEntryOffer,
    MysticCommandCoordinator,
    MysticCommandResult,
    parse_mystic_group_command,
    parse_mystic_private_command,
)
from .storage import InsufficientSpiritStones, JsonStore, MysticRescueRequest
from .net import close_shared_http_client
from .resource_pack import configure as configure_resource_pack
from .resource_pack import ensure_pack, pack_status as resource_pack_status
from . import state as _state  # 共享单例（config/store/admin_manager/mystic_coordinator 等）
from .state import (  # noqa: F401
    config, store, admin_manager, mystic_coordinator, mystic_catalog,
    local_now, local_today, get_data_dir,
    pending_fishing_users,
    normal_duel_queue, normal_duel_sessions,
    doudizhu_tables, beast_realm_tables, beast_realm_private_routes,
)

# 斗地主命令子模块（import 即注册 matcher）；提供 is_doudizhu_command_text 供兜底判定。
from .commands.doudizhu import is_doudizhu_command_text  # noqa: E402

# --- 命令子模块（R-18）-----------------------------------------------------
# 入口只保留插件元数据、生命周期钩子与模块导入；命令实现按域放在 commands/ 下。
# matchers 与 handlers 靠 import 副作用注册，必须显式导入。
from .commands import handlers, matchers  # noqa: F401
from .commands.formatting import _is_likely_sent_despite_error, format_rank_message  # noqa: F401
from .commands.matchers import dual_cultivation_cmd  # noqa: F401
from .commands.panels import finish_panel, panel_segment  # noqa: F401
from .commands.parsing import (  # noqa: F401
    at_user_ids,
    group_member_display_name,
    nickname_from_event,
    normalized_plain_text,
    remember_group_member,
)
from .commands.picmenu import PICMENU_NEXT_FUNCS  # noqa: F401
from .commands.ranking import (  # noqa: F401
    group_cultivation_rank_entries,
    group_power_rank_entries,
    is_settle_time,
    rank_entries_from_group,
)

__version__ = "0.6.0"





__plugin_meta__ = PluginMetadata(
    name="修仙签到",
    description="以图片面板输出的修仙签到、境界突破、灵器战力、功法阵盘、神通、秘境探索、交易和后台管理插件。",
    usage=(
        "入门：签到 / 面板 / 历练 / 新手教程 / 帮助，首次签到抽取灵根，每天获得修为和 1 次灵河垂钓\n"
        "修为：突破 / 炼化灵液 / 炼化妖丹 1 / 后天灵根，处理瓶颈、灵液、妖丹和五行补全\n"
        "背包：背包 / 图鉴 / 图鉴 名称，查看物品用途、故事、获取方式和制作素材\n"
        "灵器：灵器 / 装备灵器 1 主手 / 战力，灵器按境界绑定，假仙后可获得仙器\n"
        "功法阵盘：功法 / 参悟功法 1 / 阵法推演 1，重复获得会推演升层或升品\n"
        "神通：神通 / 神通图鉴 / 领悟神通 1，查看传承材料并在斗法中触发\n"
        "秘境：秘境 / 秘境帮助 / 创建单人秘境 普通 / 创建秘境队伍 普通 / 投骰 / 秘境地图 / 秘境救援 1000\n"
        "御兽秘境：御兽秘境开局 PVE / PVP，私聊任务堂招募随从，群聊播报战报\n"
        "交易：商店 / 万宝楼 / 交易 @对方 灵器 1 100 / 批量出售 杂物 20 / 批量出售低阶灵器\n"
        "后台：浏览器访问 /xiuxian-admin，可查看玩家档案、物品属性、灵器规则和秘境掉落配置"
    ),
    type="application",
    homepage="https://github.com/hszxjs/nonebot-plugin-xiuxian-signin",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "author": "fallen_rainy",
        "version": __version__,
        "pmn": {
            "hidden": False,
            "markdown": True,
            "template": None,
        },
        "funcs": PICMENU_NEXT_FUNCS,
        "menu_data": PICMENU_NEXT_FUNCS,
    },
)

driver = get_driver()

# 共享可变状态（钓鱼待结算、斗法队列、牌桌等）统一定义在 state.py，
# 此处只沿用上方 `from .state import ...` 的引用。曾经在这里重新赋值为新的
# 空字典，导致入口模块与 commands/ 子模块各持一份、互不可见（F811）。
rank_scheduler_task: Optional[asyncio.Task] = None
mystic_recovery_task: Optional[asyncio.Task] = None
# 秘境背景图外置包的后台下载任务（R-09）：不阻塞启动，失败只降级为占位背景。
asset_download_task: Optional[asyncio.Task] = None
admin_http_server = None






















































































































async def settle_daily_chat_ranks() -> None:
    now = local_now()
    if not is_settle_time(now):
        return
    date_text = now.date().isoformat()
    groups = await store.get_unsettled_rank_groups(date_text)
    for group_id, group_data in groups.items():
        entries = rank_entries_from_group(group_data)
        if not entries:
            await store.mark_rank_group_settled(group_id, date_text)
            continue
        rewards: dict[str, RankReward] = {}
        for index, entry in enumerate(entries[:10], start=1):
            exp, fishing_chances = rank_reward_for(index)
            if exp <= 0 and fishing_chances <= 0:
                continue
            user_id = str(entry.get("user_id", ""))

            def updater(record, rank=index, reward_map=rewards):
                reward_map[record.user_id] = apply_rank_reward(record, rank)

            await store.apply_to_user(user_id, updater)
        cultivation_entries = await group_cultivation_rank_entries(group_id)
        power_entries = await group_power_rank_entries(group_id)
        message = format_rank_message(
            group_id,
            date_text,
            entries,
            rewards,
            cultivation_entries,
            power_entries,
        )
        try:
            bot = get_bot()
            await bot.send_group_msg(
                group_id=int(group_id),
                message=await render_in_thread(panel_segment, "每日话痨榜", message, icon="rank"),
            )
        except Exception as exc:
            logger.exception(f"发送群 {group_id} 每日话痨榜失败")
            # NapCat/QQ 内核 ACK 超时（retcode=1200）时，消息实际往往已送达。
            # 无论真假失败，都标记已结算，否则 get_unsettled_rank_groups 会反复
            # 取到该群导致无限重发（群里疯狂刷屏话痨榜）。
            if _is_likely_sent_despite_error(exc):
                logger.warning("话痨榜发送超时但可能已送达（retcode=1200），标记已结算避免重复发送")
        # 无论发送成功还是失败，都标记已结算（避免无限重发 > 单次失败的容错）
        try:
            await store.mark_rank_group_settled(group_id, date_text)
        except Exception:
            logger.exception("标记话痨榜已结算失败")

async def rank_scheduler() -> None:
    while True:
        try:
            await settle_daily_chat_ranks()
        except Exception:
            logger.exception("每日话痨榜结算任务失败")
        await asyncio.sleep(60)


async def recover_mystic_dungeons() -> None:
    try:
        recovered = await mystic_coordinator.recover_active_runs()
        logger.info(
            "秘境状态恢复完成："
            f"应战超时 {recovered.response_expirations}，"
            f"投票超时 {recovered.vote_expirations}，"
            f"恢复截止时间 {recovered.scheduled_deadline_count}"
        )
    except Exception:
        logger.exception("秘境状态恢复失败")


async def mystic_recovery_sweep() -> None:
    """周期性巡检进行中的秘境，兜底重建丢失的截止时间任务。

    秘境的截止时间建在内存 asyncio task 上，进程异常或任务抛出非冲突异常
    时可能丢失，导致秘境卡在某个阶段不推进。recover_active_runs 本身幂等
    （deadline 在未来就重建 task，已过期就立即推进），故可安全地周期调用。
    """
    while True:
        try:
            await mystic_coordinator.recover_active_runs()
        except Exception:
            logger.exception("秘境周期巡检失败")
        await asyncio.sleep(60)


@driver.on_startup
async def start_rank_scheduler() -> None:
    global admin_http_server, rank_scheduler_task, mystic_recovery_task, asset_download_task
    admin_ready = False
    if config.xiuxian_signin_admin_enabled:
        # fail-closed：账号初始化失败（数据目录不可写、凭据文件损坏）时
        # 直接不启动后台，而不是启动一个没人能登录、或没人需要登录的后台。
        try:
            admin_manager.auth.ensure_initialized()
            admin_ready = True
        except Exception:
            logger.exception(
                "后台账号初始化失败，本次不启动后台。"
                "请检查数据目录写权限，或删除 admin_auth.json 后重启重建。"
            )
    if admin_ready:
        mounted = False
        try:
            # 首选：把后台路由挂到 NoneBot driver 的 FastAPI server_app 上。
            # 这样后台与命令处理共用同一个事件循环，且不额外占用端口，
            # 从结构上消除"主循环 + 独立 uvicorn 线程"两个写者的局面。
            mounted = install_admin_routes(driver, admin_manager, config.xiuxian_signin_admin_path)
        except Exception:
            logger.exception("修仙签到后台挂载到 driver 失败，回退独立端口")
            mounted = False
        if mounted:
            logger.info(f"修仙签到后台已挂载到 driver：{config.xiuxian_signin_admin_path}")
        else:
            try:
                admin_http_server = start_admin_server(
                    admin_manager,
                    config.xiuxian_signin_admin_host,
                    config.xiuxian_signin_admin_port,
                    config.xiuxian_signin_admin_path,
                )
                logger.info(
                    "修仙签到后台已启动："
                    f"http://{admin_http_server.host}:{admin_http_server.port}{admin_http_server.base_path}"
                )
            except Exception:
                logger.exception(
                    f"修仙签到后台启动失败：{config.xiuxian_signin_admin_host}:{config.xiuxian_signin_admin_port}"
                )
                admin_manager.apply_config()
    else:
        admin_manager.apply_config()
    await recover_mystic_dungeons()
    rank_scheduler_task = asyncio.create_task(rank_scheduler())
    mystic_recovery_task = asyncio.create_task(mystic_recovery_sweep())
    global chat_flush_task
    chat_flush_task = asyncio.create_task(chat_flush_loop())

    # 秘境背景图（202 MB）不进 wheel，启动后再后台拉取：先让机器人可用，
    # 下载期间出图用程序化占位背景，完成即切换到真图（resolve_background 每次解析）。
    configure_resource_pack(get_data_dir())
    if config.xiuxian_signin_asset_auto_download:
        asset_download_task = asyncio.create_task(
            ensure_asset_pack(data_dir=get_data_dir(), url=config.xiuxian_signin_asset_url)
        )


async def ensure_asset_pack(*, data_dir, url: Optional[str]) -> None:
    """后台准备秘境资源包；任何失败都只告警，不影响机器人运行。"""
    status = resource_pack_status(data_dir)
    if status.complete:
        logger.info(f"秘境资源包已就绪：{status.summary()}")
        return
    logger.info(f"秘境资源包不完整：{status.summary()}")
    await ensure_pack(data_dir=data_dir, url=url)


async def chat_flush_loop() -> None:
    """R-17：每 30s 把内存中聚合的聊天计数批量落盘。"""
    while True:
        await asyncio.sleep(30)
        try:
            applied = await store.flush_chat_counts()
            if applied:
                logger.debug(f"聊天计数已批量落盘 {applied} 条")
        except Exception:
            logger.exception("聊天计数批量落盘失败")


@driver.on_shutdown
async def stop_admin_http_server() -> None:
    global admin_http_server, mystic_recovery_task, rank_scheduler_task, asset_download_task, chat_flush_task
    # 停机前先冲掉未落盘的聊天计数，再取消任务。
    try:
        await store.flush_chat_counts()
    except Exception:
        logger.exception("停机时冲刷聊天计数失败")
    if admin_http_server is not None:
        admin_http_server.stop()
        admin_http_server = None
    await close_shared_http_client()
    # SQLite 后端：关闭连接，清理 WAL/-shm 文件。
    if hasattr(store, "close"):
        store.close()
    # 后台任务都必须取消并 await，否则停机后仍有协程在写存档 / 下载资源。
    pending = [
        task
        for task in (mystic_recovery_task, rank_scheduler_task, asset_download_task, chat_flush_task)
        if task is not None
    ]
    for task in pending:
        task.cancel()
    for task in pending:
        try:
            await task
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("后台任务在停机时抛出异常")
    mystic_recovery_task = None
    rank_scheduler_task = None
    asset_download_task = None
    chat_flush_task = None



























































































































