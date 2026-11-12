"""普通斗法的准备与收尾（R-18）。

负责开局三选一卡面、群内准备消息、结算播报与招式记录。
斗地主在 commands/doudizhu.py，此处只管「普通斗法」这一条线。"""
from __future__ import annotations

import asyncio
import time

from datetime import datetime
from io import BytesIO
from typing import Any, Optional

from nonebot import get_bot, logger
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment

from ..cards import render_battle_card, render_in_thread
from ..domain import (
    array_multiplier,
    available_battle_techniques,
    available_talismans,
    battle_power,
    combat_max_mana,
    ensure_combat_profile,
    reward_display_name,
    simulate_normal_duel,
    technique_cooldown,
    technique_mana_cost,
)
from ..net import fetch_avatar
from ..state import config, normal_duel_sessions, store
from .panels import panel_segment
from .texts import NORMAL_DUEL_DURATION_SECONDS


def normal_duel_prepare_cards(record, nickname: str) -> list[tuple[str, str, str]]:
    ensure_combat_profile(record)
    techniques = available_battle_techniques(record)
    technique_lines = []
    for index, tech in enumerate(techniques[:6], start=1):
        technique_lines.append(f"{index}. {tech}\uff1a\u8017\u7075{technique_mana_cost(record, tech)}\uff0cCD{technique_cooldown(tech)}\u606f")
    if not technique_lines:
        technique_lines.append("\u6682\u65e0\u6218\u6280\uff0c\u53ef\u53d1\u9001\u8868\u60c5\u6216\u5373\u5174\u53f0\u8bcd\u5c1d\u8bd5\u7275\u52a8\u57fa\u7840\u672f\u5f0f\u3002")
    abilities = "\u3001".join(record.special_abilities or []) or "\u6682\u65e0\u663e\u5316"
    talismans = available_talismans(record)
    talisman_lines = []
    for index, talisman in enumerate(talismans[:6], start=1):
        talisman_lines.append(f"{index}. {reward_display_name(talisman)}")
    if not talisman_lines:
        talisman_lines.append("\u6682\u65e0\u53ef\u7528\u7b26\u7b93\uff1b\u672c\u573a\u53ef\u4f9d\u9760\u6218\u6280\u3001\u795e\u901a\u3001\u4f53\u672f\u548c\u4f53\u8d28\u7279\u6027\u3002")
    equipped_talisman = reward_display_name(record.equipped_talisman) if record.equipped_talisman else "\u672a\u88c5\u5907\u7b26\u7b93"
    array_text = reward_display_name(record.equipped_array) if record.equipped_array else "\u672a\u5e03\u7f6e\u9635\u76d8"
    cards = [
        (
            "\u6597\u6cd5\u51c6\u5907\u00b7\u4fee\u4e3a\u786e\u8ba4",
            "\n".join(
                [
                    f"{nickname or '\u5bbf\u4e3b'}\uff0c\u666e\u901a\u6597\u6cd5\u5c06\u572860\u79d2\u540e\u5f00\u59cb\u3002",
                    f"\u5883\u754c\uff1a{record.realm if record.root else '\u672a\u5165\u95e8'}",
                    f"\u5883\u754c\u54c1\u76f8\uff1a{record.realm_quality}",
                    f"\u6218\u529b\uff1a{battle_power(record)}",
                    f"\u7075\u529b\u4e0a\u9650\uff1a{combat_max_mana(record)}",
                    f"\u7075\u6839\uff1a{record.root_summary}",
                    f"\u79cd\u65cf\uff1a{record.combat_race or '\u672a\u8bb0\u5f55'}",
                    f"\u4f53\u8d28\uff1a{record.physique or '\u672a\u8bb0\u5f55'}",
                ]
            ),
            "realm",
        ),
        (
            "\u6597\u6cd5\u51c6\u5907\u00b7\u6218\u6280\u914d\u7f6e",
            "\n".join(
                [
                    f"\u5f53\u524d\u529f\u6cd5\uff1a{reward_display_name(record.equipped_method) if record.equipped_method else '\u672a\u53c2\u609f\u529f\u6cd5'}",
                    "\u53ef\u7528\u6218\u6280\uff1a",
                    *technique_lines,
                    f"\u795e\u901a\uff1a{abilities}",
                    "\u6218\u6280\u4f1a\u6d88\u8017\u7075\u529b\u5e76\u8fdb\u5165CD\uff1b\u672a\u547d\u4e2d\u7684\u53d1\u8a00\u4f1a\u4f5c\u4e3a\u5373\u5174\u672f\u5f0f\u3002",
                ]
            ),
            "method",
        ),
        (
            "\u6597\u6cd5\u51c6\u5907\u00b7\u9635\u76d8\u914d\u7f6e",
            "\n".join(
                [
                    f"\u5f53\u524d\u9635\u76d8\uff1a{array_text}",
                    f"\u9635\u6cd5\u500d\u7387\uff1a{array_multiplier(record):.1f}x",
                    "\u9635\u76d8\u4f1a\u5f71\u54cd\u529f\u6cd5\u6536\u76ca\u4e0e\u90e8\u5206\u6218\u6597\u9762\u677f\u8ba1\u7b97\uff1b\u719f\u7ec3\u5ea6\u8d8a\u9ad8\u8d8a\u7a33\u5b9a\u3002",
                ]
            ),
            "array",
        ),
        (
            "\u6597\u6cd5\u51c6\u5907\u00b7\u7b26\u7b93\u51c6\u5907",
            "\n".join(
                [
                    f"\u5f53\u524d\u7b26\u7b93\u680f\uff1a{equipped_talisman}",
                    "\u53ef\u7528\u7b26\u7b93\uff1a",
                    *talisman_lines,
                    "\u53d1\u9001\u201c\u88c5\u5907\u7b26\u7b93 \u7f16\u53f7\u201d\u53ef\u653e\u5165\u7b26\u7b93\u680f\uff1b\u666e\u901a\u6597\u6cd5\u751f\u6548\u4e14\u4e0d\u6d88\u8017\u3002",
                    "\u53d1\u9001\u201c\u4f7f\u7528\u7b26\u7b93 \u7f16\u53f7\u201d\u4ecd\u4f1a\u4f5c\u4e3a\u4e00\u6b21\u6027\u7b26\u7b93\u6fc0\u53d1\u5e76\u6d88\u8017\u3002",
                ]
            ),
            "talisman",
        ),
    ]
    return cards


async def send_normal_duel_prepare_cards(user_id: str, record, nickname: str) -> None:
    bot = get_bot()
    for title, content, icon in normal_duel_prepare_cards(record, nickname):
        try:
            segment = await render_in_thread(panel_segment, title, content, record, icon=icon)
            await bot.send_private_msg(
                user_id=int(user_id),
                message=segment,
            )
        except Exception as exc:
            logger.debug(f"\u53d1\u9001\u6597\u6cd5\u51c6\u5907\u79c1\u804a\u5931\u8d25: {user_id} {exc}")


async def send_normal_duel_prepare_messages(session: dict[str, Any]) -> None:
    left_id = str(session.get("left_id"))
    right_id = str(session.get("right_id"))
    left_record, right_record = await asyncio.gather(store.get_user(left_id), store.get_user(right_id))
    ensure_combat_profile(left_record)
    ensure_combat_profile(right_record)
    await asyncio.gather(store.save_user(left_record), store.save_user(right_record))
    await asyncio.gather(
        send_normal_duel_prepare_cards(left_id, left_record, str(session.get("left_name") or left_id)),
        send_normal_duel_prepare_cards(right_id, right_record, str(session.get("right_name") or right_id)),
    )


def mystic_prepare_cards(
    record, nickname: str, prepare_hint: str = "", monster_info: str = ""
) -> list[tuple[str, str, str]]:
    """秘境战备面板，结构与斗法战备一致，文案适配秘境战斗。

    之前 boss 战/遭遇战进入准备阶段时只给玩家发了“秘境配装”四个字，
    没有任何战斗信息。这里复用斗法战备的渲染逻辑，让玩家在秘境里也能
    看到自己的修为、战技、阵盘、符箓配置，再决定是否调整装备并确认配装。

    prepare_hint 为准备阶段的倒计时提示（如“剩余 45 秒”），为空则不显示。
    """
    ensure_combat_profile(record)
    techniques = available_battle_techniques(record)
    technique_lines = []
    for index, tech in enumerate(techniques[:6], start=1):
        technique_lines.append(
            f"{index}. {tech}：耗灵{technique_mana_cost(record, tech)}，CD{technique_cooldown(tech)}息"
        )
    if not technique_lines:
        technique_lines.append("暂无战技，可发表情或即兴台词尝试牵动基础术式。")
    abilities = "、".join(record.special_abilities or []) or "暂无显化"
    talismans = available_talismans(record)
    talisman_lines = []
    for index, talisman in enumerate(talismans[:6], start=1):
        talisman_lines.append(f"{index}. {reward_display_name(talisman)}")
    if not talisman_lines:
        talisman_lines.append("暂无可用符箓；本场可依靠战技、神通、体质和体质特性。")
    equipped_talisman = (
        reward_display_name(record.equipped_talisman)
        if record.equipped_talisman
        else "未装备符箓"
    )
    array_text = (
        reward_display_name(record.equipped_array)
        if record.equipped_array
        else "未布置阵盘"
    )
    intro_lines = [
        f"{nickname or '宿主'}，秘境战斗已进入准备阶段，请检查配装后私聊发送“确认配装”。"
    ]
    if prepare_hint:
        # 倒计时放在最显眼的第一行之后，让玩家知道还剩多少时间调整装备。
        intro_lines.append(prepare_hint)
    intro_lines.extend(
        [
            f"境界：{record.realm if record.root else '未入门'}",
            f"境界品相：{record.realm_quality}",
            f"战力：{battle_power(record)}",
            f"灵力上限：{combat_max_mana(record)}",
            f"灵根：{record.root_summary}",
            f"种族：{record.combat_race or '未记录'}",
            f"体质：{record.physique or '未记录'}",
        ]
    )
    cards = [
        (
            "秘境战备·修为确认",
            "\n".join(intro_lines),
            "realm",
        ),
        (
            "秘境战备·战技配置",
            "\n".join(
                [
                    f"当前功法：{reward_display_name(record.equipped_method) if record.equipped_method else '未参悟功法'}",
                    "可用战技：",
                    *technique_lines,
                    f"神通：{abilities}",
                    "战技会消耗灵力并进入CD；未命中的发言会作为即兴术式。",
                ]
            ),
            "method",
        ),
        (
            "秘境战备·阵盘配置",
            "\n".join(
                [
                    f"当前阵盘：{array_text}",
                    f"阵法倍率：{array_multiplier(record):.1f}x",
                    "阵盘会影响功法收益与部分战斗面板计算；熟练度越高越稳定。",
                ]
            ),
            "array",
        ),
        (
            "秘境战备·符箓准备",
            "\n".join(
                [
                    f"当前符箓栏：{equipped_talisman}",
                    "可用符箓：",
                    *talisman_lines,
                    "发送“装备符箓 编号”可放入符箓栏；普通战法生效且不消耗。",
                    "发送“使用符箓 编号”仍会作为一次性符箓激发并消耗。",
                ]
            ),
            "talisman",
        ),
    ]
    if monster_info:
        # 神识探查：敌方信息。原本战备面板只有己方配置，玩家不知道要面对什么，
        # 这里补一张敌方情报卡（境界/灵根/战力/血量等），便于针对性配装。
        cards.append(
            (
                "秘境战备·神识探查",
                monster_info,
                "mystic",
            )
        )
    return cards


async def send_mystic_prepare_cards(
    user_id: str, record, nickname: str, prepare_hint: str = "", monster_info: str = ""
) -> None:
    """把秘境战备面板逐张私聊发给指定玩家。"""
    bot = get_bot()
    for title, content, icon in mystic_prepare_cards(
        record, nickname, prepare_hint, monster_info
    ):
        try:
            segment = await render_in_thread(panel_segment, title, content, record, icon=icon)
            await bot.send_private_msg(
                user_id=int(user_id),
                message=segment,
            )
        except Exception as exc:
            logger.debug(f"发送秘境战备私聊失败: {user_id} {exc}")


async def _mystic_prepare_info(run) -> tuple[str, str]:
    """读取秘境遭遇信息，返回 (倒计时提示, 神识探查敌方情报)。

    倒计时：准备阶段默认仅 60 秒，玩家很容易没赶上就被自动确认。把剩余时间
    显示在战备面板上，让玩家知道得抓紧。
    神识探查：战备面板原本只有己方配置，补上敌方情报（境界/灵根/战力/血量），
    让玩家能针对性配装。任一项解析失败返回空串（不显示）。
    """
    hint = ""
    monster_info = ""
    if run is None or not getattr(run, "active_encounter_id", None):
        return hint, monster_info
    try:
        encounter = await store.get_mystic_encounter(run.active_encounter_id)
    except Exception:
        return hint, monster_info
    if encounter is None:
        return hint, monster_info

    # 倒计时
    deadline_raw = getattr(encounter, "phase_deadline", None)
    if deadline_raw:
        try:
            deadline = datetime.fromisoformat(str(deadline_raw))
            remaining = int((deadline - datetime.now(deadline.tzinfo)).total_seconds())
            if remaining > 0:
                minutes, seconds = divmod(remaining, 60)
                if minutes > 0:
                    hint = f"⏰ 准备阶段剩余 {minutes} 分 {seconds} 秒，超时将按当前配装自动开战。"
                else:
                    hint = f"⏰ 准备阶段剩余 {seconds} 秒，超时将按当前配装自动开战。"
        except ValueError:
            pass

    # 神识探查：解析怪物存档，构造敌方情报
    try:
        monster_record_data = encounter.monster_record or {}
        if monster_record_data:
            from ..domain import UserRecord, combat_max_hp

            monster = UserRecord.from_dict(monster_record_data)
            kind_label = "Boss" if encounter.kind.value == "boss" else "秘境怪物"
            lines = [
                f"敌方：{kind_label}",
                f"境界：{monster.realm if monster.root else '未知'}",
                f"灵根：{monster.root_summary}",
                f"推测战力：{battle_power(monster)}",
                f"生命上限：{combat_max_hp(monster)}",
                f"灵力上限：{combat_max_mana(monster)}",
                f"种族：{monster.combat_race or '未记录'}",
                f"体质：{monster.physique or '未记录'}",
            ]
            monster_info = "\n".join(lines)
    except Exception:
        logger.debug("神识探查敌方情报构造失败")

    return hint, monster_info


async def build_normal_duel_image(result: dict[str, Any]) -> bytes:
    left = result.get("left", {})
    right = result.get("right", {})
    left_avatar, right_avatar = await asyncio.gather(
        fetch_avatar(str(left.get("user_id", ""))),
        fetch_avatar(str(right.get("user_id", ""))),
    )
    return await render_in_thread(
        render_battle_card,
        result,
        left_avatar=left_avatar,
        right_avatar=right_avatar,
        width=config.xiuxian_signin_image_width,
    )


def group_duel_session(group_id: str) -> Optional[dict[str, Any]]:
    session = normal_duel_sessions.get(group_id)
    if not session:
        return None
    now = time.monotonic()
    if now > float(session.get("end_at", 0)) + 10:
        normal_duel_sessions.pop(group_id, None)
        return None
    return session


async def finish_normal_duel(group_id: str, session: dict[str, Any]) -> None:
    try:
        await asyncio.sleep(max(0.0, float(session["start_at"]) - time.monotonic()))
        session["active"] = True
        bot = get_bot()
        await bot.send_group_msg(
            group_id=int(group_id),
            message=await render_in_thread(
                panel_segment,
                "\u666e\u901a\u6597\u6cd5",
                "\u6597\u6cd5\u5df2\u5f00\u59cb\uff0c60\u79d2\u5185\u53d1\u9001\u6218\u6280\u3001\u795e\u901a\u3001\u8868\u60c5\u6216\u5373\u5174\u672f\u5f0f\u3002",
                icon="duel",
            ),
        )
        await asyncio.sleep(max(0.0, float(session["end_at"]) - time.monotonic()))
        current = normal_duel_sessions.get(group_id)
        if current is not session:
            return
        left_id = str(session["left_id"])
        right_id = str(session["right_id"])
        left_record, right_record = await asyncio.gather(store.get_user(left_id), store.get_user(right_id))
        ensure_combat_profile(left_record)
        ensure_combat_profile(right_record)
        result = simulate_normal_duel(
            left_record,
            right_record,
            str(session.get("left_name") or left_id),
            str(session.get("right_name") or right_id),
            list(session.get("actions", {}).get(left_id, [])),
            list(session.get("actions", {}).get(right_id, [])),
            NORMAL_DUEL_DURATION_SECONDS,
        )
        await store.save_user(left_record)
        await store.save_user(right_record)
        image = await build_normal_duel_image(result)
        await bot.send_group_msg(group_id=int(group_id), message=MessageSegment.image(BytesIO(image)))
    except Exception:
        logger.exception("\u666e\u901a\u6597\u6cd5\u7ed3\u7b97\u5931\u8d25")
    finally:
        if normal_duel_sessions.get(group_id) is session:
            normal_duel_sessions.pop(group_id, None)


def append_normal_duel_action(event: GroupMessageEvent, text: str) -> bool:
    group_id = str(event.group_id)
    session = group_duel_session(group_id)
    if not session or not session.get("active"):
        return False
    now = time.monotonic()
    if now < float(session.get("start_at", 0)) or now > float(session.get("end_at", 0)):
        return False
    user_id = event.get_user_id()
    if user_id not in {str(session.get("left_id")), str(session.get("right_id"))}:
        return False
    actions = session.setdefault("actions", {}).setdefault(user_id, [])
    actions.append({"text": text, "time": now})
    return True
