import { Plus, RefreshCcw, Save, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { Badge } from "../components/ui/badge";
import { Button, PrimaryButton } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { api } from "../lib/api";
import type { AdminItem, ItemPayload, MysticPayload } from "../lib/types";

type SaveState = "idle" | "saving" | "saved" | "error";
type ConfigPayload = { ok: boolean; config: Record<string, unknown> };
type MysticState = MysticPayload["mystic"];

type WeightRow = Record<string, unknown> & {
  category?: string;
  weight?: number;
};

type DropRow = Record<string, unknown> & {
  category?: string;
  tier?: string;
  grade?: string;
  name?: string;
  weight?: number;
};

const DEFAULT_FISHING_RATE = 0.05;
const DEFAULT_EXTRA_FISHING_RATE = 0.1;

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function cloneMystic(value: MysticState): MysticState {
  return JSON.parse(JSON.stringify(value)) as MysticState;
}

function finiteNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function stringList(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item)).filter(Boolean) : [];
}

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

function rateFromConfig(config: Record<string, unknown>, payloadMystic: MysticState, key: "fishing_option_rate" | "extra_fishing_chance_rate") {
  if (key === "fishing_option_rate") {
    return finiteNumber(asRecord(config.mystic).fishing_option_rate) ?? finiteNumber(payloadMystic.fishing_option_rate) ?? DEFAULT_FISHING_RATE;
  }
  return finiteNumber(asRecord(config.signin).extra_fishing_chance_rate) ?? finiteNumber(payloadMystic.extra_fishing_chance_rate) ?? DEFAULT_EXTRA_FISHING_RATE;
}

function normalizeMystic(payloadMystic: MysticState, config: Record<string, unknown>): MysticState {
  const configMystic = asRecord(config.mystic);
  return {
    ...payloadMystic,
    enabled_types: stringList(configMystic.enabled_types).length ? stringList(configMystic.enabled_types) : payloadMystic.enabled_types ?? [],
    enabled_high_risk_types: stringList(configMystic.enabled_high_risk_types).length ? stringList(configMystic.enabled_high_risk_types) : payloadMystic.enabled_high_risk_types ?? [],
    category_weights: payloadMystic.category_weights ?? {},
    drop_overrides: payloadMystic.drop_overrides ?? {},
    fishing_option_rate: rateFromConfig(config, payloadMystic, "fishing_option_rate"),
    extra_fishing_chance_rate: rateFromConfig(config, payloadMystic, "extra_fishing_chance_rate"),
  };
}

function weightRows(source: MysticState, typeName: string): WeightRow[] {
  const rows = source.category_weights?.[typeName];
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows.map((row) => {
    const record = asRecord(row);
    const next: Record<string, unknown> = { ...record };
    if (record.category !== undefined && record.category !== null) {
      next.category = String(record.category);
    }
    return next as WeightRow;
  });
}

function dropRows(source: MysticState, typeName: string): DropRow[] {
  const rows = source.drop_overrides?.[typeName];
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows.map((row) => {
    const record = asRecord(row);
    const next: Record<string, unknown> = { ...record };
    for (const key of ["category", "tier", "grade", "name"] as const) {
      if (record[key] !== undefined && record[key] !== null) {
        next[key] = String(record[key]);
      }
    }
    return next as DropRow;
  });
}

function serializeWeightRow(row: WeightRow) {
  const next: Record<string, unknown> = { ...row };
  if (typeof row.category === "string") {
    next.category = row.category.trim();
  }
  if (row.weight === undefined) {
    next.weight = undefined;
  } else if (Number.isFinite(row.weight)) {
    next.weight = row.weight;
  }
  return next;
}

function serializeDropRow(row: DropRow) {
  const next: Record<string, unknown> = { ...row };
  for (const key of ["category", "tier", "grade", "name"] as const) {
    const value = row[key];
    if (typeof value === "string") {
      next[key] = value.trim();
    }
  }
  if (row.weight === undefined) {
    next.weight = undefined;
  } else if (Number.isFinite(row.weight)) {
    next.weight = row.weight;
  }
  return next;
}

function setWeightRows(mystic: MysticState, typeName: string, rows: WeightRow[]): MysticState {
  return {
    ...mystic,
    category_weights: {
      ...(mystic.category_weights ?? {}),
      [typeName]: rows.map(serializeWeightRow),
    },
  };
}

function setDropRows(mystic: MysticState, typeName: string, rows: DropRow[]): MysticState {
  return {
    ...mystic,
    drop_overrides: {
      ...(mystic.drop_overrides ?? {}),
      [typeName]: rows.map(serializeDropRow),
    },
  };
}

function sectionTypes(mystic: MysticState) {
  return uniqueValues([
    ...(mystic.enabled_types ?? []),
    ...(mystic.enabled_high_risk_types ?? []),
    ...Object.keys(mystic.category_weights ?? {}),
    ...Object.keys(mystic.drop_overrides ?? {}),
    ...(mystic.category_weights?.default || mystic.drop_overrides?.default ? ["default"] : []),
  ]);
}

function statusLabel(dirty: boolean, saveState: SaveState) {
  if (saveState === "saving") {
    return "保存中";
  }
  if (saveState === "saved") {
    return "已保存";
  }
  return dirty ? "未保存" : "同步";
}

function validateProbability(value: number | undefined, label: string) {
  if (value === undefined) {
    return `${label}不能为空。`;
  }
  if (!Number.isFinite(value) || value < 0 || value > 1) {
    return `${label}必须是 0 到 1 之间的数字。`;
  }
  return "";
}

function validateWeightMap(rowsByType: Record<string, Array<Record<string, unknown>>> | undefined, label: string) {
  for (const [typeName, rows] of Object.entries(rowsByType ?? {})) {
    if (!Array.isArray(rows)) {
      continue;
    }
    for (const [rowIndex, row] of rows.entries()) {
      const weight = asRecord(row).weight;
      if (weight !== undefined && (typeof weight !== "number" || !Number.isFinite(weight) || weight < 0)) {
        return `${typeName} ${label}第 ${rowIndex + 1} 行权重必须是非负数字。`;
      }
    }
  }
  return "";
}

function SelectOrInput({ disabled, onChange, options, value }: { disabled?: boolean; onChange: (value: string) => void; options?: string[]; value?: string }) {
  const availableOptions = optionValues(options, value);
  if (!availableOptions.length) {
    return <Input disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value ?? ""} />;
  }
  return (
    <Select disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value ?? ""}>
      <option value="">未设置</option>
      {availableOptions.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </Select>
  );
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

function CheckboxGrid({ disabled, label, onChange, options, values }: { disabled?: boolean; label: string; onChange: (values: string[]) => void; options?: string[]; values?: string[] }) {
  const selected = new Set(values ?? []);
  function toggle(option: string) {
    const next = new Set(selected);
    if (next.has(option)) {
      next.delete(option);
    } else {
      next.add(option);
    }
    onChange([...next]);
  }

  return (
    <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
      <div className="min-w-0">
        <h2 className="truncate text-base font-medium">{label}</h2>
        <div className="mt-1 truncate text-xs text-muted-foreground">已启用 {selected.size} 项</div>
      </div>
      {options?.length ? (
        <div className="grid min-w-0 gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {options.map((option) => (
            <label className="flex min-w-0 items-center gap-2 rounded-md border border-border p-3 text-sm" key={option}>
              <input checked={selected.has(option)} disabled={disabled} onChange={() => toggle(option)} type="checkbox" />
              <span className="min-w-0 truncate">{option}</span>
            </label>
          ))}
        </div>
      ) : (
        <EmptyState title="暂无类型" detail="后端未返回可切换的类型列表。" />
      )}
    </section>
  );
}

function RateEditor({ disabled, mystic, onChange }: { disabled?: boolean; mystic: MysticState; onChange: (mystic: MysticState) => void }) {
  return (
    <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
      <h2 className="truncate text-base font-medium">概率设置</h2>
      <div className="grid min-w-0 gap-3 md:grid-cols-2">
        <label className="grid min-w-0 gap-2 rounded-md border border-border p-3">
          <span className="truncate text-sm font-medium">秘境选项概率</span>
          <NumberInput disabled={disabled} max={1} min={0} onChange={(value) => onChange({ ...mystic, fishing_option_rate: value })} step={0.01} value={mystic.fishing_option_rate} />
        </label>
        <label className="grid min-w-0 gap-2 rounded-md border border-border p-3">
          <span className="truncate text-sm font-medium">额外钓鱼概率</span>
          <NumberInput disabled={disabled} max={1} min={0} onChange={(value) => onChange({ ...mystic, extra_fishing_chance_rate: value })} step={0.01} value={mystic.extra_fishing_chance_rate} />
        </label>
      </div>
    </section>
  );
}

function WeightRowsEditor({ categories, disabled, onChange, rows }: { categories?: string[]; disabled?: boolean; onChange: (rows: WeightRow[]) => void; rows: WeightRow[] }) {
  function setRow(index: number, patch: Partial<WeightRow>) {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  return (
    <div className="grid min-w-0 gap-2">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <div className="truncate text-sm font-medium">类别权重</div>
        <Button disabled={disabled} onClick={() => onChange([...rows, {}])}>
          <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>新增</span>
        </Button>
      </div>
      {rows.length ? (
        <div className="min-w-0 overflow-x-auto">
          <div className="grid min-w-[420px] gap-2">
            <div className="grid grid-cols-[minmax(0,1fr)_120px_44px] gap-2 px-1 text-xs text-muted-foreground">
              <span>类别</span>
              <span>权重</span>
              <span />
            </div>
            {rows.map((row, index) => (
              <div className="grid grid-cols-[minmax(0,1fr)_120px_44px] gap-2" key={index}>
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { category: value })} options={categories} value={row.category} />
                <NumberInput disabled={disabled} onChange={(value) => setRow(index, { weight: value })} value={finiteNumber(row.weight)} />
                <Button aria-label={`删除类别权重${index + 1}`} className="h-9 w-9 px-0" disabled={disabled} onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState title="暂无类别权重" detail="点击新增配置该类型的掉落类别权重。" />
      )}
    </div>
  );
}

function DropRowsEditor({ disabled, itemNames, mystic, onChange, rows }: { disabled?: boolean; itemNames: string[]; mystic: MysticState; onChange: (rows: DropRow[]) => void; rows: DropRow[] }) {
  function setRow(index: number, patch: Partial<DropRow>) {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  return (
    <div className="grid min-w-0 gap-2">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <div className="truncate text-sm font-medium">固定掉落</div>
        <Button disabled={disabled} onClick={() => onChange([...rows, {}])}>
          <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>新增</span>
        </Button>
      </div>
      {rows.length ? (
        <div className="min-w-0 overflow-x-auto">
          <div className="grid min-w-[820px] gap-2">
            <div className="grid grid-cols-[1fr_1fr_1fr_1.5fr_120px_44px] gap-2 px-1 text-xs text-muted-foreground">
              <span>类别</span>
              <span>阶级</span>
              <span>品质</span>
              <span>物品</span>
              <span>权重</span>
              <span />
            </div>
            {rows.map((row, index) => (
              <div className="grid grid-cols-[1fr_1fr_1fr_1.5fr_120px_44px] gap-2" key={index}>
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { category: value })} options={mystic.categories} value={row.category} />
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { tier: value })} options={mystic.tiers} value={row.tier} />
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { grade: value })} options={mystic.grades} value={row.grade} />
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { name: value })} options={itemNames} value={row.name} />
                <NumberInput disabled={disabled} onChange={(value) => setRow(index, { weight: value })} value={finiteNumber(row.weight)} />
                <Button aria-label={`删除固定掉落${index + 1}`} className="h-9 w-9 px-0" disabled={disabled} onClick={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState title="暂无固定掉落" detail="点击新增配置该类型的固定掉落池。" />
      )}
    </div>
  );
}

function TypeSection({ disabled, itemNames, mystic, onChange, typeName }: { disabled?: boolean; itemNames: string[]; mystic: MysticState; onChange: (mystic: MysticState) => void; typeName: string }) {
  const weights = weightRows(mystic, typeName);
  const drops = dropRows(mystic, typeName);
  return (
    <section className="grid min-w-0 gap-4 rounded-md border border-border bg-card p-4">
      <div className="min-w-0">
        <h2 className="truncate text-base font-medium">{typeName}</h2>
        <div className="mt-1 truncate text-xs text-muted-foreground">{weights.length} 条类别权重 · {drops.length} 条固定掉落</div>
      </div>
      <WeightRowsEditor categories={mystic.categories} disabled={disabled} onChange={(rows) => onChange(setWeightRows(mystic, typeName, rows))} rows={weights} />
      <DropRowsEditor disabled={disabled} itemNames={itemNames} mystic={mystic} onChange={(rows) => onChange(setDropRows(mystic, typeName, rows))} rows={drops} />
    </section>
  );
}

export function MysticPage() {
  const [mystic, setMystic] = useState<MysticState>({});
  const [originalMystic, setOriginalMystic] = useState<MysticState>({});
  const [items, setItems] = useState<AdminItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState("");
  const loadRequestId = useRef(0);
  const saveRequestId = useRef(0);

  const dirty = JSON.stringify(mystic) !== JSON.stringify(originalMystic);
  const saving = saveState === "saving";
  const itemNames = useMemo(() => uniqueValues(items.map((item) => item.name)), [items]);
  const sections = sectionTypes(mystic);

  function updateMystic(nextMystic: MysticState) {
    setMystic(nextMystic);
    setSaveState("idle");
    setSaveError("");
  }

  async function loadMystic() {
    const requestId = loadRequestId.current + 1;
    loadRequestId.current = requestId;
    setLoading(true);
    setError("");
    try {
      const [mysticPayload, itemPayload, configPayload] = await Promise.all([api<MysticPayload>("/api/mystic"), api<ItemPayload>("/api/items"), api<ConfigPayload>("/api/config")]);
      if (loadRequestId.current !== requestId) {
        return false;
      }
      const nextMystic = normalizeMystic(mysticPayload.mystic ?? {}, asRecord(configPayload.config));
      setMystic(cloneMystic(nextMystic));
      setOriginalMystic(cloneMystic(nextMystic));
      setItems(itemPayload.items ?? []);
      return true;
    } catch (loadError) {
      if (loadRequestId.current === requestId) {
        setError(loadError instanceof Error ? loadError.message : "秘境掉落载入失败");
      }
      return false;
    } finally {
      if (loadRequestId.current === requestId) {
        setLoading(false);
      }
    }
  }

  async function reloadMystic() {
    if (saving) {
      return;
    }
    await loadMystic();
    setSaveState("idle");
    setSaveError("");
  }

  async function saveMystic() {
    const fishingError = validateProbability(mystic.fishing_option_rate, "秘境选项概率");
    const extraFishingError = validateProbability(mystic.extra_fishing_chance_rate, "额外钓鱼概率");
    const categoryWeightError = validateWeightMap(mystic.category_weights, "类别权重");
    const dropWeightError = validateWeightMap(mystic.drop_overrides, "固定掉落");
    if (fishingError || extraFishingError || categoryWeightError || dropWeightError) {
      setSaveState("error");
      setSaveError(fishingError || extraFishingError || categoryWeightError || dropWeightError);
      return;
    }

    const requestId = saveRequestId.current + 1;
    saveRequestId.current = requestId;
    setSaveState("saving");
    setSaveError("");
    try {
      const payload = await api<ConfigPayload>("/api/config");
      const config = asRecord(payload.config);
      const configMystic = { ...asRecord(config.mystic) };
      configMystic.enabled_types = mystic.enabled_types ?? [];
      configMystic.enabled_high_risk_types = mystic.enabled_high_risk_types ?? [];
      configMystic.category_weights = mystic.category_weights ?? {};
      configMystic.drop_overrides = mystic.drop_overrides ?? {};
      configMystic.fishing_option_rate = Number(mystic.fishing_option_rate);
      config.mystic = configMystic;
      const signin = { ...asRecord(config.signin) };
      signin.extra_fishing_chance_rate = Number(mystic.extra_fishing_chance_rate);
      config.signin = signin;
      await api<ConfigPayload>("/api/config", { body: JSON.stringify(config, null, 2), method: "PUT" });
      if (saveRequestId.current !== requestId) {
        return;
      }
      const reloaded = await loadMystic();
      if (saveRequestId.current === requestId) {
        if (reloaded) {
          setSaveState("saved");
        } else {
          setSaveState("error");
          setSaveError("配置已保存，但秘境掉落重新载入失败。请重试载入。");
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
    void loadMystic();
  }, []);

  return (
    <div className="grid min-w-0 gap-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold tracking-normal">秘境掉落</h1>
          <p className="mt-1 truncate text-sm text-muted-foreground">配置秘境类型、概率、类别权重与固定掉落</p>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge className="shrink-0">{statusLabel(dirty, saveState)}</Badge>
          <Button disabled={saving} onClick={() => void reloadMystic()}>
            <RefreshCcw className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>重载</span>
          </Button>
          <PrimaryButton disabled={!dirty || saving} onClick={() => void saveMystic()}>
            <Save className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>保存</span>
          </PrimaryButton>
        </div>
      </div>
      {saveError ? <div className="text-sm text-destructive">{saveError}</div> : null}
      {loading ? <LoadingState label="正在载入秘境掉落" /> : null}
      {error ? <ErrorState message={error} onRetry={() => void loadMystic()} /> : null}
      {!loading && !error ? (
        <div className="grid min-w-0 gap-4">
          <Card className="grid min-w-0 gap-4 rounded-md p-4">
            <RateEditor disabled={saving} mystic={mystic} onChange={updateMystic} />
            <div className="grid min-w-0 gap-4 xl:grid-cols-2">
              <CheckboxGrid disabled={saving} label="普通秘境类型" onChange={(values) => updateMystic({ ...mystic, enabled_types: values })} options={mystic.types} values={mystic.enabled_types} />
              <CheckboxGrid disabled={saving} label="高风险秘境类型" onChange={(values) => updateMystic({ ...mystic, enabled_high_risk_types: values })} options={mystic.high_risk_types} values={mystic.enabled_high_risk_types} />
            </div>
          </Card>
          {sections.length ? (
            <Card className="grid min-w-0 gap-4 rounded-md p-4">
              {sections.map((typeName) => (
                <TypeSection disabled={saving} itemNames={itemNames} key={typeName} mystic={mystic} onChange={updateMystic} typeName={typeName} />
              ))}
            </Card>
          ) : (
            <EmptyState title="暂无秘境规则" detail="启用类型或保留已有规则后可编辑掉落配置。" />
          )}
        </div>
      ) : null}
    </div>
  );
}

