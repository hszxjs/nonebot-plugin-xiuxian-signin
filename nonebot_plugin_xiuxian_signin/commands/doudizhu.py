"""斗地主命令子模块。

自包含的斗地主玩法：触发词、卡牌引擎、matcher 与 handler。
外部 helper 通过 _g（插件入口模块）延迟访问，store 经 state 获取。
"""
from __future__ import annotations

from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher
from nonebot.rule import Rule

from ..state import store

# 插件入口模块引用（由 commands/__init__.py 注入），用于延迟访问 finish_panel 等 helper。
_g = None

DOUDIZHU_HELP_TEXTS = {"斗地主帮助", "斗地主规则", "斗牌帮助"}
DOUDIZHU_TEXTS = {
    "斗地主",
    "斗地主开桌",
    "加入斗地主",
    "退出斗地主",
    "开始斗地主",
    "人机斗地主",
    "手牌",
    "提示",
    "托管",
    "结束斗地主",
    "叫地主",
    "不叫",
    "抢地主",
    "不抢",
    "施加威压",
    "保留地主",
    "放弃地主",
    "加倍",
    "不加倍",
    "不要",
} | DOUDIZHU_HELP_TEXTS
DOUDIZHU_PLAY_PREFIXES = ("出牌", "打牌")
DOUDIZHU_BID_PREFIXES = ("叫分",)

DDZ_RANKS = ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2", "小王", "大王"]

DDZ_VALUES = {rank: index for index, rank in enumerate(DDZ_RANKS)}

DDZ_HUMAN_WAIT_SECONDS = 120

def doudizhu_group_key(event: GroupMessageEvent) -> str:
    return str(event.group_id)


def is_doudizhu_play_text(text: str) -> bool:
    return any(text == prefix or text.startswith(prefix) for prefix in DOUDIZHU_PLAY_PREFIXES)


def is_doudizhu_bid_text(text: str) -> bool:
    return text in {"叫地主", "不叫"} or any(text == prefix or text.startswith(prefix) for prefix in DOUDIZHU_BID_PREFIXES)


def is_doudizhu_command_text(text: str) -> bool:
    return (
        text in DOUDIZHU_TEXTS
        or is_doudizhu_play_text(text)
        or is_doudizhu_bid_text(text)
    )


def is_doudizhu_entry_text(text: str) -> bool:
    return text in DOUDIZHU_HELP_TEXTS or text in {"\u6597\u5730\u4e3b", "\u6597\u5730\u4e3b\u5f00\u684c", "\u4eba\u673a\u6597\u5730\u4e3b"}


def doudizhu_help_text() -> str:
    return "\n".join(
        [
            "【斗地主帮助】",
            "开桌流程：斗地主开桌 -> 加入斗地主 -> 开始斗地主；也可直接人机斗地主。",
            "手牌会私聊发送，群内发送手牌可重新查看。",
            "叫分阶段：叫分 1/2/3，或发送叫地主 / 不叫。分数最高者进入抢地主阶段。",
            "抢地主阶段：其他玩家可发送抢地主 / 不抢。高修为玩家可发送施加威压提高抢夺概率。",
            "威压成功后，原定地主可以发送保留地主 / 放弃地主。若保留，牌局结束后强制进行普通斗法。",
            "地主确定后进入加倍阶段，发送加倍 / 不加倍；每次加倍会翻倍最终倍数。",
            "出牌：出牌 34567、出牌 3334、出牌 小王大王；跟不上发送不要。",
            "修仙牌型：炸弹显示为雷劫，王炸显示为天罚雷劫，触发后都会让当前倍数翻倍。",
            "春天 / 反春天已实装：达成条件时会在结算面板中标记，并再翻倍。",
            "其他指令：提示 / 托管 / 结束斗地主。",
        ]
    )


def ddz_new_deck() -> list[str]:
    deck = []
    for rank in DDZ_RANKS[:-2]:
        deck.extend([rank] * 4)
    deck.extend(["小王", "大王"])
    random.shuffle(deck)
    return deck


def ddz_sort_cards(cards: list[str]) -> list[str]:
    return sorted(cards, key=lambda card: (DDZ_VALUES.get(card, -1), card))


def ddz_cards_text(cards: list[str]) -> str:
    return " ".join(ddz_sort_cards(list(cards))) or "无"


def ddz_parse_cards(text: str) -> list[str]:
    stripped = text.strip()
    for prefix in DOUDIZHU_PLAY_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):].strip()
            break
    stripped = stripped.replace("王炸", "小王 大王").replace("双王", "小王 大王").replace("天罚雷劫", "小王 大王")
    for sep in [",", "，", "、", ";", "；", "|", "/"]:
        stripped = stripped.replace(sep, " ")
    result: list[str] = []
    index = 0
    compact = "".join(stripped.split())
    while index < len(compact):
        matched = None
        for token in ("小王", "大王", "10", "J", "Q", "K", "A", "2", "3", "4", "5", "6", "7", "8", "9"):
            if compact.startswith(token, index):
                matched = token
                break
        if matched is None:
            return []
        result.append(matched)
        index += len(matched)
    return result


def ddz_has_cards(hand: list[str], cards: list[str]) -> bool:
    hand_counter = Counter(hand)
    for card, count in Counter(cards).items():
        if hand_counter[card] < count:
            return False
    return True


def ddz_remove_cards(hand: list[str], cards: list[str]) -> None:
    for card in cards:
        hand.remove(card)


def ddz_is_consecutive(ranks: list[str]) -> bool:
    values = [DDZ_VALUES[rank] for rank in ranks]
    return all(values[i] + 1 == values[i + 1] for i in range(len(values) - 1))


def ddz_no_high_sequence(ranks: list[str]) -> bool:
    return all(rank not in {"2", "小王", "大王"} for rank in ranks)


def ddz_analyze_cards(cards: list[str]) -> Optional[dict[str, Any]]:
    if not cards:
        return None
    cards = ddz_sort_cards(cards)
    total = len(cards)
    counts = Counter(cards)
    count_values = sorted(counts.values(), reverse=True)
    ranks = sorted(counts, key=lambda rank: DDZ_VALUES[rank])
    if total == 2 and set(cards) == {"小王", "大王"}:
        return {"type": "rocket", "main": DDZ_VALUES["大王"], "length": 2, "label": "天罚雷劫"}
    if total == 4 and len(counts) == 1:
        return {"type": "bomb", "main": DDZ_VALUES[ranks[0]], "length": 4, "label": f"{ranks[0]}重雷劫"}
    if total == 1:
        return {"type": "single", "main": DDZ_VALUES[cards[0]], "length": 1, "label": "单牌"}
    if total == 2 and len(counts) == 1:
        return {"type": "pair", "main": DDZ_VALUES[ranks[0]], "length": 1, "label": "对子"}
    if total == 3 and len(counts) == 1:
        return {"type": "triple", "main": DDZ_VALUES[ranks[0]], "length": 1, "label": "三同"}
    if total == 4 and count_values == [3, 1]:
        triple = next(rank for rank, count in counts.items() if count == 3)
        return {"type": "triple_single", "main": DDZ_VALUES[triple], "length": 1, "label": "三带一"}
    if total == 5 and count_values == [3, 2]:
        triple = next(rank for rank, count in counts.items() if count == 3)
        return {"type": "triple_pair", "main": DDZ_VALUES[triple], "length": 1, "label": "三带一对"}
    if total >= 5 and len(counts) == total and ddz_no_high_sequence(ranks) and ddz_is_consecutive(ranks):
        return {"type": "straight", "main": DDZ_VALUES[ranks[-1]], "length": total, "label": f"{total}连顺"}
    if total >= 6 and total % 2 == 0 and all(count == 2 for count in counts.values()) and ddz_no_high_sequence(ranks) and ddz_is_consecutive(ranks):
        return {"type": "pair_chain", "main": DDZ_VALUES[ranks[-1]], "length": total // 2, "label": f"{total // 2}连对"}
    triple_ranks = sorted([rank for rank, count in counts.items() if count == 3], key=lambda rank: DDZ_VALUES[rank])
    if len(triple_ranks) >= 2 and ddz_no_high_sequence(triple_ranks) and ddz_is_consecutive(triple_ranks):
        wings = total - len(triple_ranks) * 3
        if wings == 0:
            return {"type": "airplane", "main": DDZ_VALUES[triple_ranks[-1]], "length": len(triple_ranks), "label": f"飞舟{len(triple_ranks)}舱"}
        if wings == len(triple_ranks):
            return {"type": "airplane_single", "main": DDZ_VALUES[triple_ranks[-1]], "length": len(triple_ranks), "label": f"飞舟带翼{len(triple_ranks)}舱"}
        if wings == len(triple_ranks) * 2:
            pair_wings = [rank for rank, count in counts.items() if count == 2]
            if len(pair_wings) == len(triple_ranks):
                return {"type": "airplane_pair", "main": DDZ_VALUES[triple_ranks[-1]], "length": len(triple_ranks), "label": f"飞舟载侣{len(triple_ranks)}舱"}
    return None


def ddz_can_beat(play: dict[str, Any], last_play: Optional[dict[str, Any]]) -> bool:
    if not last_play:
        return True
    if play["type"] == "rocket":
        return last_play["type"] != "rocket"
    if play["type"] == "bomb" and last_play["type"] not in {"bomb", "rocket"}:
        return True
    if play["type"] != last_play["type"]:
        return False
    if int(play.get("length", 0)) != int(last_play.get("length", 0)):
        return False
    return int(play["main"]) > int(last_play["main"])


def ddz_player(table: dict[str, Any], user_id: str) -> Optional[dict[str, Any]]:
    for player in table.get("players", []):
        if str(player.get("id")) == str(user_id):
            return player
    return None


def ddz_current_player(table: dict[str, Any]) -> dict[str, Any]:
    return table["players"][int(table.get("current", 0)) % len(table["players"])]


def ddz_next_turn(table: dict[str, Any]) -> None:
    table["current"] = (int(table.get("current", 0)) + 1) % len(table["players"])


def ddz_player_line(player: dict[str, Any], table: dict[str, Any]) -> str:
    role = "地主" if str(player.get("id")) == str(table.get("landlord")) else "散修"
    bot = "机关傀儡" if player.get("bot") else ""
    doubled = "已加倍" if str(player.get("id")) in set(table.get("double_votes", [])) else "未加倍"
    return f"{player.get('name')}｜{role}{bot}｜剩{len(player.get('hand', []))}张｜{doubled}"


def ddz_table_text(table: dict[str, Any], extra: str = "") -> str:
    lines = ["【斗地主牌局】", f"阶段：{table.get('phase_text', table.get('phase', '未知'))}"]
    if table.get("landlord"):
        landlord = ddz_player(table, str(table.get("landlord")))
        lines.append(f"地主：{landlord.get('name') if landlord else table.get('landlord')}｜倍数 {table.get('multiplier', 1)}x")
    if table.get("bottom"):
        lines.append(f"底牌：{ddz_cards_text(list(table.get('bottom', [])))}")
    if table.get("last_play"):
        last_player = ddz_player(table, str(table.get("last_player")))
        lines.append(f"上一手：{last_player.get('name') if last_player else '未知'} {table['last_play']['label']} [{ddz_cards_text(table['last_play']['cards'])}]")
    lines.append("玩家：")
    for player in table.get("players", []):
        marker = " ->" if player is ddz_current_player(table) and table.get("phase") == "playing" else ""
        lines.append(f"{marker}{ddz_player_line(player, table)}")
    if extra:
        lines.append("")
        lines.extend(str(extra).splitlines())
    return "\n".join(lines)


def ddz_hand_text(player: dict[str, Any], table: dict[str, Any]) -> str:
    lines = [f"【{player.get('name')}的手牌】", ddz_cards_text(list(player.get("hand", [])))]
    if table.get("phase") == "playing":
        current = ddz_current_player(table)
        lines.append(f"当前出牌：{current.get('name')}")
    if table.get("last_play"):
        lines.append(f"上一手：{table['last_play']['label']} [{ddz_cards_text(table['last_play']['cards'])}]")
    lines.append("指令：出牌 34567 / 不要 / 提示")
    return "\n".join(lines)


def ddz_deal(table: dict[str, Any]) -> None:
    deck = ddz_new_deck()
    for index, player in enumerate(table["players"]):
        player["hand"] = ddz_sort_cards(deck[index * 17:(index + 1) * 17])
        player["bid"] = None
    table["bottom"] = ddz_sort_cards(deck[51:54])
    table["phase"] = "bidding"
    table["phase_text"] = "叫分"
    table["current"] = random.randrange(0, 3)
    table["highest_bid"] = 0
    table["landlord_candidate"] = None
    table["original_landlord"] = None
    table["bid_count"] = 0
    table["rob_passes"] = set()
    table["double_responses"] = set()
    table["double_votes"] = set()
    table["multiplier"] = 1
    table["last_play"] = None
    table["last_player"] = None
    table["pass_count"] = 0
    table["landlord_play_count"] = 0
    table["farmer_play_count"] = 0
    table["pressure_duel"] = None


def ddz_finalize_landlord(table: dict[str, Any], landlord_id: str) -> None:
    table["landlord"] = str(landlord_id)
    table["original_landlord"] = table.get("original_landlord") or str(landlord_id)
    landlord = ddz_player(table, str(landlord_id))
    if landlord:
        landlord["hand"] = ddz_sort_cards(list(landlord.get("hand", [])) + list(table.get("bottom", [])))
    table["phase"] = "double"
    table["phase_text"] = "加倍"
    table["double_responses"] = set()
    table["double_votes"] = set()


def ddz_start_play(table: dict[str, Any]) -> None:
    landlord_id = str(table.get("landlord"))
    table["phase"] = "playing"
    table["phase_text"] = "出牌"
    for idx, player in enumerate(table["players"]):
        if str(player.get("id")) == landlord_id:
            table["current"] = idx
            break


def ddz_bid_status(table: dict[str, Any]) -> str:
    current = ddz_current_player(table)
    lines = ["【叫分阶段】", f"当前轮到：{current.get('name')}", f"当前最高分：{table.get('highest_bid', 0)}"]
    lines.append("可发送：叫分 1 / 叫分 2 / 叫分 3 / 叫地主 / 不叫")
    return "\n".join(lines)


def ddz_begin_rob_text(table: dict[str, Any]) -> str:
    candidate = ddz_player(table, str(table.get("landlord_candidate")))
    names = [p.get("name") for p in table["players"] if str(p.get("id")) != str(table.get("landlord_candidate"))]
    return "\n".join([
        "【抢地主阶段】",
        f"候选地主：{candidate.get('name') if candidate else '未知'}",
        f"可抢修士：{'、'.join(names)}",
        "修为越高，抢夺成功率越高；施加威压会额外提升概率。",
        "可发送：抢地主 / 不抢 / 施加威压",
    ])


def ddz_pressure_chance(actor_power: int, target_power: int, pressure: bool = False) -> float:
    diff = actor_power - target_power
    chance = 0.35 + max(-0.25, min(0.25, diff / max(1, target_power + actor_power) * 1.6))
    if pressure:
        chance += 0.20
    return max(0.10, min(0.85, chance))


def ddz_generate_basic_candidates(hand: list[str]) -> list[list[str]]:
    counter = Counter(hand)
    candidates: list[list[str]] = []
    for rank in DDZ_RANKS:
        if counter[rank] >= 1:
            candidates.append([rank])
    for rank in DDZ_RANKS:
        if counter[rank] >= 2:
            candidates.append([rank, rank])
    for rank in DDZ_RANKS:
        if counter[rank] >= 3:
            candidates.append([rank, rank, rank])
    for rank in DDZ_RANKS:
        if counter[rank] >= 4:
            candidates.append([rank, rank, rank, rank])
    if counter["小王"] and counter["大王"]:
        candidates.append(["小王", "大王"])
    return candidates


def ddz_find_hint(hand: list[str], last_play: Optional[dict[str, Any]]) -> Optional[list[str]]:
    for cards in ddz_generate_basic_candidates(hand):
        analyzed = ddz_analyze_cards(cards)
        if analyzed and ddz_can_beat(analyzed, last_play):
            return cards
    return None


def ddz_bot_should_double(player: dict[str, Any]) -> bool:
    hand = list(player.get("hand", []))
    counter = Counter(hand)
    bombs = sum(1 for rank, count in counter.items() if count == 4)
    jokers = int(counter["小王"] > 0 and counter["大王"] > 0)
    high_cards = sum(1 for card in hand if DDZ_VALUES.get(card, 0) >= DDZ_VALUES["A"])
    return bombs + jokers > 0 or high_cards >= 6


def ddz_bot_play(player: dict[str, Any], table: dict[str, Any]) -> tuple[bool, str]:
    last_play = table.get("last_play") if str(table.get("last_player")) != str(player.get("id")) else None
    cards = ddz_find_hint(list(player.get("hand", [])), last_play)
    if not cards:
        return False, f"{player.get('name')} 选择不出"
    analyzed = ddz_analyze_cards(cards)
    if not analyzed:
        return False, f"{player.get('name')} 选择不出"
    ddz_remove_cards(player["hand"], cards)
    table["last_play"] = {**analyzed, "cards": cards}
    table["last_player"] = str(player.get("id"))
    table["pass_count"] = 0
    if analyzed["type"] in {"bomb", "rocket"}:
        table["multiplier"] = int(table.get("multiplier", 1)) * 2
    if str(player.get("id")) == str(table.get("landlord")):
        table["landlord_play_count"] = int(table.get("landlord_play_count", 0)) + 1
    else:
        table["farmer_play_count"] = int(table.get("farmer_play_count", 0)) + 1
    return True, f"{player.get('name')} 打出 {analyzed['label']}：{ddz_cards_text(cards)}"


async def ddz_send_hand(player: dict[str, Any], table: dict[str, Any], group_id: Optional[str] = None) -> None:
    if player.get("bot"):
        return
    bot = get_bot()
    record = await store.get_user(str(player.get("id")))
    message = _g.panel_segment("斗地主手牌", ddz_hand_text(player, table), record, icon="poker")
    try:
        await bot.send_private_msg(user_id=int(player["id"]), message=message)
    except Exception as exc:
        logger.debug(f"发送斗地主手牌私聊失败: {player.get('id')} {exc}")
        if group_id:
            await bot.send_group_msg(group_id=int(group_id), message=_g.panel_segment("斗地主手牌", "私聊手牌发送失败，请检查好友或临时会话权限。", record, icon="warning"))


async def ddz_send_all_hands(table: dict[str, Any], group_id: str) -> None:
    await asyncio.gather(*(ddz_send_hand(player, table, group_id) for player in table.get("players", []) if not player.get("bot")))


async def start_forced_normal_duel(group_id: str, left_id: str, right_id: str, left_name: str, right_name: str) -> str:
    if group_duel_session(group_id):
        return "本群已有普通斗法进行中，威压约战暂时顺延。"
    start_at = time.monotonic() + NORMAL_DUEL_PREPARE_SECONDS
    session = {
        "left_id": str(left_id),
        "right_id": str(right_id),
        "left_name": left_name,
        "right_name": right_name,
        "created_at": time.monotonic(),
        "start_at": start_at,
        "end_at": start_at + NORMAL_DUEL_DURATION_SECONDS,
        "active": False,
        "actions": {str(left_id): [], str(right_id): []},
    }
    normal_duel_sessions[group_id] = session
    asyncio.create_task(send_normal_duel_prepare_messages(session))
    asyncio.create_task(finish_normal_duel(group_id, session))
    return f"威压结算：{left_name} 与 {right_name} 将在 1 分钟后强制进行普通斗法。"


async def ddz_finish_game(group_id: str, table: dict[str, Any], winner_id: str) -> str:
    landlord_id = str(table.get("landlord"))
    landlord_win = str(winner_id) == landlord_id
    winner = ddz_player(table, str(winner_id))
    landlord = ddz_player(table, landlord_id)
    spring = False
    spring_name = ""
    if landlord_win and int(table.get("farmer_play_count", 0)) == 0:
        spring = True
        spring_name = "春天"
    elif not landlord_win and int(table.get("landlord_play_count", 0)) <= 1:
        spring = True
        spring_name = "反春天"
    if spring:
        table["multiplier"] = int(table.get("multiplier", 1)) * 2
    lines = ["【斗地主结算】"]
    lines.append(f"胜方：{'地主' if landlord_win else '农家'}｜定胜修士：{winner.get('name') if winner else winner_id}")
    lines.append(f"地主：{landlord.get('name') if landlord else landlord_id}")
    lines.append(f"最终倍数：{table.get('multiplier', 1)}x" + (f"｜{spring_name}" if spring else ""))
    lines.append("剩余手牌：")
    for player in table.get("players", []):
        lines.append(f"{player.get('name')}｜剩{len(player.get('hand', []))}张｜[{ddz_cards_text(list(player.get('hand', [])))}]")
    duel_info = table.get("pressure_duel")
    if duel_info:
        duel_message = await _g.start_forced_normal_duel(
            group_id,
            str(duel_info.get("left_id")),
            str(duel_info.get("right_id")),
            str(duel_info.get("left_name")),
            str(duel_info.get("right_name")),
        )
        lines.append("")
        lines.append(duel_message)
    doudizhu_tables.pop(group_id, None)
    return "\n".join(lines)


def ddz_hand_strength(hand: list[str]) -> int:
    counter = Counter(hand)
    score = sum(DDZ_VALUES.get(card, 0) for card in hand)
    score += sum(16 for _rank, count in counter.items() if count == 4)
    if counter["小王"] and counter["大王"]:
        score += 24
    score += sum(5 for card in hand if card in {"2", "小王", "大王"})
    return score


def ddz_bot_bid_value(player: dict[str, Any], highest: int) -> int:
    strength = ddz_hand_strength(list(player.get("hand", [])))
    wanted = 0
    if strength >= 145:
        wanted = 3
    elif strength >= 126:
        wanted = 2
    elif strength >= 108:
        wanted = 1
    return wanted if wanted > highest else 0


def ddz_apply_bid(table: dict[str, Any], player: dict[str, Any], bid: int) -> str:
    table["bid_count"] = int(table.get("bid_count", 0)) + 1
    player["bid"] = bid
    if bid > int(table.get("highest_bid", 0)):
        table["highest_bid"] = bid
        table["landlord_candidate"] = str(player.get("id"))
        return f"{player.get('name')} 叫分 {bid}"
    return f"{player.get('name')} 不叫"


def ddz_after_bid(table: dict[str, Any]) -> Optional[str]:
    if int(table.get("highest_bid", 0)) >= 3 or int(table.get("bid_count", 0)) >= len(table.get("players", [])):
        if not table.get("landlord_candidate"):
            ddz_deal(table)
            return "无人叫地主，重新洗牌。\n" + ddz_bid_status(table)
        table["phase"] = "rob"
        table["phase_text"] = "抢地主"
        table["original_landlord"] = str(table.get("landlord_candidate"))
        table["rob_passes"] = set()
        return ddz_begin_rob_text(table)
    ddz_next_turn(table)
    return None


async def ddz_process_bot_bidding(group_id: str, table: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    while table.get("phase") == "bidding" and ddz_current_player(table).get("bot"):
        player = ddz_current_player(table)
        bid = ddz_bot_bid_value(player, int(table.get("highest_bid", 0)))
        logs.append(ddz_apply_bid(table, player, bid))
        result = ddz_after_bid(table)
        if result:
            logs.append(result)
            break
    if table.get("phase") == "rob":
        logs.extend(await ddz_process_bot_rob(group_id, table))
    return logs


async def ddz_process_bot_rob(group_id: str, table: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    candidate = str(table.get("landlord_candidate"))
    for player in table.get("players", []):
        player_id = str(player.get("id"))
        if player_id == candidate or player_id in set(table.get("rob_passes", set())):
            continue
        if not player.get("bot"):
            continue
        table.setdefault("rob_passes", set()).add(player_id)
        logs.append(f"{player.get('name')} 不抢")
    needed = {str(p.get("id")) for p in table.get("players", []) if str(p.get("id")) != candidate}
    if needed and needed.issubset(set(table.get("rob_passes", set()))):
        logs.append(await ddz_finalize_and_advance(group_id, table, candidate))
    return logs


def ddz_parse_bid(text: str, highest: int) -> Optional[int]:
    stripped = text.strip()
    if stripped == "不叫":
        return 0
    if stripped == "叫地主":
        return min(3, max(1, highest + 1))
    match = re.search(r"(\d+)", stripped)
    if match and stripped.startswith("叫分"):
        return int(match.group(1))
    return None


def ddz_rob_needed_done(table: dict[str, Any]) -> bool:
    candidate = str(table.get("landlord_candidate"))
    needed = {str(p.get("id")) for p in table.get("players", []) if str(p.get("id")) != candidate}
    return bool(needed) and needed.issubset(set(table.get("rob_passes", set())))


def ddz_user_can_act(table: dict[str, Any], user_id: str) -> bool:
    return ddz_current_player(table).get("id") == user_id


async def ddz_process_bot_steps(group_id: str, table: dict[str, Any]) -> list[str]:
    logs: list[str] = []
    while table.get("phase") == "double":
        pending = [p for p in table["players"] if str(p.get("id")) not in set(table.get("double_responses", set()))]
        bot_pending = [p for p in pending if p.get("bot")]
        if not bot_pending:
            break
        for player in bot_pending:
            table.setdefault("double_responses", set()).add(str(player.get("id")))
            if ddz_bot_should_double(player):
                table.setdefault("double_votes", set()).add(str(player.get("id")))
                table["multiplier"] = int(table.get("multiplier", 1)) * 2
                logs.append(f"{player.get('name')} 选择加倍")
            else:
                logs.append(f"{player.get('name')} 不加倍")
        if len(table.get("double_responses", set())) >= len(table["players"]):
            ddz_start_play(table)
            logs.append("加倍阶段结束，地主先出牌。")
            await ddz_send_all_hands(table, group_id)
    while table.get("phase") == "playing" and ddz_current_player(table).get("bot"):
        player = ddz_current_player(table)
        if table.get("last_play") and str(table.get("last_player")) != str(player.get("id")):
            played, line = ddz_bot_play(player, table)
            logs.append(line)
            if not played:
                table["pass_count"] = int(table.get("pass_count", 0)) + 1
                if int(table.get("pass_count", 0)) >= 2:
                    last = ddz_player(table, str(table.get("last_player")))
                    logs.append(f"一轮跟牌结束，{last.get('name') if last else '上家'} 重新领牌。")
                    for idx, candidate in enumerate(table["players"]):
                        if str(candidate.get("id")) == str(table.get("last_player")):
                            table["current"] = idx
                            break
                    table["last_play"] = None
                    table["pass_count"] = 0
                    continue
        else:
            played, line = ddz_bot_play(player, table)
            logs.append(line)
        if not player.get("hand"):
            logs.append(await ddz_finish_game(group_id, table, str(player.get("id"))))
            break
        ddz_next_turn(table)
    return logs


async def ddz_finalize_and_advance(group_id: str, table: dict[str, Any], landlord_id: str) -> str:
    ddz_finalize_landlord(table, landlord_id)
    await ddz_send_all_hands(table, group_id)
    logs = [ddz_table_text(table, "地主已定，请发送 加倍 / 不加倍")]
    logs.extend(await ddz_process_bot_steps(group_id, table))
    if table.get("phase") == "playing":
        logs.append(ddz_table_text(table, "牌局开始，地主先出牌。"))
    return "\n".join(logs)


def ddz_create_human_player(event: GroupMessageEvent) -> dict[str, Any]:
    return {"id": event.get_user_id(), "name": _g.nickname_from_event(event) or f"QQ {event.get_user_id()}", "bot": False, "hand": []}


def ddz_create_bot_player(index: int) -> dict[str, Any]:
    return {"id": f"bot-{index}", "name": f"机关修士{index}", "bot": True, "hand": []}


def ddz_lobby_text(table: dict[str, Any]) -> str:
    lines = ["【斗地主等待房】", f"桌主：{table.get('host_name')}", f"人数：{len(table.get('players', []))}/3"]
    lines.extend(f"{idx}. {player.get('name')}" for idx, player in enumerate(table.get("players", []), start=1))
    lines.append("发送 加入斗地主 入座；满3人后由桌主发送 开始斗地主。")
    return "\n".join(lines)

async def is_doudizhu_message(event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return False
    text = _g.normalized_plain_text(event)
    return is_doudizhu_entry_text(text) or (doudizhu_group_key(event) in doudizhu_tables and is_doudizhu_command_text(text))

doudizhu_cmd = on_message(rule=Rule(is_doudizhu_message), priority=10, block=True)

async def handle_doudizhu(matcher: Matcher, event: GroupMessageEvent) -> None:
    await _g.remember_group_member(event)
    group_id = doudizhu_group_key(event)
    user_id = event.get_user_id()
    text_value = _g.normalized_plain_text(event)
    record = await store.get_user(user_id)

    if text_value in DOUDIZHU_HELP_TEXTS:
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b\u5e2e\u52a9", doudizhu_help_text(), record, icon="poker")

    table = doudizhu_tables.get(group_id)
    if table and table.get("phase") == "lobby" and float(table.get("expires_at", 0)) < time.monotonic():
        doudizhu_tables.pop(group_id, None)
        table = None

    if text_value == "\u6597\u5730\u4e3b" and not table:
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", doudizhu_help_text(), record, icon="poker")

    if text_value == "\u6597\u5730\u4e3b\u5f00\u684c":
        if table:
            content = ddz_table_text(table) if table.get("phase") != "lobby" else ddz_lobby_text(table)
            await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", content, record, icon="poker")
        table = {
            "phase": "lobby",
            "phase_text": "\u7b49\u4eba",
            "host_id": user_id,
            "host_name": _g.nickname_from_event(event) or f"QQ {user_id}",
            "players": [ddz_create_human_player(event)],
            "created_at": time.monotonic(),
            "expires_at": time.monotonic() + DDZ_HUMAN_WAIT_SECONDS,
        }
        doudizhu_tables[group_id] = table
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b\u5f00\u684c", ddz_lobby_text(table), record, icon="poker")

    if text_value == "\u4eba\u673a\u6597\u5730\u4e3b":
        if table:
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u672c\u7fa4\u5df2\u6709\u6597\u5730\u4e3b\u724c\u684c\uff0c\u8bf7\u5148\u7ed3\u675f\u6597\u5730\u4e3b\u3002", record, icon="warning")
        table = {
            "phase": "lobby",
            "phase_text": "\u7b49\u4eba",
            "host_id": user_id,
            "host_name": _g.nickname_from_event(event) or f"QQ {user_id}",
            "players": [ddz_create_human_player(event), ddz_create_bot_player(1), ddz_create_bot_player(2)],
            "created_at": time.monotonic(),
        }
        doudizhu_tables[group_id] = table
        ddz_deal(table)
        await ddz_send_all_hands(table, group_id)
        logs = ["\u4eba\u673a\u6597\u5730\u4e3b\u5df2\u5f00\u5c40", ddz_bid_status(table)]
        logs.extend(await ddz_process_bot_bidding(group_id, table))
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if not table:
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\u6682\u65e0\u6597\u5730\u4e3b\u724c\u684c\uff0c\u53ef\u53d1\u9001 \u6597\u5730\u4e3b\u5f00\u684c \u6216 \u4eba\u673a\u6597\u5730\u4e3b\u3002", record, icon="poker")

    player = ddz_player(table, user_id)

    if text_value == "\u6597\u5730\u4e3b":
        content = ddz_lobby_text(table) if table.get("phase") == "lobby" else ddz_table_text(table)
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", content, record, icon="poker")

    if text_value == "\u7ed3\u675f\u6597\u5730\u4e3b":
        if not player and str(table.get("host_id")) != user_id:
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u53ea\u6709\u724c\u5c40\u73a9\u5bb6\u6216\u684c\u4e3b\u53ef\u4ee5\u7ed3\u675f\u6597\u5730\u4e3b\u3002", record, icon="warning")
        doudizhu_tables.pop(group_id, None)
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\u724c\u684c\u5df2\u7ed3\u675f\u3002", record, icon="poker")

    if text_value == "\u52a0\u5165\u6597\u5730\u4e3b":
        if table.get("phase") != "lobby":
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u724c\u5c40\u5df2\u5f00\u59cb\uff0c\u65e0\u6cd5\u4e2d\u9014\u5165\u5ea7\u3002", record, icon="warning")
        if player:
            await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\u4f60\u5df2\u7ecf\u5728\u8fd9\u5f20\u724c\u684c\u4e0a\u3002", record, icon="poker")
        if len(table.get("players", [])) >= 3:
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u724c\u684c\u5df2\u6ee1\u5458\u3002", record, icon="warning")
        table["players"].append(ddz_create_human_player(event))
        hint = "\n\u4eba\u6ee1\u4e86\uff0c\u53ef\u7531\u684c\u4e3b\u53d1\u9001 \u5f00\u59cb\u6597\u5730\u4e3b\u3002" if len(table["players"]) == 3 else ""
        await _g.finish_panel(matcher, "\u52a0\u5165\u6597\u5730\u4e3b", ddz_lobby_text(table) + hint, record, icon="poker")

    if text_value == "\u9000\u51fa\u6597\u5730\u4e3b":
        if table.get("phase") != "lobby":
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u724c\u5c40\u5df2\u5f00\u59cb\uff0c\u4e0d\u80fd\u9000\u51fa\uff0c\u53ef\u53d1\u9001\u6258\u7ba1\u3002", record, icon="warning")
        if not player:
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u4f60\u4e0d\u5728\u8fd9\u5f20\u724c\u684c\u4e0a\u3002", record, icon="warning")
        table["players"] = [item for item in table["players"] if str(item.get("id")) != user_id]
        if not table["players"]:
            doudizhu_tables.pop(group_id, None)
            await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\u724c\u684c\u5df2\u89e3\u6563\u3002", record, icon="poker")
        if str(table.get("host_id")) == user_id:
            table["host_id"] = str(table["players"][0].get("id"))
            table["host_name"] = str(table["players"][0].get("name"))
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b\u7b49\u5f85\u623f", ddz_lobby_text(table), record, icon="poker")

    if text_value == "\u5f00\u59cb\u6597\u5730\u4e3b":
        if table.get("phase") != "lobby":
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u724c\u5c40\u5df2\u7ecf\u5f00\u59cb\u3002", record, icon="warning")
        if str(table.get("host_id")) != user_id:
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u53ea\u6709\u684c\u4e3b\u53ef\u4ee5\u5f00\u59cb\u724c\u5c40\u3002", record, icon="warning")
        if len(table.get("players", [])) != 3:
            await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u9700\u8981 3 \u4f4d\u73a9\u5bb6\u624d\u80fd\u5f00\u59cb\u3002", record, icon="warning")
        ddz_deal(table)
        await ddz_send_all_hands(table, group_id)
        logs = ["\u6597\u5730\u4e3b\u5f00\u5c40", ddz_bid_status(table)]
        logs.extend(await ddz_process_bot_bidding(group_id, table))
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if not player:
        await _g.finish_panel(matcher, "\u64cd\u4f5c\u5931\u8d25", "\u4f60\u8fd8\u6ca1\u6709\u5165\u5ea7\u8fd9\u5f20\u6597\u5730\u4e3b\u724c\u684c\u3002", record, icon="warning")

    if text_value == "\u624b\u724c":
        await ddz_send_hand(player, table, group_id)
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b\u624b\u724c", "\u5df2\u5c1d\u8bd5\u79c1\u804a\u53d1\u9001\u624b\u724c\u3002", record, icon="poker")

    if text_value == "\u6258\u7ba1":
        player["bot"] = True
        logs = [f"{player.get('name')} \u5df2\u8fdb\u5165\u6258\u7ba1"]
        logs.extend(await ddz_process_bot_steps(group_id, table))
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if table.get("phase") == "bidding" and is_doudizhu_bid_text(text_value):
        if not ddz_user_can_act(table, user_id):
            await _g.finish_panel(matcher, "\u7b49\u5f85\u51fa\u624b", f"\u5f53\u524d\u8f6e\u5230 {ddz_current_player(table).get('name')} \u53eb\u5206\u3002", record, icon="warning")
        bid = ddz_parse_bid(text_value, int(table.get("highest_bid", 0)))
        if bid is None or bid < 0 or bid > 3:
            await _g.finish_panel(matcher, "\u53eb\u5206\u5931\u8d25", "\u8bf7\u53d1\u9001\uff1a\u53eb\u5206 1 / \u53eb\u5206 2 / \u53eb\u5206 3 / \u53eb\u5730\u4e3b / \u4e0d\u53eb", record, icon="warning")
        if bid and bid <= int(table.get("highest_bid", 0)):
            await _g.finish_panel(matcher, "\u53eb\u5206\u5931\u8d25", f"\u5fc5\u987b\u9ad8\u4e8e\u5f53\u524d\u6700\u9ad8\u5206 {table.get('highest_bid', 0)}\u3002", record, icon="warning")
        logs = [ddz_apply_bid(table, player, bid)]
        result = ddz_after_bid(table)
        if result:
            logs.append(result)
        else:
            logs.append(ddz_bid_status(table))
        logs.extend(await ddz_process_bot_bidding(group_id, table))
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if table.get("phase") == "rob" and text_value in {"\u62a2\u5730\u4e3b", "\u4e0d\u62a2", "\u65bd\u52a0\u5a01\u538b"}:
        candidate_id = str(table.get("landlord_candidate"))
        if user_id == candidate_id:
            await _g.finish_panel(matcher, "\u62a2\u5730\u4e3b", "\u5019\u9009\u5730\u4e3b\u4e0d\u80fd\u81ea\u5df1\u62a2\u81ea\u5df1\u3002", record, icon="warning")
        if user_id in set(table.get("rob_passes", set())):
            await _g.finish_panel(matcher, "\u62a2\u5730\u4e3b", "\u4f60\u5df2\u7ecf\u8868\u6001\u8fc7\u4e86\u3002", record, icon="warning")
        if text_value == "\u4e0d\u62a2":
            table.setdefault("rob_passes", set()).add(user_id)
            logs = [f"{player.get('name')} \u4e0d\u62a2"]
            if ddz_rob_needed_done(table):
                logs.append(await ddz_finalize_and_advance(group_id, table, candidate_id))
            else:
                logs.append(ddz_begin_rob_text(table))
            logs.extend(await ddz_process_bot_rob(group_id, table))
            await _g.finish_panel(matcher, "\u62a2\u5730\u4e3b", "\n".join(logs), record, icon="poker")
        pressure = text_value == "\u65bd\u52a0\u5a01\u538b"
        candidate = ddz_player(table, candidate_id)
        challenger_record = await store.get_user(user_id)
        candidate_record = await store.get_user(candidate_id) if candidate and not candidate.get("bot") else None
        actor_power = battle_power(challenger_record)
        target_power = battle_power(candidate_record) if candidate_record else 1
        chance = ddz_pressure_chance(actor_power, target_power, pressure)
        success = random.random() < chance
        action_name = "\u65bd\u52a0\u5a01\u538b\u62a2\u5730\u4e3b" if pressure else "\u62a2\u5730\u4e3b"
        logs = [f"{player.get('name')} {action_name}\uff0c\u6210\u529f\u7387 {int(chance * 100)}%\u3002"]
        if success:
            if pressure:
                table["phase"] = "retain"
                table["phase_text"] = "\u5a01\u538b\u4fdd\u7559"
                table["pending_pressure"] = {
                    "original_id": candidate_id,
                    "original_name": candidate.get("name") if candidate else candidate_id,
                    "challenger_id": user_id,
                    "challenger_name": player.get("name"),
                }
                logs.append(f"\u5a01\u538b\u6210\u529f\uff01{candidate.get('name') if candidate else candidate_id} \u53ef\u56de\u590d \u4fdd\u7559\u5730\u4e3b / \u653e\u5f03\u5730\u4e3b\u3002")
            else:
                table["landlord_candidate"] = user_id
                table["original_landlord"] = table.get("original_landlord") or candidate_id
                logs.append(await ddz_finalize_and_advance(group_id, table, user_id))
        else:
            table.setdefault("rob_passes", set()).add(user_id)
            logs.append("\u62a2\u5730\u4e3b\u5931\u8d25\u3002")
            if ddz_rob_needed_done(table):
                logs.append(await ddz_finalize_and_advance(group_id, table, candidate_id))
            else:
                logs.append(ddz_begin_rob_text(table))
            logs.extend(await ddz_process_bot_rob(group_id, table))
        await _g.finish_panel(matcher, "\u62a2\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    if table.get("phase") == "retain" and text_value in {"\u4fdd\u7559\u5730\u4e3b", "\u653e\u5f03\u5730\u4e3b"}:
        pending = dict(table.get("pending_pressure") or {})
        if user_id != str(pending.get("original_id")):
            await _g.finish_panel(matcher, "\u5a01\u538b\u4fdd\u7559", "\u53ea\u6709\u539f\u5b9a\u5730\u4e3b\u53ef\u4ee5\u51b3\u5b9a\u662f\u5426\u4fdd\u7559\u3002", record, icon="warning")
        if text_value == "\u4fdd\u7559\u5730\u4e3b":
            table["pressure_duel"] = {
                "left_id": pending.get("original_id"),
                "left_name": pending.get("original_name"),
                "right_id": pending.get("challenger_id"),
                "right_name": pending.get("challenger_name"),
            }
            content = await ddz_finalize_and_advance(group_id, table, str(pending.get("original_id")))
            await _g.finish_panel(matcher, "\u4fdd\u7559\u5730\u4e3b", content + "\n\u724c\u5c40\u7ed3\u675f\u540e\u5c06\u5f3a\u5236\u89e6\u53d1\u666e\u901a\u6597\u6cd5\u3002", record, icon="poker")
        content = await ddz_finalize_and_advance(group_id, table, str(pending.get("challenger_id")))
        await _g.finish_panel(matcher, "\u653e\u5f03\u5730\u4e3b", content, record, icon="poker")

    if table.get("phase") == "double" and text_value in {"\u52a0\u500d", "\u4e0d\u52a0\u500d"}:
        responses = table.setdefault("double_responses", set())
        if user_id in responses:
            await _g.finish_panel(matcher, "\u52a0\u500d\u9636\u6bb5", "\u4f60\u5df2\u7ecf\u8868\u6001\u8fc7\u4e86\u3002", record, icon="warning")
        responses.add(user_id)
        logs = []
        if text_value == "\u52a0\u500d":
            table.setdefault("double_votes", set()).add(user_id)
            table["multiplier"] = int(table.get("multiplier", 1)) * 2
            logs.append(f"{player.get('name')} \u9009\u62e9\u52a0\u500d")
        else:
            logs.append(f"{player.get('name')} \u4e0d\u52a0\u500d")
        logs.extend(await ddz_process_bot_steps(group_id, table))
        if table.get("phase") == "double" and len(table.get("double_responses", set())) >= len(table.get("players", [])):
            ddz_start_play(table)
            await ddz_send_all_hands(table, group_id)
            logs.append("\u52a0\u500d\u9636\u6bb5\u7ed3\u675f\uff0c\u5730\u4e3b\u5148\u51fa\u724c\u3002")
        logs.extend(await ddz_process_bot_steps(group_id, table))
        if group_id in doudizhu_tables:
            logs.append(ddz_table_text(table))
        await _g.finish_panel(matcher, "\u52a0\u500d\u9636\u6bb5", "\n".join(logs), record, icon="poker")

    if table.get("phase") == "playing" and text_value == "\u63d0\u793a":
        if not ddz_user_can_act(table, user_id):
            await _g.finish_panel(matcher, "\u7b49\u5f85\u51fa\u624b", f"\u5f53\u524d\u8f6e\u5230 {ddz_current_player(table).get('name')}\u3002", record, icon="warning")
        last_play = table.get("last_play") if str(table.get("last_player")) != user_id else None
        hint = ddz_find_hint(list(player.get("hand", [])), last_play)
        await _g.finish_panel(matcher, "\u51fa\u724c\u63d0\u793a", f"\u5efa\u8bae\uff1a{''.join(hint) if hint else '\u6682\u65e0\u53ef\u538b\u8fc7\u7684\u724c\uff0c\u53ef\u53d1\u9001 \u4e0d\u8981'}", record, icon="poker")

    if table.get("phase") == "playing" and (is_doudizhu_play_text(text_value) or text_value == "\u4e0d\u8981"):
        if not ddz_user_can_act(table, user_id):
            await _g.finish_panel(matcher, "\u7b49\u5f85\u51fa\u624b", f"\u5f53\u524d\u8f6e\u5230 {ddz_current_player(table).get('name')}\u3002", record, icon="warning")
        logs = []
        if text_value == "\u4e0d\u8981":
            if not table.get("last_play") or str(table.get("last_player")) == user_id:
                await _g.finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", "\u4f60\u662f\u5f53\u524d\u9886\u724c\u8005\uff0c\u5fc5\u987b\u51fa\u724c\u3002", record, icon="warning")
            table["pass_count"] = int(table.get("pass_count", 0)) + 1
            logs.append(f"{player.get('name')} \u4e0d\u8981")
            if int(table.get("pass_count", 0)) >= 2:
                last = ddz_player(table, str(table.get("last_player")))
                logs.append(f"\u4e00\u8f6e\u8ddf\u724c\u7ed3\u675f\uff0c{last.get('name') if last else '\u4e0a\u5bb6'} \u91cd\u65b0\u9886\u724c\u3002")
                for idx, candidate in enumerate(table["players"]):
                    if str(candidate.get("id")) == str(table.get("last_player")):
                        table["current"] = idx
                        break
                table["last_play"] = None
                table["pass_count"] = 0
            else:
                ddz_next_turn(table)
        else:
            cards = ddz_parse_cards(text_value)
            if not cards:
                await _g.finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", "\u672a\u8bc6\u522b\u724c\u9762\uff0c\u4f8b\u5982\uff1a\u51fa\u724c 34567 / \u51fa\u724c 3334 / \u51fa\u724c \u5c0f\u738b\u5927\u738b\u3002", record, icon="warning")
            if not ddz_has_cards(list(player.get("hand", [])), cards):
                await _g.finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", f"\u624b\u724c\u4e2d\u6ca1\u6709\uff1a{ddz_cards_text(cards)}", record, icon="warning")
            analyzed = ddz_analyze_cards(cards)
            if not analyzed:
                await _g.finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", "\u8fd9\u7ec4\u724c\u4e0d\u7b26\u5408\u5f53\u524d\u6597\u5730\u4e3b\u724c\u578b\u3002", record, icon="warning")
            last_play = table.get("last_play") if str(table.get("last_player")) != user_id else None
            if not ddz_can_beat(analyzed, last_play):
                await _g.finish_panel(matcher, "\u51fa\u724c\u5931\u8d25", "\u538b\u4e0d\u8fc7\u4e0a\u4e00\u624b\u724c\u3002", record, icon="warning")
            ddz_remove_cards(player["hand"], cards)
            table["last_play"] = {**analyzed, "cards": cards}
            table["last_player"] = user_id
            table["pass_count"] = 0
            if analyzed["type"] in {"bomb", "rocket"}:
                table["multiplier"] = int(table.get("multiplier", 1)) * 2
                logs.append("\u96f7\u52ab\u964d\u4e34\uff01\u5f53\u524d\u500d\u6570\u7ffb\u500d\u3002")
            if user_id == str(table.get("landlord")):
                table["landlord_play_count"] = int(table.get("landlord_play_count", 0)) + 1
            else:
                table["farmer_play_count"] = int(table.get("farmer_play_count", 0)) + 1
            logs.append(f"{player.get('name')} \u6253\u51fa {analyzed['label']}\uff1a{ddz_cards_text(cards)}")
            if not player.get("hand"):
                logs.append(await ddz_finish_game(group_id, table, user_id))
                await _g.finish_panel(matcher, "\u6597\u5730\u4e3b\u7ed3\u7b97", "\n".join(logs), record, icon="poker")
            ddz_next_turn(table)
        logs.extend(await ddz_process_bot_steps(group_id, table))
        if group_id in doudizhu_tables:
            logs.append(ddz_table_text(table))
        await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", "\n".join(logs), record, icon="poker")

    await _g.finish_panel(matcher, "\u6597\u5730\u4e3b", ddz_table_text(table), record, icon="poker")
