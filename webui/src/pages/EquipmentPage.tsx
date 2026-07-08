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
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";

type SaveState = "idle" | "saving" | "saved" | "error";
type ConfigPayload = { ok: boolean; config: Record<string, unknown> };
type EquipmentMeta = EquipmentPayload["meta"];

type EquipmentRow = Record<string, unknown> & {
  tier_min?: string;
  tier_max?: string;
  grade?: string;
  attribute?: string;
  name?: string;
  weight?: number;
};

const TEXT_KEYS: Array<Exclude<keyof EquipmentRow, "weight">> = ["tier_min", "tier_max", "grade", "attribute", "name"];

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function cloneRecord(value: Record<string, unknown>) {
  return JSON.parse(JSON.stringify(value)) as Record<string, unknown>;
}

function optionValues(options: string[] | undefined, current?: string) {
  const values = [...(options ?? [])];
  const currentValue = String(current ?? "").trim();
  if (currentValue && !values.includes(currentValue)) {
    values.unshift(currentValue);
  }
  return values;
}

function finiteNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function rowsFromRules(rules: Record<string, unknown>, realmIndex: number): EquipmentRow[] {
  const rows = asRecord(rules.artifact_drop_pools)[String(realmIndex)];
  if (!Array.isArray(rows)) {
    return [];
  }
  return rows.map((row) => {
    const source = asRecord(row);
    const next: Record<string, unknown> = { ...source };
    for (const key of TEXT_KEYS) {
      if (source[key] !== undefined && source[key] !== null) {
        next[key] = String(source[key]);
      }
    }
    if (source.weight !== undefined) {
      next.weight = source.weight;
    }
    return next as EquipmentRow;
  });
}

function serializeRow(row: EquipmentRow) {
  const next: Record<string, unknown> = { ...row };
  for (const key of TEXT_KEYS) {
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

function writeRowsToRules(rules: Record<string, unknown>, realmIndex: number, rows: EquipmentRow[]) {
  const nextRules = cloneRecord(rules);
  const pools = { ...asRecord(nextRules.artifact_drop_pools) };
  pools[String(realmIndex)] = rows.map(serializeRow);
  nextRules.artifact_drop_pools = pools;
  return nextRules;
}

function validateEquipmentWeights(rules: Record<string, unknown>) {
  const pools = asRecord(rules.artifact_drop_pools);
  for (const [realmIndex, rows] of Object.entries(pools)) {
    if (!Array.isArray(rows)) {
      continue;
    }
    for (const [rowIndex, row] of rows.entries()) {
      const weight = asRecord(row).weight;
      if (weight !== undefined && (typeof weight !== "number" || !Number.isFinite(weight) || weight < 0)) {
        return `境界 ${realmIndex} 第 ${rowIndex + 1} 行权重必须是非负数字。`;
      }
    }
  }
  return "";
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

function NumberInput({ disabled, onChange, value }: { disabled?: boolean; onChange: (value: number | undefined) => void; value?: number }) {
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

  return <Input disabled={disabled} onChange={(event) => update(event.target.value)} type="number" value={value ?? ""} />;
}

function RealmTable({
  disabled,
  meta,
  onRowsChange,
  realm,
  rows,
}: {
  disabled?: boolean;
  meta: EquipmentMeta;
  onRowsChange: (rows: EquipmentRow[]) => void;
  realm: { index: number; name: string };
  rows: EquipmentRow[];
}) {
  const artifactOptions = useMemo(() => {
    const scoped = (meta.artifacts ?? []).filter((artifact) => artifact.realm_index === realm.index).map((artifact) => artifact.name);
    return scoped.length ? scoped : (meta.artifacts ?? []).map((artifact) => artifact.name);
  }, [meta.artifacts, realm.index]);

  function setRow(index: number, patch: Partial<EquipmentRow>) {
    onRowsChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  return (
    <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-base font-medium">{realm.name}</h2>
          <div className="mt-1 truncate text-xs text-muted-foreground">境界序号 {realm.index} · {rows.length} 条规则</div>
        </div>
        <Button disabled={disabled} onClick={() => onRowsChange([...rows, {}])}>
          <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>新增</span>
        </Button>
      </div>
      {rows.length ? (
        <div className="min-w-0 overflow-x-auto">
          <div className="grid min-w-[900px] gap-2">
            <div className="grid grid-cols-[1fr_1fr_1fr_1fr_1.4fr_120px_44px] gap-2 px-1 text-xs text-muted-foreground">
              <span>最低阶级</span>
              <span>最高阶级</span>
              <span>品质</span>
              <span>灵根</span>
              <span>灵器</span>
              <span>权重</span>
              <span />
            </div>
            {rows.map((row, index) => (
              <div className="grid grid-cols-[1fr_1fr_1fr_1fr_1.4fr_120px_44px] gap-2" key={`${realm.index}:${index}`}>
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { tier_min: value })} options={meta.tiers} value={row.tier_min} />
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { tier_max: value })} options={meta.tiers} value={row.tier_max} />
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { grade: value })} options={meta.grades} value={row.grade} />
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { attribute: value })} options={meta.attributes} value={row.attribute} />
                <SelectOrInput disabled={disabled} onChange={(value) => setRow(index, { name: value })} options={artifactOptions} value={row.name} />
                <NumberInput disabled={disabled} onChange={(value) => setRow(index, { weight: value })} value={finiteNumber(row.weight)} />
                <Button aria-label={`删除${realm.name}规则${index + 1}`} className="h-9 w-9 px-0" disabled={disabled} onClick={() => onRowsChange(rows.filter((_, rowIndex) => rowIndex !== index))}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <EmptyState title="暂无规则" detail="点击新增为该境界配置灵器掉落池。" />
      )}
    </section>
  );
}

export function EquipmentPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [rules, setRules] = useState<Record<string, unknown>>({});
  const [originalRules, setOriginalRules] = useState<Record<string, unknown>>({});
  const [meta, setMeta] = useState<EquipmentMeta>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState("");
  const loadRequestId = useRef(0);
  const saveRequestId = useRef(0);

  const realms = meta.realms ?? [];
  const dirty = JSON.stringify(rules) !== JSON.stringify(originalRules);
  const saving = saveState === "saving";
  useDirtyFlag(dirty, onDirtyChange);

  async function loadEquipment() {
    const requestId = loadRequestId.current + 1;
    loadRequestId.current = requestId;
    setLoading(true);
    setError("");
    try {
      const payload = await api<EquipmentPayload>("/api/equipment-rules");
      if (loadRequestId.current !== requestId) {
        return false;
      }
      const nextRules = payload.rules ?? {};
      setRules(cloneRecord(nextRules));
      setOriginalRules(cloneRecord(nextRules));
      setMeta(payload.meta ?? {});
      return true;
    } catch (loadError) {
      if (loadRequestId.current === requestId) {
        setError(loadError instanceof Error ? loadError.message : "灵器规则载入失败");
      }
      return false;
    } finally {
      if (loadRequestId.current === requestId) {
        setLoading(false);
      }
    }
  }

  async function reloadEquipment() {
    if (saving) {
      return;
    }
    await loadEquipment();
    setSaveState("idle");
    setSaveError("");
  }

  async function saveEquipment() {
    const weightError = validateEquipmentWeights(rules);
    if (weightError) {
      setSaveState("error");
      setSaveError(weightError);
      return;
    }

    const requestId = saveRequestId.current + 1;
    saveRequestId.current = requestId;
    setSaveState("saving");
    setSaveError("");
    try {
      const payload = await api<ConfigPayload>("/api/config");
      const config = asRecord(payload.config);
      config.equipment_rules = cloneRecord(rules);
      await api<ConfigPayload>("/api/config", { body: JSON.stringify(config, null, 2), method: "PUT" });
      if (saveRequestId.current !== requestId) {
        return;
      }
      const reloaded = await loadEquipment();
      if (saveRequestId.current === requestId) {
        if (reloaded) {
          setSaveState("saved");
        } else {
          setSaveState("error");
          setSaveError("配置已保存，但灵器规则重新载入失败。请重试载入。");
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
    void loadEquipment();
  }, []);

  return (
    <div className="grid min-w-0 gap-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold tracking-normal">灵器规则</h1>
          <p className="mt-1 truncate text-sm text-muted-foreground">按境界编辑灵器掉落池</p>
        </div>
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <Badge className="shrink-0">{statusLabel(dirty, saveState)}</Badge>
          <Button disabled={saving} onClick={() => void reloadEquipment()}>
            <RefreshCcw className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>重载</span>
          </Button>
          <PrimaryButton disabled={!dirty || saving} onClick={() => void saveEquipment()}>
            <Save className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>保存</span>
          </PrimaryButton>
        </div>
      </div>
      {saveError ? <div className="text-sm text-destructive">{saveError}</div> : null}
      {loading ? <LoadingState label="正在载入灵器规则" /> : null}
      {error ? <ErrorState message={error} onRetry={() => void loadEquipment()} /> : null}
      {!loading && !error && !realms.length ? <EmptyState title="暂无境界" detail="后端未返回可编辑的境界列表。" /> : null}
      {!loading && !error && realms.length ? (
        <Card className="grid min-w-0 gap-4 rounded-md p-4">
          {realms.map((realm) => (
            <RealmTable
              disabled={saving}
              key={realm.index}
              meta={meta}
              onRowsChange={(rows) => {
                setRules(writeRowsToRules(rules, realm.index, rows));
                setSaveState("idle");
                setSaveError("");
              }}
              realm={realm}
              rows={rowsFromRules(rules, realm.index)}
            />
          ))}
        </Card>
      ) : null}
    </div>
  );
}
