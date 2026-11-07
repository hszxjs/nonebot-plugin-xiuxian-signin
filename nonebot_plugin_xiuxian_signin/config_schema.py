"""后台配置契约：Pydantic schema、结构版本号与迁移链（R-07）。

设计取向是「写严读宽」：

* **写入侧严格**——未知键、类型错误、越界一律整份拒绝，返回带字段路径的问题
  列表。配置写坏不会立刻报错，而是到运行时才表现为「钓鱼概率诡异」或「掉落
  全空」，事后极难回溯到某次保存，所以必须当场拦下。
* **读取侧宽容**——``load_config`` 任何时候都要能把配置读出来（补默认、裁掉
  未知键、跑迁移），绝不因为文件不合规让后台打不开；不合规只在保存时暴露。

``version`` 是**结构版本**（写死在代码里），``revision`` 是**修订号**（每次成功
写入自增，用于发现「隔夜旧标签页按了保存」这类静默覆盖）。
"""

from __future__ import annotations

from typing import Annotated, Any, get_args, get_origin

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

CURRENT_CONFIG_VERSION = 1

# 返回给前端的最大问题条数，避免一次贴出上百行把界面撑爆。
MAX_REPORTED_ISSUES = 20

# 已退役的 mystic 配置键：a4a85d9 起秘境令牌改为签到概率掉落 / 每日任务固定 1 枚，
# 这四个键不再有任何读取方。保留在默认值里会让运营以为可以调节，故彻底移除，
# 旧配置文件在迁移时裁掉。
RETIRED_MYSTIC_CONFIG_KEYS = (
    "signin_normal_token_count",
    "signin_high_risk_token_count",
    "daily_task_normal_token_count",
    "daily_task_high_risk_token_count",
)


def _reject_bool(value: Any) -> Any:
    """bool 是 int 的子类，不拦住的话 ``true`` 会被静默当成 1。"""
    if isinstance(value, bool):
        raise ValueError("不能填 true/false，请填数字")
    return value


NonNegativeInt = Annotated[int, BeforeValidator(_reject_bool), Field(ge=0)]
PositiveInt = Annotated[int, BeforeValidator(_reject_bool), Field(ge=1)]
NonNegativeFloat = Annotated[float, BeforeValidator(_reject_bool), Field(ge=0.0)]
Rate = Annotated[float, BeforeValidator(_reject_bool), Field(ge=0.0, le=1.0)]


class _StrictModel(BaseModel):
    """未知键一律拒绝：拼写错误（``fishing_option_rat``）必须当场暴露。"""

    model_config = ConfigDict(extra="forbid")


class DropPoolEntry(_StrictModel):
    """装备掉落池条目。消费方按需取值，缺字段等价于空串。"""

    tier_min: str = ""
    tier_max: str = ""
    grade: str = ""
    attribute: str = ""
    name: str = ""
    weight: NonNegativeInt = 1


class EquipmentRules(_StrictModel):
    realm_tier_unlocks: dict[str, list[str]]
    tier_default_realm: dict[str, NonNegativeInt]
    artifact_drop_pools: dict[str, list[DropPoolEntry]]
    artifact_power_base: dict[str, NonNegativeInt]
    artifact_realm_power_base: dict[str, NonNegativeInt]
    artifact_tier_power_ratio: dict[str, NonNegativeFloat]
    artifact_grade_ratio: dict[str, NonNegativeFloat]
    artifact_immortal_upgrade_rate: Rate

    @field_validator("tier_default_realm")
    @classmethod
    def _check_realm_index(cls, value: dict[str, int]) -> dict[str, int]:
        from .domain import REALMS

        limit = len(REALMS) - 1
        for tier, index in value.items():
            if index > limit:
                raise ValueError(f"{tier} 的境界下标 {index} 超出范围 0~{limit}")
        return value


class MapSizeRule(_StrictModel):
    minimum_boss_realm_index: NonNegativeInt
    node_count: PositiveInt


class CategoryWeight(_StrictModel):
    category: str
    weight: NonNegativeInt


class MysticConfig(_StrictModel):
    map_size_rules: list[MapSizeRule]
    min_map_size: PositiveInt
    max_map_size: PositiveInt
    normal_node_weights: dict[str, Rate]
    high_risk_node_weights: dict[str, Rate]
    normal_branch_density: Rate
    high_risk_branch_density: Rate
    high_risk_loop_count: NonNegativeInt
    consecutive_combat_limit: NonNegativeInt
    ordinary_monster_hp_multiplier: NonNegativeFloat
    boss_hp_multiplier: NonNegativeFloat
    reward_multiplier: NonNegativeFloat
    damage_growth_per_ten_rounds: NonNegativeFloat
    encounter_response_seconds: NonNegativeInt
    battle_prepare_seconds: NonNegativeInt
    player_action_seconds: NonNegativeInt
    boss_vote_seconds: NonNegativeInt
    leader_inactive_seconds: NonNegativeInt
    leader_transfer_vote_seconds: NonNegativeInt
    rescue_wait_seconds: NonNegativeInt
    enabled_types: list[str]
    enabled_high_risk_types: list[str]
    # 三种形状历史上都出现过：新版 [{category, weight}]、旧版 {类别: 权重}、
    # 更早的扁平 {类别: 权重}。消费方 _category_weight_pairs 逐层兼容，
    # 配置原样保留、不做归一，否则一次保存就会改写运营手里的旧数据。
    category_weights: dict[str, list[CategoryWeight] | dict[str, Rate] | Rate]
    # 旧配置里可能是字典（运行时忽略），新版是奖励列表。
    drop_overrides: dict[str, list[dict[str, Any]] | dict[str, Any]]
    fishing_option_rate: Rate

    @model_validator(mode="after")
    def _check_map_size_range(self) -> MysticConfig:
        if self.min_map_size > self.max_map_size:
            raise ValueError("min_map_size 不能大于 max_map_size")
        return self


class SigninConfig(_StrictModel):
    extra_fishing_chance_rate: Rate


class BeastRealmConfig(_StrictModel):
    card_pool_copies: NonNegativeInt
    card_overrides: dict[str, dict[str, Any]]


class AdminConfig(_StrictModel):
    version: int
    revision: NonNegativeInt = 0
    equipment_rules: EquipmentRules
    mystic: MysticConfig
    signin: SigninConfig
    # 两个自由字典的键是物品名 / 卡牌 id，值直接合入领域对象，故不做字段建模。
    item_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    beast_realm: BeastRealmConfig


class ConfigValidationError(ValueError):
    """配置校验失败，``issues`` 可直接序列化返回给前端。"""

    def __init__(self, issues: list[dict[str, str]], total: int) -> None:
        self.issues = issues
        self.total = total
        summary = "；".join(f"{item['path']}: {item['message']}" for item in issues[:3])
        super().__init__(summary or "配置校验未通过")


class ConfigConflictError(ValueError):
    """提交的 revision 落后于磁盘（多个标签页，或隔夜未刷新的页面）。"""

    def __init__(self, current_revision: int) -> None:
        self.current_revision = current_revision
        super().__init__(f"配置已在别处被修改（当前修订号 {current_revision}），请刷新后重试")


class ConfigVersionError(ValueError):
    """提交的是旧结构的配置，直接落盘会把新结构字段清掉。"""

    def __init__(self, submitted: Any) -> None:
        self.submitted = submitted
        super().__init__(f"配置结构版本不符（提交 {submitted}，当前 {CURRENT_CONFIG_VERSION}），请刷新页面后重试")


def validate_config(data: dict[str, Any]) -> dict[str, Any]:
    """校验并规范化整份配置；失败抛 :class:`ConfigValidationError`。"""
    try:
        model = AdminConfig.model_validate(data)
    except ValidationError as exc:
        issues = _format_issues(exc)
        raise ConfigValidationError(issues, len(exc.errors())) from exc
    return model.model_dump(mode="json")


_ERROR_TEXT: dict[str, str] = {
    "missing": "缺少必填项",
    "extra_forbidden": "未知字段（可能是拼写错误或已退役的键）",
    "greater_than_equal": "不能小于 {ge}",
    "greater_than": "必须大于 {gt}",
    "less_than_equal": "不能大于 {le}",
    "less_than": "必须小于 {lt}",
    "int_type": "必须是整数",
    "int_parsing": "必须是整数",
    "int_from_float": "必须是整数（不能带小数）",
    "float_type": "必须是数字",
    "float_parsing": "必须是数字",
    "bool_type": "必须是布尔值",
    "string_type": "必须是字符串",
    "list_type": "必须是列表",
    "dict_type": "必须是对象",
    "model_type": "必须是对象",
    "value_error": "取值不合法",
}


def _format_issues(exc: ValidationError) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for error in exc.errors()[:MAX_REPORTED_ISSUES]:
        path = ".".join(str(part) for part in error.get("loc", ())) or "(根)"
        template = _ERROR_TEXT.get(str(error.get("type")), str(error.get("msg") or "取值不合法"))
        context = error.get("ctx") or {}
        # 自定义校验器（model_validator / field_validator）抛的 ValueError，
        # 真正的说明在 ctx["error"] 里，直接透出比「取值不合法」有用得多。
        custom = context.get("error")
        if str(error.get("type")) == "value_error" and custom is not None:
            message = str(custom)
        else:
            try:
                message = template.format(**context)
            except (KeyError, IndexError, ValueError):
                message = str(error.get("msg") or template)
        issues.append({"path": path, "message": message})
    return issues


def migrate_config(data: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """按 ``version`` 逐级升级配置，并裁掉已退役的键。

    迁移链现在是空的（结构仍是 v1），但入口先立在这里：以后改结构只需往
    ``MIGRATIONS`` 里加一个 ``from_version`` 的处理函数，读取路径无需再动。
    """
    notes: list[str] = []
    version = data.get("version")
    if not isinstance(version, int):
        version = CURRENT_CONFIG_VERSION
    while version < CURRENT_CONFIG_VERSION:
        step = MIGRATIONS.get(version)
        if step is None:
            notes.append(f"缺少 v{version}→v{version + 1} 迁移，按当前结构处理")
            break
        data = step(data)
        version += 1
        data["version"] = version
        notes.append(f"配置已迁移 v{version - 1}→v{version}")

    mystic = data.get("mystic")
    if isinstance(mystic, dict):
        for key in RETIRED_MYSTIC_CONFIG_KEYS:
            if key in mystic:
                mystic.pop(key)
                notes.append(f"移除已退役配置项 mystic.{key}")
    return data, notes


# from_version -> 升级函数。加新版本时在这里登记，迁移即可自动串联。
MIGRATIONS: dict[int, Any] = {}


def prune_unknown_config(data: dict[str, Any]) -> dict[str, Any]:
    """按 schema 裁掉未定义的键（读取侧，绝不抛错）。

    ``load_config`` 会把文件内容深合并进默认值，文件里残留的历史键会原样出现在
    GET 响应里，前端再整体回写。写入侧既然 ``extra="forbid"``，读取侧就必须裁，
    否则线上那份旧配置会导致「一保存就 400」。
    """
    if not isinstance(data, dict):
        return data
    pruned = _prune_model(data, AdminConfig)
    return pruned if isinstance(pruned, dict) else data


def _prune_model(value: Any, model: type[BaseModel]) -> Any:
    if not isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        if name not in value:
            continue
        result[name] = _prune_value(value[name], field.annotation)
    return result


def _prune_value(value: Any, annotation: Any) -> Any:
    if hasattr(annotation, "__metadata__"):  # Annotated[X, ...]
        annotation = annotation.__origin__
    origin = get_origin(annotation)
    if origin is list:
        args = get_args(annotation)
        if not args or not isinstance(value, list):
            return value
        return [_prune_value(item, args[0]) for item in value]
    if origin is dict:
        args = get_args(annotation)
        if len(args) != 2 or not isinstance(value, dict):
            return value
        return {key: _prune_value(item, args[1]) for key, item in value.items()}
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _prune_model(value, annotation)
    return value
