"""秘境命令结果的统一播报（R-18）。

秘境命令的返回是 MysticCommandResult（标题/正文/分段/令牌提示），
这里把它渲染成玩家看到的图片或文本，供发现、救援、天机等多条链路复用。"""
from __future__ import annotations

from io import BytesIO

from nonebot import get_bot, logger
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.exception import ActionFailed, NetworkError
from nonebot.matcher import Matcher

from ..domain.rewards import reward_count_by_names
from ..mystic_cards import render_no_token_panel
from ..mystic_dungeon import DungeonRisk, active_mystic_theme_ids
from ..mystic_runtime import MysticCommandResult
from ..state import (
    config,
    mystic_catalog,
    store,
)
from .duel import _mystic_prepare_info, send_mystic_prepare_cards
from .panels import finish_panel


def _collect_theme_display_names(risk: DungeonRisk) -> tuple[str, ...]:
    """收集某风险等级下已启用主题的展示名(按 theme_id 排序),用于缺令牌提示图。"""
    enabled_ids = active_mystic_theme_ids(risk)
    themes = sorted(
        (t for t in mystic_catalog.themes.values() if t.risk is risk),
        key=lambda t: t.theme_id,
    )
    if enabled_ids:
        enabled_set = set(enabled_ids)
        themes = [t for t in themes if t.theme_id in enabled_set]
    return tuple(t.display_name for t in themes)


async def finish_mystic_command_result(
    matcher: Matcher,
    user_id: str,
    result: MysticCommandResult,
) -> None:
    record = await store.get_user(user_id)
    if result.token_missing_risk is not None:
        # 缺少秘境令牌:渲染专属提示图(含令牌图标、持有数、获取途径、可进入秘境)
        normal_count = reward_count_by_names(record, ["普通秘境令牌"])
        high_count = reward_count_by_names(record, ["高风险秘境令牌"])
        try:
            image_bytes = render_no_token_panel(
                normal_count=normal_count,
                high_count=high_count,
                normal_theme_names=_collect_theme_display_names(DungeonRisk.NORMAL),
                high_theme_names=_collect_theme_display_names(DungeonRisk.HIGH),
                width=config.xiuxian_signin_image_width,
            )
            await matcher.send(MessageSegment.image(BytesIO(image_bytes)))
            await matcher.finish()
            return
        except (ActionFailed, NetworkError, OSError, RuntimeError, ValueError):
            # 图片发送失败时回退到通用 warning 面板
            await finish_panel(matcher, "秘境操作失败", result.error or "令牌不足", record, icon="warning")
            return
    if result.error:
        await finish_panel(matcher, "秘境操作失败", result.error, record, icon="warning")
        return
    # 准备阶段倒计时 + 神识探查敌方情报：从当前秘境遭遇读取，一并带进战备面板，
    # 让玩家知道还剩多少秒调整装备、以及要面对什么样的敌人。仅计算一次。
    prepare_hint = ""
    monster_info = ""
    if any(text == "秘境配装" for _, text in result.private_messages):
        prepare_hint, monster_info = await _mystic_prepare_info(result.run)
    for target_user_id, private_text in result.private_messages:
        try:
            if private_text == "秘境配装":
                # 战斗准备阶段：原先只发“秘境配装”四个字，没有任何战斗信息。
                # 这里加载目标玩家存档，发送与斗法一致的战备面板（修为/战技/阵盘/符箓），
                # 让玩家在确认配装前能看到自己的配置。
                target_record = await store.get_user(target_user_id)
                await send_mystic_prepare_cards(
                    target_user_id,
                    target_record,
                    "",
                    prepare_hint,
                    monster_info,
                )
            else:
                await get_bot().send_private_msg(
                    user_id=int(target_user_id),
                    message=private_text,
                )
        except (ActionFailed, NetworkError, RuntimeError, ValueError):
            logger.debug(f"发送秘境私聊提示失败: {target_user_id}")
    if result.image_bytes is not None:
        try:
            await matcher.send(MessageSegment.image(BytesIO(result.image_bytes)))
        except (ActionFailed, NetworkError, OSError, RuntimeError, ValueError):
            await finish_panel(
                matcher,
                "秘境地图",
                result.message or "地图图片发送失败，请稍后重试。",
                record,
                icon="mystic",
            )
            return
        await matcher.finish()
        return
    await finish_panel(
        matcher,
        "秘境",
        result.message or "秘境状态已更新。",
        record,
        icon=result.panel_icon or "mystic",
    )
