"""domain signin 子系统。

由原 domain.py 抽取。跨子系统反向依赖一律在函数内 import，模块级不持有全局访问器。
"""
from __future__ import annotations

import hashlib
import random
import re
import uuid
from datetime import date, timedelta
from typing import Any, Optional

from .constants import *  # noqa: F401,F403
from .utils import *  # noqa: F401,F403
from .models import *  # noqa: F401,F403
from .rewards import *  # noqa: F401,F403
from .roots import *  # noqa: F401,F403
from .realms import *  # noqa: F401,F403
from .methods_arrays import *  # noqa: F401,F403
from .equipment import *  # noqa: F401,F403
from .abilities import *  # noqa: F401,F403
from .crafting import *  # noqa: F401,F403
from .mystic_drops import *  # noqa: F401,F403
from .economy import *  # noqa: F401,F403

def maybe_apply_encounter(record: UserRecord, today: date) -> EncounterResult:
    today_text = today.isoformat()
    if record.root is None or record.last_encounter_date == today_text:
        return EncounterResult()

    normalize_root_profile(record)
    record.last_encounter_date = today_text
    if record.root and record.root.tier == "\u53d8\u5f02\u7075\u6839":
        if random.randint(1, 999) > 1 + max(0, record.sign_count // 30):
            return EncounterResult()
        old_root = Root.from_dict(record.root.to_dict())
        new_root = improve_root_once(record.root)
        record.root = new_root
        record.extra_roots = []
        return EncounterResult(
            happened=True,
            success=True,
            message=f"\u4eca\u65e5\u5148\u5929\u5f02\u8c61\u56de\u54cd\uff0c{new_root.display_name}\u7cbe\u7eaf\u5ea6\u63d0\u5347\u81f3{new_root.purity}%\u3002",
            old_root=old_root,
            new_root=new_root,
        )

    if not record.is_peak_aptitude:
        if random.randint(1, 365) != 1:
            return EncounterResult()
        old_root = Root.from_dict(record.root.to_dict()) if record.root else None
        if random.random() >= 0.5:
            return EncounterResult(
                happened=True,
                success=False,
                message="\u4eca\u65e5\u5ffd\u9022\u5c71\u4e2d\u53e4\u6d1e\uff0c\u53ef\u60dc\u673a\u7f18\u4e00\u95ea\u800c\u901d\uff0c\u8d44\u8d28\u672a\u6709\u53d8\u5316\u3002",
                old_root=old_root,
            )
        if record.root:
            record.root = improve_root_once(record.root)
            normalize_root_profile(record)
        return EncounterResult(
            happened=True,
            success=True,
            message=f"\u4eca\u65e5\u5947\u9047\u5165\u68a6\uff0c\u7075\u6839\u7cbe\u7eaf\u5ea6\u63d0\u5347\uff0c\u8d44\u8d28\u8bc4\u5b9a\u4e3a{record.root.tier}{record.root.grade}\uff01",
            old_root=old_root,
            new_root=record.root,
        )

    return EncounterResult()

def apply_signin(record: UserRecord, today: date) -> SigninResult:
    today_text = today.isoformat()
    if record.last_sign_date == today_text:
        return SigninResult(record=record, is_first=False, already_signed=True)

    is_first = record.root is None
    if record.root is None:
        roots = draw_roots()
        record.root = roots[0]
        record.extra_roots = [] if roots[0].tier == "\u53d8\u5f02\u7075\u6839" else roots[1:]
        normalize_root_profile(record)
    else:
        ensure_legacy_extra_roots(record)

    low, high = record.root.exp_gain_range
    base_exp = random.randint(low, high)
    method_bonus = method_sign_bonus(record, base_exp)
    plant_bonus = plant_sign_bonus(record, base_exp)
    locked = is_cultivation_locked(record, today)
    pending_exp = 0 if locked else record.pending_exp
    if not locked:
        record.pending_exp = 0
    record.last_sign_date = today_text
    record.sign_count += 1
    conversion_happened, conversion_message = progress_fake_immortal_conversion(record, today)
    if conversion_happened and is_fake_immortal_conversion(record):
        exp_result = ExpApplyResult()
    else:
        exp_result = apply_exp(record, base_exp + method_bonus + plant_bonus + pending_exp, today)
    applied_exp, leveled_realms = exp_result
    if applied_exp:
        increase_array_proficiency(record, 1)
        increase_method_proficiency(record, 2)
    # 逐日签到记录：供签到日历渲染（补签另行写入 makeup 标记）
    history = dict(record.sign_history or {})
    history[today_text] = {"exp": int(applied_exp)}
    record.sign_history = history
    encounter = maybe_apply_encounter(record, today)
    breakthrough_reward = maybe_grant_breakthrough_item(record)
    record_identity_sign_day(record, today)
    tasks = ensure_daily_tasks(record, today)

    gained_fishing_chance = True
    fishing_gain = 1
    if random.random() < current_mystic_tuning().signin_extra_fishing_chance_rate:
        fishing_gain += 1
    record.fishing_chances += fishing_gain
    record.pending_fishing = record.fishing_chances
    # 签到概率掉落秘境令牌:50% 普通令牌,30% 高风险令牌(独立判定)。
    signin_normal = 1 if random.random() < 0.50 else 0
    signin_high = 1 if random.random() < 0.30 else 0
    grant_mystic_tokens(record, signin_normal, signin_high)

    return SigninResult(
        record=record,
        is_first=is_first,
        already_signed=False,
        gained_exp=applied_exp,
        pending_exp_applied=min(pending_exp, applied_exp) if pending_exp else 0,
        method_bonus_exp=min(method_bonus, applied_exp) if method_bonus else 0,
        item_bonus_exp=min(plant_bonus, applied_exp) if plant_bonus else 0,
        overflow_exp=exp_result.overflow,
        spirit_liquid_gain=exp_result.spirit_liquid,
        bottleneck_days=record.bottleneck_days,
        leveled_realms=leveled_realms,
        gained_fishing_chance=gained_fishing_chance,
        fishing_chances_gained=fishing_gain,
        encounter=encounter,
        breakthrough_reward=breakthrough_reward,
        lock_message=conversion_message or (cultivation_lock_text(record, today) if locked else ""),
        daily_tasks=tasks,
    )

def draw_fishing_rewards(count: int, record: Optional[UserRecord] = None) -> list[dict[str, Any]]:
    rewards = []
    pool = [(reward, float(reward[5])) for reward in FISHING_REWARDS]
    for _ in range(count):
        tier, grade, category, name, description, _ = weighted_choice(pool)
        if category == ARTIFACT_CATEGORY:
            raw = draw_configured_artifact_reward(tier, grade)
        else:
            raw = {
                "tier": tier,
                "grade": grade,
                "category": category,
                "name": name,
                "description": description,
            }
        rewards.append(normalize_reward(raw, record))
    return rewards

def apply_fishing(record: UserRecord, requested_count: int) -> list[dict[str, Any]]:
    count = max(1, min(requested_count, record.fishing_chances, 10))
    rewards = draw_fishing_rewards(count, record)
    shown_rewards = []
    record.fishing_chances -= count
    record.pending_fishing = record.fishing_chances
    for reward in rewards:
        reward = normalize_reward(reward, record)
        category = reward_category(reward)
        if category == "\u4ed9\u7f18":
            exp = tier_exp(INSTANT_EXP_BASE, str(reward.get("tier")), str(reward.get("grade")))
            applied_exp, leveled = apply_exp(record, exp)
            reward["used"] = True
            reward["exp_gain"] = applied_exp
            reward["leveled_realms"] = leveled
            if applied_exp < exp:
                reward["blocked"] = True
        else:
            append_reward(record, reward)
        shown_rewards.append(reward)
        bonus_reward = maybe_grant_breakthrough_item(record, source="fishing")
        if bonus_reward:
            bonus_reward["source"] = "\u74f6\u9888\u673a\u7f18"
            shown_rewards.append(bonus_reward)
        special_reward = maybe_grant_special_ability_material(record, chance=0.16, source="垂钓灵光")
        if special_reward:
            shown_rewards.append(special_reward)
    return shown_rewards

def fishing_count_from_text(text: str, chances: int) -> int:
    normalized = text.strip().lower()
    if "\u5341" in normalized or "10" in normalized:
        return min(10, chances)
    return 1

def makeup_price(day: date, today: date) -> int:
    """补签价格：300 灵石起步，每往前一天加 100，惩罚拖延。"""
    distance = max(1, (today - day).days)
    return 300 + 100 * distance

def makeup_used_this_month(record: UserRecord, today: date) -> int:
    """统计当月已补签次数（每月上限 3 次）。"""
    prefix = today.strftime("%Y-%m")
    return sum(
        1
        for key, value in (record.sign_history or {}).items()
        if str(key).startswith(prefix) and isinstance(value, dict) and value.get("makeup")
    )

def makeup_sign(record: UserRecord, day: date, today: date) -> tuple[bool, str]:
    """补签：扣灵石把当月漏掉的日子记入 sign_history。

    规则（与玩家确认的设计一致）：
    - 只能补当月内、严格早于今天、且尚无签到记录的日子
    - 每月最多补 3 次
    - 价格 = 300 + 100 × 距今天数
    - 补签只改日历不发修为，但计入连签（渲染侧按 sign_history 统计）
    """
    if day >= today:
        return False, "只能补过去的日子。"
    if (day.year, day.month) != (today.year, today.month):
        return False, "只能补本月内漏掉的日子。"
    key = day.isoformat()
    history = dict(record.sign_history or {})
    if key in history:
        return False, f"{day.month} 月 {day.day} 日已经有签到记录了。"
    if makeup_used_this_month(record, today) >= 3:
        return False, "本月补签次数已用完（每月限 3 次）。"
    price = makeup_price(day, today)
    if record.spirit_stones < price:
        return False, f"灵石不足：补签 {day.month} 月 {day.day} 日需要 {spirit_stone_text(price)}。"
    record.spirit_stones -= price
    history[key] = {"exp": 0, "makeup": True}
    record.sign_history = history
    return True, f"已补签 {day.month} 月 {day.day} 日，消耗 {spirit_stone_text(price)}。"

def signin_streak(record: UserRecord, today: date) -> int:
    """连续签到天数：从今天（或昨天）往回逐日数 sign_history，补签日计入。"""
    history = record.sign_history or {}
    cursor = today if today.isoformat() in history else today - timedelta(days=1)
    streak = 0
    while cursor.isoformat() in history:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
