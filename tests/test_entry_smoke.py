"""入口 smoke（R-19）：插件被真正 import 一遍，核对「注册结果」而不是函数行为。

NoneBot 的 handler 注册发生在模块执行期：少一个 ``@matcher.handle()``、少 import 一个
``commands/handlers/*`` 子模块，都不会抛任何异常，只是让整组命令静默消失。
``commands/handlers/__init__.py`` 的 docstring 已经点明这个风险，但此前没有任何测试验证。

本文件把注册结果当契约钉住：

1. 每个 matcher 都必须挂上 handler（R-19 期间实测抓到斗地主 matcher 无 handler：
   ``a3d850e`` 抽取 ``commands/doudizhu.py`` 时把 ``@doudizhu_cmd.handle()`` 丢了，
   上线表现为「斗地主整个玩法不响应任何消息」；函数级测试直接调用 handler，
   完全绕过了注册环节，所以一直没发现）；
2. matcher 数量与优先级分布是快照，变动必须显式确认；
3. 每个 handler 域模块都必须至少贡献一个 handler；
4. ``texts`` 里登记的每个触发词集合，都必须能被 ``is_managed_command_text`` 认出来。
"""
from __future__ import annotations

import importlib
import json
import pathlib
import subprocess
import sys
import textwrap
from collections import Counter

import pytest

PLUGIN_PACKAGE = "nonebot_plugin_xiuxian_signin"
ROOT = pathlib.Path(__file__).resolve().parents[1]

# matcher 数量与优先级快照。数字变化意味着新增/删除了命令入口，需同步本表并确认意图。
EXPECTED_PRIORITY_INVENTORY = {6: 1, 7: 1, 8: 2, 9: 1, 10: 50, 99: 1}

# 每个 handler 域必须存在且只允许这些模块贡献 handler。
EXPECTED_HANDLER_MODULES = {
    f"{PLUGIN_PACKAGE}.commands.doudizhu",
    f"{PLUGIN_PACKAGE}.commands.handlers.beast",
    f"{PLUGIN_PACKAGE}.commands.handlers.collection",
    f"{PLUGIN_PACKAGE}.commands.handlers.craft",
    f"{PLUGIN_PACKAGE}.commands.handlers.duel",
    f"{PLUGIN_PACKAGE}.commands.handlers.fishing",
    f"{PLUGIN_PACKAGE}.commands.handlers.inventory",
    f"{PLUGIN_PACKAGE}.commands.handlers.mystic",
    f"{PLUGIN_PACKAGE}.commands.handlers.signin",
    f"{PLUGIN_PACKAGE}.commands.handlers.status",
    f"{PLUGIN_PACKAGE}.commands.handlers.trade",
}


@pytest.fixture(scope="module")
def registered_matchers():
    """导入注册模块并返回注册表快照。

    这里刻意不 import 插件入口 ``__init__.py``：测试套件里有一批用例（``test_admin_auth`` /
    ``test_combat_turns`` / ``test_domain_features`` 等）在收集阶段就往 ``sys.modules`` 里塞了
    一个只有 ``__path__`` 的空壳包，导致真入口在整个会话里永远不会执行。入口自身的完整性
    由 ``test_real_entry_registers_complete_matcher_set`` 在子进程里验证。
    """
    import nonebot.matcher as matcher_module

    importlib.import_module(f"{PLUGIN_PACKAGE}.commands.matchers")
    importlib.import_module(f"{PLUGIN_PACKAGE}.commands.handlers")
    return [matcher for group in matcher_module.matchers.values() for matcher in group]


def test_every_matcher_has_a_handler(registered_matchers) -> None:
    """没有 handler 的 matcher 等于一个永远不回复的命令入口。"""
    orphans = [str(matcher) for matcher in registered_matchers if not matcher.handlers]
    assert not orphans, "以下 matcher 没有任何 handler，命令会静默失效：\n" + "\n".join(orphans)


def test_matcher_count_matches_priority_inventory(registered_matchers) -> None:
    inventory = Counter(int(matcher.priority) for matcher in registered_matchers)
    assert dict(sorted(inventory.items())) == EXPECTED_PRIORITY_INVENTORY, (
        "matcher 优先级分布变化，请确认新增/删除了哪个命令入口后同步本表："
        f"实际 {dict(sorted(inventory.items()))}"
    )


def test_each_matcher_has_exactly_one_handler(registered_matchers) -> None:
    """一个入口挂多个 handler 会让同一条消息触发多次回复，多为重复注册。"""
    duplicated = {
        str(matcher): len(matcher.handlers)
        for matcher in registered_matchers
        if len(matcher.handlers) != 1
    }
    assert not duplicated, f"这些 matcher 的 handler 数不是 1：{duplicated}"


def test_handler_modules_cover_all_domains(registered_matchers) -> None:
    modules = {handler.call.__module__ for matcher in registered_matchers for handler in matcher.handlers}
    assert modules == EXPECTED_HANDLER_MODULES, (
        "handler 所属模块与约定不一致；新增域请同时更新 commands/handlers/__init__.py 与本表。"
        f"多出：{sorted(modules - EXPECTED_HANDLER_MODULES)}，缺失：{sorted(EXPECTED_HANDLER_MODULES - modules)}"
    )


def test_handler_entry_points_are_unique(registered_matchers) -> None:
    """同一个函数被注册到两处，说明有复制粘贴的 handler 没删干净。"""
    seen: dict[tuple[str, str], int] = {}
    for matcher in registered_matchers:
        for handler in matcher.handlers:
            key = (handler.call.__module__, handler.call.__qualname__)
            seen[key] = seen.get(key, 0) + 1
    repeats = {key: count for key, count in seen.items() if count > 1}
    assert not repeats, f"同一 handler 被重复注册：{repeats}"


def test_trigger_text_inventories_are_dispatched() -> None:
    """``texts`` 里每个触发词集合都必须被 ``is_managed_command_text`` 认出。

    这个函数决定「这条消息算不算本插件的命令」：聊天排行榜靠它排除命令消息，
    普通斗法的聊天判定靠它避免把命令当成出招。漏登记会让该命令被当成闲聊。
    R-19 期间实测漏了 ``SIGNIN_CALENDAR_TEXTS``（签到日历整组）。
    """
    from nonebot_plugin_xiuxian_signin.commands import rules, texts

    inventories = {
        name: value
        for name, value in vars(texts).items()
        if name.endswith("_TEXTS") and isinstance(value, (set, frozenset)) and value
    }
    assert inventories, "texts 模块里应至少有一个触发词集合"

    missed = {
        name: sorted(word for word in words if not rules.is_managed_command_text(word))
        for name, words in inventories.items()
        if any(not rules.is_managed_command_text(word) for word in words)
    }
    assert not missed, f"这些触发词没有被 is_managed_command_text 覆盖：{missed}"


def test_unrelated_text_is_not_treated_as_command() -> None:
    """反向约束：避免为了通过上一条把判定写成「一律返回 True」。"""
    from nonebot_plugin_xiuxian_signin.commands import rules

    for text in ("今天天气不错", "1234567890", "hello world"):
        assert not rules.is_managed_command_text(text), f"{text!r} 不应被当成插件命令"


def test_real_entry_registers_complete_matcher_set() -> None:
    """在干净子进程里 import 真入口，验证它确实把命令全部注册上了。

    必须开子进程：测试套件里已有多个文件往 ``sys.modules`` 注入过空壳包，进程内的入口
    导入是 no-op，测不出任何东西。子进程同时也验证了「入口在全新解释器下可导入」。
    """
    code = textwrap.dedent(
        f"""
        import json
        import nonebot
        nonebot.init()                      # 默认 fastapi driver，与线上一致
        import {PLUGIN_PACKAGE}             # noqa: F401  入口执行即注册
        import nonebot.matcher as matcher_module

        matchers = [m for group in matcher_module.matchers.values() for m in group]
        handlers = [h for m in matchers for h in m.handlers]
        print("RESULT" + json.dumps({{
            "matchers": len(matchers),
            "handlers": len(handlers),
            "orphans": [str(m) for m in matchers if not m.handlers],
            "modules": sorted({{h.call.__module__ for h in handlers}}),
            "priorities": sorted(m.priority for m in matchers),
        }}))
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    payload = json.loads(result.stdout.split("RESULT", 1)[1].strip().splitlines()[0])

    assert payload["orphans"] == [], f"入口注册后仍有 matcher 没有 handler：{payload['orphans']}"
    assert payload["matchers"] == sum(EXPECTED_PRIORITY_INVENTORY.values())
    assert payload["handlers"] == payload["matchers"], "每个入口应恰好挂一个 handler"
    assert Counter(payload["priorities"]) == Counter(EXPECTED_PRIORITY_INVENTORY)
    assert set(payload["modules"]) == EXPECTED_HANDLER_MODULES
