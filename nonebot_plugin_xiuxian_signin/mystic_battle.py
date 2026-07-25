from __future__ import annotations

import asyncio
import inspect
import threading
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from contextlib import contextmanager
from typing import Any, Awaitable, Callable, Iterator, Mapping, Sequence

from .domain import (
    CombatRuntimeState,
    UserRecord,
    combat_max_hp,
    resolve_combat_action,
)
from .mystic_dungeon import MysticGameplayConfig


class EncounterKind(StrEnum):
    ORDINARY = "ordinary"
    BOSS = "boss"
    RESCUE = "rescue"


class EncounterPhase(StrEnum):
    AWAITING_RESPONSE = "awaiting_response"
    PREPARING = "preparing"
    ACTIVE = "active"
    AWAITING_CONTINUE_VOTE = "awaiting_continue_vote"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DungeonBattleParticipant:
    user_id: str
    state: CombatRuntimeState
    equipment_snapshot: dict[str, Any]
    valid_action_count: int = 0
    defeated: bool = False
    auto_battle: bool = False
    target_segment_id: str | None = None
    record_snapshot: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "state": _combat_state_to_dict(self.state),
            "equipment_snapshot": dict(self.equipment_snapshot),
            "valid_action_count": self.valid_action_count,
            "defeated": self.defeated,
            "auto_battle": self.auto_battle,
            "target_segment_id": self.target_segment_id,
            "record_snapshot": dict(self.record_snapshot),
        }

    @classmethod
    def from_dict(cls, value: Any) -> DungeonBattleParticipant:
        data = _object(value, "battle participant")
        _keys(
            data,
            {
                "user_id",
                "state",
                "equipment_snapshot",
                "valid_action_count",
                "defeated",
                "auto_battle",
                "target_segment_id",
            },
            {"record_snapshot"},
            "battle participant",
        )
        participant = cls(
            user_id=_string(data["user_id"], "battle participant.user_id"),
            state=_combat_state_from_dict(data["state"]),
            equipment_snapshot=_object(
                data["equipment_snapshot"],
                "battle participant.equipment_snapshot",
            ),
            valid_action_count=_integer(
                data["valid_action_count"],
                "battle participant.valid_action_count",
            ),
            defeated=_boolean(data["defeated"], "battle participant.defeated"),
            auto_battle=_boolean(data["auto_battle"], "battle participant.auto_battle"),
            target_segment_id=_optional_string(
                data["target_segment_id"],
                "battle participant.target_segment_id",
            ),
            record_snapshot=_object(
                data.get("record_snapshot", {}),
                "battle participant.record_snapshot",
            ),
        )
        if participant.valid_action_count < 0:
            raise ValueError("battle participant action count must not be negative")
        if participant.state.hp == 0 and not participant.defeated:
            raise ValueError("zero-HP battle participant must be defeated")
        return participant


@dataclass
class BossHealthSegment:
    segment_id: str
    owner_user_id: str
    initial_hp: int
    hp: int
    cleared: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "owner_user_id": self.owner_user_id,
            "initial_hp": self.initial_hp,
            "hp": self.hp,
            "cleared": self.cleared,
        }

    @classmethod
    def from_dict(cls, value: Any) -> BossHealthSegment:
        data = _object(value, "boss segment")
        _exact_keys(
            data,
            {"segment_id", "owner_user_id", "initial_hp", "hp", "cleared"},
            "boss segment",
        )
        segment = cls(
            segment_id=_string(data["segment_id"], "boss segment.segment_id"),
            owner_user_id=_string(data["owner_user_id"], "boss segment.owner_user_id"),
            initial_hp=_integer(data["initial_hp"], "boss segment.initial_hp"),
            hp=_integer(data["hp"], "boss segment.hp"),
            cleared=_boolean(data["cleared"], "boss segment.cleared"),
        )
        if segment.initial_hp <= 0 or not 0 <= segment.hp <= segment.initial_hp:
            raise ValueError("boss segment HP is outside its valid range")
        if segment.cleared != (segment.hp == 0):
            raise ValueError("boss segment cleared flag does not match HP")
        return segment


@dataclass
class DungeonEncounter:
    encounter_id: str
    run_id: str
    kind: EncounterKind
    phase: EncounterPhase
    monster_record: dict[str, Any]
    shared_monster_hp: int
    participants: dict[str, DungeonBattleParticipant]
    boss_segments: dict[str, BossHealthSegment] = field(default_factory=dict)
    action_ids: set[str] = field(default_factory=set)
    cached_action_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    shared_round: int = 0
    damage_multiplier: float = 1.0
    revision: int = 0
    fixed_member_ids: tuple[str, ...] = ()
    attempted_user_ids: set[str] = field(default_factory=set)
    prepared_user_ids: set[str] = field(default_factory=set)
    phase_deadline: str | None = None
    monster_state: CombatRuntimeState | None = None

    @property
    def total_initial_hp(self) -> int:
        if self.kind is EncounterKind.BOSS:
            return sum(segment.initial_hp for segment in self.boss_segments.values())
        return max(0, self.shared_monster_hp)

    def to_dict(self) -> dict[str, Any]:
        return {
            "encounter_id": self.encounter_id,
            "run_id": self.run_id,
            "kind": self.kind.value,
            "phase": self.phase.value,
            "monster_record": dict(self.monster_record),
            "shared_monster_hp": self.shared_monster_hp,
            "participants": {
                user_id: participant.to_dict()
                for user_id, participant in self.participants.items()
            },
            "boss_segments": {
                segment_id: segment.to_dict()
                for segment_id, segment in self.boss_segments.items()
            },
            "action_ids": sorted(self.action_ids),
            "cached_action_results": {
                action_id: dict(result)
                for action_id, result in self.cached_action_results.items()
            },
            "shared_round": self.shared_round,
            "damage_multiplier": self.damage_multiplier,
            "revision": self.revision,
            "fixed_member_ids": list(self.fixed_member_ids),
            "attempted_user_ids": sorted(self.attempted_user_ids),
            "prepared_user_ids": sorted(self.prepared_user_ids),
            "phase_deadline": self.phase_deadline,
            "monster_state": (
                _combat_state_to_dict(self.monster_state)
                if self.monster_state is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, value: Any) -> DungeonEncounter:
        data = _object(value, "dungeon encounter")
        _keys(
            data,
            {
                "encounter_id",
                "run_id",
                "kind",
                "phase",
                "monster_record",
                "shared_monster_hp",
                "participants",
                "boss_segments",
                "action_ids",
                "cached_action_results",
                "shared_round",
                "damage_multiplier",
                "revision",
            },
            {
                "fixed_member_ids",
                "attempted_user_ids",
                "prepared_user_ids",
                "phase_deadline",
                "monster_state",
            },
            "dungeon encounter",
        )
        kind = _encounter_kind(data["kind"])
        phase = _encounter_phase(data["phase"])
        raw_participants = _object(data["participants"], "dungeon encounter.participants")
        participants: dict[str, DungeonBattleParticipant] = {}
        for user_id, raw_participant in raw_participants.items():
            participant = DungeonBattleParticipant.from_dict(raw_participant)
            if participant.user_id != user_id:
                raise ValueError("encounter participant key must match user_id")
            participants[user_id] = participant
        raw_segments = _object(data["boss_segments"], "dungeon encounter.boss_segments")
        boss_segments: dict[str, BossHealthSegment] = {}
        for segment_id, raw_segment in raw_segments.items():
            segment = BossHealthSegment.from_dict(raw_segment)
            if segment.segment_id != segment_id:
                raise ValueError("boss segment key must match segment_id")
            boss_segments[segment_id] = segment
        action_ids = set(_string_list(data["action_ids"], "dungeon encounter.action_ids"))
        cached_results_raw = _object(
            data["cached_action_results"],
            "dungeon encounter.cached_action_results",
        )
        cached_results = {
            action_id: _object(result, f"dungeon encounter.cached_action_results[{action_id!r}]")
            for action_id, result in cached_results_raw.items()
        }
        fixed_member_ids = tuple(
            _string_list(
                data.get("fixed_member_ids", list(participants)),
                "dungeon encounter.fixed_member_ids",
            )
        )
        attempted_user_ids = set(
            _string_list(
                data.get("attempted_user_ids", list(participants)),
                "dungeon encounter.attempted_user_ids",
            )
        )
        prepared_user_ids = set(
            _string_list(
                data.get("prepared_user_ids", []),
                "dungeon encounter.prepared_user_ids",
            )
        )
        monster_state_data = data.get("monster_state")
        encounter = cls(
            encounter_id=_string(data["encounter_id"], "dungeon encounter.encounter_id"),
            run_id=_string_allow_empty(data["run_id"], "dungeon encounter.run_id"),
            kind=kind,
            phase=phase,
            monster_record=_object(data["monster_record"], "dungeon encounter.monster_record"),
            shared_monster_hp=_integer(
                data["shared_monster_hp"],
                "dungeon encounter.shared_monster_hp",
            ),
            participants=participants,
            boss_segments=boss_segments,
            action_ids=action_ids,
            cached_action_results=cached_results,
            shared_round=_integer(data["shared_round"], "dungeon encounter.shared_round"),
            damage_multiplier=_number(
                data["damage_multiplier"],
                "dungeon encounter.damage_multiplier",
            ),
            revision=_integer(data["revision"], "dungeon encounter.revision"),
            fixed_member_ids=fixed_member_ids,
            attempted_user_ids=attempted_user_ids,
            prepared_user_ids=prepared_user_ids,
            phase_deadline=_optional_string(
                data.get("phase_deadline"),
                "dungeon encounter.phase_deadline",
            ),
            monster_state=(
                _combat_state_from_dict(monster_state_data)
                if monster_state_data is not None
                else None
            ),
        )
        encounter._validate()
        return encounter

    def _validate(self) -> None:
        if self.shared_monster_hp < 0 or self.shared_round < 0 or self.revision < 0:
            raise ValueError("encounter counters and HP must not be negative")
        if self.damage_multiplier <= 0:
            raise ValueError("encounter damage multiplier must be positive")
        if len(set(self.fixed_member_ids)) != len(self.fixed_member_ids):
            raise ValueError("encounter fixed member roster must be unique")
        if set(self.participants) - set(self.fixed_member_ids):
            raise ValueError("encounter contains participant outside the fixed roster")
        if not self.attempted_user_ids <= set(self.fixed_member_ids):
            raise ValueError("encounter attempted roster contains an unknown member")
        if not self.prepared_user_ids <= set(self.participants):
            raise ValueError("encounter prepared roster contains a non-participant")
        if set(self.cached_action_results) != self.action_ids:
            raise ValueError("encounter action cache must match action ids")
        if self.kind is EncounterKind.BOSS:
            if len(self.boss_segments) != len(self.fixed_member_ids):
                raise ValueError("boss encounter requires one segment per fixed member")
            owners = {segment.owner_user_id for segment in self.boss_segments.values()}
            if owners != set(self.fixed_member_ids):
                raise ValueError("boss segment owners must match the fixed roster")
        elif self.boss_segments:
            raise ValueError("non-boss encounter must not contain boss segments")


@dataclass(frozen=True)
class EncounterResult:
    completed: bool
    failed: bool
    needs_rescue: bool
    eligible_loot_user_ids: tuple[str, ...]


class MysticBattleService:
    def __init__(
        self,
        config: MysticGameplayConfig,
        now: Callable[[], datetime],
        config_provider: Callable[[], MysticGameplayConfig] | None = None,
    ) -> None:
        self._config_provider = config_provider or (lambda: config)
        self._now = now
        self._locks: dict[str, tuple[threading.RLock, int]] = {}
        self._locks_guard = threading.Lock()

    @property
    def config(self) -> MysticGameplayConfig:
        return self._config_provider()

    def create_ordinary_encounter(
        self,
        encounter_id: str,
        run_id: str,
        monster_record: UserRecord,
        fixed_member_ids: Sequence[str],
    ) -> DungeonEncounter:
        member_ids = _unique_ids(fixed_member_ids, "fixed member")
        monster_hp = max(
            1,
            int(combat_max_hp(monster_record) * self.config.ordinary_monster_hp_multiplier),
        )
        return DungeonEncounter(
            encounter_id=_nonempty(encounter_id, "encounter id"),
            run_id=_nonempty(run_id, "run id"),
            kind=EncounterKind.ORDINARY,
            phase=EncounterPhase.AWAITING_RESPONSE,
            monster_record=monster_record.to_dict(),
            shared_monster_hp=monster_hp,
            participants={},
            fixed_member_ids=member_ids,
            monster_state=CombatRuntimeState.initial(monster_record),
        )

    def join_ordinary_encounter(
        self,
        encounter: DungeonEncounter,
        user_id: str,
        record: UserRecord,
        equipment_snapshot: dict[str, Any],
    ) -> None:
        if encounter.kind not in {EncounterKind.ORDINARY, EncounterKind.RESCUE}:
            raise ValueError("only ordinary or rescue encounters accept response joins")
        if user_id not in encounter.fixed_member_ids:
            raise PermissionError("user is not a fixed encounter member")
        if user_id in encounter.participants:
            raise ValueError("user already joined this encounter batch")
        encounter.participants[user_id] = DungeonBattleParticipant(
            user_id=user_id,
            state=CombatRuntimeState.initial(record),
            equipment_snapshot=dict(equipment_snapshot),
            record_snapshot=record.to_dict(),
        )
        encounter.attempted_user_ids.add(user_id)
        encounter.revision += 1

    def begin_preparation(
        self,
        encounter: DungeonEncounter,
        deadline: datetime,
    ) -> None:
        if not encounter.participants:
            raise ValueError("encounter preparation requires participants")
        encounter.prepared_user_ids.clear()
        encounter.phase_deadline = self._future_deadline(deadline)
        encounter.phase = EncounterPhase.PREPARING
        encounter.revision += 1

    def confirm_loadout(
        self,
        encounter: DungeonEncounter,
        user_id: str,
        record: UserRecord,
        equipment_snapshot: dict[str, Any],
    ) -> bool:
        if encounter.phase is not EncounterPhase.PREPARING:
            raise ValueError("loadout confirmation requires preparation phase")
        participant = encounter.participants.get(user_id)
        if participant is None:
            raise PermissionError("user is not an encounter participant")
        participant.record_snapshot = record.to_dict()
        participant.equipment_snapshot = dict(equipment_snapshot)
        participant.state = CombatRuntimeState.initial(record)
        encounter.prepared_user_ids.add(user_id)
        encounter.revision += 1
        return encounter.prepared_user_ids == set(encounter.participants)
    def begin_next_response_batch(
        self,
        encounter: DungeonEncounter,
        deadline: datetime,
    ) -> tuple[str, ...]:
        if encounter.shared_monster_hp <= 0:
            return ()
        remaining = tuple(
            user_id
            for user_id in encounter.fixed_member_ids
            if user_id not in encounter.attempted_user_ids
        )
        encounter.phase_deadline = self._future_deadline(deadline)
        encounter.phase = EncounterPhase.AWAITING_RESPONSE
        encounter.revision += 1
        return remaining

    def submit_action(
        self,
        encounter: DungeonEncounter,
        user_id: str,
        action_text: str,
        *,
        action_id: str,
        lock_key: str = "",
    ) -> dict[str, Any]:
        action_key = _nonempty(action_id, "action id")
        with self._lock_for(lock_key or encounter.encounter_id):
            cached = encounter.cached_action_results.get(action_key)
            if cached is not None:
                return dict(cached)
            if encounter.phase is not EncounterPhase.ACTIVE:
                raise ValueError("encounter action requires active phase")
            participant = encounter.participants.get(user_id)
            if participant is None:
                raise PermissionError("user is not an encounter participant")
            if participant.defeated or participant.state.hp <= 0:
                raise ValueError("defeated participant cannot act")

            record = self._participant_record(participant)
            outcome = resolve_combat_action(
                record,
                action_text,
                participant.state,
                f"{encounter.encounter_id}:{action_key}:player",
            )
            participant.state = outcome.state
            participant.valid_action_count += 1
            encounter.shared_round += 1
            growth_steps = encounter.shared_round // 10
            encounter.damage_multiplier = 1.0 + (
                growth_steps * self.config.damage_growth_per_ten_rounds
            )
            damage = max(1, int(outcome.damage * encounter.damage_multiplier))
            target_hp, target_cleared = self._apply_player_damage(
                encounter,
                participant,
                damage,
            )
            retaliation_damage = 0
            if not target_cleared:
                retaliation_damage = self._retaliate(
                    encounter,
                    participant,
                    outcome.defense,
                    action_key,
                )
            result = {
                "action_id": action_key,
                "user_id": user_id,
                "damage": damage,
                "retaliation_damage": retaliation_damage,
                "player_hp": participant.state.hp,
                "target_hp": target_hp,
                "target_cleared": target_cleared,
                "encounter_phase": encounter.phase.value,
                "logs": [*outcome.logs],
            }
            encounter.action_ids.add(action_key)
            encounter.cached_action_results[action_key] = dict(result)
            encounter.revision += 1
            return dict(result)

    def resolve_timed_out_action(
        self,
        encounter: DungeonEncounter,
        user_id: str,
        *,
        action_id: str,
        lock_key: str = "",
    ) -> dict[str, Any]:
        return self.submit_action(
            encounter,
            user_id,
            self._legal_action(encounter, user_id),
            action_id=action_id,
            lock_key=lock_key,
        )

    def set_auto_battle(
        self,
        encounter: DungeonEncounter,
        user_id: str,
        record: UserRecord,
    ) -> None:
        participant = encounter.participants.get(user_id)
        if participant is None:
            raise PermissionError("user is not an encounter participant")
        enemy_realm_index = int(encounter.monster_record.get("realm_index", 0))
        if record.realm_index <= enemy_realm_index:
            raise ValueError("auto battle requires a strictly higher player realm")
        participant.auto_battle = True
        participant.record_snapshot = record.to_dict()
        encounter.revision += 1

    async def run_auto_actions(
        self,
        encounter: DungeonEncounter,
        user_id: str,
        *,
        persist: Callable[[DungeonEncounter], Awaitable[None] | None],
        max_actions: int = 100,
        lock_key: str = "",
    ) -> tuple[dict[str, Any], ...]:
        results: list[dict[str, Any]] = []
        for index in range(max(0, int(max_actions))):
            participant = encounter.participants.get(user_id)
            if (
                participant is None
                or not participant.auto_battle
                or participant.defeated
                or encounter.phase is not EncounterPhase.ACTIVE
            ):
                break
            action_id = (
                f"auto:{encounter.encounter_id}:{user_id}:"
                f"{encounter.shared_round + 1}:{index + 1}"
            )
            result = self.submit_action(
                encounter,
                user_id,
                self._legal_action(encounter, user_id),
                action_id=action_id,
                lock_key=lock_key,
            )
            results.append(result)
            persisted = persist(encounter)
            if inspect.isawaitable(persisted):
                await persisted
            await asyncio.sleep(0)
        return tuple(results)

    def finish_encounter(self, encounter: DungeonEncounter) -> EncounterResult:
        eligible = tuple(
            user_id
            for user_id in encounter.fixed_member_ids
            if (
                user_id in encounter.participants
                and encounter.participants[user_id].valid_action_count > 0
            )
        )
        if encounter.kind is EncounterKind.BOSS:
            completed = all(segment.cleared for segment in encounter.boss_segments.values())
        else:
            completed = encounter.shared_monster_hp <= 0
        if completed:
            encounter.phase = EncounterPhase.COMPLETED
            return EncounterResult(
                completed=True,
                failed=False,
                needs_rescue=False,
                eligible_loot_user_ids=eligible,
            )
        all_attempted = set(encounter.fixed_member_ids) <= encounter.attempted_user_ids
        all_current_defeated = bool(encounter.participants) and all(
            participant.defeated or participant.state.hp <= 0
            for participant in encounter.participants.values()
        )
        needs_rescue = (
            encounter.kind is not EncounterKind.BOSS
            and all_attempted
            and all_current_defeated
        )
        if needs_rescue:
            encounter.phase = EncounterPhase.FAILED
        return EncounterResult(
            completed=False,
            failed=encounter.phase is EncounterPhase.FAILED,
            needs_rescue=needs_rescue,
            eligible_loot_user_ids=eligible,
        )

    def create_boss_encounter(
        self,
        base_hp: int,
        member_ids: Sequence[str],
        *,
        encounter_id: str = "boss",
        run_id: str = "",
        monster_record: UserRecord | None = None,
        member_records: Mapping[str, UserRecord] | None = None,
    ) -> DungeonEncounter:
        if not isinstance(base_hp, int) or isinstance(base_hp, bool) or base_hp <= 0:
            raise ValueError("boss base HP must be a positive integer")
        fixed_member_ids = _unique_ids(member_ids, "boss member")
        if not 1 <= len(fixed_member_ids) <= 3:
            raise ValueError("boss encounter requires one to three members")
        boss_record = monster_record or UserRecord(user_id="mystic-boss")
        records = dict(member_records or {})
        participants: dict[str, DungeonBattleParticipant] = {}
        segments: dict[str, BossHealthSegment] = {}
        for user_id in fixed_member_ids:
            player_record = records.get(user_id) or UserRecord(user_id=user_id)
            segment_id = f"segment:{user_id}"
            participants[user_id] = DungeonBattleParticipant(
                user_id=user_id,
                state=CombatRuntimeState.initial(player_record),
                equipment_snapshot={},
                target_segment_id=segment_id,
                record_snapshot=player_record.to_dict(),
            )
            segments[segment_id] = BossHealthSegment(
                segment_id=segment_id,
                owner_user_id=user_id,
                initial_hp=base_hp,
                hp=base_hp,
            )
        return DungeonEncounter(
            encounter_id=_nonempty(encounter_id, "encounter id"),
            run_id=str(run_id or ""),
            kind=EncounterKind.BOSS,
            phase=EncounterPhase.ACTIVE,
            monster_record=boss_record.to_dict(),
            shared_monster_hp=base_hp * len(fixed_member_ids),
            participants=participants,
            boss_segments=segments,
            fixed_member_ids=fixed_member_ids,
            attempted_user_ids=set(fixed_member_ids),
            monster_state=CombatRuntimeState.initial(boss_record),
        )

    def open_boss_continuation(
        self,
        encounter: DungeonEncounter,
        approvals: Mapping[str, bool],
    ) -> bool:
        if encounter.kind is not EncounterKind.BOSS:
            raise ValueError("continuation is only valid for boss encounters")
        if encounter.phase is not EncounterPhase.AWAITING_CONTINUE_VOTE:
            raise ValueError("boss encounter is not awaiting a continuation vote")
        if all(participant.state.hp <= 0 for participant in encounter.participants.values()):
            encounter.phase = EncounterPhase.FAILED
            encounter.revision += 1
            return False
        required = len(encounter.fixed_member_ids) if len(encounter.fixed_member_ids) <= 2 else 2
        approval_count = sum(
            bool(approvals.get(user_id, False))
            for user_id in encounter.fixed_member_ids
        )
        passed = approval_count >= required
        encounter.phase = EncounterPhase.ACTIVE if passed else EncounterPhase.FAILED
        encounter.revision += 1
        return passed

    def join_boss_assist(
        self,
        encounter: DungeonEncounter,
        helper_id: str,
        segment_id: str,
    ) -> None:
        if encounter.kind is not EncounterKind.BOSS:
            raise ValueError("assistance is only valid for boss encounters")
        if encounter.phase is not EncounterPhase.ACTIVE:
            raise ValueError("boss assistance requires active combat")
        helper = encounter.participants.get(helper_id)
        if helper is None:
            raise PermissionError("helper is not a fixed boss participant")
        if helper.state.hp <= 0:
            raise ValueError("zero HP helper cannot assist")
        own_segment = encounter.boss_segments.get(f"segment:{helper_id}")
        if own_segment is None or not own_segment.cleared:
            raise ValueError("helper must clear their own boss segment first")
        target = encounter.boss_segments.get(segment_id)
        if target is None:
            raise ValueError("boss assistance target segment does not exist")
        if target.cleared:
            raise ValueError("boss assistance target segment is already cleared")
        helper.target_segment_id = segment_id
        encounter.revision += 1

    def _apply_player_damage(
        self,
        encounter: DungeonEncounter,
        participant: DungeonBattleParticipant,
        damage: int,
    ) -> tuple[int, bool]:
        if encounter.kind is EncounterKind.BOSS:
            segment_id = participant.target_segment_id
            if segment_id is None:
                raise ValueError("boss participant has no target segment")
            segment = encounter.boss_segments.get(segment_id)
            if segment is None or segment.cleared:
                raise ValueError("boss target segment is not available")
            segment.hp = max(0, segment.hp - damage)
            segment.cleared = segment.hp == 0
            if all(item.cleared for item in encounter.boss_segments.values()):
                encounter.phase = EncounterPhase.COMPLETED
            return segment.hp, segment.cleared
        encounter.shared_monster_hp = max(0, encounter.shared_monster_hp - damage)
        if encounter.shared_monster_hp == 0:
            encounter.phase = EncounterPhase.COMPLETED
        return encounter.shared_monster_hp, encounter.shared_monster_hp == 0

    def _retaliate(
        self,
        encounter: DungeonEncounter,
        participant: DungeonBattleParticipant,
        player_defense: int,
        action_id: str,
    ) -> int:
        monster = UserRecord.from_dict(encounter.monster_record)
        monster_state = encounter.monster_state or CombatRuntimeState.initial(monster)
        outcome = resolve_combat_action(
            monster,
            "普通攻击",
            monster_state,
            f"{encounter.encounter_id}:{action_id}:monster",
        )
        encounter.monster_state = outcome.state
        damage = max(1, outcome.damage - max(0, player_defense))
        participant.state = replace(
            participant.state,
            hp=max(0, participant.state.hp - damage),
        )
        if participant.state.hp == 0:
            participant.defeated = True
        return damage

    def _participant_record(self, participant: DungeonBattleParticipant) -> UserRecord:
        if participant.record_snapshot:
            return UserRecord.from_dict(participant.record_snapshot)
        return UserRecord(user_id=participant.user_id)

    def _legal_action(self, encounter: DungeonEncounter, user_id: str) -> str:
        if user_id not in encounter.participants:
            raise PermissionError("user is not an encounter participant")
        return "普通攻击"

    @contextmanager
    def _lock_for(self, key: str) -> Iterator[None]:
        with self._locks_guard:
            entry = self._locks.get(key)
            if entry is None:
                lock = threading.RLock()
                users = 0
            else:
                lock, users = entry
            self._locks[key] = (lock, users + 1)
        try:
            with lock:
                yield
        finally:
            with self._locks_guard:
                current = self._locks.get(key)
                if current is None or current[0] is not lock:
                    return
                remaining_users = current[1] - 1
                if remaining_users <= 0:
                    self._locks.pop(key, None)
                else:
                    self._locks[key] = (lock, remaining_users)

    def _future_deadline(self, deadline: datetime) -> str:
        if not isinstance(deadline, datetime):
            raise ValueError("encounter deadline must be a datetime")
        now = self._now()
        if not isinstance(now, datetime):
            raise TypeError("now callback must return a datetime")
        try:
            is_future = deadline > now
        except TypeError as exc:
            raise ValueError("encounter deadline timezone does not match service time") from exc
        if not is_future:
            raise ValueError("encounter deadline must be in the future")
        return deadline.isoformat()


def _combat_state_to_dict(state: CombatRuntimeState) -> dict[str, Any]:
    return {
        "hp": state.hp,
        "max_hp": state.max_hp,
        "mana": state.mana,
        "max_mana": state.max_mana,
        "cooldowns": dict(state.cooldowns),
        "turn": state.turn,
        "triggered_abilities": list(state.triggered_abilities),
    }


def _combat_state_from_dict(value: Any) -> CombatRuntimeState:
    data = _object(value, "combat runtime state")
    _exact_keys(
        data,
        {
            "hp",
            "max_hp",
            "mana",
            "max_mana",
            "cooldowns",
            "turn",
            "triggered_abilities",
        },
        "combat runtime state",
    )
    cooldowns_raw = _object(data["cooldowns"], "combat runtime state.cooldowns")
    state = CombatRuntimeState(
        hp=_integer(data["hp"], "combat runtime state.hp"),
        max_hp=_integer(data["max_hp"], "combat runtime state.max_hp"),
        mana=_integer(data["mana"], "combat runtime state.mana"),
        max_mana=_integer(data["max_mana"], "combat runtime state.max_mana"),
        cooldowns={
            name: _integer(turns, f"combat runtime state.cooldowns[{name!r}]")
            for name, turns in cooldowns_raw.items()
        },
        turn=_integer(data["turn"], "combat runtime state.turn"),
        triggered_abilities=tuple(
            _string_list(
                data["triggered_abilities"],
                "combat runtime state.triggered_abilities",
            )
        ),
    )
    if (
        state.max_hp <= 0
        or state.max_mana < 0
        or not 0 <= state.hp <= state.max_hp
        or not 0 <= state.mana <= state.max_mana
        or state.turn < 0
    ):
        raise ValueError("combat runtime state values are outside valid ranges")
    return state


def _encounter_kind(value: Any) -> EncounterKind:
    raw = _string(value, "dungeon encounter.kind")
    try:
        return EncounterKind(raw)
    except ValueError as exc:
        raise ValueError(f"dungeon encounter.kind has unknown value {raw!r}") from exc


def _encounter_phase(value: Any) -> EncounterPhase:
    raw = _string(value, "dungeon encounter.phase")
    try:
        return EncounterPhase(raw)
    except ValueError as exc:
        raise ValueError(f"dungeon encounter.phase has unknown value {raw!r}") from exc


def _unique_ids(values: Sequence[str], label: str) -> tuple[str, ...]:
    result = tuple(_nonempty(value, label) for value in values)
    if not result or len(set(result)) != len(result):
        raise ValueError(f"{label} roster must be non-empty and unique")
    return result


def _nonempty(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must not be empty")
    return text


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be an object with string keys")
    return dict(value)


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _string_allow_empty(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    return value


def _optional_string(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _string(value, label)


def _integer(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{label} must be an integer")
    return value


def _number(value: Any, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number")
    return float(value)


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label} must be a boolean")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    items = [
        _string(item, f"{label}[{index}]")
        for index, item in enumerate(_list(value, label))
    ]
    if len(set(items)) != len(items):
        raise ValueError(f"{label} must contain unique strings")
    return items


def _exact_keys(data: dict[str, Any], expected: set[str], label: str) -> None:
    _keys(data, expected, set(), label)


def _keys(
    data: dict[str, Any],
    required: set[str],
    optional: set[str],
    label: str,
) -> None:
    actual = set(data)
    missing = required - actual
    extra = actual - required - optional
    if missing or extra:
        raise ValueError(
            f"{label} keys mismatch: missing={sorted(missing)!r}, extra={sorted(extra)!r}"
        )
