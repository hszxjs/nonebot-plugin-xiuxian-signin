import type { PlayerMeta } from "../lib/types";

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonRecord = Record<string, JsonValue>;

export type SelectOption = {
  value: string;
  label: string;
};

export type ValueKind = "string" | "number" | "boolean" | "object" | "array";

const FALLBACK_REALMS = [
  "炼气境",
  "筑基境",
  "结晶境",
  "金丹境",
  "元婴境",
  "化神境",
  "炼虚境",
  "合体境",
  "大乘境",
  "渡劫境",
  "真仙境",
  "金仙境",
  "太乙境",
  "大罗境",
  "仙王境",
  "仙帝境",
];

const FALLBACK_ATTRIBUTES = ["金", "木", "水", "火", "土", "雷", "冰", "风", "光", "暗", "先天道体", "混沌"];
const FALLBACK_TIERS = ["凡品", "黄阶", "玄阶", "地阶", "天阶", "仙阶", "仙帝兵", "变异灵根"];
const FALLBACK_GRADES = ["下品", "中品", "上品", "极品"];
const FALLBACK_CULTIVATION_ROUTES = ["剑修", "术修", "炼丹师", "阵法师", "炼器师"];
const FALLBACK_QUALITY_TITLES = [
  "普通筑基",
  "良好筑基",
  "优秀筑基",
  "无瑕道基",
  "天道筑基",
  "凡品",
  "下品",
  "中品",
  "上品",
  "极品",
  "完美",
];

const ROOT_TEMPLATE: JsonRecord = {
  tier: "凡品",
  tier_rank: 0,
  grade: "中品",
  grade_rank: 1,
  attribute: "金",
  purity: 72,
  sources: ["金"],
  mutated: false,
  trait: "",
  source_purities: {},
};

const FIELD_LABELS: Record<string, string> = {
  user_id: "玩家 ID",
  root: "主灵根",
  acquired_roots: "后天灵根",
  extra_roots: "额外灵根",
  sign_count: "签到次数",
  total_exp: "总修为",
  realm_index: "境界",
  realm_exp: "当前境界修为",
  last_sign_date: "上次签到日期",
  last_encounter_date: "上次奇遇日期",
  fishing_chances: "垂钓次数",
  pending_fishing: "待领取垂钓",
  pending_exp: "待领取修为",
  spirit_liquid: "灵液",
  bottleneck_days: "瓶颈天数",
  bottleneck_realm_index: "瓶颈境界",
  last_bottleneck_date: "上次瓶颈日期",
  rewards: "奖励",
  equipped_artifact: "已装备法器",
  equipped_artifacts: "已装备法器槽位",
  equipped_talisman: "已装备符箓",
  equipped_method: "已装备功法",
  equipped_array: "已装备阵法",
  equipped_puppet: "已装备傀儡",
  planted_spirit_plant: "种植灵植",
  array_proficiency: "阵法熟练度",
  array_layers: "阵法层数",
  spirit_stones: "灵石",
  foundation_type: "筑基品质",
  realm_marks: "境界品相",
  mystic_realm: "秘境",
  cultivation_lock_until: "修炼锁定至",
  cultivation_route: "修炼路线",
  evil_cultivator: "邪修",
  faction_identity: "势力身份",
  identity_sign_days: "身份签到天数",
  daily_tasks: "每日任务",
  dual_cultivation_date: "双修日期",
  dual_cultivation_used: "双修次数",
  last_tianji_mystic_date: "上次天机秘境日期",
  combat_race: "战斗种族",
  physique: "体质",
  special_abilities: "特殊能力",
  method_layers: "功法层数",
  method_proficiency: "功法熟练度",
  life_artifact: "本命灵器",
  immortal_seeds: "仙种",
  equipped_immortal_seed: "已装备仙种",
  immortal_conversion_days: "仙化天数",
  last_immortal_conversion_date: "上次仙化日期",
  last_failed_mystic_realm: "上次失败秘境",
  mystic_boss_successes: "秘境首领通关",
  mystic_boss_daily_date: "首领每日日期",
  mystic_boss_daily_attempts: "首领每日次数",
  mystic_boss_daily_bonus: "首领每日加成",
  mystic_boss_week_key: "首领周键",
  mystic_boss_week_attempts: "首领每周次数",
  mystic_boss_week_claimed: "首领周奖励",
  tier: "品阶",
  tier_rank: "品阶序号",
  grade: "品质",
  grade_rank: "品质序号",
  attribute: "属性",
  purity: "纯度",
  sources: "来源属性",
  mutated: "变异",
  trait: "特质",
  source_purities: "来源纯度",
  name: "名称",
  category: "类别",
  count: "数量",
  level: "等级",
  rank: "序号",
  realm: "境界名称",
  required_realm: "所需境界",
  required_realm_index: "所需境界",
  required_attribute: "所需属性",
  min_realm_index: "最低境界",
  boss_realm: "首领境界",
};

const TOP_LEVEL_ORDER = [
  "user_id",
  "realm_index",
  "realm_exp",
  "total_exp",
  "spirit_stones",
  "spirit_liquid",
  "sign_count",
  "last_sign_date",
  "cultivation_route",
  "evil_cultivator",
  "root",
  "extra_roots",
  "acquired_roots",
  "foundation_type",
  "realm_marks",
];

export const PLAYER_SECTIONS = [
  {
    title: "基础状态",
    keys: [
      "user_id",
      "realm_index",
      "realm_exp",
      "total_exp",
      "spirit_stones",
      "spirit_liquid",
      "sign_count",
      "fishing_chances",
      "pending_fishing",
      "pending_exp",
      "cultivation_route",
      "evil_cultivator",
      "cultivation_lock_until",
    ],
  },
  {
    title: "日期记录",
    keys: [
      "last_sign_date",
      "last_encounter_date",
      "last_bottleneck_date",
      "dual_cultivation_date",
      "last_tianji_mystic_date",
      "last_immortal_conversion_date",
      "mystic_boss_daily_date",
      "mystic_boss_week_key",
    ],
  },
  {
    title: "灵根与突破",
    keys: ["root", "extra_roots", "acquired_roots", "foundation_type", "realm_marks", "bottleneck_days", "bottleneck_realm_index"],
  },
  {
    title: "装备与养成",
    keys: [
      "equipped_artifact",
      "equipped_artifacts",
      "equipped_talisman",
      "equipped_method",
      "equipped_array",
      "equipped_puppet",
      "planted_spirit_plant",
      "array_proficiency",
      "array_layers",
      "method_layers",
      "method_proficiency",
      "life_artifact",
    ],
  },
  {
    title: "身份与任务",
    keys: [
      "faction_identity",
      "identity_sign_days",
      "daily_tasks",
      "dual_cultivation_used",
      "combat_race",
      "physique",
      "special_abilities",
    ],
  },
  {
    title: "秘境与首领",
    keys: [
      "mystic_realm",
      "last_failed_mystic_realm",
      "mystic_boss_successes",
      "mystic_boss_daily_attempts",
      "mystic_boss_daily_bonus",
      "mystic_boss_week_attempts",
      "mystic_boss_week_claimed",
    ],
  },
  {
    title: "奖励与仙种",
    keys: ["rewards", "immortal_seeds", "equipped_immortal_seed", "immortal_conversion_days"],
  },
] as const;

export function fieldLabel(key: string) {
  return FIELD_LABELS[key] ?? key.replace(/_/g, " ");
}

export function orderedKeys(record: JsonRecord, preferredKeys: readonly string[] = TOP_LEVEL_ORDER) {
  const keys = Object.keys(record);
  return keys.sort((left, right) => {
    const leftIndex = preferredKeys.indexOf(left);
    const rightIndex = preferredKeys.indexOf(right);
    if (leftIndex >= 0 || rightIndex >= 0) {
      return (leftIndex >= 0 ? leftIndex : 9999) - (rightIndex >= 0 ? rightIndex : 9999);
    }
    return left.localeCompare(right, "zh-CN");
  });
}

export function sanitizeJsonValue(value: unknown): JsonValue {
  if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map((item) => sanitizeJsonValue(item));
  }
  if (typeof value === "object" && value) {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, sanitizeJsonValue(item)]),
    ) as JsonRecord;
  }
  return null;
}

export function sanitizeRecord(value: unknown): JsonRecord {
  const sanitized = sanitizeJsonValue(value);
  return isJsonRecord(sanitized) ? sanitized : {};
}

export function isJsonRecord(value: JsonValue): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function valueKind(value: JsonValue): ValueKind {
  if (Array.isArray(value)) {
    return "array";
  }
  if (isJsonRecord(value)) {
    return "object";
  }
  if (typeof value === "number") {
    return "number";
  }
  if (typeof value === "boolean") {
    return "boolean";
  }
  return "string";
}

export function createValue(kind: ValueKind, key = "", path: readonly string[] = []): JsonValue {
  if (kind === "number") {
    return 0;
  }
  if (kind === "boolean") {
    return false;
  }
  if (kind === "array") {
    return [];
  }
  if (kind === "object") {
    return defaultObjectForField(key, path);
  }
  return "";
}

export function defaultObjectForField(key: string, path: readonly string[] = []): JsonRecord {
  const lowerKey = key.toLowerCase();
  const joinedPath = [...path, key].join(".");
  if (lowerKey.includes("root") || joinedPath.includes("root")) {
    return cloneRecord(ROOT_TEMPLATE);
  }
  if (lowerKey.includes("task")) {
    return { done: false, count: 0 };
  }
  if (lowerKey.includes("realm")) {
    return { name: "", realm_index: 0 };
  }
  return { name: "" };
}

export function defaultArrayItem(key: string, path: readonly string[] = []): JsonValue {
  const lowerKey = key.toLowerCase();
  if (lowerKey.includes("root")) {
    return defaultObjectForField("root", path);
  }
  if (lowerKey.includes("claimed") || lowerKey.includes("rank")) {
    return 0;
  }
  if (lowerKey.includes("abilities") || lowerKey.includes("sources")) {
    return "";
  }
  return { name: "" };
}

export function defaultValueForKey(key: string, path: readonly string[] = []): JsonValue {
  if (isArrayField(key)) {
    return [];
  }
  if (isObjectField(key)) {
    return defaultObjectForField(key, path);
  }
  if (isBooleanField(key)) {
    return false;
  }
  if (isNumberField(key)) {
    return 0;
  }
  return "";
}

export function optionsForField(key: string, path: readonly string[], meta?: PlayerMeta): SelectOption[] {
  const normalized = normalizedMeta(meta);
  const lowerKey = key.toLowerCase();
  const parent = path.length > 1 ? path[path.length - 2].toLowerCase() : "";
  const ancestors = path.slice(0, -1).map((part) => part.toLowerCase());

  if (lowerKey === "realm_index" || lowerKey.endsWith("_realm_index") || lowerKey === "min_realm_index") {
    return normalized.realms.map((realm) => ({
      value: String(realm.index),
      label: `${realm.index} ${realm.name}`,
    }));
  }
  if (lowerKey === "cultivation_route") {
    return normalized.cultivationRoutes.map(simpleOption);
  }
  if (
    lowerKey === "attribute" ||
    lowerKey.endsWith("_attribute") ||
    lowerKey === "required_attribute" ||
    lowerKey === "combat_race"
  ) {
    return normalized.attributes.map((value) => ({
      value,
      label: normalized.attributeLabels[value] ? `${value} ${normalized.attributeLabels[value]}` : value,
    }));
  }
  if (lowerKey === "tier" || lowerKey.endsWith("_tier")) {
    return normalized.tiers.map(simpleOption);
  }
  if (lowerKey === "grade" || lowerKey.endsWith("_grade")) {
    return normalized.grades.map(simpleOption);
  }
  if (
    lowerKey.includes("quality") ||
    lowerKey.includes("品相") ||
    lowerKey.includes("品质") ||
    lowerKey === "foundation_type" ||
    parent === "realm_marks" ||
    ancestors.includes("realm_marks")
  ) {
    return normalized.qualityTitles.map(simpleOption);
  }
  if (lowerKey === "category" && normalized.categories.length) {
    return normalized.categories.map(simpleOption);
  }
  if (lowerKey === "type" && normalized.mysticTypes.length) {
    return normalized.mysticTypes.map(simpleOption);
  }
  return [];
}

export function isDateField(key: string) {
  const lowerKey = key.toLowerCase();
  return lowerKey.endsWith("_date") || lowerKey.includes("date") || lowerKey.endsWith("_until");
}

export function isNumberField(key: string) {
  const lowerKey = key.toLowerCase();
  return (
    lowerKey.endsWith("_index") ||
    lowerKey.endsWith("_rank") ||
    lowerKey.endsWith("_count") ||
    lowerKey.endsWith("_days") ||
    lowerKey.endsWith("_attempts") ||
    lowerKey.endsWith("_bonus") ||
    lowerKey.endsWith("_chances") ||
    lowerKey.endsWith("_exp") ||
    lowerKey.endsWith("_stones") ||
    lowerKey.endsWith("_liquid") ||
    lowerKey === "purity" ||
    lowerKey === "level" ||
    lowerKey === "rank" ||
    lowerKey === "count"
  );
}

export function isBooleanField(key: string) {
  const lowerKey = key.toLowerCase();
  return lowerKey.startsWith("is_") || lowerKey.startsWith("has_") || lowerKey === "mutated" || lowerKey === "evil_cultivator" || lowerKey === "done";
}

export function parseFieldValue(key: string, currentValue: JsonValue, rawValue: string): JsonValue {
  if (rawValue === "") {
    return currentValue === null ? null : "";
  }
  if (typeof currentValue === "number" || isNumberField(key)) {
    const next = Number(rawValue);
    return Number.isFinite(next) ? next : 0;
  }
  return rawValue;
}

export function cloneRecord(record: JsonRecord): JsonRecord {
  return JSON.parse(JSON.stringify(record)) as JsonRecord;
}

export function ensureCurrentOption(options: SelectOption[], value: JsonValue) {
  const text = String(value ?? "");
  if (!text || options.some((option) => option.value === text)) {
    return options;
  }
  return [{ value: text, label: text }, ...options];
}

function normalizedMeta(meta?: PlayerMeta) {
  const qualityTitles = [
    ...(meta?.quality_titles ?? []),
    ...(meta?.foundation_quality_titles ?? []),
    ...Object.values(meta?.realm_quality_titles ?? {}).flat(),
    ...FALLBACK_QUALITY_TITLES,
  ];
  return {
    realms:
      meta?.realms && meta.realms.length > 0 ? meta.realms : FALLBACK_REALMS.map((name, index) => ({ index, name })),
    attributes: unique([...(meta?.attributes ?? []), ...FALLBACK_ATTRIBUTES]),
    attributeLabels: meta?.attribute_labels ?? {},
    tiers: unique([...(meta?.tiers ?? []), ...FALLBACK_TIERS]),
    grades: unique([...(meta?.grades ?? []), ...FALLBACK_GRADES]),
    categories: unique(meta?.categories ?? []),
    mysticTypes: unique(meta?.mystic_types ?? []),
    cultivationRoutes: unique([...(meta?.cultivation_routes ?? []), ...FALLBACK_CULTIVATION_ROUTES]),
    qualityTitles: unique(qualityTitles),
  };
}

function isArrayField(key: string) {
  const lowerKey = key.toLowerCase();
  return (
    lowerKey.endsWith("s") ||
    lowerKey.includes("roots") ||
    lowerKey.includes("rewards") ||
    lowerKey.includes("abilities") ||
    lowerKey.includes("sources") ||
    lowerKey.includes("claimed")
  );
}

function isObjectField(key: string) {
  const lowerKey = key.toLowerCase();
  return lowerKey.includes("root") || lowerKey.includes("artifact") || lowerKey.includes("realm") || lowerKey.includes("task");
}

function unique(values: string[]) {
  return Array.from(new Set(values.map((value) => String(value).trim()).filter(Boolean)));
}

function simpleOption(value: string) {
  return { value, label: value };
}
