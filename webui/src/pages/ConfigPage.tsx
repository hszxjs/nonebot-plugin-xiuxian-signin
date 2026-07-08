import { Plus, RefreshCcw, Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { Badge } from "../components/ui/badge";
import { Button, PrimaryButton } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { api } from "../lib/api";
import type { EquipmentPayload } from "../lib/types";
import {
  asRecord,
  cloneJson,
  finiteNumber,
  hasUnsavedChanges,
  statusLabel,
  type DirtyChangeHandler,
  type SaveState,
  useDirtyFlag,
} from "./pageShared";

type ConfigPayload = { ok: boolean; config: Record<string, unknown> };
type EquipmentMeta = EquipmentPayload["meta"];
type NumberRow = { key: string; value: number | undefined };

const DEFAULT_TIERS = ["凡品", "黄阶", "玄阶", "地阶", "天阶", "仙阶", "仙帝兵"];
const DEFAULT_FISHING_RATE = 0.05;
const DEFAULT_EXTRA_FISHING_RATE = 0.1;

function optionValues(options: string[] | undefined, current?: string) {
  const values = [...(options ?? [])];
  const currentValue = String(current ?? "").trim();
  if (currentValue && !values.includes(currentValue)) {
    values.unshift(currentValue);
  }
  return values;
}

function uniqueValues(values: string[]) {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}

function normalizeConfig(source: Record<string, unknown>) {
  const config = cloneJson(source);
  const mystic = { ...asRecord(config.mystic) };
  if (finiteNumber(mystic.fishing_option_rate) === undefined) {
    mystic.fishing_option_rate = DEFAULT_FISHING_RATE;
  }
  config.mystic = mystic;

  const signin = { ...asRecord(config.signin) };
  if (finiteNumber(signin.extra_fishing_chance_rate) === undefined) {
    signin.extra_fishing_chance_rate = DEFAULT_EXTRA_FISHING_RATE;
  }
  config.signin = signin;

  const beastRealm = { ...asRecord(config.beast_realm) };
  if (finiteNumber(beastRealm.card_pool_copies) === undefined) {
    beastRealm.card_pool_copies = 10;
  }
  config.beast_realm = beastRealm;
  return config;
}

function numberRows(value: unknown): NumberRow[] {
  return Object.entries(asRecord(value)).map(([key, rowValue]) => ({ key, value: finiteNumber(rowValue) }));
}

function rowsToRecord(rows: NumberRow[]) {
  const record: Record<string, number> = {};
  for (const row of rows) {
    const key = row.key.trim();
    if (key && row.value !== undefined) {
      record[key] = row.value;
    }
  }
  return record;
}

function recordSize(value: unknown) {
  return Object.keys(asRecord(value)).length;
}

function mapKeys(value: unknown) {
  return Object.keys(asRecord(value));
}

function realmOptions(meta: EquipmentMeta) {
  return (meta.realms ?? []).map((realm) => ({ label: realm.name, value: String(realm.index) }));
}

function NumberInput({
  disabled,
  max,
  min,
  onChange,
  step,
  value,
}: {
  disabled?: boolean;
  max?: number;
  min?: number;
  onChange: (value: number | undefined) => void;
  step?: number;
  value?: number;
}) {
  function update(valueText: string) {
    if (valueText === "") {
      onChange(undefined);
      return;
    }
    const nextValue = Number(valueText);
    if (Number.isFinite(nextValue)) {
      onChange(nextValue);
    }
  }

  return <Input disabled={disabled} max={max} min={min} onChange={(event) => update(event.target.value)} step={step} type="number" value={value ?? ""} />;
}

function NumberField({
  disabled,
  hint,
  label,
  max,
  min,
  onChange,
  step,
  value,
}: {
  disabled?: boolean;
  hint?: string;
  label: string;
  max?: number;
  min?: number;
  onChange: (value: number | undefined) => void;
  step?: number;
  value?: number;
}) {
  return (
    <label className="grid min-w-0 gap-2 rounded-md border border-border p-3">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium">{label}</div>
        {hint ? <div className="truncate text-xs text-muted-foreground">{hint}</div> : null}
      </div>
      <NumberInput disabled={disabled} max={max} min={min} onChange={onChange} step={step} value={value} />
    </label>
  );
}

function KeyField({
  disabled,
  onChange,
  options,
  value,
}: {
  disabled?: boolean;
  onChange: (value: string) => void;
  options?: string[];
  value: string;
}) {
  const availableOptions = optionValues(options, value);
  if (!availableOptions.length) {
    return <Input disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value} />;
  }
  return (
    <Select disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value}>
      <option value="">未设置</option>
      {availableOptions.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </Select>
  );
}

function NumberMapEditor({
  disabled,
  detail,
  keyLabel,
  keyOptions,
  onChange,
  rows,
  title,
  valueLabel,
}: {
  disabled?: boolean;
  detail: string;
  keyLabel: string;
  keyOptions?: string[];
  onChange: (rows: NumberRow[]) => void;
  rows: NumberRow[];
  title: string;
  valueLabel: string;
}) {
  function setRow(index: number, patch: Partial<NumberRow>) {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  return (
    <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-medium">{title}</h2>
          <div className="mt-1 truncate text-xs text-muted-foreground">{detail}</div>
        </div>
        <Button disabled={disabled} onClick={() => onChange([...rows, { key: "", value: undefined }])}>
          <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>新增</span>
        </Button>
      </div>
      {rows.length ? (
        <div className="grid min-w-0 gap-2">
          <div className="grid grid-cols-[minmax(0,1fr)_160px_44px] gap-2 px-1 text-xs text-muted-foreground">
            <span>{keyLabel}</span>
            <span>{valueLabel}</span>
            <span />
          </div>
          {rows.map((row, index) => (
            <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_160px_44px] gap-2" key={`${title}:${index}`}>
              <KeyField disabled={disabled} onChange={(value) => setRow(index, { key: value })} options={keyOptions} value={row.key} />
              <NumberInput disabled={disabled} min={0} onChange={(value) => setRow(index, { value })} step={0.01} value={row.value} />
              <Button aria-label={`删除${title}${index + 1}`} className="h-9 w-9 px-0" disabled={disabled} onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}>
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState title="暂无配置" detail="点击新增添加一条数值映射。" />
      )}
    </section>
  );
}

function TierRealmEditor({
  disabled,
  meta,
  onChange,
  rows,
}: {
  disabled?: boolean;
  meta: EquipmentMeta;
  onChange: (rows: NumberRow[]) => void;
  rows: NumberRow[];
}) {
  const realms = realmOptions(meta);
  function setRow(index: number, patch: Partial<NumberRow>) {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  return (
    <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-medium">阶级默认境界</h2>
          <div className="mt-1 truncate text-xs text-muted-foreground">用于缺省灵器境界推断</div>
        </div>
        <Button disabled={disabled} onClick={() => onChange([...rows, { key: "", value: undefined }])}>
          <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>新增</span>
        </Button>
      </div>
      <div className="grid min-w-0 gap-2">
        {rows.map((row, index) => (
          <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_220px_44px]" key={`tier-realm:${index}`}>
            <KeyField disabled={disabled} onChange={(value) => setRow(index, { key: value })} options={DEFAULT_TIERS} value={row.key} />
            <Select
              disabled={disabled}
              onChange={(event) => setRow(index, { value: event.target.value === "" ? undefined : Number(event.target.value) })}
              value={row.value === undefined ? "" : String(row.value)}
            >
              <option value="">未设置</option>
              {realms.map((realm) => (
                <option key={realm.value} value={realm.value}>
                  {realm.label}
                </option>
              ))}
            </Select>
            <Button aria-label={`删除阶级默认境界${index + 1}`} className="h-9 w-9 px-0" disabled={disabled} onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}>
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        ))}
        {!rows.length ? <EmptyState title="暂无默认境界" detail="点击新增设置阶级与境界的默认对应关系。" /> : null}
      </div>
    </section>
  );
}

function RealmTierUnlockEditor({
  disabled,
  meta,
  onChange,
  unlocks,
}: {
  disabled?: boolean;
  meta: EquipmentMeta;
  onChange: (unlocks: Record<string, string[]>) => void;
  unlocks: Record<string, unknown>;
}) {
  const normalizedUnlocks = Object.fromEntries(
    Object.entries(unlocks).map(([key, value]) => [key, Array.isArray(value) ? value.map(String) : []]),
  );
  const tierOptions = uniqueValues([...(meta.tiers ?? []), ...DEFAULT_TIERS, ...Object.values(normalizedUnlocks).flatMap((value) => value)]);
  const realms = meta.realms?.length
    ? meta.realms
    : Object.keys(normalizedUnlocks).map((key) => ({ index: Number(key), name: `境界 ${key}` })).filter((realm) => Number.isFinite(realm.index));

  function selectedTiers(realmIndex: number) {
    return normalizedUnlocks[String(realmIndex)] ?? [];
  }

  function toggleTier(realmIndex: number, tier: string) {
    const current = new Set(selectedTiers(realmIndex));
    if (current.has(tier)) {
      current.delete(tier);
    } else {
      current.add(tier);
    }
    onChange({ ...normalizedUnlocks, [String(realmIndex)]: [...current] });
  }

  return (
    <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
      <div className="min-w-0">
        <h2 className="truncate text-base font-medium">境界阶级解锁</h2>
        <div className="mt-1 truncate text-xs text-muted-foreground">控制每个境界可自然产出的灵器阶级</div>
      </div>
      {realms.length ? (
        <div className="grid min-w-0 gap-3 xl:grid-cols-2">
          {realms.map((realm) => {
            const selected = new Set(selectedTiers(realm.index));
            return (
              <div className="grid min-w-0 gap-2 rounded-md border border-border p-3" key={realm.index}>
                <div className="flex min-w-0 items-center justify-between gap-2">
                  <div className="truncate text-sm font-medium">{realm.name}</div>
                  <Badge className="shrink-0">{selected.size} 项</Badge>
                </div>
                <div className="grid min-w-0 gap-2 sm:grid-cols-2">
                  {tierOptions.map((tier) => (
                    <label className="flex min-w-0 items-center gap-2 rounded-md border border-border p-2 text-sm" key={`${realm.index}:${tier}`}>
                      <input checked={selected.has(tier)} disabled={disabled} onChange={() => toggleTier(realm.index, tier)} type="checkbox" />
                      <span className="min-w-0 truncate">{tier}</span>
                    </label>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <EmptyState title="暂无境界" detail="后端未返回境界信息，暂无法编辑解锁表。" />
      )}
    </section>
  );
}

function ManagedSummary({ config }: { config: Record<string, unknown> }) {
  const beastRealm = asRecord(config.beast_realm);
  const equipmentRules = asRecord(config.equipment_rules);
  const mystic = asRecord(config.mystic);
  const knownKeys = new Set(["version", "equipment_rules", "mystic", "signin", "item_overrides", "beast_realm"]);
  const extraKeys = Object.keys(config).filter((key) => !knownKeys.has(key));

  const summaries = [
    { label: "物品覆盖", value: recordSize(config.item_overrides), detail: "物品图鉴专页管理" },
    { label: "御兽卡牌覆盖", value: recordSize(beastRealm.card_overrides), detail: "御兽卡牌专页管理" },
    { label: "灵器掉落境界", value: recordSize(equipmentRules.artifact_drop_pools), detail: "灵器规则专页管理" },
    { label: "秘境类别权重", value: recordSize(mystic.category_weights), detail: "秘境掉落专页管理" },
    { label: "秘境固定掉落", value: recordSize(mystic.drop_overrides), detail: "秘境掉落专页管理" },
  ];

  return (
    <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
      <div className="min-w-0">
        <h2 className="truncate text-base font-medium">专页配置概览</h2>
        <div className="mt-1 truncate text-xs text-muted-foreground">这些内容会随保存原样保留</div>
      </div>
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 2xl:grid-cols-5">
        {summaries.map((item) => (
          <div className="grid min-w-0 gap-1 rounded-md border border-border p-3" key={item.label}>
            <div className="truncate text-xs text-muted-foreground">{item.label}</div>
            <div className="text-xl font-semibold">{item.value}</div>
            <div className="truncate text-xs text-muted-foreground">{item.detail}</div>
          </div>
        ))}
      </div>
      {extraKeys.length ? (
        <div className="flex min-w-0 flex-wrap gap-2">
          {extraKeys.map((key) => (
            <Badge className="max-w-full truncate" key={key}>
              {key}
            </Badge>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function validateRows(rows: NumberRow[], label: string) {
  const seen = new Set<string>();
  for (const [index, row] of rows.entries()) {
    const key = row.key.trim();
    if (!key) {
      return `${label}第 ${index + 1} 行名称不能为空。`;
    }
    if (seen.has(key)) {
      return `${label}存在重复名称：${key}`;
    }
    seen.add(key);
    if (row.value === undefined || !Number.isFinite(row.value) || row.value < 0) {
      return `${label}第 ${index + 1} 行数值必须是非负数字。`;
    }
  }
  return "";
}

function validateConfig(config: Record<string, unknown>, meta: EquipmentMeta) {
  const equipmentRules = asRecord(config.equipment_rules);
  const beastRealm = asRecord(config.beast_realm);
  const mystic = asRecord(config.mystic);
  const signin = asRecord(config.signin);

  const version = finiteNumber(config.version);
  if (version === undefined || version < 0 || !Number.isInteger(version)) {
    return "配置版本必须是非负整数。";
  }
  const cardPoolCopies = finiteNumber(beastRealm.card_pool_copies);
  if (cardPoolCopies === undefined || cardPoolCopies < 0 || !Number.isInteger(cardPoolCopies)) {
    return "御兽默认卡池数量必须是非负整数。";
  }
  const fishingRate = finiteNumber(mystic.fishing_option_rate);
  if (fishingRate === undefined || fishingRate < 0 || fishingRate > 1) {
    return "秘境垂钓选项概率必须是 0 到 1 之间的数字。";
  }
  const extraFishingRate = finiteNumber(signin.extra_fishing_chance_rate);
  if (extraFishingRate === undefined || extraFishingRate < 0 || extraFishingRate > 1) {
    return "签到额外垂钓概率必须是 0 到 1 之间的数字。";
  }
  const upgradeRate = finiteNumber(equipmentRules.artifact_immortal_upgrade_rate);
  if (upgradeRate === undefined || upgradeRate < 0 || upgradeRate > 1) {
    return "仙阶升级概率必须是 0 到 1 之间的数字。";
  }

  return (
    validateRows(numberRows(equipmentRules.tier_default_realm), "阶级默认境界") ||
    validateRows(numberRows(equipmentRules.artifact_power_base), "灵器类别基础战力") ||
    validateRows(numberRows(equipmentRules.artifact_realm_power_base), "灵器境界基础战力") ||
    validateRows(numberRows(equipmentRules.artifact_tier_power_ratio), "灵器阶级倍率") ||
    validateRows(numberRows(equipmentRules.artifact_grade_ratio), "灵器品相倍率") ||
    validateRealmIndexes(numberRows(equipmentRules.tier_default_realm), meta)
  );
}

function validateRealmIndexes(rows: NumberRow[], meta: EquipmentMeta) {
  const validIndexes = new Set((meta.realms ?? []).map((realm) => realm.index));
  if (!validIndexes.size) {
    return "";
  }
  for (const row of rows) {
    if (row.value !== undefined && !validIndexes.has(row.value)) {
      return `${row.key} 默认境界不存在：${row.value}`;
    }
  }
  return "";
}

export function ConfigPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [originalConfig, setOriginalConfig] = useState<Record<string, unknown>>({});
  const [meta, setMeta] = useState<EquipmentMeta>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState("");
  const loadRequestId = useRef(0);
  const saveRequestId = useRef(0);

  const dirty = hasUnsavedChanges(config, originalConfig);
  const saving = saveState === "saving";
  const equipmentRules = asRecord(config.equipment_rules);
  const beastRealm = asRecord(config.beast_realm);
  const mystic = asRecord(config.mystic);
  const signin = asRecord(config.signin);
  const tierOptions = useMemo(() => uniqueValues([...(meta.tiers ?? []), ...DEFAULT_TIERS, ...mapKeys(equipmentRules.tier_default_realm)]), [equipmentRules.tier_default_realm, meta.tiers]);
  const gradeOptions = useMemo(() => uniqueValues([...(meta.grades ?? []), ...mapKeys(equipmentRules.artifact_grade_ratio)]), [equipmentRules.artifact_grade_ratio, meta.grades]);
  const realmIndexOptions = useMemo(() => {
    const labels = (meta.realms ?? []).map((realm) => String(realm.index));
    return uniqueValues([...labels, ...mapKeys(equipmentRules.artifact_realm_power_base)]);
  }, [equipmentRules.artifact_realm_power_base, meta.realms]);
  useDirtyFlag(dirty, onDirtyChange);

  function updateConfig(updater: (draft: Record<string, unknown>) => void) {
    setConfig((current) => {
      const next = cloneJson(current);
      updater(next);
      return next;
    });
    setSaveState("idle");
    setSaveError("");
  }

  function setNested(path: string[], value: unknown) {
    updateConfig((draft) => {
      let target = draft;
      for (const key of path.slice(0, -1)) {
        target[key] = { ...asRecord(target[key]) };
        target = target[key] as Record<string, unknown>;
      }
      target[path[path.length - 1]] = value;
    });
  }

  async function loadConfig() {
    const requestId = loadRequestId.current + 1;
    loadRequestId.current = requestId;
    setLoading(true);
    setError("");
    try {
      const [configPayload, equipmentPayload] = await Promise.all([api<ConfigPayload>("/api/config"), api<EquipmentPayload>("/api/equipment-rules")]);
      if (loadRequestId.current !== requestId) {
        return false;
      }
      const normalized = normalizeConfig(asRecord(configPayload.config));
      setConfig(cloneJson(normalized));
      setOriginalConfig(cloneJson(normalized));
      setMeta(equipmentPayload.meta ?? {});
      return true;
    } catch (loadError) {
      if (loadRequestId.current === requestId) {
        setError(loadError instanceof Error ? loadError.message : "高级配置载入失败");
      }
      return false;
    } finally {
      if (loadRequestId.current === requestId) {
        setLoading(false);
      }
    }
  }

  async function reloadConfig() {
    if (saving) {
      return;
    }
    await loadConfig();
    setSaveState("idle");
    setSaveError("");
  }

  async function saveConfig() {
    const validationError = validateConfig(config, meta);
    if (validationError) {
      setSaveState("error");
      setSaveError(validationError);
      return;
    }
    const requestId = saveRequestId.current + 1;
    saveRequestId.current = requestId;
    setSaveState("saving");
    setSaveError("");
    try {
      await api<ConfigPayload>("/api/config", { body: JSON.stringify(config, null, 2), method: "PUT" });
      if (saveRequestId.current !== requestId) {
        return;
      }
      const reloaded = await loadConfig();
      if (saveRequestId.current === requestId) {
        if (reloaded) {
          setSaveState("saved");
        } else {
          setSaveState("error");
          setSaveError("配置已保存，但重新载入失败。请重试载入。");
        }
      }
    } catch (saveErrorValue) {
      if (saveRequestId.current === requestId) {
        setSaveState("error");
        setSaveError(saveErrorValue instanceof Error ? saveErrorValue.message : "保存失败");
      }
    }
  }

  useEffect(() => {
    void loadConfig();
  }, []);

  return (
    <div className="grid min-w-0 gap-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold tracking-normal">高级配置</h1>
          <p className="mt-1 truncate text-sm text-muted-foreground">结构化编辑全局概率、战力倍率与解锁规则</p>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge className="shrink-0">{statusLabel(dirty, saveState)}</Badge>
          <Button disabled={saving} onClick={() => void reloadConfig()}>
            <RefreshCcw className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>重载</span>
          </Button>
          <PrimaryButton disabled={!dirty || saving} onClick={() => void saveConfig()}>
            <Save className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>保存</span>
          </PrimaryButton>
        </div>
      </div>

      {saveError ? <div className="text-sm text-destructive">{saveError}</div> : null}
      {loading ? <LoadingState label="正在载入高级配置" /> : null}
      {error ? <ErrorState message={error} onRetry={() => void loadConfig()} /> : null}
      {!loading && !error ? (
        <div className="grid min-w-0 gap-4">
          <Card className="grid min-w-0 gap-4 rounded-md p-4">
            <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
              <h2 className="truncate text-base font-medium">全局参数</h2>
              <div className="grid min-w-0 gap-3 md:grid-cols-2 xl:grid-cols-3">
                <NumberField disabled={saving} label="配置版本" min={0} onChange={(value) => setNested(["version"], value)} step={1} value={finiteNumber(config.version)} />
                <NumberField
                  disabled={saving}
                  hint="影响新牌池默认复制数"
                  label="御兽默认卡池数量"
                  min={0}
                  onChange={(value) => setNested(["beast_realm", "card_pool_copies"], value)}
                  step={1}
                  value={finiteNumber(beastRealm.card_pool_copies)}
                />
                <NumberField
                  disabled={saving}
                  hint="灵器掉落时升级为仙阶的概率"
                  label="仙阶升级概率"
                  max={1}
                  min={0}
                  onChange={(value) => setNested(["equipment_rules", "artifact_immortal_upgrade_rate"], value)}
                  step={0.01}
                  value={finiteNumber(equipmentRules.artifact_immortal_upgrade_rate)}
                />
              </div>
            </section>

            <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
              <h2 className="truncate text-base font-medium">概率设置</h2>
              <div className="grid min-w-0 gap-3 md:grid-cols-2">
                <NumberField
                  disabled={saving}
                  hint="秘境中刷新增加一次垂钓次数选项"
                  label="秘境垂钓选项概率"
                  max={1}
                  min={0}
                  onChange={(value) => setNested(["mystic", "fishing_option_rate"], value)}
                  step={0.01}
                  value={finiteNumber(mystic.fishing_option_rate)}
                />
                <NumberField
                  disabled={saving}
                  hint="每日签到额外增加一次垂钓次数"
                  label="签到额外垂钓概率"
                  max={1}
                  min={0}
                  onChange={(value) => setNested(["signin", "extra_fishing_chance_rate"], value)}
                  step={0.01}
                  value={finiteNumber(signin.extra_fishing_chance_rate)}
                />
              </div>
            </section>
          </Card>

          <Card className="grid min-w-0 gap-4 rounded-md p-4">
            <TierRealmEditor
              disabled={saving}
              meta={meta}
              onChange={(rows) => setNested(["equipment_rules", "tier_default_realm"], rowsToRecord(rows))}
              rows={numberRows(equipmentRules.tier_default_realm)}
            />
            <RealmTierUnlockEditor
              disabled={saving}
              meta={meta}
              onChange={(nextUnlocks) => setNested(["equipment_rules", "realm_tier_unlocks"], nextUnlocks)}
              unlocks={asRecord(equipmentRules.realm_tier_unlocks)}
            />
          </Card>

          <Card className="grid min-w-0 gap-4 rounded-md p-4">
            <NumberMapEditor
              detail="不同灵器类别的基础战力"
              disabled={saving}
              keyLabel="类别"
              onChange={(rows) => setNested(["equipment_rules", "artifact_power_base"], rowsToRecord(rows))}
              rows={numberRows(equipmentRules.artifact_power_base)}
              title="灵器类别基础战力"
              valueLabel="基础值"
            />
            <NumberMapEditor
              detail="不同境界灵器的基础战力"
              disabled={saving}
              keyLabel="境界序号"
              keyOptions={realmIndexOptions}
              onChange={(rows) => setNested(["equipment_rules", "artifact_realm_power_base"], rowsToRecord(rows))}
              rows={numberRows(equipmentRules.artifact_realm_power_base)}
              title="灵器境界基础战力"
              valueLabel="基础值"
            />
            <NumberMapEditor
              detail="不同阶级对战力的倍率"
              disabled={saving}
              keyLabel="阶级"
              keyOptions={tierOptions}
              onChange={(rows) => setNested(["equipment_rules", "artifact_tier_power_ratio"], rowsToRecord(rows))}
              rows={numberRows(equipmentRules.artifact_tier_power_ratio)}
              title="灵器阶级倍率"
              valueLabel="倍率"
            />
            <NumberMapEditor
              detail="不同品相对战力的倍率"
              disabled={saving}
              keyLabel="品相"
              keyOptions={gradeOptions}
              onChange={(rows) => setNested(["equipment_rules", "artifact_grade_ratio"], rowsToRecord(rows))}
              rows={numberRows(equipmentRules.artifact_grade_ratio)}
              title="灵器品相倍率"
              valueLabel="倍率"
            />
          </Card>

          <ManagedSummary config={config} />
        </div>
      ) : null}
    </div>
  );
}



