from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Sequence


SUPPORTED_MAP_SIZES = (24, 28, 32, 36, 40, 44, 48)
DEFAULT_MAP_SIZE_RULES = ((0, 24), (5, 28), (10, 32), (15, 36), (20, 40), (25, 44), (30, 48))


class DungeonRisk(StrEnum):
    NORMAL = "normal"
    HIGH = "high"


class DungeonMode(StrEnum):
    SOLO = "solo"
    TEAM = "team"


class DungeonPhase(StrEnum):
    CREATING = "creating"
    LOBBY = "lobby"
    READY_TO_ROLL = "ready_to_roll"
    MOVING = "moving"
    AWAITING_BRANCH = "awaiting_branch"
    RESOLVING_NODE = "resolving_node"
    AWAITING_ENCOUNTER_RESPONSE = "awaiting_encounter_response"
    PREPARING_BATTLE = "preparing_battle"
    BATTLE_TURN = "battle_turn"
    AWAITING_RESCUE = "awaiting_rescue"
    AWAITING_BOSS_VOTE = "awaiting_boss_vote"
    AWAITING_LEADER_TRANSFER_VOTE = "awaiting_leader_transfer_vote"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class VoteKind(StrEnum):
    BOSS_CONTINUE = "boss_continue"
    LEADER_TRANSFER = "leader_transfer"
    ABANDON = "abandon"


@dataclass
class MysticDungeonMember:
    user_id: str
    nickname: str
    ready: bool = False
    joined_at: str = ""
    boss_segment_id: str | None = None
    boss_segment_cleared: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "ready": self.ready,
            "joined_at": self.joined_at,
            "boss_segment_id": self.boss_segment_id,
            "boss_segment_cleared": self.boss_segment_cleared,
        }

    @classmethod
    def from_dict(cls, value: Any) -> MysticDungeonMember:
        data = _as_object(value, "dungeon member")
        _require_exact_keys(
            data,
            {
                "user_id",
                "nickname",
                "ready",
                "joined_at",
                "boss_segment_id",
                "boss_segment_cleared",
            },
            "dungeon member",
        )
        boss_segment_id = _as_optional_string(data["boss_segment_id"], "dungeon member.boss_segment_id")
        return cls(
            user_id=_as_string(data["user_id"], "dungeon member.user_id"),
            nickname=_as_string_allow_empty(data["nickname"], "dungeon member.nickname"),
            ready=_as_bool(data["ready"], "dungeon member.ready"),
            joined_at=_as_string_allow_empty(data["joined_at"], "dungeon member.joined_at"),
            boss_segment_id=boss_segment_id,
            boss_segment_cleared=_as_bool(
                data["boss_segment_cleared"],
                "dungeon member.boss_segment_cleared",
            ),
        )


@dataclass
class DungeonVote:
    vote_id: str
    kind: VoteKind
    eligible_user_ids: tuple[str, ...]
    approvals: set[str]
    rejections: set[str]
    deadline: str
    nominee_id: str | None = None
    prior_phase: DungeonPhase | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "vote_id": self.vote_id,
            "kind": self.kind.value,
            "eligible_user_ids": list(self.eligible_user_ids),
            "approvals": sorted(self.approvals),
            "rejections": sorted(self.rejections),
            "deadline": self.deadline,
            "nominee_id": self.nominee_id,
            "prior_phase": self.prior_phase.value if self.prior_phase is not None else None,
        }

    @classmethod
    def from_dict(cls, value: Any) -> DungeonVote:
        data = _as_object(value, "dungeon vote")
        required_keys = {
            "vote_id",
            "kind",
            "eligible_user_ids",
            "approvals",
            "rejections",
            "deadline",
        }
        optional_keys = {"nominee_id", "prior_phase"}
        _require_keys(data, required_keys, optional_keys, "dungeon vote")

        raw_kind = _as_string(data["kind"], "dungeon vote.kind")
        try:
            kind = VoteKind(raw_kind)
        except ValueError as exc:
            raise ValueError(f"dungeon vote has unknown vote kind {raw_kind!r}") from exc

        eligible_user_ids = tuple(
            _as_string(item, f"dungeon vote.eligible_user_ids[{index}]")
            for index, item in enumerate(_as_list(data["eligible_user_ids"], "dungeon vote.eligible_user_ids"))
        )
        approvals_list = [
            _as_string(item, f"dungeon vote.approvals[{index}]")
            for index, item in enumerate(_as_list(data["approvals"], "dungeon vote.approvals"))
        ]
        rejections_list = [
            _as_string(item, f"dungeon vote.rejections[{index}]")
            for index, item in enumerate(_as_list(data["rejections"], "dungeon vote.rejections"))
        ]
        if not eligible_user_ids or len(set(eligible_user_ids)) != len(eligible_user_ids):
            raise ValueError("dungeon vote eligible roster must be non-empty and unique")
        if len(set(approvals_list)) != len(approvals_list) or len(set(rejections_list)) != len(rejections_list):
            raise ValueError("dungeon vote ballots must not contain duplicates")
        approvals = set(approvals_list)
        rejections = set(rejections_list)
        eligible = set(eligible_user_ids)
        if approvals & rejections:
            raise ValueError("dungeon vote approvals and rejections must be disjoint")
        if not approvals | rejections <= eligible:
            raise ValueError("dungeon vote contains an ineligible ballot")

        nominee_id = _as_optional_string(data.get("nominee_id"), "dungeon vote.nominee_id")
        raw_prior_phase = data.get("prior_phase")
        prior_phase: DungeonPhase | None = None
        if raw_prior_phase is not None:
            prior_phase_name = _as_string(raw_prior_phase, "dungeon vote.prior_phase")
            try:
                prior_phase = DungeonPhase(prior_phase_name)
            except ValueError as exc:
                raise ValueError(f"dungeon vote has unknown prior phase {prior_phase_name!r}") from exc
        if kind is VoteKind.LEADER_TRANSFER and (nominee_id is None or prior_phase is None):
            raise ValueError("leader transfer vote requires nominee and prior phase")
        return cls(
            vote_id=_as_string(data["vote_id"], "dungeon vote.vote_id"),
            kind=kind,
            eligible_user_ids=eligible_user_ids,
            approvals=approvals,
            rejections=rejections,
            deadline=_as_datetime_string(data["deadline"], "dungeon vote.deadline"),
            nominee_id=nominee_id,
            prior_phase=prior_phase,
        )


@dataclass(frozen=True)
class EntryCharge:
    payer_id: str
    token_name: str
    amount: int = 1


@dataclass(frozen=True)
class MovementResult:
    traversed_edge_ids: tuple[str, ...]
    landed_node_id: str | None
    pending_branch_choices: tuple[str, ...]
    node_resolution_required: bool


@dataclass(frozen=True)
class VoteResult:
    passed: bool
    failed: bool
    pending: bool


@dataclass
class DungeonRewardLedger:
    rewards_by_user: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    settled_node_keys: set[str] = field(default_factory=set)

    def add_personal(
        self,
        user_id: str,
        node_id: str,
        reward: dict[str, Any],
    ) -> bool:
        key = f"{node_id}:{user_id}"
        if key in self.settled_node_keys:
            return False
        self.settled_node_keys.add(key)
        self.rewards_by_user.setdefault(user_id, []).append(dict(reward))
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "rewards_by_user": {
                user_id: [dict(reward) for reward in rewards]
                for user_id, rewards in self.rewards_by_user.items()
            },
            "settled_node_keys": sorted(self.settled_node_keys),
        }

    @classmethod
    def from_dict(cls, value: Any) -> DungeonRewardLedger:
        data = _as_object(value, "dungeon reward ledger")
        _require_exact_keys(
            data,
            {"rewards_by_user", "settled_node_keys"},
            "dungeon reward ledger",
        )
        raw_rewards = _as_object(data["rewards_by_user"], "dungeon reward ledger.rewards_by_user")
        rewards_by_user: dict[str, list[dict[str, Any]]] = {}
        for user_id, raw_user_rewards in raw_rewards.items():
            rewards_by_user[user_id] = [
                _as_object(reward, f"dungeon reward ledger.rewards_by_user[{user_id!r}][{index}]")
                for index, reward in enumerate(
                    _as_list(
                        raw_user_rewards,
                        f"dungeon reward ledger.rewards_by_user[{user_id!r}]",
                    )
                )
            ]
        settled_keys = _as_string_list(
            data["settled_node_keys"],
            "dungeon reward ledger.settled_node_keys",
        )
        if len(set(settled_keys)) != len(settled_keys):
            raise ValueError("dungeon reward ledger settled keys must be unique")
        return cls(
            rewards_by_user=rewards_by_user,
            settled_node_keys=set(settled_keys),
        )


@dataclass(frozen=True)
class NodeRewardResult:
    rewards_by_user: dict[str, list[dict[str, Any]]]


@dataclass
class MysticDungeonRun:
    run_id: str
    source_group_id: str
    mode: DungeonMode
    risk: DungeonRisk
    leader_id: str
    members: dict[str, MysticDungeonMember]
    phase: DungeonPhase = DungeonPhase.LOBBY
    template_id: str = ""
    theme_id: str = ""
    map_size: int = 24
    map_seed: int = 0
    content_seed: int = 0
    current_node_id: str = ""
    boss_node_id: str = ""
    visited_node_ids: list[str] = field(default_factory=list)
    visited_edge_ids: list[str] = field(default_factory=list)
    cleared_node_ids: list[str] = field(default_factory=list)
    remaining_steps: int = 0
    pending_branch_choices: list[str] = field(default_factory=list)
    last_leader_action_at: str = ""
    active_encounter_id: str | None = None
    temporary_rewards_by_user: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    node_contents: dict[str, DungeonNodeContent] = field(default_factory=dict)
    settled_reward_node_keys: list[str] = field(default_factory=list)
    revision: int = 0
    active_vote: DungeonVote | None = None

    @property
    def member_ids(self) -> tuple[str, ...]:
        return tuple(self.members)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source_group_id": self.source_group_id,
            "mode": self.mode.value,
            "risk": self.risk.value,
            "leader_id": self.leader_id,
            "members": {user_id: member.to_dict() for user_id, member in self.members.items()},
            "phase": self.phase.value,
            "template_id": self.template_id,
            "theme_id": self.theme_id,
            "map_size": self.map_size,
            "map_seed": self.map_seed,
            "content_seed": self.content_seed,
            "current_node_id": self.current_node_id,
            "boss_node_id": self.boss_node_id,
            "visited_node_ids": list(self.visited_node_ids),
            "visited_edge_ids": list(self.visited_edge_ids),
            "cleared_node_ids": list(self.cleared_node_ids),
            "remaining_steps": self.remaining_steps,
            "pending_branch_choices": list(self.pending_branch_choices),
            "last_leader_action_at": self.last_leader_action_at,
            "active_encounter_id": self.active_encounter_id,
            "temporary_rewards_by_user": {
                user_id: [dict(reward) for reward in rewards]
                for user_id, rewards in self.temporary_rewards_by_user.items()
            },
            "node_contents": {
                node_id: content.to_dict()
                for node_id, content in self.node_contents.items()
            },
            "settled_reward_node_keys": sorted(set(self.settled_reward_node_keys)),
            "revision": self.revision,
            "active_vote": self.active_vote.to_dict() if self.active_vote is not None else None,
        }

    @classmethod
    def from_dict(cls, value: Any) -> MysticDungeonRun:
        data = _as_object(value, "dungeon run")
        required_keys = {
            "run_id",
            "source_group_id",
            "mode",
            "risk",
            "leader_id",
            "members",
            "phase",
            "template_id",
            "theme_id",
            "map_size",
            "map_seed",
            "content_seed",
            "current_node_id",
            "boss_node_id",
            "visited_node_ids",
            "visited_edge_ids",
            "cleared_node_ids",
            "remaining_steps",
            "pending_branch_choices",
            "last_leader_action_at",
            "active_encounter_id",
            "temporary_rewards_by_user",
            "revision",
        }
        _require_keys(
            data,
            required_keys,
            {"active_vote", "node_contents", "settled_reward_node_keys"},
            "dungeon run",
        )

        raw_mode = _as_string(data["mode"], "dungeon run.mode")
        try:
            mode = DungeonMode(raw_mode)
        except ValueError as exc:
            raise ValueError(f"dungeon run has unknown mode {raw_mode!r}") from exc
        risk = _parse_risk(data["risk"], "dungeon run.risk")
        raw_phase = _as_string(data["phase"], "dungeon run.phase")
        try:
            phase = DungeonPhase(raw_phase)
        except ValueError as exc:
            raise ValueError(f"dungeon run has unknown phase {raw_phase!r}") from exc

        raw_members = _as_object(data["members"], "dungeon run.members")
        members: dict[str, MysticDungeonMember] = {}
        for user_id, raw_member in raw_members.items():
            member = MysticDungeonMember.from_dict(raw_member)
            if user_id != member.user_id:
                raise ValueError("dungeon run member key must match member user id")
            members[user_id] = member

        raw_rewards = _as_object(
            data["temporary_rewards_by_user"],
            "dungeon run.temporary_rewards_by_user",
        )
        temporary_rewards_by_user: dict[str, list[dict[str, Any]]] = {}
        for user_id, raw_user_rewards in raw_rewards.items():
            reward_items = _as_list(
                raw_user_rewards,
                f"dungeon run.temporary_rewards_by_user[{user_id!r}]",
            )
            temporary_rewards_by_user[user_id] = [
                _as_object(
                    reward,
                    f"dungeon run.temporary_rewards_by_user[{user_id!r}][{index}]",
                )
                for index, reward in enumerate(reward_items)
            ]

        active_vote_data = data.get("active_vote")
        active_vote = None if active_vote_data is None else DungeonVote.from_dict(active_vote_data)
        raw_node_contents = _as_object(data.get("node_contents", {}), "dungeon run.node_contents")
        node_contents: dict[str, DungeonNodeContent] = {}
        for node_id, raw_content in raw_node_contents.items():
            content = DungeonNodeContent.from_dict(raw_content)
            if node_id != content.node_id:
                raise ValueError("dungeon run node content key must match node_id")
            node_contents[node_id] = content
        settled_reward_node_keys = _as_string_list(
            data.get("settled_reward_node_keys", []),
            "dungeon run.settled_reward_node_keys",
        )
        run = cls(
            run_id=_as_string(data["run_id"], "dungeon run.run_id"),
            source_group_id=_as_string(data["source_group_id"], "dungeon run.source_group_id"),
            mode=mode,
            risk=risk,
            leader_id=_as_string(data["leader_id"], "dungeon run.leader_id"),
            members=members,
            phase=phase,
            template_id=_as_string_allow_empty(data["template_id"], "dungeon run.template_id"),
            theme_id=_as_string_allow_empty(data["theme_id"], "dungeon run.theme_id"),
            map_size=_as_int(data["map_size"], "dungeon run.map_size"),
            map_seed=_as_int(data["map_seed"], "dungeon run.map_seed"),
            content_seed=_as_int(data["content_seed"], "dungeon run.content_seed"),
            current_node_id=_as_string_allow_empty(
                data["current_node_id"],
                "dungeon run.current_node_id",
            ),
            boss_node_id=_as_string_allow_empty(data["boss_node_id"], "dungeon run.boss_node_id"),
            visited_node_ids=_as_string_list(data["visited_node_ids"], "dungeon run.visited_node_ids"),
            visited_edge_ids=_as_string_list(data["visited_edge_ids"], "dungeon run.visited_edge_ids"),
            cleared_node_ids=_as_string_list(data["cleared_node_ids"], "dungeon run.cleared_node_ids"),
            remaining_steps=_as_int(data["remaining_steps"], "dungeon run.remaining_steps"),
            pending_branch_choices=_as_string_list(
                data["pending_branch_choices"],
                "dungeon run.pending_branch_choices",
            ),
            last_leader_action_at=_as_string_allow_empty(
                data["last_leader_action_at"],
                "dungeon run.last_leader_action_at",
            ),
            active_encounter_id=_as_optional_string(
                data["active_encounter_id"],
                "dungeon run.active_encounter_id",
            ),
            temporary_rewards_by_user=temporary_rewards_by_user,
            node_contents=node_contents,
            settled_reward_node_keys=settled_reward_node_keys,
            revision=_as_int(data["revision"], "dungeon run.revision"),
            active_vote=active_vote,
        )
        run._validate_persistent_state()
        return run

    def _validate_persistent_state(self) -> None:
        member_count = len(self.members)
        if self.mode is DungeonMode.SOLO and member_count != 1:
            raise ValueError("solo roster must contain exactly one member")
        prestart_phases = {DungeonPhase.CREATING, DungeonPhase.LOBBY}
        if self.mode is DungeonMode.TEAM:
            minimum_members = 1 if self.phase in prestart_phases else 2
            if not minimum_members <= member_count <= 3:
                raise ValueError("team roster has an invalid size for the current phase")
        if self.leader_id not in self.members:
            raise ValueError("dungeon run leader must be in the fixed roster")
        if self.map_size not in SUPPORTED_MAP_SIZES:
            raise ValueError(f"unsupported map size: {self.map_size}")
        if self.remaining_steps < 0 or self.revision < 0:
            raise ValueError("dungeon run counters must not be negative")
        for values, label in (
            (self.visited_node_ids, "visited nodes"),
            (self.visited_edge_ids, "visited edges"),
            (self.cleared_node_ids, "cleared nodes"),
            (self.pending_branch_choices, "pending branch choices"),
            (self.settled_reward_node_keys, "settled reward node keys"),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"dungeon run {label} must be unique")
        if not set(self.cleared_node_ids) <= set(self.visited_node_ids):
            raise ValueError("dungeon run cleared nodes must have been visited")
        if set(self.temporary_rewards_by_user) - set(self.members):
            raise ValueError("dungeon run rewards contain an unknown member")
        if self.node_contents and len(self.node_contents) != self.map_size:
            raise ValueError("dungeon run node contents do not match map size")

        if self.phase not in prestart_phases:
            if not self.template_id or not self.theme_id or not self.current_node_id or not self.boss_node_id:
                raise ValueError("started dungeon run is missing map state")
            if self.current_node_id not in self.visited_node_ids:
                raise ValueError("dungeon run current node must have been visited")

        branch_phase = self.phase is DungeonPhase.AWAITING_BRANCH
        if (
            self.active_vote is not None
            and self.active_vote.kind is VoteKind.LEADER_TRANSFER
            and self.active_vote.prior_phase is DungeonPhase.AWAITING_BRANCH
        ):
            branch_phase = True
        if branch_phase:
            if self.remaining_steps <= 0 or not self.pending_branch_choices:
                raise ValueError("awaiting branch state requires steps and choices")
        elif self.remaining_steps or self.pending_branch_choices:
            raise ValueError("dungeon run has branch state outside an awaiting branch phase")

        if self.phase is DungeonPhase.AWAITING_LEADER_TRANSFER_VOTE:
            if self.active_vote is None or self.active_vote.kind is not VoteKind.LEADER_TRANSFER:
                raise ValueError("leader transfer phase requires an active leader transfer vote")
        if self.phase is DungeonPhase.AWAITING_BOSS_VOTE:
            if self.active_vote is None or self.active_vote.kind is not VoteKind.BOSS_CONTINUE:
                raise ValueError("boss vote phase requires an active boss continuation vote")
        if self.active_vote is not None:
            if self.mode is not DungeonMode.TEAM or not 2 <= member_count <= 3:
                raise ValueError("active votes require a started team roster")
            if not set(self.active_vote.eligible_user_ids) <= set(self.members):
                raise ValueError("active vote contains an unknown member")
            forbidden_vote_phases = {
                DungeonPhase.CREATING,
                DungeonPhase.LOBBY,
                DungeonPhase.COMPLETED,
                DungeonPhase.FAILED,
                DungeonPhase.ABANDONED,
            }
            if self.active_vote.kind is VoteKind.LEADER_TRANSFER:
                if self.phase is not DungeonPhase.AWAITING_LEADER_TRANSFER_VOTE:
                    raise ValueError("active leader transfer vote has an invalid phase")
                if self.active_vote.prior_phase in forbidden_vote_phases | {
                    DungeonPhase.AWAITING_LEADER_TRANSFER_VOTE,
                    DungeonPhase.AWAITING_BOSS_VOTE,
                }:
                    raise ValueError("leader transfer vote has an invalid prior phase")
                expected_eligible_user_ids = tuple(
                    user_id for user_id in self.member_ids if user_id != self.leader_id
                )
                if self.active_vote.eligible_user_ids != expected_eligible_user_ids:
                    raise ValueError("leader transfer vote has an invalid eligible roster")
                if self.active_vote.nominee_id not in self.members:
                    raise ValueError("leader transfer nominee must be in the fixed roster")
                if self.active_vote.nominee_id == self.leader_id:
                    raise ValueError("leader transfer nominee must not be the current leader")
            elif self.active_vote.kind is VoteKind.ABANDON:
                if self.active_vote.eligible_user_ids != self.member_ids:
                    raise ValueError("abandon vote has an invalid eligible roster")
                if self.phase in forbidden_vote_phases:
                    raise ValueError("abandon vote has an invalid phase")
                if self.active_vote.prior_phase is not self.phase:
                    raise ValueError("abandon vote must retain the previous active phase")
            elif self.active_vote.kind is VoteKind.BOSS_CONTINUE:
                if self.phase is not DungeonPhase.AWAITING_BOSS_VOTE:
                    raise ValueError("boss continuation vote has an invalid phase")


class NodeKind(StrEnum):
    START = "start"
    RANDOM = "random"
    COMBAT = "combat"
    RESOURCE = "resource"
    TRAP = "trap"
    REST = "rest"
    BOSS = "boss"


@dataclass(frozen=True)
class MapSizeRule:
    minimum_boss_realm_index: int
    node_count: int


@dataclass(frozen=True)
class MysticGameplayConfig:
    map_size_rules: tuple[MapSizeRule, ...]
    min_map_size: int
    max_map_size: int
    normal_node_weights: dict[str, float]
    high_risk_node_weights: dict[str, float]
    normal_branch_density: float
    high_risk_branch_density: float
    high_risk_loop_count: int
    consecutive_combat_limit: int
    ordinary_monster_hp_multiplier: float
    boss_hp_multiplier: float
    reward_multiplier: float
    damage_growth_per_ten_rounds: float
    encounter_response_seconds: int
    battle_prepare_seconds: int
    player_action_seconds: int
    boss_vote_seconds: int
    leader_inactive_seconds: int
    leader_transfer_vote_seconds: int
    rescue_wait_seconds: int
    signin_normal_token_count: int
    signin_high_risk_token_count: int
    daily_task_normal_token_count: int
    daily_task_high_risk_token_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "normal_node_weights", dict(self.normal_node_weights))
        object.__setattr__(self, "high_risk_node_weights", dict(self.high_risk_node_weights))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "map_size_rules": [
                {
                    "minimum_boss_realm_index": rule.minimum_boss_realm_index,
                    "node_count": rule.node_count,
                }
                for rule in self.map_size_rules
            ],
            "min_map_size": self.min_map_size,
            "max_map_size": self.max_map_size,
            "normal_node_weights": dict(self.normal_node_weights),
            "high_risk_node_weights": dict(self.high_risk_node_weights),
            "normal_branch_density": self.normal_branch_density,
            "high_risk_branch_density": self.high_risk_branch_density,
            "high_risk_loop_count": self.high_risk_loop_count,
            "consecutive_combat_limit": self.consecutive_combat_limit,
            "ordinary_monster_hp_multiplier": self.ordinary_monster_hp_multiplier,
            "boss_hp_multiplier": self.boss_hp_multiplier,
            "reward_multiplier": self.reward_multiplier,
            "damage_growth_per_ten_rounds": self.damage_growth_per_ten_rounds,
            "encounter_response_seconds": self.encounter_response_seconds,
            "battle_prepare_seconds": self.battle_prepare_seconds,
            "player_action_seconds": self.player_action_seconds,
            "boss_vote_seconds": self.boss_vote_seconds,
            "leader_inactive_seconds": self.leader_inactive_seconds,
            "leader_transfer_vote_seconds": self.leader_transfer_vote_seconds,
            "rescue_wait_seconds": self.rescue_wait_seconds,
            "signin_normal_token_count": self.signin_normal_token_count,
            "signin_high_risk_token_count": self.signin_high_risk_token_count,
            "daily_task_normal_token_count": self.daily_task_normal_token_count,
            "daily_task_high_risk_token_count": self.daily_task_high_risk_token_count,
        }

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> MysticGameplayConfig:
        if not isinstance(value, dict):
            raise ValueError("mystic config must be an object")
        defaults = default_mystic_gameplay_config().to_mapping()
        data = {key: value.get(key, default) for key, default in defaults.items()}
        raw_rules = data["map_size_rules"]
        if not isinstance(raw_rules, list) or not raw_rules:
            raise ValueError("map_size_rules must be a non-empty list")
        rules: list[MapSizeRule] = []
        previous_realm = -1
        previous_count = -1
        for raw_rule in raw_rules:
            if not isinstance(raw_rule, dict):
                raise ValueError("map_size_rules entries must be objects")
            minimum = int(raw_rule.get("minimum_boss_realm_index", -1))
            node_count = int(raw_rule.get("node_count", 0))
            if node_count not in SUPPORTED_MAP_SIZES:
                raise ValueError(f"unsupported node_count: {node_count}")
            if minimum <= previous_realm:
                raise ValueError("map size realm thresholds must be strictly increasing")
            if node_count < previous_count:
                raise ValueError("map size node counts must be nondecreasing")
            previous_realm = minimum
            previous_count = node_count
            rules.append(MapSizeRule(minimum, node_count))

        def weight_map(name: str) -> dict[str, float]:
            raw = data[name]
            if not isinstance(raw, dict) or not raw:
                raise ValueError(f"{name} weights must be an object")
            weights = {str(key): float(item) for key, item in raw.items()}
            if any(item < 0 for item in weights.values()):
                raise ValueError(f"{name} weights must be nonnegative")
            if abs(sum(weights.values()) - 1.0) > 1e-6:
                raise ValueError(f"{name} weights must sum to 1")
            return weights

        def bounded_int(name: str, minimum: int, maximum: int) -> int:
            result = int(data[name])
            if not minimum <= result <= maximum:
                raise ValueError(f"{name} must be between {minimum} and {maximum}")
            return result

        def positive_float(name: str) -> float:
            result = float(data[name])
            if result <= 0:
                raise ValueError(f"{name} must be positive")
            return result

        min_map_size = int(data["min_map_size"])
        max_map_size = int(data["max_map_size"])
        if min_map_size not in SUPPORTED_MAP_SIZES or max_map_size not in SUPPORTED_MAP_SIZES:
            raise ValueError("min_map_size and max_map_size must be supported sizes")
        if min_map_size > max_map_size:
            raise ValueError("min_map_size must not exceed max_map_size")
        normal_branch_density = float(data["normal_branch_density"])
        high_risk_branch_density = float(data["high_risk_branch_density"])
        if not 0 <= normal_branch_density <= 1 or not 0 <= high_risk_branch_density <= 1:
            raise ValueError("branch density must be between 0 and 1")
        return cls(
            map_size_rules=tuple(rules),
            min_map_size=min_map_size,
            max_map_size=max_map_size,
            normal_node_weights=weight_map("normal_node_weights"),
            high_risk_node_weights=weight_map("high_risk_node_weights"),
            normal_branch_density=normal_branch_density,
            high_risk_branch_density=high_risk_branch_density,
            high_risk_loop_count=bounded_int("high_risk_loop_count", 0, 100),
            consecutive_combat_limit=bounded_int("consecutive_combat_limit", 1, 100),
            ordinary_monster_hp_multiplier=positive_float("ordinary_monster_hp_multiplier"),
            boss_hp_multiplier=positive_float("boss_hp_multiplier"),
            reward_multiplier=positive_float("reward_multiplier"),
            damage_growth_per_ten_rounds=positive_float("damage_growth_per_ten_rounds"),
            encounter_response_seconds=bounded_int("encounter_response_seconds", 10, 3600),
            battle_prepare_seconds=bounded_int("battle_prepare_seconds", 10, 3600),
            player_action_seconds=bounded_int("player_action_seconds", 10, 3600),
            boss_vote_seconds=bounded_int("boss_vote_seconds", 10, 3600),
            leader_inactive_seconds=bounded_int("leader_inactive_seconds", 10, 3600),
            leader_transfer_vote_seconds=bounded_int("leader_transfer_vote_seconds", 10, 3600),
            rescue_wait_seconds=bounded_int("rescue_wait_seconds", 10, 3600),
            signin_normal_token_count=bounded_int("signin_normal_token_count", 0, 10),
            signin_high_risk_token_count=bounded_int("signin_high_risk_token_count", 0, 10),
            daily_task_normal_token_count=bounded_int("daily_task_normal_token_count", 0, 10),
            daily_task_high_risk_token_count=bounded_int("daily_task_high_risk_token_count", 0, 10),
        )


@dataclass(frozen=True)
class DungeonNodeContent:
    node_id: str
    kind: NodeKind
    event_id: str
    visible_label: str
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", dict(self.payload))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "kind": self.kind.value,
            "event_id": self.event_id,
            "visible_label": self.visible_label,
            "payload": dict(self.payload),
        }

    @classmethod
    def from_dict(cls, value: Any) -> DungeonNodeContent:
        data = _as_object(value, "dungeon node content")
        _require_exact_keys(
            data,
            {"node_id", "kind", "event_id", "visible_label", "payload"},
            "dungeon node content",
        )
        raw_kind = _as_string(data["kind"], "dungeon node content.kind")
        try:
            kind = NodeKind(raw_kind)
        except ValueError as exc:
            raise ValueError(f"dungeon node content has unknown kind {raw_kind!r}") from exc
        return cls(
            node_id=_as_string(data["node_id"], "dungeon node content.node_id"),
            kind=kind,
            event_id=_as_string(data["event_id"], "dungeon node content.event_id"),
            visible_label=_as_string(data["visible_label"], "dungeon node content.visible_label"),
            payload=_as_object(data["payload"], "dungeon node content.payload"),
        )


def default_mystic_gameplay_config() -> MysticGameplayConfig:
    return MysticGameplayConfig(
        map_size_rules=tuple(
            MapSizeRule(minimum_boss_realm_index=minimum, node_count=node_count)
            for minimum, node_count in DEFAULT_MAP_SIZE_RULES
        ),
        min_map_size=24,
        max_map_size=48,
        normal_node_weights={
            NodeKind.RANDOM.value: 0.28,
            NodeKind.COMBAT.value: 0.26,
            NodeKind.RESOURCE.value: 0.22,
            NodeKind.TRAP.value: 0.10,
            NodeKind.REST.value: 0.14,
        },
        high_risk_node_weights={
            NodeKind.RANDOM.value: 0.20,
            NodeKind.COMBAT.value: 0.36,
            NodeKind.RESOURCE.value: 0.15,
            NodeKind.TRAP.value: 0.18,
            NodeKind.REST.value: 0.11,
        },
        normal_branch_density=0.18,
        high_risk_branch_density=0.30,
        high_risk_loop_count=4,
        consecutive_combat_limit=2,
        ordinary_monster_hp_multiplier=1.0,
        boss_hp_multiplier=1.0,
        reward_multiplier=1.0,
        damage_growth_per_ten_rounds=0.10,
        encounter_response_seconds=60,
        battle_prepare_seconds=60,
        player_action_seconds=60,
        boss_vote_seconds=60,
        leader_inactive_seconds=600,
        leader_transfer_vote_seconds=60,
        rescue_wait_seconds=1800,
        signin_normal_token_count=0,
        signin_high_risk_token_count=0,
        daily_task_normal_token_count=0,
        daily_task_high_risk_token_count=0,
    )


ACTIVE_MYSTIC_GAMEPLAY_CONFIG = default_mystic_gameplay_config()
ACTIVE_MYSTIC_ENABLED_THEME_IDS: dict[
    DungeonRisk,
    tuple[str, ...] | None,
] = {
    DungeonRisk.NORMAL: None,
    DungeonRisk.HIGH: None,
}


def active_mystic_gameplay_config() -> MysticGameplayConfig:
    return ACTIVE_MYSTIC_GAMEPLAY_CONFIG


def active_mystic_theme_ids(risk: DungeonRisk) -> tuple[str, ...] | None:
    parsed_risk = DungeonRisk(risk)
    return ACTIVE_MYSTIC_ENABLED_THEME_IDS[parsed_risk]


def apply_admin_config(config: dict[str, Any]) -> MysticGameplayConfig:
    global ACTIVE_MYSTIC_GAMEPLAY_CONFIG, ACTIVE_MYSTIC_ENABLED_THEME_IDS
    mystic = config.get("mystic", config)
    if not isinstance(mystic, dict):
        raise ValueError("mystic config must be an object")

    def optional_theme_ids(key: str) -> tuple[str, ...] | None:
        value = mystic.get(key)
        if value is None:
            return None
        if not isinstance(value, list):
            raise ValueError(f"{key} must be a list")
        return tuple(str(item) for item in value)

    ACTIVE_MYSTIC_GAMEPLAY_CONFIG = MysticGameplayConfig.from_mapping(mystic)
    ACTIVE_MYSTIC_ENABLED_THEME_IDS = {
        DungeonRisk.NORMAL: optional_theme_ids("enabled_types"),
        DungeonRisk.HIGH: optional_theme_ids("enabled_high_risk_types"),
    }
    return ACTIVE_MYSTIC_GAMEPLAY_CONFIG


@dataclass(frozen=True)
class DungeonNodeSlot:
    node_id: str
    x: float
    y: float
    depth: int
    activation_size: int
    allowed_kinds: tuple[NodeKind, ...]
    is_safe: bool = False
    is_terminal_candidate: bool = False


@dataclass(frozen=True)
class DungeonEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    activation_size: int
    is_loop: bool = False


@dataclass(frozen=True)
class ActiveDungeonGraph:
    nodes: tuple[DungeonNodeSlot, ...]
    edges: tuple[DungeonEdge, ...]
    start_node_id: str
    boss_node_id: str

    @property
    def loop_edges(self) -> tuple[DungeonEdge, ...]:
        return tuple(edge for edge in self.edges if edge.is_loop)

    @property
    def branch_count(self) -> int:
        outgoing: dict[str, set[str]] = {}
        for edge in self.edges:
            outgoing.setdefault(edge.source_node_id, set()).add(edge.target_node_id)
        return sum(len(targets) > 1 for targets in outgoing.values())

    def has_path(
        self,
        source_node_id: str,
        target_node_id: str,
        *,
        include_loop_edges: bool = True,
    ) -> bool:
        return target_node_id in self.reachable_node_ids(
            source_node_id,
            include_loop_edges=include_loop_edges,
        )

    def reachable_node_ids(
        self,
        source_node_id: str,
        *,
        include_loop_edges: bool = True,
    ) -> frozenset[str]:
        node_ids = {node.node_id for node in self.nodes}
        if source_node_id not in node_ids:
            return frozenset()

        outgoing: dict[str, list[str]] = {}
        for edge in self.edges:
            if edge.is_loop and not include_loop_edges:
                continue
            outgoing.setdefault(edge.source_node_id, []).append(edge.target_node_id)

        pending = [source_node_id]
        visited = {source_node_id}
        while pending:
            current = pending.pop()
            for next_node_id in outgoing.get(current, ()):
                if next_node_id not in visited:
                    visited.add(next_node_id)
                    pending.append(next_node_id)
        return frozenset(visited)

    def node_ids_reaching(
        self,
        target_node_id: str,
        *,
        include_loop_edges: bool = True,
    ) -> frozenset[str]:
        node_ids = {node.node_id for node in self.nodes}
        if target_node_id not in node_ids:
            return frozenset()

        incoming: dict[str, list[str]] = {}
        for edge in self.edges:
            if edge.is_loop and not include_loop_edges:
                continue
            incoming.setdefault(edge.target_node_id, []).append(edge.source_node_id)

        pending = [target_node_id]
        visited = {target_node_id}
        while pending:
            current = pending.pop()
            for previous_node_id in incoming.get(current, ()):
                if previous_node_id not in visited:
                    visited.add(previous_node_id)
                    pending.append(previous_node_id)
        return frozenset(visited)


@dataclass(frozen=True)
class DungeonMapTemplate:
    template_id: str
    risk: DungeonRisk
    nodes: tuple[DungeonNodeSlot, ...]
    edges: tuple[DungeonEdge, ...]

    def active_graph(self, size: int) -> ActiveDungeonGraph:
        if size not in SUPPORTED_MAP_SIZES:
            raise ValueError(f"unsupported map size: {size}")

        active_nodes = tuple(
            sorted(
                (node for node in self.nodes if node.activation_size <= size),
                key=lambda node: (node.depth, node.node_id),
            )
        )
        if len(active_nodes) != size:
            raise ValueError(
                f"template {self.template_id!r} activates {len(active_nodes)} nodes at size {size}, expected {size}"
            )

        node_ids = {node.node_id for node in active_nodes}
        active_edges = tuple(edge for edge in self.edges if edge.activation_size <= size)
        for edge in active_edges:
            if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
                raise ValueError(
                    f"template {self.template_id!r} edge {edge.edge_id!r} activates before one of its nodes"
                )

        start_nodes = [node for node in active_nodes if NodeKind.START in node.allowed_kinds]
        if len(start_nodes) != 1:
            raise ValueError(f"template {self.template_id!r} must have exactly one active start node")

        terminal_nodes = [node for node in active_nodes if node.is_terminal_candidate]
        if not terminal_nodes:
            raise ValueError(f"template {self.template_id!r} has no terminal candidate at size {size}")
        boss_node = max(
            terminal_nodes,
            key=lambda node: (node.activation_size, node.depth, node.node_id),
        )
        if boss_node.activation_size != size:
            raise ValueError(
                f"template {self.template_id!r} has no terminal candidate activated at size {size}"
            )

        graph = ActiveDungeonGraph(
            nodes=active_nodes,
            edges=active_edges,
            start_node_id=start_nodes[0].node_id,
            boss_node_id=boss_node.node_id,
        )
        if not graph.has_path(graph.start_node_id, graph.boss_node_id):
            raise ValueError(f"template {self.template_id!r} has no path from start to boss at size {size}")
        unreachable = node_ids - graph.reachable_node_ids(graph.start_node_id)
        if unreachable:
            raise ValueError(
                f"template {self.template_id!r} has nodes unreachable from start at size {size}: {sorted(unreachable)!r}"
            )
        dead_ends = node_ids - graph.node_ids_reaching(graph.boss_node_id)
        if dead_ends:
            raise ValueError(
                f"template {self.template_id!r} has nodes that cannot reach boss at size {size}: {sorted(dead_ends)!r}"
            )
        return graph

    def validate_loop_safety(self) -> None:
        for size in SUPPORTED_MAP_SIZES:
            graph = self.active_graph(size)
            if not graph.has_path(
                graph.start_node_id,
                graph.boss_node_id,
                include_loop_edges=False,
            ):
                raise ValueError(
                    f"template {self.template_id!r} requires a loop edge to reach the boss at size {size}"
                )

    def validate(self) -> None:
        if not self.template_id:
            raise ValueError("template id must not be empty")
        if len(self.nodes) != SUPPORTED_MAP_SIZES[-1]:
            raise ValueError(f"template {self.template_id!r} must define exactly 48 nodes")

        nodes_by_id = {node.node_id: node for node in self.nodes}
        if len(nodes_by_id) != len(self.nodes):
            raise ValueError(f"template {self.template_id!r} contains duplicate node ids")

        start_count = 0
        for node in self.nodes:
            if not node.node_id:
                raise ValueError(f"template {self.template_id!r} contains an empty node id")
            if not 0.0 <= node.x <= 1.0 or not 0.0 <= node.y <= 1.0:
                raise ValueError(
                    f"template {self.template_id!r} node {node.node_id!r} coordinate must be within [0, 1]"
                )
            if node.depth < 0:
                raise ValueError(f"template {self.template_id!r} node {node.node_id!r} has negative depth")
            if node.activation_size not in SUPPORTED_MAP_SIZES:
                raise ValueError(
                    f"template {self.template_id!r} node {node.node_id!r} has unsupported activation size"
                )
            if not node.allowed_kinds:
                raise ValueError(f"template {self.template_id!r} node {node.node_id!r} has no allowed kinds")
            if len(set(node.allowed_kinds)) != len(node.allowed_kinds):
                raise ValueError(f"template {self.template_id!r} node {node.node_id!r} repeats an allowed kind")
            if NodeKind.START in node.allowed_kinds:
                start_count += 1
        if start_count != 1:
            raise ValueError(f"template {self.template_id!r} must define exactly one start node")

        activation_counts = tuple(
            sum(node.activation_size <= size for node in self.nodes) for size in SUPPORTED_MAP_SIZES
        )
        if activation_counts != SUPPORTED_MAP_SIZES:
            raise ValueError(
                f"template {self.template_id!r} activation counts {activation_counts!r} do not match supported sizes"
            )

        edge_ids: set[str] = set()
        for edge in self.edges:
            if not edge.edge_id:
                raise ValueError(f"template {self.template_id!r} contains an empty edge id")
            if edge.edge_id in edge_ids:
                raise ValueError(f"template {self.template_id!r} contains duplicate edge id {edge.edge_id!r}")
            edge_ids.add(edge.edge_id)
            if edge.source_node_id not in nodes_by_id or edge.target_node_id not in nodes_by_id:
                raise ValueError(
                    f"template {self.template_id!r} edge {edge.edge_id!r} references an unknown node"
                )
            if edge.source_node_id == edge.target_node_id:
                raise ValueError(f"template {self.template_id!r} edge {edge.edge_id!r} is a self edge")
            if edge.activation_size not in SUPPORTED_MAP_SIZES:
                raise ValueError(
                    f"template {self.template_id!r} edge {edge.edge_id!r} has unsupported activation size"
                )
            source = nodes_by_id[edge.source_node_id]
            target = nodes_by_id[edge.target_node_id]
            if edge.activation_size < max(source.activation_size, target.activation_size):
                raise ValueError(
                    f"template {self.template_id!r} edge {edge.edge_id!r} activates before one of its nodes"
                )
            if edge.is_loop and source.depth <= target.depth:
                raise ValueError(
                    f"template {self.template_id!r} loop edge {edge.edge_id!r} must decrease node depth"
                )
            if not edge.is_loop and source.depth >= target.depth:
                raise ValueError(
                    f"template {self.template_id!r} non-loop edge {edge.edge_id!r} must increase node depth"
                )

        for size in SUPPORTED_MAP_SIZES:
            graph = self.active_graph(size)
            if not any(node.is_safe and node.node_id != graph.start_node_id for node in graph.nodes):
                raise ValueError(f"template {self.template_id!r} has no safe node at size {size}")

        graph_24 = self.active_graph(24)
        graph_48 = self.active_graph(48)
        if self.risk is DungeonRisk.NORMAL:
            if graph_24.branch_count not in {3, 4} or graph_48.branch_count not in {5, 6}:
                raise ValueError(f"normal template {self.template_id!r} has invalid branch density")
            if graph_48.loop_edges:
                raise ValueError(f"normal template {self.template_id!r} must not contain loop edges")
        else:
            if graph_24.branch_count < 5 or graph_48.branch_count < 8:
                raise ValueError(f"high-risk template {self.template_id!r} has invalid branch density")
            if not 1 <= len(graph_24.loop_edges) <= 2 or not 1 <= len(graph_48.loop_edges) <= 4:
                raise ValueError(f"high-risk template {self.template_id!r} has invalid loop density")
        self.validate_loop_safety()


@dataclass(frozen=True)
class MysticThemeDefinition:
    theme_id: str
    display_name: str
    risk: DungeonRisk
    template_id: str
    background_path: Path
    background_sha256: str = ""


@dataclass(frozen=True)
class MysticTemplateCatalog:
    themes: dict[str, MysticThemeDefinition]
    templates: dict[str, DungeonMapTemplate]

    @classmethod
    def from_files(
        cls,
        manifest_path: str | Path | None = None,
        templates_path: str | Path | None = None,
    ) -> MysticTemplateCatalog:
        asset_root = Path(__file__).resolve().parent / "assets" / "mystic_maps"
        manifest_file = Path(manifest_path) if manifest_path is not None else asset_root / "manifest.json"
        templates_file = Path(templates_path) if templates_path is not None else asset_root / "templates.json"

        manifest = _load_json_object(manifest_file)
        _require_exact_keys(manifest, {"schema_version", "themes"}, "manifest")
        _require_schema_version(manifest["schema_version"], "manifest")
        raw_themes = _as_object(manifest["themes"], "manifest.themes")

        themes: dict[str, MysticThemeDefinition] = {}
        for theme_id, raw_theme in raw_themes.items():
            theme_data = _as_object(raw_theme, f"theme {theme_id!r}")
            _require_keys(
                theme_data,
                {"display_name", "risk", "template_id", "background"},
                {"sha256"},
                f"theme {theme_id!r}",
            )
            risk = _parse_risk(theme_data["risk"], f"theme {theme_id!r}.risk")
            background = _as_string(theme_data["background"], f"theme {theme_id!r}.background")
            relative_background = Path(background)
            if relative_background.is_absolute() or ".." in relative_background.parts:
                raise ValueError(f"theme {theme_id!r} background must be a relative asset path")
            if relative_background.parts[:1] != ("backgrounds",) or relative_background.suffix.lower() != ".png":
                raise ValueError(f"theme {theme_id!r} background must be a PNG under backgrounds/")
            background_sha256 = str(theme_data.get("sha256") or "").lower()
            if background_sha256 and (
                len(background_sha256) != 64
                or any(character not in "0123456789abcdef" for character in background_sha256)
            ):
                raise ValueError(f"theme {theme_id!r} sha256 must be a 64-character hexadecimal digest")
            background_path = (manifest_file.parent / relative_background).resolve()
            themes[theme_id] = MysticThemeDefinition(
                theme_id=theme_id,
                display_name=_as_string(theme_data["display_name"], f"theme {theme_id!r}.display_name"),
                risk=risk,
                template_id=_as_string(theme_data["template_id"], f"theme {theme_id!r}.template_id"),
                background_path=background_path,
                background_sha256=background_sha256,
            )

        templates_document = _load_json_object(templates_file)
        _require_exact_keys(templates_document, {"schema_version", "templates"}, "templates")
        _require_schema_version(templates_document["schema_version"], "templates")
        raw_templates = _as_object(templates_document["templates"], "templates.templates")

        templates: dict[str, DungeonMapTemplate] = {}
        for template_id, raw_template in raw_templates.items():
            template_data = _as_object(raw_template, f"template {template_id!r}")
            _require_exact_keys(template_data, {"risk", "nodes", "edges"}, f"template {template_id!r}")
            risk = _parse_risk(template_data["risk"], f"template {template_id!r}.risk")
            raw_nodes = _as_list(template_data["nodes"], f"template {template_id!r}.nodes")
            raw_edges = _as_list(template_data["edges"], f"template {template_id!r}.edges")
            nodes = tuple(
                _parse_node(raw_node, f"template {template_id!r}.nodes[{index}]")
                for index, raw_node in enumerate(raw_nodes)
            )
            edges = tuple(
                _parse_edge(raw_edge, f"template {template_id!r}.edges[{index}]")
                for index, raw_edge in enumerate(raw_edges)
            )
            template = DungeonMapTemplate(
                template_id=template_id,
                risk=risk,
                nodes=nodes,
                edges=edges,
            )
            template.validate()
            templates[template_id] = template

        catalog = cls(themes=themes, templates=templates)
        catalog._validate_bindings()
        catalog._validate_background_hashes()
        return catalog

    def _validate_background_hashes(self) -> None:
        for theme in self.themes.values():
            if not theme.background_sha256:
                continue
            try:
                with theme.background_path.open("rb") as background_file:
                    actual_sha256 = hashlib.file_digest(
                        background_file,
                        "sha256",
                    ).hexdigest()
            except OSError as exc:
                raise ValueError(
                    f"unable to read theme {theme.theme_id!r} "
                    f"background {theme.background_path}"
                ) from exc
            if actual_sha256 != theme.background_sha256:
                raise ValueError(
                    f"theme {theme.theme_id!r} background sha256 "
                    "does not match manifest"
                )

    def normal_templates(self) -> tuple[DungeonMapTemplate, ...]:
        return tuple(
            template for template in self.templates.values() if template.risk is DungeonRisk.NORMAL
        )

    def high_risk_templates(self) -> tuple[DungeonMapTemplate, ...]:
        return tuple(template for template in self.templates.values() if template.risk is DungeonRisk.HIGH)

    def _validate_bindings(self) -> None:
        theme_ids = set(self.themes)
        template_ids = set(self.templates)
        if theme_ids != template_ids:
            missing = sorted(theme_ids - template_ids)
            unused = sorted(template_ids - theme_ids)
            raise ValueError(f"catalog theme/template mismatch: missing={missing!r}, unused={unused!r}")
        bound_template_ids = {theme.template_id for theme in self.themes.values()}
        if bound_template_ids != template_ids or len(bound_template_ids) != len(self.themes):
            raise ValueError("each theme must bind its own unique template")
        for theme in self.themes.values():
            template = self.templates[theme.template_id]
            if theme.risk is not template.risk:
                raise ValueError(f"theme {theme.theme_id!r} risk does not match its template")


def map_size_for_boss(realm_index: int, rules: tuple[tuple[int, int], ...]) -> int:
    selected = SUPPORTED_MAP_SIZES[0]
    for minimum_realm, node_count in sorted(rules):
        if realm_index < minimum_realm:
            break
        selected = node_count
    if selected not in SUPPORTED_MAP_SIZES:
        raise ValueError(f"unsupported map size: {selected}")
    return selected


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except OSError as exc:
        raise ValueError(f"unable to read catalog file {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in catalog file {path}") from exc
    return _as_object(raw, str(path))


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _require_schema_version(value: Any, context: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value != 1:
        raise ValueError(f"{context}.schema_version must be 1")


def _require_exact_keys(data: dict[str, Any], expected: set[str], context: str) -> None:
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(f"{context} keys mismatch: missing={missing!r}, extra={extra!r}")


def _require_keys(
    data: dict[str, Any],
    required: set[str],
    optional: set[str],
    context: str,
) -> None:
    actual = set(data)
    missing = sorted(required - actual)
    extra = sorted(actual - required - optional)
    if missing or extra:
        raise ValueError(f"{context} keys mismatch: missing={missing!r}, extra={extra!r}")


def _as_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{context} must be an object with string keys")
    return dict(value)


def _as_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{context} must be a list")
    return value


def _as_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string")
    return value


def _as_string_allow_empty(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{context} must be a string")
    return value


def _as_optional_string(value: Any, context: str) -> str | None:
    if value is None:
        return None
    return _as_string(value, context)


def _as_datetime_string(value: Any, context: str) -> str:
    raw = _as_string(value, context)
    try:
        datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{context} must be an ISO datetime") from exc
    return raw


def _as_string_list(value: Any, context: str) -> list[str]:
    return [
        _as_string(item, f"{context}[{index}]")
        for index, item in enumerate(_as_list(value, context))
    ]


def _as_int(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{context} must be an integer")
    return value


def _as_float(value: Any, context: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise ValueError(f"{context} must be a number")
    return float(value)


def _as_bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{context} must be a boolean")
    return value


def _parse_risk(value: Any, context: str) -> DungeonRisk:
    raw = _as_string(value, context)
    try:
        return DungeonRisk(raw)
    except ValueError as exc:
        raise ValueError(f"{context} has unknown risk {raw!r}") from exc


def _parse_node(value: Any, context: str) -> DungeonNodeSlot:
    data = _as_object(value, context)
    _require_exact_keys(
        data,
        {
            "node_id",
            "x",
            "y",
            "depth",
            "activation_size",
            "allowed_kinds",
            "is_safe",
            "is_terminal_candidate",
        },
        context,
    )
    raw_kinds = _as_list(data["allowed_kinds"], f"{context}.allowed_kinds")
    allowed_kinds: list[NodeKind] = []
    for index, raw_kind in enumerate(raw_kinds):
        kind_name = _as_string(raw_kind, f"{context}.allowed_kinds[{index}]")
        try:
            allowed_kinds.append(NodeKind(kind_name))
        except ValueError as exc:
            raise ValueError(f"{context}.allowed_kinds[{index}] has unknown node kind {kind_name!r}") from exc
    return DungeonNodeSlot(
        node_id=_as_string(data["node_id"], f"{context}.node_id"),
        x=_as_float(data["x"], f"{context}.x"),
        y=_as_float(data["y"], f"{context}.y"),
        depth=_as_int(data["depth"], f"{context}.depth"),
        activation_size=_as_int(data["activation_size"], f"{context}.activation_size"),
        allowed_kinds=tuple(allowed_kinds),
        is_safe=_as_bool(data["is_safe"], f"{context}.is_safe"),
        is_terminal_candidate=_as_bool(
            data["is_terminal_candidate"],
            f"{context}.is_terminal_candidate",
        ),
    )


def _parse_edge(value: Any, context: str) -> DungeonEdge:
    data = _as_object(value, context)
    _require_exact_keys(
        data,
        {
            "edge_id",
            "source_node_id",
            "target_node_id",
            "activation_size",
            "is_loop",
        },
        context,
    )
    return DungeonEdge(
        edge_id=_as_string(data["edge_id"], f"{context}.edge_id"),
        source_node_id=_as_string(data["source_node_id"], f"{context}.source_node_id"),
        target_node_id=_as_string(data["target_node_id"], f"{context}.target_node_id"),
        activation_size=_as_int(data["activation_size"], f"{context}.activation_size"),
        is_loop=_as_bool(data["is_loop"], f"{context}.is_loop"),
    )


class MysticContentFactory:
    _VISIBLE_LABELS = {
        NodeKind.START: "起点",
        NodeKind.RANDOM: "随机事件",
        NodeKind.COMBAT: "战斗",
        NodeKind.RESOURCE: "资源",
        NodeKind.TRAP: "陷阱",
        NodeKind.REST: "休整",
        NodeKind.BOSS: "BOSS",
    }

    def instantiate(
        self,
        template: DungeonMapTemplate,
        map_size: int,
        content_seed: int,
        config: MysticGameplayConfig,
    ) -> dict[str, DungeonNodeContent]:
        graph = template.active_graph(map_size)
        rng = random.Random(content_seed)
        weights = (
            config.normal_node_weights
            if template.risk is DungeonRisk.NORMAL
            else config.high_risk_node_weights
        )
        combat_limit = max(0, int(config.consecutive_combat_limit))
        combat_streak = 0
        safe_node_index = 0
        contents: dict[str, DungeonNodeContent] = {}
        for node in graph.nodes:
            if node.node_id == graph.start_node_id:
                kind = NodeKind.START
            elif node.node_id == graph.boss_node_id:
                kind = NodeKind.BOSS
            elif node.is_safe:
                safe_kinds = [
                    candidate
                    for candidate in (NodeKind.REST, NodeKind.RESOURCE)
                    if candidate in node.allowed_kinds
                ]
                if safe_kinds:
                    kind = safe_kinds[safe_node_index % len(safe_kinds)]
                    safe_node_index += 1
                else:
                    kind = NodeKind.RANDOM
            else:
                allowed_kinds = [
                    candidate
                    for candidate in node.allowed_kinds
                    if candidate not in {NodeKind.START, NodeKind.BOSS}
                ]
                if combat_limit == 0 or combat_streak >= combat_limit:
                    allowed_kinds = [
                        candidate for candidate in allowed_kinds if candidate is not NodeKind.COMBAT
                    ]
                kind = self._weighted_kind(rng, allowed_kinds, weights)
            combat_streak = combat_streak + 1 if kind is NodeKind.COMBAT else 0
            event_roll = rng.randrange(0, 2**32)
            contents[node.node_id] = DungeonNodeContent(
                node_id=node.node_id,
                kind=kind,
                event_id=f"{template.template_id}:{node.node_id}:{kind.value}:{event_roll:08x}",
                visible_label=self._VISIBLE_LABELS[kind],
                payload={
                    "template_id": template.template_id,
                    "risk": template.risk.value,
                    "depth": node.depth,
                    "content_roll": event_roll,
                },
            )
        return contents

    def _weighted_kind(
        self,
        rng: random.Random,
        allowed_kinds: Sequence[NodeKind],
        weights: dict[str, float],
    ) -> NodeKind:
        weighted = [
            (kind, max(0.0, float(weights.get(kind.value, 0.0))))
            for kind in allowed_kinds
        ]
        weighted = [(kind, weight) for kind, weight in weighted if weight > 0]
        if not weighted:
            if not allowed_kinds:
                raise ValueError("dungeon node has no selectable content kinds")
            return allowed_kinds[0]
        point = rng.random() * sum(weight for _, weight in weighted)
        cursor = 0.0
        for kind, weight in weighted:
            cursor += weight
            if point <= cursor:
                return kind
        return weighted[-1][0]


class MysticDungeonService:
    def __init__(
        self,
        catalog: MysticTemplateCatalog,
        now: Callable[[], datetime],
        config_provider: Callable[[], MysticGameplayConfig] | None = None,
        enabled_theme_ids_provider: (
            Callable[[DungeonRisk], Sequence[str] | None] | None
        ) = None,
    ) -> None:
        self._catalog = catalog
        self._now = now
        self._config_provider = config_provider or default_mystic_gameplay_config
        self._enabled_theme_ids_provider = enabled_theme_ids_provider

    @property
    def catalog(self) -> MysticTemplateCatalog:
        return self._catalog

    @property
    def config(self) -> MysticGameplayConfig:
        return self._config_provider()

    def create_solo_run(
        self,
        run_id: str,
        group_id: str,
        user_id: str,
        risk: DungeonRisk,
        boss_realm_index: int,
        map_seed: int,
        content_seed: int,
    ) -> tuple[MysticDungeonRun, EntryCharge]:
        parsed_risk = self._validate_risk(risk)
        self._validate_identifier(run_id, "run id")
        self._validate_identifier(group_id, "group id")
        self._validate_identifier(user_id, "user id")
        member = MysticDungeonMember(
            user_id=user_id,
            nickname="",
            ready=True,
            joined_at=self._current_time().isoformat(),
        )
        run = MysticDungeonRun(
            run_id=run_id,
            source_group_id=group_id,
            mode=DungeonMode.SOLO,
            risk=parsed_risk,
            leader_id=user_id,
            members={user_id: member},
        )
        self._initialize_started_run(run, boss_realm_index, map_seed, content_seed)
        return run, self._entry_charge(run)

    def create_lobby(
        self,
        run_id: str,
        group_id: str,
        leader_id: str,
        risk: DungeonRisk,
    ) -> MysticDungeonRun:
        parsed_risk = self._validate_risk(risk)
        self._validate_identifier(run_id, "run id")
        self._validate_identifier(group_id, "group id")
        self._validate_identifier(leader_id, "leader id")
        leader = MysticDungeonMember(
            user_id=leader_id,
            nickname="",
            joined_at=self._current_time().isoformat(),
        )
        return MysticDungeonRun(
            run_id=run_id,
            source_group_id=group_id,
            mode=DungeonMode.TEAM,
            risk=parsed_risk,
            leader_id=leader_id,
            members={leader_id: leader},
        )

    def join_lobby(
        self,
        run: MysticDungeonRun,
        user_id: str,
        nickname: str = "",
    ) -> None:
        self._require_team_lobby(run)
        self._validate_identifier(user_id, "user id")
        if not isinstance(nickname, str):
            raise ValueError("nickname must be a string")
        if user_id in run.members:
            raise ValueError("user is already in the dungeon lobby")
        if len(run.members) >= 3:
            raise ValueError("dungeon lobby is full")
        run.members[user_id] = MysticDungeonMember(
            user_id=user_id,
            nickname=nickname,
            joined_at=self._current_time().isoformat(),
        )
        run.revision += 1

    def remove_lobby_member(self, run: MysticDungeonRun, user_id: str) -> None:
        self._require_team_lobby(run)
        if user_id == run.leader_id:
            raise ValueError("the lobby leader cannot be removed")
        if user_id not in run.members:
            raise ValueError("user is not in the dungeon lobby")
        del run.members[user_id]
        run.revision += 1

    def set_ready(self, run: MysticDungeonRun, user_id: str, ready: bool) -> None:
        self._require_team_lobby(run)
        if user_id not in run.members:
            raise ValueError("user is not in the dungeon lobby")
        if not isinstance(ready, bool):
            raise ValueError("ready must be a boolean")
        run.members[user_id].ready = ready
        run.revision += 1

    def start_run(
        self,
        run: MysticDungeonRun,
        boss_realm_index: int,
        map_seed: int,
        content_seed: int,
    ) -> EntryCharge:
        self._require_team_lobby(run)
        if not 2 <= len(run.members) <= 3:
            raise ValueError("team dungeon requires exactly two or three members")
        if not all(member.ready for member in run.members.values()):
            raise ValueError("all dungeon members must be ready")
        self._initialize_started_run(run, boss_realm_index, map_seed, content_seed)
        return self._entry_charge(run)

    def _initialize_started_run(
        self,
        run: MysticDungeonRun,
        boss_realm_index: int,
        map_seed: int,
        content_seed: int,
    ) -> None:
        if not isinstance(boss_realm_index, int) or isinstance(boss_realm_index, bool):
            raise ValueError("boss realm index must be an integer")
        if not isinstance(map_seed, int) or isinstance(map_seed, bool):
            raise ValueError("map seed must be an integer")
        if not isinstance(content_seed, int) or isinstance(content_seed, bool):
            raise ValueError("content seed must be an integer")
        enabled_theme_ids = (
            self._enabled_theme_ids_provider(run.risk)
            if self._enabled_theme_ids_provider is not None
            else None
        )
        enabled_theme_id_set = (
            None if enabled_theme_ids is None else set(enabled_theme_ids)
        )
        choices = sorted(
            (
                theme
                for theme in self._catalog.themes.values()
                if theme.risk is run.risk
                and (
                    enabled_theme_id_set is None
                    or theme.theme_id in enabled_theme_id_set
                )
            ),
            key=lambda theme: theme.theme_id,
        )
        if not choices:
            raise ValueError(f"catalog has no themes for risk {run.risk.value!r}")
        theme = choices[map_seed % len(choices)]
        try:
            template = self._catalog.templates[theme.template_id]
        except KeyError as exc:
            raise ValueError(f"catalog is missing template {theme.template_id!r}") from exc
        if template.risk is not run.risk:
            raise ValueError("selected dungeon template has the wrong risk")
        config = self.config
        configured_rules = tuple(
            (rule.minimum_boss_realm_index, rule.node_count)
            for rule in config.map_size_rules
        )
        configured_map_size = map_size_for_boss(
            boss_realm_index,
            configured_rules,
        )
        map_size = min(
            config.max_map_size,
            max(config.min_map_size, configured_map_size),
        )
        graph = template.active_graph(map_size)

        run.template_id = template.template_id
        run.theme_id = theme.theme_id
        run.map_size = map_size
        run.map_seed = map_seed
        run.content_seed = content_seed
        run.current_node_id = graph.start_node_id
        run.boss_node_id = graph.boss_node_id
        run.visited_node_ids = [graph.start_node_id]
        run.visited_edge_ids = []
        run.cleared_node_ids = [graph.start_node_id]
        run.remaining_steps = 0
        run.pending_branch_choices = []
        run.last_leader_action_at = self._current_time().isoformat()
        run.active_encounter_id = None
        run.temporary_rewards_by_user = {user_id: [] for user_id in run.members}
        run.node_contents = MysticContentFactory().instantiate(
            template,
            map_size,
            content_seed,
            config,
        )
        run.settled_reward_node_keys = []
        run.active_vote = None
        run.phase = DungeonPhase.READY_TO_ROLL
        run.revision += 1

    def _entry_charge(self, run: MysticDungeonRun) -> EntryCharge:
        token_name = "普通秘境令牌" if run.risk is DungeonRisk.NORMAL else "高风险秘境令牌"
        return EntryCharge(payer_id=run.leader_id, token_name=token_name)

    def node_resolution_kind(
        self,
        run: MysticDungeonRun,
        node_id: str,
    ) -> NodeKind:
        content = run.node_contents.get(node_id)
        if content is None:
            raise ValueError(f"dungeon node {node_id!r} has no instantiated content")
        if content.kind is not NodeKind.RANDOM:
            return content.kind
        outcomes = (
            NodeKind.COMBAT,
            NodeKind.RESOURCE,
            NodeKind.TRAP,
            NodeKind.REST,
        )
        content_roll = int(content.payload.get("content_roll", 0))
        return outcomes[content_roll % len(outcomes)]

    def resolve_reward_node(
        self,
        run: MysticDungeonRun,
        node_id: str,
    ) -> NodeRewardResult:
        return self.resolve_noncombat_node(
            run,
            node_id,
            resolved_kind=NodeKind.RESOURCE,
        )

    def resolve_noncombat_node(
        self,
        run: MysticDungeonRun,
        node_id: str,
        *,
        resolved_kind: NodeKind | None = None,
    ) -> NodeRewardResult:
        if node_id != run.current_node_id:
            raise ValueError("resolved node must be the dungeon current node")
        kind = resolved_kind or self.node_resolution_kind(run, node_id)
        if kind not in {NodeKind.RESOURCE, NodeKind.TRAP, NodeKind.REST}:
            raise ValueError("node is not a non-combat node")
        if node_id in run.cleared_node_ids:
            return NodeRewardResult(rewards_by_user={})

        granted: dict[str, list[dict[str, Any]]] = {}
        if kind is NodeKind.RESOURCE:
            ledger = DungeonRewardLedger(
                rewards_by_user={
                    user_id: [dict(reward) for reward in rewards]
                    for user_id, rewards in run.temporary_rewards_by_user.items()
                },
                settled_node_keys=set(run.settled_reward_node_keys),
            )
            for user_id in run.member_ids:
                reward = self._personal_node_reward(run, node_id, user_id)
                if ledger.add_personal(user_id, node_id, reward):
                    granted[user_id] = [dict(reward)]
            run.temporary_rewards_by_user = ledger.rewards_by_user
            run.settled_reward_node_keys = sorted(ledger.settled_node_keys)
        elif kind is NodeKind.TRAP:
            for user_id in run.member_ids:
                rewards = run.temporary_rewards_by_user.setdefault(user_id, [])
                if rewards:
                    rewards.pop()

        run.cleared_node_ids.append(node_id)
        run.phase = DungeonPhase.READY_TO_ROLL
        run.revision += 1
        return NodeRewardResult(rewards_by_user=granted)
    def grant_encounter_rewards(
        self,
        run: MysticDungeonRun,
        node_id: str,
        eligible_user_ids: Sequence[str],
    ) -> NodeRewardResult:
        ledger = DungeonRewardLedger(
            rewards_by_user={
                user_id: [dict(reward) for reward in rewards]
                for user_id, rewards in run.temporary_rewards_by_user.items()
            },
            settled_node_keys=set(run.settled_reward_node_keys),
        )
        granted: dict[str, list[dict[str, Any]]] = {}
        reward_key = f"{node_id}:combat"
        for user_id in eligible_user_ids:
            if user_id not in run.members:
                raise ValueError("encounter loot contains a non-member")
            reward = self._personal_node_reward(run, reward_key, user_id)
            if ledger.add_personal(user_id, reward_key, reward):
                granted[user_id] = [dict(reward)]
        run.temporary_rewards_by_user = ledger.rewards_by_user
        run.settled_reward_node_keys = sorted(ledger.settled_node_keys)
        return NodeRewardResult(rewards_by_user=granted)
    def _personal_node_reward(
        self,
        run: MysticDungeonRun,
        node_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(
            f"{run.content_seed}:{run.theme_id}:{node_id}:{user_id}".encode("utf-8")
        ).hexdigest()
        roll = int(digest[:16], 16)
        reward_kind = roll % 4
        if reward_kind == 0:
            return {
                "category": "灵石",
                "name": "灵石",
                "amount": max(
                    1,
                    int((20 + roll % 81) * self.config.reward_multiplier),
                ),
            }
        if reward_kind == 1:
            return {
                "category": "修为",
                "name": "修为",
                "amount": max(
                    1,
                    int((10 + roll % 41) * self.config.reward_multiplier),
                ),
            }
        if reward_kind == 2:
            return {
                "category": "垂钓次数",
                "name": "垂钓次数",
                "amount": max(1, int(self.config.reward_multiplier)),
            }
        return {
            "tier": "凡品",
            "grade": "中品",
            "category": "杂物",
            "name": f"{run.theme_id}秘境灵材",
            "description": "从秘境资源节点采集的灵材。",
        }

    def _require_team_lobby(self, run: MysticDungeonRun) -> None:
        if run.mode is not DungeonMode.TEAM or run.phase is not DungeonPhase.LOBBY:
            raise ValueError("operation is only valid for a team dungeon lobby")

    def _validate_risk(self, risk: DungeonRisk) -> DungeonRisk:
        try:
            return DungeonRisk(risk)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"unknown dungeon risk {risk!r}") from exc

    def _validate_identifier(self, value: str, label: str) -> None:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must be a non-empty string")

    def _current_time(self) -> datetime:
        current = self._now()
        if not isinstance(current, datetime):
            raise TypeError("now callback must return a datetime")
        return current

    def roll(
        self,
        run: MysticDungeonRun,
        actor_id: str,
        dice_value: int,
    ) -> MovementResult:
        if not isinstance(dice_value, int) or isinstance(dice_value, bool) or not 1 <= dice_value <= 6:
            raise ValueError("dice value must be between 1 and 6")
        self._require_movement_actor(run, actor_id)
        action_time = self._current_time()
        phase = self._effective_movement_phase(run, actor_id, action_time)
        if phase is not DungeonPhase.READY_TO_ROLL:
            raise ValueError("roll requires phase ready_to_roll")
        self._cancel_leader_transfer(run)
        run.phase = DungeonPhase.MOVING
        result = self._advance(run, dice_value)
        run.last_leader_action_at = action_time.isoformat()
        run.revision += 1
        return result

    def choose_branch(
        self,
        run: MysticDungeonRun,
        actor_id: str,
        target_node_id: str,
    ) -> MovementResult:
        self._require_movement_actor(run, actor_id)
        self._validate_identifier(target_node_id, "target node id")
        action_time = self._current_time()
        phase = self._effective_movement_phase(run, actor_id, action_time)
        if phase is not DungeonPhase.AWAITING_BRANCH:
            raise ValueError("branch choice requires phase awaiting_branch")
        if target_node_id not in run.pending_branch_choices:
            raise ValueError("target node is not a pending branch choice")
        if run.remaining_steps <= 0:
            raise ValueError("awaiting branch state has no remaining steps")

        graph = self._active_graph(run)
        matching_edges = sorted(
            (
                edge
                for edge in graph.edges
                if edge.source_node_id == run.current_node_id and edge.target_node_id == target_node_id
            ),
            key=lambda edge: edge.edge_id,
        )
        if not matching_edges:
            raise ValueError("pending branch target has no active edge")

        self._cancel_leader_transfer(run)
        remaining_steps = run.remaining_steps
        run.remaining_steps = 0
        run.pending_branch_choices = []
        run.phase = DungeonPhase.MOVING
        selected_edge = matching_edges[0]
        self._record_traversal(run, selected_edge)
        remaining_steps -= 1

        if run.current_node_id == run.boss_node_id:
            continued = self._finish_landing(run)
        else:
            continued = self._advance(run, remaining_steps)
        result = MovementResult(
            traversed_edge_ids=(selected_edge.edge_id, *continued.traversed_edge_ids),
            landed_node_id=continued.landed_node_id,
            pending_branch_choices=continued.pending_branch_choices,
            node_resolution_required=continued.node_resolution_required,
        )
        run.last_leader_action_at = action_time.isoformat()
        run.revision += 1
        return result

    def _advance(self, run: MysticDungeonRun, steps: int) -> MovementResult:
        if steps < 0:
            raise ValueError("movement steps must not be negative")
        graph = self._active_graph(run)
        outgoing: dict[str, list[DungeonEdge]] = {}
        for edge in graph.edges:
            outgoing.setdefault(edge.source_node_id, []).append(edge)
        for edges in outgoing.values():
            edges.sort(key=lambda edge: (edge.target_node_id, edge.edge_id))

        traversed_edge_ids: list[str] = []
        while steps > 0:
            choices = outgoing.get(run.current_node_id, [])
            if len(choices) > 1:
                pending_choices = sorted({edge.target_node_id for edge in choices})
                run.phase = DungeonPhase.AWAITING_BRANCH
                run.remaining_steps = steps
                run.pending_branch_choices = pending_choices
                return MovementResult(
                    traversed_edge_ids=tuple(traversed_edge_ids),
                    landed_node_id=None,
                    pending_branch_choices=tuple(pending_choices),
                    node_resolution_required=False,
                )
            if not choices:
                raise ValueError(f"node {run.current_node_id!r} has no outgoing edge before the boss")
            edge = choices[0]
            self._record_traversal(run, edge)
            traversed_edge_ids.append(edge.edge_id)
            steps -= 1
            if run.current_node_id == run.boss_node_id:
                landed = self._finish_landing(run)
                return MovementResult(
                    traversed_edge_ids=tuple(traversed_edge_ids),
                    landed_node_id=landed.landed_node_id,
                    pending_branch_choices=landed.pending_branch_choices,
                    node_resolution_required=landed.node_resolution_required,
                )

        landed = self._finish_landing(run)
        return MovementResult(
            traversed_edge_ids=tuple(traversed_edge_ids),
            landed_node_id=landed.landed_node_id,
            pending_branch_choices=landed.pending_branch_choices,
            node_resolution_required=landed.node_resolution_required,
        )

    def _finish_landing(self, run: MysticDungeonRun) -> MovementResult:
        run.remaining_steps = 0
        run.pending_branch_choices = []
        node_resolution_required = run.current_node_id not in run.cleared_node_ids
        run.phase = (
            DungeonPhase.RESOLVING_NODE if node_resolution_required else DungeonPhase.READY_TO_ROLL
        )
        return MovementResult(
            traversed_edge_ids=(),
            landed_node_id=run.current_node_id,
            pending_branch_choices=(),
            node_resolution_required=node_resolution_required,
        )

    def _record_traversal(self, run: MysticDungeonRun, edge: DungeonEdge) -> None:
        if edge.edge_id not in run.visited_edge_ids:
            run.visited_edge_ids.append(edge.edge_id)
        run.current_node_id = edge.target_node_id
        if edge.target_node_id not in run.visited_node_ids:
            run.visited_node_ids.append(edge.target_node_id)

    def _active_graph(self, run: MysticDungeonRun) -> ActiveDungeonGraph:
        try:
            template = self._catalog.templates[run.template_id]
        except KeyError as exc:
            raise ValueError(f"unknown dungeon template {run.template_id!r}") from exc
        return template.active_graph(run.map_size)

    def _require_movement_actor(self, run: MysticDungeonRun, actor_id: str) -> None:
        if actor_id != run.leader_id:
            raise PermissionError("only the dungeon leader can move")

    def _effective_movement_phase(
        self,
        run: MysticDungeonRun,
        actor_id: str,
        action_time: datetime,
    ) -> DungeonPhase:
        vote = run.active_vote
        if vote is None:
            return run.phase
        if (
            vote.kind is VoteKind.LEADER_TRANSFER
            and run.phase is DungeonPhase.AWAITING_LEADER_TRANSFER_VOTE
            and actor_id == run.leader_id
            and vote.prior_phase is not None
        ):
            deadline = datetime.fromisoformat(vote.deadline)
            try:
                before_deadline = action_time <= deadline
            except TypeError as exc:
                raise ValueError("leader transfer deadline timezone does not match service time") from exc
            if not before_deadline:
                raise ValueError("leader transfer vote deadline has passed")
            return vote.prior_phase
        raise ValueError("movement is blocked while a vote is active")

    def _cancel_leader_transfer(self, run: MysticDungeonRun) -> None:
        vote = run.active_vote
        if vote is None or vote.kind is not VoteKind.LEADER_TRANSFER:
            return
        if vote.prior_phase is None:
            raise ValueError("leader transfer vote is missing its previous phase")
        run.phase = vote.prior_phase
        run.active_vote = None

    def begin_boss_continuation_vote(
        self,
        run: MysticDungeonRun,
        deadline: datetime,
    ) -> DungeonVote:
        self._validate_vote_start(run, run.leader_id, deadline)
        if run.phase is not DungeonPhase.BATTLE_TURN:
            raise ValueError("boss continuation vote requires an active battle")
        vote = DungeonVote(
            vote_id=f"{run.run_id}:{VoteKind.BOSS_CONTINUE.value}:{run.revision + 1}",
            kind=VoteKind.BOSS_CONTINUE,
            eligible_user_ids=run.member_ids,
            approvals=set(),
            rejections=set(),
            deadline=deadline.isoformat(),
            prior_phase=DungeonPhase.BATTLE_TURN,
        )
        run.active_vote = vote
        run.phase = DungeonPhase.AWAITING_BOSS_VOTE
        run.revision += 1
        return vote

    def begin_leader_transfer(
        self,
        run: MysticDungeonRun,
        actor_id: str,
        nominee_id: str,
        deadline: datetime,
    ) -> DungeonVote:
        self._validate_vote_start(run, actor_id, deadline)
        if actor_id == run.leader_id:
            raise PermissionError("the current leader cannot initiate a leader transfer vote")
        if nominee_id not in run.members:
            raise ValueError("leader transfer nominee must be in the fixed roster")
        if nominee_id == run.leader_id:
            raise ValueError("leader transfer nominee must not be the current leader")
        eligible_user_ids = tuple(user_id for user_id in run.member_ids if user_id != run.leader_id)
        vote = DungeonVote(
            vote_id=f"{run.run_id}:{VoteKind.LEADER_TRANSFER.value}:{run.revision + 1}",
            kind=VoteKind.LEADER_TRANSFER,
            eligible_user_ids=eligible_user_ids,
            approvals=set(),
            rejections=set(),
            deadline=deadline.isoformat(),
            nominee_id=nominee_id,
            prior_phase=run.phase,
        )
        run.active_vote = vote
        run.phase = DungeonPhase.AWAITING_LEADER_TRANSFER_VOTE
        run.revision += 1
        return vote

    def cast_vote(
        self,
        run: MysticDungeonRun,
        actor_id: str,
        approve: bool,
    ) -> VoteResult:
        vote = run.active_vote
        if vote is None:
            raise ValueError("dungeon run has no active vote")
        if actor_id not in vote.eligible_user_ids:
            raise PermissionError("actor is not eligible for this vote")
        deadline = datetime.fromisoformat(vote.deadline)
        try:
            expired = self._current_time() >= deadline
        except TypeError as exc:
            raise ValueError("vote deadline timezone does not match service time") from exc
        if expired:
            if vote.kind in {VoteKind.LEADER_TRANSFER, VoteKind.ABANDON}:
                self._restore_vote_phase(run, vote)
                run.revision += 1
                return VoteResult(passed=False, failed=True, pending=False)
            raise ValueError("vote deadline has passed")
        if actor_id in vote.approvals or actor_id in vote.rejections:
            raise ValueError("actor has already voted")
        if not isinstance(approve, bool):
            raise ValueError("approve must be a boolean")

        if approve:
            vote.approvals.add(actor_id)
        else:
            vote.rejections.add(actor_id)
        required_approvals = self._required_approvals(vote)
        remaining_voters = (
            set(vote.eligible_user_ids) - vote.approvals - vote.rejections
        )
        passed = len(vote.approvals) >= required_approvals
        failed = not passed and len(vote.approvals) + len(remaining_voters) < required_approvals

        if passed:
            self._apply_passed_vote(run, vote)
        elif failed:
            self._restore_vote_phase(run, vote)
        run.revision += 1
        return VoteResult(passed=passed, failed=failed, pending=not passed and not failed)

    def begin_abandon_vote(
        self,
        run: MysticDungeonRun,
        actor_id: str,
        deadline: datetime,
    ) -> DungeonVote:
        self._validate_vote_start(run, actor_id, deadline)
        vote = DungeonVote(
            vote_id=f"{run.run_id}:{VoteKind.ABANDON.value}:{run.revision + 1}",
            kind=VoteKind.ABANDON,
            eligible_user_ids=run.member_ids,
            approvals=set(),
            rejections=set(),
            deadline=deadline.isoformat(),
            prior_phase=run.phase,
        )
        run.active_vote = vote
        run.revision += 1
        return vote

    def _validate_vote_start(
        self,
        run: MysticDungeonRun,
        actor_id: str,
        deadline: datetime,
    ) -> None:
        if run.mode is not DungeonMode.TEAM or not 2 <= len(run.members) <= 3:
            raise ValueError("votes require a started two or three member team dungeon")
        if actor_id not in run.members:
            raise PermissionError("actor is not a fixed dungeon member")
        if run.phase in {
            DungeonPhase.CREATING,
            DungeonPhase.LOBBY,
            DungeonPhase.COMPLETED,
            DungeonPhase.FAILED,
            DungeonPhase.ABANDONED,
        }:
            raise ValueError("vote cannot start in the current dungeon phase")
        if run.active_vote is not None:
            raise ValueError("dungeon run already has an active vote")
        if not isinstance(deadline, datetime):
            raise ValueError("vote deadline must be a datetime")
        current = self._current_time()
        try:
            future_deadline = deadline > current
        except TypeError as exc:
            raise ValueError("vote deadline timezone does not match service time") from exc
        if not future_deadline:
            raise ValueError("vote deadline must be in the future")

    def _required_approvals(self, vote: DungeonVote) -> int:
        if vote.kind is VoteKind.LEADER_TRANSFER:
            return len(vote.eligible_user_ids)
        return 2 if len(vote.eligible_user_ids) >= 2 else 1

    def _apply_passed_vote(self, run: MysticDungeonRun, vote: DungeonVote) -> None:
        if vote.kind is VoteKind.LEADER_TRANSFER:
            nominee_id = vote.nominee_id
            if nominee_id is None or nominee_id not in run.members:
                raise ValueError("leader transfer vote has an invalid nominee")
            if vote.prior_phase is None:
                raise ValueError("leader transfer vote is missing its previous dungeon phase")
            run.leader_id = nominee_id
            run.last_leader_action_at = self._current_time().isoformat()
            run.phase = vote.prior_phase
            run.active_vote = None
            return
        if vote.kind is VoteKind.ABANDON:
            run.phase = DungeonPhase.ABANDONED
            run.temporary_rewards_by_user = {}
            run.active_vote = None
            return
        self._restore_vote_phase(run, vote)

    def _restore_vote_phase(self, run: MysticDungeonRun, vote: DungeonVote) -> None:
        if vote.prior_phase is None:
            raise ValueError("vote is missing its previous dungeon phase")
        run.phase = vote.prior_phase
        run.active_vote = None
