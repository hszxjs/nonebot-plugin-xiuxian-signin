"""domain economy 子系统。

由原 domain.py 抽取。依赖 Layer 0+ 已提取子系统，跨子系统调用通过 _domain 延迟访问。
"""
from __future__ import annotations

import hashlib

import random
from typing import Any, Optional
from datetime import date

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

_domain = None

# 直接引用 mystic_drops 模块对象，读取其可调标量（apply_admin_config 运行时重绑）。
from . import mystic_drops as _mystic_drops_module  # noqa: E402

def shop_items_for_date(date_text: str, record: Optional[UserRecord] = None) -> list[dict[str, Any]]:
    seed = f"{date_text}:{getattr(record, 'user_id', '')}:{getattr(record, 'realm_index', '')}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    pool = [(reward, float(reward[5])) for reward in FISHING_REWARDS if reward[2] != "仙缘"]
    items = []
    for _ in range(8):
        tier, grade, category, name, description, _ = weighted_choice_rng(pool, rng)
        if category == ARTIFACT_CATEGORY:
            item = _domain.draw_configured_artifact_reward(tier, grade, rng)
        else:
            item = {"tier": tier, "grade": grade, "category": category, "name": name, "description": description}
        item = normalize_reward(item, record)
        item["price"] = reward_price(item)
        items.append(item)
    return items

def buy_shop_item(record: UserRecord, item_index: int, date_text: str) -> tuple[bool, str]:
    items = shop_items_for_date(date_text, record)
    if item_index < 1 or item_index > len(items):
        return False, f"请选择 1-{len(items)} 之间的商品编号。"
    item = normalize_reward(dict(items[item_index - 1]), record)
    allowed, reason = can_buy_reward(record, item)
    if not allowed:
        return False, reason
    price = int(item.get("price") or reward_price(item))
    record.spirit_stones -= price
    append_reward(record, item)
    return True, f"购买 {reward_display_name(item)} 成功，花费 {spirit_stone_text(price)}，剩余 {spirit_stone_text(record.spirit_stones)}。"

def sell_reward(record: UserRecord, category: str, item_index: int) -> tuple[bool, str]:
    result = pop_reward_by_category_index(record, category, item_index)
    if result is None:
        return False, f"没有找到这个编号的{category}。"
    price = recycle_price(result)
    record.spirit_stones += price
    extra = ""
    if category == ARTIFACT_CATEGORY:
        signature = reward_signature(result)
        source_uid = reward_instance_uid(result)
        remove_equipped_artifact_by_signature(record, signature, source_uid)
        removed = prune_broken_artifact_roots(record, signature, source_uid)
        if removed:
            extra = f"\n该灵器所系 {removed} 条器灵根随器离身而失效。"
    return True, f"出售 {reward_display_name(result)}，获得 {spirit_stone_text(price)}，当前共有 {spirit_stone_text(record.spirit_stones)}。{extra}"

def divination_topic(question: str) -> str:
    text = question.strip()
    if any(token in text for token in ("修行", "突破", "境界", "功法", "秘境", "渡劫", "签到")):
        return "修行"
    if any(token in text for token in ("情", "缘", "爱", "复合", "姻", "双修")):
        return "情缘"
    if any(token in text for token in ("财", "钱", "灵石", "买", "卖", "商店", "事业", "工作")):
        return "财事"
    return "通用"

def divination_pick_pair(options: Sequence[str], seed: str) -> str:
    if len(options) <= 1:
        return "、".join(options)
    first = stable_int(seed + ":a") % len(options)
    second = stable_int(seed + ":b") % len(options)
    if second == first:
        second = (second + 1) % len(options)
    return f"{options[first]}、{options[second]}"

def tianji_divination_text(record: UserRecord, question: str, today: Optional[date] = None) -> str:
    clean_question = " ".join(str(question or "").strip().split())[:80] or "未言之事"
    today = today or date.today()
    seed = f"divination:{record.user_id}:{today.isoformat()}:{clean_question}:{record.realm_index}:{record.sign_count}"
    hexagram = stable_choice(DIVINATION_HEXAGRAMS, seed + ":hexagram")
    upper = stable_choice(DIVINATION_TRIGRAMS, seed + ":upper")
    lower = stable_choice(DIVINATION_TRIGRAMS, seed + ":lower")
    changed_yao = stable_choice(DIVINATION_YAO, seed + ":yao")
    image = stable_choice(DIVINATION_IMAGES, seed + ":image")
    fortune, fortune_text = stable_choice(DIVINATION_FORTUNES, seed + ":fortune")
    topic = divination_topic(clean_question)
    advice = stable_choice(DIVINATION_TOPIC_ADVICES[topic], seed + ":advice")
    yi = divination_pick_pair(DIVINATION_YI, seed + ":yi")
    ji = divination_pick_pair(DIVINATION_JI, seed + ":ji")
    realm = record.realm if record.root else "未入门"
    root_text = record.root_summary if record.root else "未觉醒灵根"
    lines = [
        "【天机占卜】",
        f"所问：{clean_question}",
        f"命盘：{realm}，{root_text}",
        f"起卦：{hexagram}；变爻：{changed_yao}；签等：{fortune}",
        f"卦象：{upper[0]}{upper[1]}在上，{lower[0]}{lower[1]}在下；{image}",
        f"签语：{fortune_text}",
        f"断曰：上卦为{upper[2]}，下卦为{lower[2]}，此事须看时、势、心三处是否相合。",
        f"宜：{yi}",
        f"忌：{ji}",
        f"修士建议：{advice}",
        "注：此为趣味占卜，天机只露一线，取舍仍在宿主自心。",
    ]
    return "\n".join(lines)

def route_status_text(record: UserRecord) -> str:
    lines = [
        "\u3010\u4fee\u70bc\u8def\u7ebf\u3011",
        f"\u5f53\u524d\u4e3b\u8def\u7ebf\uff1a{record.cultivation_route or '\u672a\u9009\u62e9'}",
        f"\u90aa\u4fee\u540c\u4fee\uff1a{'\u5df2\u5f00\u542f' if record.evil_cultivator else '\u672a\u5f00\u542f'}",
        f"\u5b97\u95e8\u8eab\u4efd\uff1a{record.identity_summary}",
        f"\u5929\u673a\u79d8\u5883\uff1a{tianji_status_text(record)}",
        f"\u53cc\u4fee\u6b21\u6570\uff1a{hehuan_remaining_text(record)}",
        "",
        "\u3010\u4e3b\u4fee\u8def\u7ebf\u3011",
        "\u5251\u4fee\uff1a\u88c5\u5907\u5251\u7c7b\u7075\u5668\u65f6\u6218\u529b\u63d0\u534730%\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u5251\u4fee\u3002",
        "\u672f\u4fee\uff1a\u88c5\u5907\u975e\u5251\u7c7b\u7075\u5668\u65f6\u6cd5\u672f\u4f24\u5bb3\u63d0\u534730%\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u672f\u4fee\u3002",
        "\u70bc\u4e39\u5e08\uff1a\u53ef\u4f7f\u7528\u7075\u6750\u3001\u7075\u690d\u548c\u7075\u77f3\u70bc\u5236\u4e39\u836f\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u70bc\u4e39\u5e08\u3002",
        "\u9635\u6cd5\u5e08\uff1a\u9635\u6cd5\u719f\u7ec3\u5ea6\u63d0\u5347\u66f4\u5feb\uff0c\u9635\u6cd5\u6548\u679c\u63d0\u534750%\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u9635\u6cd5\u5e08\u3002",
        "\u70bc\u5668\u5e08\uff1a\u53ef\u4f7f\u7528\u7075\u6750\u548c\u7075\u77f3\u70bc\u5236\u7075\u5668\u3001\u9635\u76d8\u4e0e\u4eff\u5236\u4ed9\u5e1d\u5175\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8def\u7ebf \u70bc\u5668\u5e08\u3002",
        "",
        "\u3010\u90aa\u4fee\u540c\u4fee\u3011",
        "\u6307\u4ee4\uff1a\u9009\u62e9\u90aa\u4fee / \u9000\u51fa\u90aa\u4fee\u3002\u90aa\u4fee\u53ef\u4e0e\u4e3b\u8def\u7ebf\u5e76\u5b58\uff0c\u4f46\u574f\u7ed3\u5c40\u60e9\u7f5a\u66f4\u91cd\u3002",
        "",
        "\u3010\u5b97\u95e8\u8eab\u4efd\u600e\u4e48\u9009\u3011",
        "\u5929\u673a\u9601\u5f1f\u5b50\uff1a\u9700\u7b51\u57fa\uff0c\u6bcf7\u5929\u4e00\u6b21\u7279\u6b8a\u79d8\u5883\u793a\u8b66\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8eab\u4efd \u5929\u673a\u9601\u5f1f\u5b50\u3002",
        "\u5929\u673a\u9601\u957f\u8001\uff1a\u9700\u5143\u5a74\uff0c\u4e14\u5f1f\u5b50\u8eab\u4efd\u7b7e\u523010\u5929\uff0c\u6bcf5\u5929\u4e00\u6b21\u793a\u8b66\u79d8\u5883\u3002",
        "\u5929\u673a\u9601\u592a\u4e0a\u957f\u8001\uff1a\u9700\u70bc\u865a\uff0c\u4e14\u957f\u8001\u8eab\u4efd\u7b7e\u523030\u5929\uff0c\u6bcf\u5929\u4e00\u6b21\u793a\u8b66\u79d8\u5883\u3002",
        "\u5408\u6b22\u5b97\u5f1f\u5b50\uff1a\u9700\u7ec3\u6c14\u4e2d\u671f\uff0c\u6bcf\u59291\u6b21\u53cc\u4fee\uff1b\u6307\u4ee4\uff1a\u9009\u62e9\u8eab\u4efd \u5408\u6b22\u5b97\u5f1f\u5b50\u3002",
        "\u5408\u6b22\u5b97\u957f\u8001\uff1a\u9700\u91d1\u4e39\uff0c\u4e14\u5f1f\u5b50\u8eab\u4efd\u7b7e\u523010\u5929\uff0c\u6bcf\u59292\u6b21\u53cc\u4fee\u3002",
        "\u5408\u6b22\u5b97\u592a\u4e0a\u957f\u8001\uff1a\u9700\u5316\u795e\uff0c\u4e14\u957f\u8001\u8eab\u4efd\u7b7e\u523020\u5929\uff0c\u6bcf\u59295\u6b21\u53cc\u4fee\u3002",
    ]
    return "\n".join(lines)

def choose_cultivation_route(record: UserRecord, route: str) -> tuple[bool, str]:
    route = route.strip()
    if route not in CULTIVATION_ROUTES:
        return False, f"路线可选：{'、'.join(CULTIVATION_ROUTES)}。"
    old = record.cultivation_route or "未选择"
    record.cultivation_route = route
    return True, f"修炼路线已从{old}调整为{route}。"

def choose_evil_cultivation(record: UserRecord, enabled: bool = True) -> tuple[bool, str]:
    record.evil_cultivator = enabled
    if enabled:
        return True, "已同修邪修路线。秘境中不会因邪修陷阱直接落入坏结局，若真正反噬则进入5分钟禁修期。"
    return True, "已暂离邪修路线。"

def identity_days(record: UserRecord, identity: str) -> int:
    return int((record.identity_sign_days or {}).get(identity, 0))

def choose_faction_identity(record: UserRecord, identity: str) -> tuple[bool, str]:
    identity = identity.strip()
    if identity not in FACTION_IDENTITIES:
        return False, f"身份可选：{'、'.join(FACTION_IDENTITIES)}。"
    requirements = {
        "天机阁弟子": (2, 0.0, None, 0, "筑基修为"),
        "天机阁长老": (4, 0.0, "天机阁弟子", 10, "元婴修为，且天机阁弟子签到10天"),
        "天机阁太上长老": (6, 0.0, "天机阁长老", 30, "炼虚修为，且天机阁长老签到30天"),
        "合欢宗弟子": (1, 0.3, None, 0, "练气中期"),
        "合欢宗长老": (3, 0.0, "合欢宗弟子", 10, "金丹修为，且合欢宗弟子签到10天"),
        "合欢宗太上长老": (5, 0.0, "合欢宗长老", 20, "化神修为，且合欢宗长老签到20天"),
    }
    realm_index, ratio, previous, days, text = requirements[identity]
    if not has_realm_progress(record, realm_index, ratio):
        return False, f"选择{identity}需要{text}。"
    if previous and identity_days(record, previous) < days:
        return False, f"选择{identity}需要{previous}身份签到{days}天，当前{identity_days(record, previous)}天。"
    old = record.faction_identity or "暂无身份"
    record.faction_identity = identity
    return True, f"身份令牌已由{old}更换为{identity}。"

def record_identity_sign_day(record: UserRecord, today: date) -> None:
    identity = record.faction_identity
    if not identity:
        return
    if record.identity_sign_days is None:
        record.identity_sign_days = {}
    record.identity_sign_days[identity] = int(record.identity_sign_days.get(identity, 0)) + 1

def hehuan_daily_limit(record: UserRecord) -> int:
    return HEHUAN_DAILY_LIMITS.get(record.faction_identity or "", 0)

def hehuan_remaining(record: UserRecord, today: Optional[date] = None) -> int:
    today_text = (today or date.today()).isoformat()
    if record.dual_cultivation_date != today_text:
        return hehuan_daily_limit(record)
    return max(0, hehuan_daily_limit(record) - int(record.dual_cultivation_used))

def hehuan_remaining_text(record: UserRecord, today: Optional[date] = None) -> str:
    limit = hehuan_daily_limit(record)
    if limit <= 0:
        return "无"
    return f"{hehuan_remaining(record, today)}/{limit}"

def special_cultivation_exp(record: UserRecord) -> int:
    method = record.equipped_method
    if not method:
        low, high = record.root.exp_gain_range if record.root else (4, 8)
        return max(4, (low + high) // 2)
    base = METHOD_CHAT_BASE.get(str(method.get("tier")), 0.8) * 10
    return max(8, int(base * grade_ratio(str(method.get("grade"))) * array_multiplier(record, method) * 2))

def apply_dual_cultivation(actor: UserRecord, target: UserRecord, today: date) -> tuple[bool, str]:
    if hehuan_daily_limit(actor) <= 0:
        return False, "当前身份没有双修次数，请先选择合欢宗身份。"
    if hehuan_remaining(actor, today) <= 0:
        return False, "今日双修次数已用完。"
    if is_cultivation_locked(actor, today) or is_cultivation_locked(target, today):
        return False, "双方有人处于禁修期，无法通过任何手段提升修为。"
    exp = special_cultivation_exp(actor)
    actor_exp, _ = apply_exp(actor, exp, today)
    target_exp, _ = apply_exp(target, exp, today)
    today_text = today.isoformat()
    if actor.dual_cultivation_date != today_text:
        actor.dual_cultivation_date = today_text
        actor.dual_cultivation_used = 0
    actor.dual_cultivation_used += 1
    return True, f"双修完成，双方各得修为：发起者 +{actor_exp}，对象 +{target_exp}。今日剩余 {hehuan_remaining(actor, today)} 次。"

def tianji_status_text(record: UserRecord, today: Optional[date] = None) -> str:
    cooldown = TIANJI_COOLDOWN_DAYS.get(record.faction_identity or "")
    if not cooldown:
        return "无"
    today = today or date.today()
    last = parse_lock_until(record.last_tianji_mystic_date)
    if last is None:
        return "可用"
    remain = cooldown - (today - last).days
    return "可用" if remain <= 0 else f"冷却{remain}天"

def generate_daily_tasks(record: UserRecord, today: date) -> list[dict[str, Any]]:
    seed = int(hashlib.sha256(f"{record.user_id}:{today.isoformat()}".encode("utf-8")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    tasks = []
    templates = rng.sample(DAILY_TASK_TEMPLATES, k=5)
    for template in templates:
        realm_label = realm_short_name(record.realm_name if record.root else "炼体期")
        exp = 10 + max(1, record.realm_index + 1) * rng.randint(3, 7)
        stones = 15 + max(1, record.realm_index + 1) * rng.randint(5, 12)
        fishing = 1 if rng.random() < 0.16 else 0
        tasks.append({"title": template.format(realm=realm_label), "exp": exp, "stones": stones, "fishing": fishing, "done": False})
    # 随机选 1 个任务作为“令牌任务”:完成后奖励 1 枚普通秘境令牌。
    token_index = rng.randrange(len(tasks))
    tasks[token_index]["token_normal"] = 1
    tasks[token_index]["title"] += "（秘境令牌）"
    record.daily_tasks = {"date": today.isoformat(), "tasks": tasks}
    return tasks

def ensure_daily_tasks(record: UserRecord, today: date) -> list[dict[str, Any]]:
    if not isinstance(record.daily_tasks, dict) or record.daily_tasks.get("date") != today.isoformat():
        return generate_daily_tasks(record, today)
    tasks = record.daily_tasks.get("tasks", [])
    return list(tasks) if isinstance(tasks, list) else generate_daily_tasks(record, today)

def daily_tasks_text(record: UserRecord, today: Optional[date] = None) -> str:
    tasks = ensure_daily_tasks(record, today or date.today())
    lines = ["【每日任务】", f"灵石：{spirit_stone_text(record.spirit_stones)}"]
    for index, task in enumerate(tasks, start=1):
        status = "已完成" if task.get("done") else "未完成"
        reward = f"修为+{int(task.get('exp', 0))}，灵石+{spirit_stone_text(int(task.get('stones', 0)))}"
        if int(task.get("fishing", 0)):
            reward += f"，垂钓+{int(task.get('fishing', 0))}"
        if int(task.get("token_normal", 0)):
            reward += f"，普通秘境令牌+{int(task.get('token_normal', 0))}"
        if int(task.get("token_high", 0)):
            reward += f"，高风险秘境令牌+{int(task.get('token_high', 0))}"
        lines.append(f"{index}. {task.get('title')} | {status} | {reward}")
    lines.append("发送“完成任务 编号”领取对应奖励。")
    return "\n".join(lines)

def complete_daily_task(record: UserRecord, task_index: int, today: date) -> tuple[bool, str]:
    tasks = ensure_daily_tasks(record, today)
    if task_index < 1 or task_index > len(tasks):
        return False, f"请选择 1-{len(tasks)} 之间的任务编号。"
    task = tasks[task_index - 1]
    if task.get("done"):
        return False, "这个任务今日已经完成。"
    if is_cultivation_locked(record, today):
        return False, blocked_cultivation_message(record)
    task["done"] = True
    exp = int(task.get("exp", 0))
    stones = int(task.get("stones", 0))
    fishing = int(task.get("fishing", 0))
    applied_result = apply_exp(record, exp, today)
    applied, leveled = applied_result
    record.spirit_stones += stones
    record.fishing_chances += fishing
    token_grants = _domain.grant_mystic_tokens(
        record,
        int(task.get("token_normal", 0)),
        int(task.get("token_high", 0)),
    )
    record.daily_tasks = {"date": today.isoformat(), "tasks": tasks}
    extra = f"，连破{leveled}境" if leveled else ""
    fish_text = f"，垂钓+{fishing}" if fishing else ""
    token_text = "".join(
        f"，{name}+{count}"
        for name, count in token_grants.items()
        if count
    )
    return True, f"完成任务：{task.get('title')}。修为+{applied}{extra}，灵石+{spirit_stone_text(stones)}{fish_text}{token_text}。"

def batch_sell_rewards(record: UserRecord, category: str, limit: int = 999) -> tuple[bool, str]:
    category = str(category).strip()
    if category not in REWARD_CATEGORIES and category != IMMORTAL_SEED_CATEGORY:
        return False, "\u7c7b\u522b\u53ef\u9009\uff1a" + "\u3001".join(REWARD_CATEGORIES + [IMMORTAL_SEED_CATEGORY])
    sold = []
    kept = []
    total = 0
    for reward in record.rewards or []:
        if reward_category(reward) == category and len(sold) < max(1, int(limit)):
            if is_unique_reward(reward):
                kept.append(reward)
                continue
            sold.append(normalize_reward(reward, record))
            total += recycle_price(reward)
        else:
            kept.append(reward)
    if not sold:
        return False, f"\u6ca1\u6709\u53ef\u6279\u91cf\u51fa\u552e\u7684{category}\u3002\u552f\u4e00\u9053\u5177\u4e0d\u4f1a\u88ab\u6279\u91cf\u51fa\u552e\u3002"
    record.rewards = kept
    record.spirit_stones += total
    return True, f"\u6279\u91cf\u51fa\u552e{category} {len(sold)} \u4ef6\uff0c\u83b7\u5f97 {spirit_stone_text(total)}\uff0c\u5f53\u524d\u5171 {spirit_stone_text(record.spirit_stones)}\u3002"

def batch_sell_low_realm_artifacts(record: UserRecord, limit: int = 999) -> tuple[bool, str]:
    sold = []
    kept = []
    total = 0
    try:
        max_count = max(1, int(limit))
    except (TypeError, ValueError):
        max_count = 999
    current_realm = max(0, int(record.realm_index))
    equipped_items = list(artifact_slots(record).values())
    equipped_uids = {reward_instance_uid(item) for item in equipped_items if reward_instance_uid(item)}
    equipped_signatures: dict[str, int] = {}
    for item in equipped_items:
        if reward_instance_uid(item):
            continue
        signature = reward_signature(item)
        if signature:
            equipped_signatures[signature] = equipped_signatures.get(signature, 0) + 1
    for reward in record.rewards or []:
        if reward_category(reward) == ARTIFACT_CATEGORY and len(sold) < max_count:
            normalized = normalize_reward(dict(reward), record)
            uid = reward_instance_uid(normalized)
            signature = reward_signature(normalized)
            if uid and uid in equipped_uids:
                kept.append(reward)
                continue
            if signature and equipped_signatures.get(signature, 0) > 0:
                equipped_signatures[signature] -= 1
                kept.append(reward)
                continue
            if is_unique_reward(normalized):
                kept.append(reward)
                continue
            if item_required_realm_index(normalized) < current_realm:
                sold.append(normalized)
                total += recycle_price(normalized)
                continue
        kept.append(reward)
    if not sold:
        return False, "没有可批量出售的低阶灵器。只会出售背包内低于自身境界、且非唯一的灵器；已装备灵器会保留。"
    record.rewards = kept
    record.spirit_stones += total
    return True, f"批量出售低阶灵器 {len(sold)} 件，获得 {spirit_stone_text(total)}，当前共有 {spirit_stone_text(record.spirit_stones)}。已装备灵器未受影响。"
