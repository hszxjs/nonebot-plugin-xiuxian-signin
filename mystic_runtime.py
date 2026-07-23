from __future__ import annotations

import asyncio
import hashlib
import io
import re
import secrets
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Callable

from .mystic_battle import (
    DungeonEncounter,
    EncounterKind,
    EncounterPhase,
    MysticBattleService,
)
from .mystic_cards import MysticMapRenderModel, MysticMapRenderer, RenderedEdge, RenderedNode
from .mystic_dungeon import (
    DungeonMode,
    DungeonPhase,
    DungeonRisk,
    MysticDungeonRun,
    MysticDungeonService,
    NodeKind,
    MovementResult,
)
from .domain import UserRecord, combat_max_hp
from .storage import (
    JsonStore,
    MysticEncounterConflict,
    MysticRunConflict,
    MysticSettlement,
)


class MysticGroupAction(StrEnum):
    STATUS = "status"
    CREATE_SOLO = "create_solo"
    CREATE_TEAM = "create_team"
    JOIN = "join"
    LEAVE_LOBBY = "leave_lobby"
    READY = "ready"
    START = "start"
    MAP = "map"
    ROLL = "roll"
    CHOOSE_BRANCH = "choose_branch"
    RESPOND = "respond"
    VOTE_CONTINUE = "vote_continue"
    VOTE_TRANSFER = "vote_transfer"
    VOTE_ABANDON = "vote_abandon"


@dataclass(frozen=True)
class MysticParsedCommand:
    action: MysticGroupAction
    argument: str = ""


class _GroupCommandParser:
    _RISK = r"(?:普通|高风险|高难)"

    def parse(self, normalized: str) -> MysticParsedCommand | None:
        exact = {
            "秘境状态": MysticParsedCommand(MysticGroupAction.STATUS),
            "秘境地图": MysticParsedCommand(MysticGroupAction.MAP),
            "加入秘境队伍": MysticParsedCommand(MysticGroupAction.JOIN),
            "退出秘境队伍": MysticParsedCommand(MysticGroupAction.LEAVE_LOBBY),
            "秘境准备": MysticParsedCommand(MysticGroupAction.READY),
            "开始秘境": MysticParsedCommand(MysticGroupAction.START),
            "投骰": MysticParsedCommand(MysticGroupAction.ROLL),
            "应战": MysticParsedCommand(MysticGroupAction.RESPOND),
            "同意继续": MysticParsedCommand(MysticGroupAction.VOTE_CONTINUE, "同意"),
            "拒绝继续": MysticParsedCommand(MysticGroupAction.VOTE_CONTINUE, "拒绝"),
            "秘境续战 同意": MysticParsedCommand(MysticGroupAction.VOTE_CONTINUE, "同意"),
            "秘境续战 拒绝": MysticParsedCommand(MysticGroupAction.VOTE_CONTINUE, "拒绝"),
            "同意转让": MysticParsedCommand(MysticGroupAction.VOTE_TRANSFER, "同意"),
            "拒绝转让": MysticParsedCommand(MysticGroupAction.VOTE_TRANSFER, "拒绝"),
            "放弃秘境": MysticParsedCommand(MysticGroupAction.VOTE_ABANDON, "同意"),
        }
        parsed = exact.get(normalized)
        if parsed is not None:
            return parsed
        patterns = (
            (rf"^创建单人秘境\s+({self._RISK})$", MysticGroupAction.CREATE_SOLO),
            (rf"^创建秘境队伍\s+({self._RISK})$", MysticGroupAction.CREATE_TEAM),
            (r"^选择分支\s+(.+)$", MysticGroupAction.CHOOSE_BRANCH),
            (r"^应战\s+(.+)$", MysticGroupAction.RESPOND),
            (r"^转让队长\s+(\S+)$", MysticGroupAction.VOTE_TRANSFER),
        )
        for pattern, action in patterns:
            match = re.fullmatch(pattern, normalized)
            if match is not None:
                return MysticParsedCommand(action, match.group(1))
        return None


class _PrivateCommandParser:
    _EXACT = {
        "秘境状态",
        "秘境地图",
        "确认配装",
        "普通攻击",
        "自动战斗",
        "同意",
        "拒绝",
        "继续战斗",
    }

    def accepts(self, normalized: str) -> bool:
        return normalized in self._EXACT or normalized.startswith(("秘境配装 ", "秘境技能 "))


_GROUP_COMMAND_PARSER = _GroupCommandParser()
_PRIVATE_COMMAND_PARSER = _PrivateCommandParser()


def parse_mystic_group_command(text: str) -> MysticParsedCommand | None:
    normalized = " ".join(text.strip().split())
    return _GROUP_COMMAND_PARSER.parse(normalized)


def parse_mystic_private_command(text: str) -> str | None:
    normalized = " ".join(text.strip().split())
    return normalized if _PRIVATE_COMMAND_PARSER.accepts(normalized) else None


@dataclass(frozen=True)
class DungeonEntryOffer:
    mode: DungeonMode
    risk: DungeonRisk
    theme_id: str
    boss_realm_index: int
    insight: bool = False


@dataclass(frozen=True)
class MysticPrivateRoute:
    run_id: str
    source_group_id: str
    rescue_request_id: str | None = None


@dataclass(frozen=True)
class MysticCommandResult:
    message: str = ""
    image_bytes: bytes | None = None
    private_targets: tuple[str, ...] = ()
    private_messages: tuple[tuple[str, str], ...] = ()
    run: MysticDungeonRun | None = None
    updated_revision: int | None = None
    map_required: bool = False
    vote_created: bool = False
    vote_passed: bool = False
    error: str = ""


@dataclass(frozen=True)
class MysticRecoveryResult:
    response_expirations: int = 0
    vote_expirations: int = 0
    scheduled_deadline_count: int = 0


class MysticCommandCoordinator:
    def __init__(
        self,
        store: JsonStore,
        dungeon_service: MysticDungeonService,
        battle_service: MysticBattleService,
        renderer: MysticMapRenderer,
        *,
        id_factory: Callable[[str, str], str] | None = None,
        now: Callable[[], datetime] | None = None,
        dice_roller: Callable[[], int] | None = None,
    ) -> None:
        self.store = store
        self.dungeon_service = dungeon_service
        self.battle_service = battle_service
        self.renderer = renderer
        self._id_factory = id_factory or (
            lambda group_id, user_id: f"mystic:{group_id}:{user_id}:{uuid.uuid4().hex}"
        )
        self._now = now or datetime.now
        self._dice_roller = dice_roller or (lambda: secrets.randbelow(6) + 1)
        self._deadline_tasks: dict[tuple[str, str], asyncio.Task[None]] = {}
        self._deadline_times: dict[tuple[str, str], datetime] = {}
        self._scheduled_deadline_count = 0

    @property
    def scheduled_deadline_count(self) -> int:
        return self._scheduled_deadline_count

    async def recover_active_runs(self) -> MysticRecoveryResult:
        result = MysticRecoveryResult()
        for run in await self.store.list_active_mystic_runs():
            await self.store.bind_mystic_private_routes(run)
            recovered = await self.recover_run(run)
            result = MysticRecoveryResult(
                response_expirations=(
                    result.response_expirations + recovered.response_expirations
                ),
                vote_expirations=result.vote_expirations + recovered.vote_expirations,
                scheduled_deadline_count=(
                    result.scheduled_deadline_count
                    + recovered.scheduled_deadline_count
                ),
            )
        self._scheduled_deadline_count = result.scheduled_deadline_count
        return result

    async def recover_run(self, run: MysticDungeonRun) -> MysticRecoveryResult:
        response_expirations = 0
        vote_expirations = 0
        scheduled_deadline_count = 0
        encounter = None
        if run.active_encounter_id is not None:
            encounter = await self.store.get_mystic_encounter(run.active_encounter_id)
        if encounter is not None and encounter.phase_deadline is not None:
            deadline = datetime.fromisoformat(encounter.phase_deadline)
            if deadline <= self._now():
                if encounter.phase is EncounterPhase.AWAITING_RESPONSE:
                    await self._expire_response_window(run, encounter)
                    response_expirations += 1
                elif encounter.phase is EncounterPhase.PREPARING:
                    await self._expire_preparation(run, encounter)
                    response_expirations += 1
                elif encounter.phase is EncounterPhase.ACTIVE:
                    await self._expire_active_action(run, encounter)
                    response_expirations += 1
            else:
                self._schedule_deadline(
                    run.run_id,
                    f"encounter:{encounter.encounter_id}:{encounter.phase.value}",
                    deadline,
                )
                scheduled_deadline_count += 1
        current_run = await self.store.get_mystic_run(run.run_id)
        if current_run is None:
            return MysticRecoveryResult(
                response_expirations=response_expirations,
                vote_expirations=vote_expirations,
                scheduled_deadline_count=scheduled_deadline_count,
            )
        vote = current_run.active_vote
        if vote is not None:
            deadline = datetime.fromisoformat(vote.deadline)
            if deadline <= self._now():
                if current_run.phase is DungeonPhase.AWAITING_BOSS_VOTE:

                    def expire_vote(item: MysticDungeonRun) -> MysticDungeonRun:
                        item.phase = DungeonPhase.FAILED
                        item.active_vote = None
                        return item

                    expired = await self.store.update_mystic_run(
                        current_run.run_id,
                        current_run.revision,
                        expire_vote,
                    )
                    await self.store.close_mystic_run(
                        expired.run_id,
                        DungeonPhase.FAILED,
                    )
                    vote_expirations += 1
            else:
                self._schedule_deadline(
                    current_run.run_id,
                    f"vote:{vote.vote_id}",
                    deadline,
                )
                scheduled_deadline_count += 1
        return MysticRecoveryResult(
            response_expirations=response_expirations,
            vote_expirations=vote_expirations,
            scheduled_deadline_count=scheduled_deadline_count,
        )

    async def _expire_response_window(
        self,
        run: MysticDungeonRun,
        encounter: DungeonEncounter,
    ) -> None:
        current_run = await self.store.get_mystic_run(run.run_id)
        if current_run is None:
            return
        if not encounter.participants:

            def fail_encounter(item: DungeonEncounter) -> DungeonEncounter:
                item.phase = EncounterPhase.FAILED
                item.phase_deadline = None
                return item

            await self.store.update_mystic_encounter(
                encounter.encounter_id,
                encounter.revision,
                fail_encounter,
            )
            await self.store.close_mystic_run(
                current_run.run_id,
                DungeonPhase.FAILED,
            )
            return

        prepare_deadline = self._now() + timedelta(
            seconds=self.battle_service.config.battle_prepare_seconds
        )

        def begin_preparation(item: DungeonEncounter) -> DungeonEncounter:
            self.battle_service.begin_preparation(item, prepare_deadline)
            return item

        saved_encounter = await self.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            begin_preparation,
        )

        def prepare_run(item: MysticDungeonRun) -> MysticDungeonRun:
            item.phase = DungeonPhase.PREPARING_BATTLE
            return item

        saved_run = await self.store.update_mystic_run(
            current_run.run_id,
            current_run.revision,
            prepare_run,
        )
        self._schedule_deadline(
            saved_run.run_id,
            f"encounter:{saved_encounter.encounter_id}:preparing",
            prepare_deadline,
        )

    async def _expire_preparation(
        self,
        run: MysticDungeonRun,
        encounter: DungeonEncounter,
    ) -> None:
        records = {
            user_id: await self.store.get_user(user_id)
            for user_id in encounter.participants
        }
        action_deadline = self._now() + timedelta(
            seconds=self.battle_service.config.player_action_seconds
        )

        def confirm_remaining(item: DungeonEncounter) -> DungeonEncounter:
            for user_id, record in records.items():
                if user_id in item.prepared_user_ids:
                    continue
                record_data = record.to_dict()
                equipment_snapshot = {
                    key: value
                    for key, value in record_data.items()
                    if key.startswith("equipped_")
                }
                self.battle_service.confirm_loadout(
                    item,
                    user_id,
                    record,
                    equipment_snapshot,
                )
            item.phase = EncounterPhase.ACTIVE
            item.phase_deadline = action_deadline.isoformat()
            return item

        saved_encounter = await self.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            confirm_remaining,
        )
        current_run = await self.store.get_mystic_run(run.run_id)
        if current_run is None:
            return

        def activate_run(item: MysticDungeonRun) -> MysticDungeonRun:
            item.phase = DungeonPhase.BATTLE_TURN
            return item

        saved_run = await self.store.update_mystic_run(
            current_run.run_id,
            current_run.revision,
            activate_run,
        )
        self._schedule_deadline(
            saved_run.run_id,
            f"encounter:{saved_encounter.encounter_id}:active",
            action_deadline,
        )

    async def _expire_active_action(
        self,
        run: MysticDungeonRun,
        encounter: DungeonEncounter,
    ) -> None:
        eligible_user_ids = []
        for user_id, participant in sorted(encounter.participants.items()):
            if participant.defeated or participant.state.hp <= 0:
                continue
            if encounter.kind is EncounterKind.BOSS:
                segment_id = participant.target_segment_id
                segment = encounter.boss_segments.get(segment_id or "")
                if segment is None or segment.cleared:
                    continue
            eligible_user_ids.append(user_id)
        if not eligible_user_ids:
            if encounter.kind is EncounterKind.BOSS:
                await self.finish_boss_batch(run.run_id)
            return
        current_run = await self.store.get_mystic_run(run.run_id)
        if current_run is None:
            return
        user_id = eligible_user_ids[0]
        await self._submit_private_action(
            current_run,
            encounter,
            user_id,
            "普通攻击",
            f"timeout:{encounter.encounter_id}:{encounter.shared_round + 1}:{user_id}",
        )
    def _schedule_deadline(
        self,
        run_id: str,
        deadline_key: str,
        deadline: datetime,
    ) -> bool:
        task_key = (run_id, deadline_key)
        existing = self._deadline_tasks.get(task_key)
        if existing is not None and not existing.done():
            if self._deadline_times.get(task_key) == deadline:
                return False
            if existing is not asyncio.current_task():
                existing.cancel()
        task = asyncio.create_task(self._wait_for_deadline(run_id, task_key, deadline))
        self._deadline_tasks[task_key] = task
        self._deadline_times[task_key] = deadline

        def cleanup(done_task: asyncio.Task[None]) -> None:
            if self._deadline_tasks.get(task_key) is done_task:
                self._deadline_tasks.pop(task_key, None)
                self._deadline_times.pop(task_key, None)

        task.add_done_callback(cleanup)
        return True

    async def _wait_for_deadline(
        self,
        run_id: str,
        task_key: tuple[str, str],
        deadline: datetime,
    ) -> None:
        delay = max(0.0, (deadline - self._now()).total_seconds())
        await asyncio.sleep(delay)
        for _ in range(3):
            run = await self.store.get_mystic_run(run_id)
            if run is None:
                return
            try:
                await self.recover_run(run)
                return
            except (MysticRunConflict, MysticEncounterConflict):
                await asyncio.sleep(0)
        self._schedule_deadline(
            run_id,
            task_key[1],
            self._now() + timedelta(seconds=1),
        )

    async def active_run_id(self, user_id: str) -> str | None:
        return await self.store.find_active_mystic_run_id(user_id)

    async def accepts_private_message(self, user_id: str, text: str) -> bool:
        if parse_mystic_private_command(text) is None:
            return False
        return await self.resolve_private_context(user_id) is not None

    async def resolve_private_context(self, user_id: str) -> MysticPrivateRoute | None:
        route = await self.store.resolve_mystic_private_route(user_id)
        if route is not None:
            run_id, group_id = route
            run = await self.store.get_mystic_run(run_id)
            if run is not None and run.phase not in {
                DungeonPhase.COMPLETED,
                DungeonPhase.FAILED,
                DungeonPhase.ABANDONED,
            }:
                return MysticPrivateRoute(run_id=run_id, source_group_id=group_id)
        rescue = await self.store.find_active_rescue_for_user(user_id)
        if rescue is None:
            return None
        return MysticPrivateRoute(
            run_id=rescue.run_id,
            source_group_id=rescue.group_id,
            rescue_request_id=rescue.request_id,
        )

    async def take_rescue(
        self,
        group_id: str,
        request_id: str,
        rescuer_id: str,
    ) -> MysticCommandResult:
        request = await self.store.take_rescue_request(
            group_id,
            request_id,
            rescuer_id,
        )
        if request is None:
            raise ValueError("救援委托不可接取。")
        encounter = await self.store.get_mystic_encounter(request.encounter_id)
        if encounter is None:
            raise LookupError("救援遭遇不存在。")
        monster_record = UserRecord.from_dict(request.monster_snapshot)
        rescue_encounter = self.battle_service.create_ordinary_encounter(
            encounter_id=request.encounter_id,
            run_id=request.run_id,
            monster_record=monster_record,
            fixed_member_ids=(rescuer_id,),
        )
        rescue_encounter.shared_monster_hp = request.remaining_hp
        record = await self.store.get_user(rescuer_id)
        self.battle_service.join_ordinary_encounter(
            rescue_encounter,
            rescuer_id,
            record,
            {},
        )
        self.battle_service.begin_preparation(
            rescue_encounter,
            self._now()
            + timedelta(seconds=self.battle_service.config.battle_prepare_seconds),
        )

        def encounter_updater(_: DungeonEncounter) -> DungeonEncounter:
            return rescue_encounter

        await self.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            encounter_updater,
        )
        return MysticCommandResult(
            message="救援委托已接取，请私聊确认配装。",
            private_targets=(rescuer_id,),
            private_messages=((rescuer_id, "秘境配装"),),
        )

    async def create_from_offer(
        self,
        group_id: str,
        user_id: str,
        offer: DungeonEntryOffer,
    ) -> MysticCommandResult:
        if offer.mode is not DungeonMode.SOLO:
            raise ValueError("天机秘境入口仅支持单人模式。")
        if await self.store.find_active_mystic_run_id(user_id) is not None:
            raise ValueError("你已经在进行中的秘境中。")
        themes = sorted(
            (
                theme
                for theme in self.dungeon_service.catalog.themes.values()
                if theme.risk is offer.risk
            ),
            key=lambda theme: theme.theme_id,
        )
        theme_ids = [theme.theme_id for theme in themes]
        if offer.theme_id not in theme_ids:
            raise ValueError("天机秘境主题与风险等级不匹配。")
        run_id = self._id_factory(group_id, user_id)
        run, charge = self.dungeon_service.create_solo_run(
            run_id=run_id,
            group_id=group_id,
            user_id=user_id,
            risk=offer.risk,
            boss_realm_index=offer.boss_realm_index,
            map_seed=theme_ids.index(offer.theme_id),
            content_seed=_seed(run_id, "content"),
        )
        saved = await self.store.create_mystic_run(run, charge.payer_id, charge.token_name)
        await self.store.bind_mystic_private_routes(saved)
        prefix = "天机示警已锁定单人秘境。" if offer.insight else "单人秘境已开启。"
        return self._map_result(saved, message=prefix)

    async def resolve_current_node(self, run_id: str) -> MysticCommandResult:
        run = await self.store.get_mystic_run(run_id)
        if run is None:
            raise LookupError("秘境不存在。")
        if run.phase is not DungeonPhase.RESOLVING_NODE:
            raise ValueError("当前秘境不在节点结算阶段。")
        content = run.node_contents.get(run.current_node_id)
        if content is None:
            raise ValueError("当前节点没有事件内容。")
        resolved_kind = self.dungeon_service.node_resolution_kind(
            run,
            run.current_node_id,
        )
        if resolved_kind is NodeKind.BOSS:
            return await self._open_boss_encounter(run)
        if resolved_kind is NodeKind.COMBAT:
            encounter_id = f"encounter:{run.run_id}:{run.current_node_id}"
            leader_record = await self.store.get_user(run.leader_id)
            monster_record = UserRecord.from_dict(leader_record.to_dict())
            monster_record.user_id = f"monster:{run.theme_id}:{run.current_node_id}"
            encounter = self.battle_service.create_ordinary_encounter(
                encounter_id=encounter_id,
                run_id=run.run_id,
                monster_record=monster_record,
                fixed_member_ids=run.member_ids,
            )
            deadline = self._now() + timedelta(
                seconds=self.battle_service.config.encounter_response_seconds
            )
            encounter.phase_deadline = deadline.isoformat()
            def encounter_run_updater(item: MysticDungeonRun) -> MysticDungeonRun:
                item.active_encounter_id = encounter.encounter_id
                item.phase = DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
                return item

            saved_run, saved_encounter = (
                await self.store.create_mystic_encounter_and_update_run(
                    run.run_id,
                    run.revision,
                    encounter,
                    encounter_run_updater,
                )
            )
            self._schedule_deadline(
                saved_run.run_id,
                f"encounter:{saved_encounter.encounter_id}",
                deadline,
            )
            if saved_run.mode is DungeonMode.SOLO:
                return await self._respond(saved_run, saved_run.leader_id)
            return MysticCommandResult(
                message="遭遇战已触发，请固定队员在群中发送“应战”。",
                run=saved_run,
                updated_revision=saved_run.revision,
            )

        node_result: object | None = None

        def noncombat_updater(item: MysticDungeonRun) -> MysticDungeonRun:
            nonlocal node_result
            node_result = self.dungeon_service.resolve_noncombat_node(
                item,
                item.current_node_id,
                resolved_kind=resolved_kind,
            )
            return item

        saved_run = await self.store.update_mystic_run(
            run.run_id,
            run.revision,
            noncombat_updater,
        )
        if resolved_kind is NodeKind.RESOURCE:
            reward_count = sum(
                len(rewards)
                for rewards in getattr(node_result, "rewards_by_user", {}).values()
            )
            message = f"资源节点结算完成，队伍获得 {reward_count} 项临时收获。"
        elif resolved_kind is NodeKind.TRAP:
            message = "触发陷阱：每位成员至多损失一项临时收获。"
        else:
            message = "休整完成，队伍可以继续投骰。"
        if content.kind is NodeKind.RANDOM:
            message = f"随机事件揭示为{resolved_kind.value}。{message}"
        return self._map_result(saved_run, message=message)
    async def _open_boss_encounter(
        self,
        run: MysticDungeonRun,
    ) -> MysticCommandResult:
        member_records = {
            user_id: await self.store.get_user(user_id)
            for user_id in run.member_ids
        }
        boss_record = UserRecord.from_dict(member_records[run.leader_id].to_dict())
        boss_record.user_id = f"boss:{run.theme_id}"
        base_hp = max(
            1,
            int(
                combat_max_hp(boss_record)
                * self.battle_service.config.boss_hp_multiplier
            ),
        )
        encounter = self.battle_service.create_boss_encounter(
            base_hp=base_hp,
            member_ids=run.member_ids,
            encounter_id=f"boss:{run.run_id}:{run.current_node_id}",
            run_id=run.run_id,
            monster_record=boss_record,
            member_records=member_records,
        )
        encounter.phase = EncounterPhase.PREPARING
        prepare_deadline = self._now() + timedelta(
            seconds=self.battle_service.config.battle_prepare_seconds
        )
        encounter.phase_deadline = prepare_deadline.isoformat()
        def updater(item: MysticDungeonRun) -> MysticDungeonRun:
            item.active_encounter_id = encounter.encounter_id
            item.phase = DungeonPhase.PREPARING_BATTLE
            for user_id, member in item.members.items():
                member.boss_segment_id = f"segment:{user_id}"
            return item

        saved_run, saved_encounter = (
            await self.store.create_mystic_encounter_and_update_run(
                run.run_id,
                run.revision,
                encounter,
                updater,
            )
        )
        self._schedule_deadline(
            saved_run.run_id,
            f"encounter:{saved_encounter.encounter_id}:preparing",
            prepare_deadline,
        )
        return MysticCommandResult(
            message="Boss 战已开启，请全员在私聊中确认配装。",
            private_targets=saved_run.member_ids,
            private_messages=tuple(
                (user_id, "秘境配装")
                for user_id in saved_run.member_ids
            ),
            run=saved_run,
            updated_revision=saved_run.revision,
        )

    async def handle_group(
        self,
        group_id: str,
        user_id: str,
        text: str,
        *,
        nickname: str = "",
    ) -> MysticCommandResult:
        parsed = parse_mystic_group_command(text)
        if parsed is None:
            return MysticCommandResult(error="不是秘境指令。")
        await self.store.touch_group_member(
            group_id,
            user_id,
            self._now().date().isoformat(),
            nickname or user_id,
        )
        try:
            return await self._dispatch_group(group_id, user_id, parsed)
        except (MysticRunConflict, MysticEncounterConflict):
            return MysticCommandResult(
                error="秘境状态已发生变化，请重新发送指令。"
            )
        except (LookupError, PermissionError, ValueError) as exc:
            return MysticCommandResult(error=self._error_text(exc))

    async def handle_private(
        self,
        user_id: str,
        text: str,
        *,
        action_id: str,
    ) -> MysticCommandResult:
        action = parse_mystic_private_command(text)
        if action is None:
            return MysticCommandResult(error="不是秘境私聊指令。")
        route = await self.resolve_private_context(user_id)
        if route is None:
            return MysticCommandResult(error="当前没有可操作的秘境。")
        run = await self.store.get_mystic_run(route.run_id)
        if run is None:
            return MysticCommandResult(error="当前没有可操作的秘境。")
        if action == "秘境状态":
            return self._status_result(run)
        if action == "秘境地图":
            return self._map_result(run)
        if run.active_encounter_id is None:
            return MysticCommandResult(error="当前没有可操作的秘境遭遇。")
        encounter = await self.store.get_mystic_encounter(run.active_encounter_id)
        if encounter is None:
            return MysticCommandResult(error="秘境遭遇状态缺失。")
        try:
            if action == "确认配装":
                return await self._confirm_loadout(run, encounter, user_id)
            if action == "自动战斗":
                return await self._run_auto_battle(
                    run,
                    encounter,
                    user_id,
                    action_id,
                )
            if action.startswith("秘境配装 "):
                return MysticCommandResult(
                    message="请先使用原有装备指令调整装备，完成后发送“确认配装”。",
                    run=run,
                    updated_revision=run.revision,
                )
            if action == "普通攻击" or action.startswith("秘境技能 "):
                action_text = (
                    action.removeprefix("秘境技能 ").strip()
                    if action.startswith("秘境技能 ")
                    else action
                )
                return await self._submit_private_action(
                    run,
                    encounter,
                    user_id,
                    action_text,
                    action_id,
                    rescue_request_id=route.rescue_request_id,
                )
            return MysticCommandResult(error="该秘境私聊指令暂不可用。")
        except (MysticRunConflict, MysticEncounterConflict):
            return MysticCommandResult(
                error="秘境状态已发生变化，请重新发送指令。"
            )
        except (LookupError, PermissionError, ValueError) as exc:
            return MysticCommandResult(error=self._error_text(exc))

    async def _confirm_loadout(
        self,
        run: MysticDungeonRun,
        encounter: DungeonEncounter,
        user_id: str,
    ) -> MysticCommandResult:
        if encounter.phase is not EncounterPhase.PREPARING:
            raise ValueError("当前不在配装准备阶段。")
        record = await self.store.get_user(user_id)
        record_data = record.to_dict()
        equipment_snapshot = {
            key: value
            for key, value in record_data.items()
            if key.startswith("equipped_")
        }
        all_confirmed = False
        action_deadline = self._now() + timedelta(
            seconds=self.battle_service.config.player_action_seconds
        )

        def encounter_updater(item: DungeonEncounter) -> DungeonEncounter:
            nonlocal all_confirmed
            all_confirmed = self.battle_service.confirm_loadout(
                item,
                user_id,
                record,
                equipment_snapshot,
            )
            if all_confirmed:
                item.phase = EncounterPhase.ACTIVE
                item.phase_deadline = action_deadline.isoformat()
            return item

        def run_updater(item: MysticDungeonRun) -> MysticDungeonRun:
            if all_confirmed:
                item.phase = DungeonPhase.BATTLE_TURN
            return item

        saved_run, saved_encounter = (
            await self.store.update_mystic_run_and_encounter(
                run.run_id,
                run.revision,
                encounter.encounter_id,
                encounter.revision,
                run_updater,
                encounter_updater,
            )
        )
        if all_confirmed:
            self._schedule_deadline(
                saved_run.run_id,
                f"encounter:{saved_encounter.encounter_id}:active",
                action_deadline,
            )
        return MysticCommandResult(
            message=(
                "配装已确认，战斗开始。"
                if all_confirmed
                else "配装已确认，等待其他参与者。"
            ),
            run=saved_run,
            updated_revision=saved_run.revision,
        )

    async def _run_auto_battle(
        self,
        run: MysticDungeonRun,
        encounter: DungeonEncounter,
        user_id: str,
        action_id: str,
    ) -> MysticCommandResult:
        record = await self.store.get_user(user_id)

        def enable_auto(item: DungeonEncounter) -> DungeonEncounter:
            self.battle_service.set_auto_battle(item, user_id, record)
            return item

        current_encounter = await self.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            enable_auto,
        )
        current_run = run
        result = MysticCommandResult(
            message="已启用自动战斗。",
            run=current_run,
            updated_revision=current_run.revision,
        )
        for index in range(100):
            participant = current_encounter.participants.get(user_id)
            if (
                current_encounter.phase is not EncounterPhase.ACTIVE
                or participant is None
                or not participant.auto_battle
                or participant.defeated
                or participant.state.hp <= 0
            ):
                break
            result = await self._submit_private_action(
                current_run,
                current_encounter,
                user_id,
                "普通攻击",
                f"{action_id}:auto:{index + 1}",
            )
            if result.run is not None:
                current_run = result.run
            if current_run.active_encounter_id is None:
                break
            restored = await self.store.get_mystic_encounter(
                current_run.active_encounter_id
            )
            if restored is None:
                break
            current_encounter = restored
        return replace(
            result,
            message=f"自动战斗已执行。\n{result.message}".strip(),
        )
    async def _submit_private_action(
        self,
        run: MysticDungeonRun,
        encounter: DungeonEncounter,
        user_id: str,
        action_text: str,
        action_id: str,
        *,
        rescue_request_id: str | None = None,
    ) -> MysticCommandResult:
        action_result: dict[str, object] = {}
        encounter_result: object | None = None
        next_action_deadline = self._now() + timedelta(
            seconds=self.battle_service.config.player_action_seconds
        )

        def encounter_updater(item: DungeonEncounter) -> DungeonEncounter:
            nonlocal action_result, encounter_result
            action_result = self.battle_service.submit_action(
                item,
                user_id,
                action_text,
                action_id=action_id,
            )
            encounter_result = self.battle_service.finish_encounter(item)
            if (
                item.kind.value == "ordinary"
                and item.shared_monster_hp > 0
                and item.phase is not EncounterPhase.FAILED
                and item.participants
                and all(
                    participant.defeated or participant.state.hp <= 0
                    for participant in item.participants.values()
                )
                and set(item.fixed_member_ids) - item.attempted_user_ids
            ):
                self.battle_service.begin_next_response_batch(
                    item,
                    self._now()
                    + timedelta(
                        seconds=self.battle_service.config.encounter_response_seconds
                    ),
                )
            elif item.phase is EncounterPhase.ACTIVE:
                item.phase_deadline = next_action_deadline.isoformat()
            return item

        encounter_phase = encounter.phase

        def run_updater(item: MysticDungeonRun) -> MysticDungeonRun:
            completed = bool(getattr(encounter_result, "completed", False))
            needs_rescue = bool(
                getattr(encounter_result, "needs_rescue", False)
            )
            eligible_loot_user_ids = tuple(
                getattr(encounter_result, "eligible_loot_user_ids", ())
            )
            if (
                completed
                and rescue_request_id is None
                and encounter.kind is not EncounterKind.BOSS
            ):
                self.dungeon_service.grant_encounter_rewards(
                    item,
                    item.current_node_id,
                    eligible_loot_user_ids,
                )
                if item.current_node_id not in item.cleared_node_ids:
                    item.cleared_node_ids.append(item.current_node_id)
                item.active_encounter_id = None
                item.phase = DungeonPhase.READY_TO_ROLL
            elif needs_rescue:
                item.phase = DungeonPhase.AWAITING_RESCUE
            elif encounter_phase is EncounterPhase.AWAITING_RESPONSE:
                item.phase = DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
            return item

        def atomic_encounter_updater(
            item: DungeonEncounter,
        ) -> DungeonEncounter:
            nonlocal encounter_phase
            updated = encounter_updater(item)
            encounter_phase = updated.phase
            return updated

        saved_run, saved_encounter = (
            await self.store.update_mystic_run_and_encounter(
                run.run_id,
                run.revision,
                encounter.encounter_id,
                encounter.revision,
                run_updater,
                atomic_encounter_updater,
            )
        )
        completed = bool(getattr(encounter_result, "completed", False))
        if saved_encounter.phase is EncounterPhase.ACTIVE:
            self._schedule_deadline(
                run.run_id,
                f"encounter:{saved_encounter.encounter_id}:active",
                next_action_deadline,
            )
        elif (
            saved_encounter.phase is EncounterPhase.AWAITING_RESPONSE
            and saved_encounter.phase_deadline is not None
        ):
            self._schedule_deadline(
                run.run_id,
                f"encounter:{saved_encounter.encounter_id}:response",
                datetime.fromisoformat(saved_encounter.phase_deadline),
            )
        if (
            saved_encounter.kind is EncounterKind.BOSS
            and not completed
            and all(
                segment.cleared
                or saved_encounter.participants[segment.owner_user_id].defeated
                or saved_encounter.participants[segment.owner_user_id].state.hp <= 0
                for segment in saved_encounter.boss_segments.values()
            )
        ):
            return await self.finish_boss_batch(run.run_id)
        if completed:
            if rescue_request_id is not None:
                await self.store.complete_rescue_request(
                    rescue_request_id,
                    user_id,
                )
                restored_run = await self.store.get_mystic_run(run.run_id)
                if restored_run is None:
                    raise LookupError("救援副本恢复失败。")
                saved_run = restored_run
            elif saved_encounter.kind is EncounterKind.BOSS:
                saved_run = await self.store.settle_mystic_run(
                    run.run_id,
                    MysticSettlement(
                        settlement_id=f"mystic:{run.run_id}:complete",
                        rewards_by_user={
                            user_id: [dict(reward) for reward in rewards]
                            for user_id, rewards in run.temporary_rewards_by_user.items()
                        },
                    ),
                )

        return MysticCommandResult(
            message=(
                f"造成 {action_result.get('damage', 0)} 点伤害，"
                f"剩余生命 {action_result.get('player_hp', 0)}。"
            ),
            run=saved_run,
            updated_revision=saved_run.revision,
        )

    async def _dispatch_group(
        self,
        group_id: str,
        user_id: str,
        parsed: MysticParsedCommand,
    ) -> MysticCommandResult:
        if parsed.action is MysticGroupAction.CREATE_SOLO:
            return await self._create_solo(group_id, user_id, parsed.argument)
        if parsed.action is MysticGroupAction.CREATE_TEAM:
            return await self._create_team(group_id, user_id, parsed.argument)
        run = await self._group_run(group_id, user_id)
        if parsed.action is MysticGroupAction.STATUS:
            return self._status_result(run)
        if run is None:
            raise ValueError("本群没有进行中的秘境。")
        if parsed.action is MysticGroupAction.JOIN:
            return await self._join_lobby(run, user_id)
        if parsed.action is MysticGroupAction.LEAVE_LOBBY:
            return await self._leave_lobby(run, user_id)
        if parsed.action is MysticGroupAction.READY:
            return await self._ready_lobby(run, user_id)
        if parsed.action is MysticGroupAction.START:
            return await self._start_run(run, user_id)
        if parsed.action is MysticGroupAction.ROLL:
            return await self._roll(run, user_id)
        if parsed.action is MysticGroupAction.CHOOSE_BRANCH:
            return await self._choose_branch(run, user_id, parsed.argument)
        if parsed.action is MysticGroupAction.MAP:
            return self._map_result(run)
        if parsed.action is MysticGroupAction.RESPOND:
            if parsed.argument:
                return await self._assist_boss(run, user_id, parsed.argument)
            return await self._respond(run, user_id)
        if parsed.action is MysticGroupAction.VOTE_CONTINUE:
            return await self._vote_boss_continuation(run, user_id, parsed.argument)
        if parsed.action in {
            MysticGroupAction.VOTE_TRANSFER,
            MysticGroupAction.VOTE_ABANDON,
        }:
            return MysticCommandResult(
                message="该秘境操作将在私聊中继续处理。",
                run=run,
                updated_revision=run.revision,
            )
        raise ValueError("秘境指令暂不支持。")

    async def finish_boss_batch(self, run_id: str) -> MysticCommandResult:
        run = await self.store.get_mystic_run(run_id)
        if run is None or run.active_encounter_id is None:
            raise LookupError("Boss 遭遇不存在。")
        encounter = await self.store.get_mystic_encounter(run.active_encounter_id)
        if encounter is None or encounter.kind is not EncounterKind.BOSS:
            raise ValueError("当前不是 Boss 遭遇。")
        if not all(
            segment.cleared
            or encounter.participants[segment.owner_user_id].defeated
            or encounter.participants[segment.owner_user_id].state.hp <= 0
            for segment in encounter.boss_segments.values()
        ):
            raise ValueError("Boss 批次尚未结束。")
        living = any(
            participant.state.hp > 0 and not participant.defeated
            for participant in encounter.participants.values()
        )
        if len(run.members) == 1 or not living:
            closed = await self.store.close_mystic_run(run.run_id, DungeonPhase.FAILED)
            return MysticCommandResult(
                message="Boss 战失败，秘境已关闭。",
                run=closed,
                updated_revision=closed.revision,
            )

        def run_updater(item: MysticDungeonRun) -> MysticDungeonRun:
            self.dungeon_service.begin_boss_continuation_vote(
                item,
                self._now()
                + timedelta(seconds=self.battle_service.config.boss_vote_seconds),
            )
            return item

        def encounter_updater(item: DungeonEncounter) -> DungeonEncounter:
            item.phase = EncounterPhase.AWAITING_CONTINUE_VOTE
            return item

        saved_run, _ = await self.store.update_mystic_run_and_encounter(
            run.run_id,
            run.revision,
            encounter.encounter_id,
            encounter.revision,
            run_updater,
            encounter_updater,
        )
        vote = saved_run.active_vote
        if vote is not None:
            self._schedule_deadline(
                saved_run.run_id,
                f"vote:{vote.vote_id}",
                datetime.fromisoformat(vote.deadline),
            )
        return MysticCommandResult(
            message="Boss 批次结束，请队伍投票是否继续战斗。",
            run=saved_run,
            updated_revision=saved_run.revision,
            vote_created=True,
        )

    async def _vote_boss_continuation(
        self,
        run: MysticDungeonRun,
        user_id: str,
        choice: str,
    ) -> MysticCommandResult:
        if run.phase is not DungeonPhase.AWAITING_BOSS_VOTE:
            raise ValueError("当前没有等待中的 Boss 续战投票。")
        encounter = await self.store.get_mystic_encounter(
            run.active_encounter_id or ""
        )
        if encounter is None:
            raise LookupError("Boss 遭遇状态缺失。")
        prospective_run = MysticDungeonRun.from_dict(run.to_dict())
        vote = prospective_run.active_vote
        if vote is None:
            raise ValueError("Boss 续战投票状态缺失。")
        vote_result = self.dungeon_service.cast_vote(
            prospective_run,
            user_id,
            choice == "同意",
        )
        approvals = {
            member_id: member_id in vote.approvals
            for member_id in vote.eligible_user_ids
        }
        if vote_result.failed:
            prospective_run.phase = DungeonPhase.FAILED
        action_deadline = self._now() + timedelta(
            seconds=self.battle_service.config.player_action_seconds
        )
        continued = False

        def run_updater(_: MysticDungeonRun) -> MysticDungeonRun:
            return prospective_run

        def encounter_updater(item: DungeonEncounter) -> DungeonEncounter:
            nonlocal continued
            if vote_result.passed:
                continued = self.battle_service.open_boss_continuation(
                    item,
                    approvals=approvals,
                )
                if continued:
                    item.phase_deadline = action_deadline.isoformat()
                else:
                    prospective_run.phase = DungeonPhase.FAILED
            elif vote_result.failed:
                item.phase = EncounterPhase.FAILED
                item.phase_deadline = None
            return item

        saved_run, saved_encounter = (
            await self.store.update_mystic_run_and_encounter(
                run.run_id,
                run.revision,
                encounter.encounter_id,
                encounter.revision,
                run_updater,
                encounter_updater,
            )
        )
        effective_passed = vote_result.passed and continued
        if effective_passed:
            self._schedule_deadline(
                saved_run.run_id,
                f"encounter:{saved_encounter.encounter_id}:active",
                action_deadline,
            )
        elif vote_result.failed or vote_result.passed:
            saved_run = await self.store.close_mystic_run(
                saved_run.run_id,
                DungeonPhase.FAILED,
            )
        return MysticCommandResult(
            message=(
                "Boss 续战投票通过。"
                if effective_passed
                else "Boss 续战投票未通过。"
                if vote_result.failed or vote_result.passed
                else "已记录 Boss 续战投票。"
            ),
            run=saved_run,
            updated_revision=saved_run.revision,
            vote_passed=effective_passed,
        )

    async def _assist_boss(
        self,
        run: MysticDungeonRun,
        helper_id: str,
        target_text: str,
    ) -> MysticCommandResult:
        if run.phase is not DungeonPhase.BATTLE_TURN:
            raise ValueError("当前不在 Boss 战斗阶段。")
        encounter = await self.store.get_mystic_encounter(run.active_encounter_id or "")
        if encounter is None or encounter.kind is not EncounterKind.BOSS:
            raise ValueError("当前不是 Boss 遭遇。")
        target_user_id = target_text
        if target_text.isdigit():
            index = int(target_text) - 1
            if not 0 <= index < len(run.member_ids):
                raise ValueError("协助目标编号超出范围。")
            target_user_id = run.member_ids[index]
        segment_id = f"segment:{target_user_id}"

        def updater(item: DungeonEncounter) -> DungeonEncounter:
            self.battle_service.join_boss_assist(
                item,
                helper_id=helper_id,
                segment_id=segment_id,
            )
            return item

        await self.store.update_mystic_encounter(
            encounter.encounter_id,
            encounter.revision,
            updater,
        )
        return MysticCommandResult(
            message=f"{helper_id} 已协助 {target_user_id} 的 Boss 分段。",
            run=run,
            updated_revision=run.revision,
        )

    async def _respond(
        self,
        run: MysticDungeonRun,
        user_id: str,
    ) -> MysticCommandResult:
        if run.phase is not DungeonPhase.AWAITING_ENCOUNTER_RESPONSE:
            raise ValueError("当前没有等待应战的秘境遭遇。")
        if run.active_encounter_id is None:
            raise ValueError("秘境遭遇状态缺失。")
        encounter = await self.store.get_mystic_encounter(run.active_encounter_id)
        if encounter is None:
            raise LookupError("秘境遭遇不存在。")
        record = await self.store.get_user(user_id)
        record_data = record.to_dict()
        equipment_snapshot = {
            key: value
            for key, value in record_data.items()
            if key.startswith("equipped_")
        }
        prepare_deadline = self._now() + timedelta(
            seconds=self.battle_service.config.battle_prepare_seconds
        )
        preparation_started = False

        def encounter_updater(item: DungeonEncounter) -> DungeonEncounter:
            nonlocal preparation_started
            self.battle_service.join_ordinary_encounter(
                item,
                user_id,
                record,
                equipment_snapshot,
            )
            preparation_started = set(item.participants) == set(item.fixed_member_ids)
            if preparation_started:
                self.battle_service.begin_preparation(item, prepare_deadline)
            return item

        def run_updater(item: MysticDungeonRun) -> MysticDungeonRun:
            item.phase = (
                DungeonPhase.PREPARING_BATTLE
                if preparation_started
                else DungeonPhase.AWAITING_ENCOUNTER_RESPONSE
            )
            return item

        saved_run, saved_encounter = (
            await self.store.update_mystic_run_and_encounter(
                run.run_id,
                run.revision,
                encounter.encounter_id,
                encounter.revision,
                run_updater,
                encounter_updater,
            )
        )
        if preparation_started:
            self._schedule_deadline(
                saved_run.run_id,
                f"encounter:{saved_encounter.encounter_id}:preparing",
                prepare_deadline,
            )
        return MysticCommandResult(
            message=(
                f"{user_id} 已应战，配装准备开始。"
                if preparation_started
                else f"{user_id} 已应战，等待其他队员或响应窗口结束。"
            ),
            private_targets=(user_id,),
            private_messages=((user_id, "秘境配装"),),
            run=saved_run,
            updated_revision=saved_run.revision,
        )
    async def _create_solo(
        self,
        group_id: str,
        user_id: str,
        risk_text: str,
    ) -> MysticCommandResult:
        if await self.store.find_active_mystic_run_id(user_id) is not None:
            raise ValueError("你已经在进行中的秘境中。")
        risk = _parse_risk(risk_text)
        record = await self.store.get_user(user_id)
        run_id = self._id_factory(group_id, user_id)
        run, charge = self.dungeon_service.create_solo_run(
            run_id=run_id,
            group_id=group_id,
            user_id=user_id,
            risk=risk,
            boss_realm_index=record.realm_index,
            map_seed=_seed(run_id, "map"),
            content_seed=_seed(run_id, "content"),
        )
        saved = await self.store.create_mystic_run(run, charge.payer_id, charge.token_name)
        await self.store.bind_mystic_private_routes(saved)
        return self._map_result(saved, message="单人秘境已开启。")

    async def _create_team(
        self,
        group_id: str,
        user_id: str,
        risk_text: str,
    ) -> MysticCommandResult:
        if await self._team_group_run(group_id) is not None:
            raise ValueError("本群已经有进行中的秘境队伍。")
        if await self.store.find_active_mystic_run_id(user_id) is not None:
            raise ValueError("你已经在进行中的秘境中。")
        run = self.dungeon_service.create_lobby(
            run_id=self._id_factory(group_id, user_id),
            group_id=group_id,
            leader_id=user_id,
            risk=_parse_risk(risk_text),
        )
        saved = await self.store.create_mystic_lobby(run)
        return MysticCommandResult(
            message="秘境队伍已创建，等待队员加入。",
            run=saved,
            updated_revision=saved.revision,
        )

    async def _join_lobby(
        self,
        run: MysticDungeonRun,
        user_id: str,
    ) -> MysticCommandResult:
        if run.phase is not DungeonPhase.LOBBY:
            raise ValueError("秘境已经开始，不能加入队伍。")
        if await self.store.find_active_mystic_run_id(user_id) not in {None, run.run_id}:
            raise ValueError("你已经在其他秘境中。")
        updated = await self.store.update_mystic_lobby(
            run.run_id,
            run.revision,
            lambda item: self._join(item, user_id),
        )
        return MysticCommandResult(
            message=f"{user_id} 已加入秘境队伍。",
            run=updated,
            updated_revision=updated.revision,
        )

    def _join(self, run: MysticDungeonRun, user_id: str) -> MysticDungeonRun:
        self.dungeon_service.join_lobby(run, user_id, user_id)
        return run

    async def _leave_lobby(
        self,
        run: MysticDungeonRun,
        user_id: str,
    ) -> MysticCommandResult:
        updated = await self.store.update_mystic_lobby(
            run.run_id,
            run.revision,
            lambda item: self._remove(item, user_id),
        )
        return MysticCommandResult(
            message=f"{user_id} 已退出秘境队伍。",
            run=updated,
            updated_revision=updated.revision,
        )

    def _remove(self, run: MysticDungeonRun, user_id: str) -> MysticDungeonRun:
        self.dungeon_service.remove_lobby_member(run, user_id)
        return run

    async def _ready_lobby(
        self,
        run: MysticDungeonRun,
        user_id: str,
    ) -> MysticCommandResult:
        updated = await self.store.update_mystic_lobby(
            run.run_id,
            run.revision,
            lambda item: self._ready(item, user_id),
        )
        return MysticCommandResult(
            message=f"{user_id} 已准备。",
            run=updated,
            updated_revision=updated.revision,
        )

    def _ready(self, run: MysticDungeonRun, user_id: str) -> MysticDungeonRun:
        self.dungeon_service.set_ready(run, user_id, True)
        return run

    async def _start_run(
        self,
        run: MysticDungeonRun,
        user_id: str,
    ) -> MysticCommandResult:
        if run.leader_id != user_id:
            raise PermissionError("只有队长可以开始秘境。")
        record = await self.store.get_user(user_id)
        charge = self.dungeon_service.start_run(
            run,
            boss_realm_index=record.realm_index,
            map_seed=_seed(run.run_id, "map"),
            content_seed=_seed(run.run_id, "content"),
        )
        saved = await self.store.create_mystic_run(run, charge.payer_id, charge.token_name)
        await self.store.bind_mystic_private_routes(saved)
        return self._map_result(saved, message="秘境已开启。")

    async def _roll(
        self,
        run: MysticDungeonRun,
        user_id: str,
    ) -> MysticCommandResult:
        if run.leader_id != user_id:
            raise PermissionError("只有队长可以投骰。")
        dice_value = int(self._dice_roller())
        if not 1 <= dice_value <= 6:
            raise ValueError("服务器骰子点数必须是 1 到 6。")
        movement: MovementResult | None = None

        def updater(item: MysticDungeonRun) -> MysticDungeonRun:
            nonlocal movement
            movement = self.dungeon_service.roll(item, user_id, dice_value)
            return item

        saved = await self.store.update_mystic_run(run.run_id, run.revision, updater)
        movement_message = f"掷出 {dice_value} 点。{self._movement_message(movement)}"
        if saved.phase is DungeonPhase.RESOLVING_NODE:
            resolved = await self.resolve_current_node(saved.run_id)
            return replace(
                resolved,
                message=f"{movement_message}\n{resolved.message}".strip(),
            )
        return self._map_result(saved, message=movement_message)
    async def _choose_branch(
        self,
        run: MysticDungeonRun,
        user_id: str,
        branch_text: str,
    ) -> MysticCommandResult:
        if run.leader_id != user_id:
            raise PermissionError("只有队长可以选择分支。")
        target_node_id = _branch_target(run, branch_text)
        movement: MovementResult | None = None

        def updater(item: MysticDungeonRun) -> MysticDungeonRun:
            nonlocal movement
            movement = self.dungeon_service.choose_branch(item, user_id, target_node_id)
            return item

        saved = await self.store.update_mystic_run(run.run_id, run.revision, updater)
        movement_message = self._movement_message(movement)
        if saved.phase is DungeonPhase.RESOLVING_NODE:
            resolved = await self.resolve_current_node(saved.run_id)
            return replace(
                resolved,
                message=f"{movement_message}\n{resolved.message}".strip(),
            )
        return self._map_result(saved, message=movement_message)

    async def _group_run(
        self,
        group_id: str,
        user_id: str = "",
    ) -> MysticDungeonRun | None:
        if user_id:
            run_id = await self.store.find_active_mystic_run_id(user_id)
            if run_id is not None:
                actor_run = await self.store.get_mystic_run(run_id)
                if actor_run is not None and actor_run.source_group_id == group_id:
                    return actor_run
        return await self._team_group_run(group_id)

    async def _team_group_run(self, group_id: str) -> MysticDungeonRun | None:
        runs = await self.store.list_active_mystic_runs()
        matching = [
            run
            for run in runs
            if run.source_group_id == group_id and run.mode is DungeonMode.TEAM
        ]
        return min(matching, key=lambda run: run.run_id) if matching else None

    def _status_result(self, run: MysticDungeonRun | None) -> MysticCommandResult:
        if run is None:
            return MysticCommandResult(message="本群没有进行中的秘境。")
        return MysticCommandResult(
            message=(
                f"秘境 {run.theme_id or '队伍大厅'} · {run.phase.value} · "
                f"{len(run.members)} 人 · 当前节点 {run.current_node_id or '未开始'}"
            ),
            run=run,
            updated_revision=run.revision,
        )

    def _map_result(
        self,
        run: MysticDungeonRun,
        *,
        message: str = "",
    ) -> MysticCommandResult:
        model = self._render_model(run)
        image = self.renderer.render(model)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        fallback = self.renderer.text_fallback(model)
        return MysticCommandResult(
            message=f"{message}\n{fallback}".strip(),
            image_bytes=buffer.getvalue(),
            private_targets=run.member_ids,
            run=run,
            updated_revision=run.revision,
            map_required=True,
        )

    def _render_model(self, run: MysticDungeonRun) -> MysticMapRenderModel:
        if run.phase in {DungeonPhase.LOBBY, DungeonPhase.CREATING}:
            raise ValueError("秘境尚未生成地图。")
        template = self.dungeon_service.catalog.templates[run.template_id]
        theme = self.dungeon_service.catalog.themes[run.theme_id]
        graph = template.active_graph(run.map_size)
        traversed = set(run.visited_edge_ids)
        boss_portrait_path = self._boss_portrait_path(run.theme_id, run.risk)
        nodes = tuple(
            RenderedNode(
                node_id=node.node_id,
                x=node.x,
                y=node.y,
                kind=self._render_node_kind(
                    run,
                    node.node_id,
                    graph.start_node_id,
                    graph.boss_node_id,
                ),
                label=node.node_id,
                boss_portrait_path=(
                    boss_portrait_path
                    if node.node_id == graph.boss_node_id
                    else None
                ),
            )
            for node in graph.nodes
        )
        next_edges = {
            edge.edge_id
            for edge in graph.edges
            if edge.source_node_id == run.current_node_id
        }
        edges = tuple(
            RenderedEdge(
                edge_id=edge.edge_id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                state=(
                    "traversed"
                    if edge.edge_id in traversed
                    else "next"
                    if edge.edge_id in next_edges
                    else "future"
                ),
            )
            for edge in graph.edges
        )
        reward_count = sum(len(rewards) for rewards in run.temporary_rewards_by_user.values())
        return MysticMapRenderModel(
            title=theme.display_name,
            subtitle=f"{run.map_size} 格秘境 · {run.risk.value}",
            background_path=theme.background_path,
            nodes=nodes,
            edges=edges,
            current_node_id=run.current_node_id,
            team_size=len(run.members),
            temporary_reward_summary=f"{reward_count} 项临时收获",
        )

    def _boss_portrait_path(
        self,
        theme_id: str,
        risk: DungeonRisk,
    ) -> Path | None:
        digest = hashlib.sha256(theme_id.encode("utf-8")).digest()
        portrait_index = int.from_bytes(digest[:2], "big") % 30 + 1
        prefix = "beast" if risk is DungeonRisk.NORMAL else "evil_god"
        portrait_path = (
            Path(__file__).resolve().parent
            / "assets"
            / "character_portraits"
            / "portraits"
            / f"{prefix}_{portrait_index:03d}.png"
        )
        return portrait_path if portrait_path.is_file() else None

    def _render_node_kind(
        self,
        run: MysticDungeonRun,
        node_id: str,
        start_node_id: str,
        boss_node_id: str,
    ) -> NodeKind:
        if node_id == start_node_id:
            return NodeKind.START
        if node_id == boss_node_id:
            return NodeKind.BOSS
        content = run.node_contents.get(node_id)
        return content.kind if content is not None else NodeKind.RANDOM

    def _movement_message(self, movement: MovementResult | None) -> str:
        if movement is None:
            return "秘境地图已更新。"
        if movement.pending_branch_choices:
            return f"前进暂停，请选择分支：{'、'.join(movement.pending_branch_choices)}"
        if movement.landed_node_id:
            return f"已抵达节点 {movement.landed_node_id}。"
        return "秘境地图已更新。"

    def _error_text(self, error: Exception) -> str:
        return str(error) or "秘境操作失败。"


def _parse_risk(value: str) -> DungeonRisk:
    if value == "普通":
        return DungeonRisk.NORMAL
    if value in {"高风险", "高难"}:
        return DungeonRisk.HIGH
    raise ValueError("秘境类型必须是普通或高风险。")


def _branch_target(run: MysticDungeonRun, branch_text: str) -> str:
    if branch_text.isdigit():
        index = int(branch_text) - 1
        if 0 <= index < len(run.pending_branch_choices):
            return run.pending_branch_choices[index]
        raise ValueError("分支编号超出范围。")
    if branch_text in run.pending_branch_choices:
        return branch_text
    raise ValueError("请选择当前显示的分支。")


def _seed(run_id: str, purpose: str) -> int:
    digest = hashlib.sha256(f"{run_id}:{purpose}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")
