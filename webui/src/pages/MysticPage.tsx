import { DeleteOutlined, PlusOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { Button, Card, Checkbox, Flex, InputNumber, Popconfirm, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { api } from "../lib/api";
import type { AdminItem, ItemPayload, MysticPayload } from "../lib/types";
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";

const { Text, Title } = Typography;

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

function statusColor(dirty: boolean, saveState: SaveState) {
  if (saveState === "saving") {
    return "processing";
  }
  if (saveState === "saved") {
    return "success";
  }
  if (saveState === "error") {
    return "error";
  }
  return dirty ? "warning" : "default";
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

function selectOptions(options?: string[], current?: string) {
  return optionValues(options, current).map((value) => ({ label: value, value }));
}

function RateEditor({ disabled, mystic, onChange }: { disabled?: boolean; mystic: MysticState; onChange: (mystic: MysticState) => void }) {
  return (
    <Card size="small" title="概率设置">
      <div className="form-grid form-grid-two">
        <div>
          <Text type="secondary">秘境选项概率</Text>
          <InputNumber disabled={disabled} max={1} min={0} onChange={(value) => onChange({ ...mystic, fishing_option_rate: value ?? undefined })} step={0.01} value={mystic.fishing_option_rate} />
        </div>
        <div>
          <Text type="secondary">额外钓鱼概率</Text>
          <InputNumber disabled={disabled} max={1} min={0} onChange={(value) => onChange({ ...mystic, extra_fishing_chance_rate: value ?? undefined })} step={0.01} value={mystic.extra_fishing_chance_rate} />
        </div>
      </div>
    </Card>
  );
}

function TypeToggles({ disabled, mystic, onChange }: { disabled?: boolean; mystic: MysticState; onChange: (mystic: MysticState) => void }) {
  return (
    <div className="form-grid form-grid-two">
      <Card size="small" title={`普通秘境类型 · 已启用 ${(mystic.enabled_types ?? []).length} 项`}>
        <Checkbox.Group disabled={disabled} onChange={(values) => onChange({ ...mystic, enabled_types: values.map(String) })} options={mystic.types ?? []} value={mystic.enabled_types ?? []} />
      </Card>
      <Card size="small" title={`高风险秘境类型 · 已启用 ${(mystic.enabled_high_risk_types ?? []).length} 项`}>
        <Checkbox.Group disabled={disabled} onChange={(values) => onChange({ ...mystic, enabled_high_risk_types: values.map(String) })} options={mystic.high_risk_types ?? []} value={mystic.enabled_high_risk_types ?? []} />
      </Card>
    </div>
  );
}

function WeightRowsEditor({ categories, disabled, onChange, rows }: { categories?: string[]; disabled?: boolean; onChange: (rows: WeightRow[]) => void; rows: WeightRow[] }) {
  function setRow(index: number, patch: Partial<WeightRow>) {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  const columns: ColumnsType<WeightRow> = [
    { title: "类别", render: (_value, row, index) => <Select allowClear disabled={disabled} onChange={(value) => setRow(index, { category: value ?? "" })} options={selectOptions(categories, row.category)} value={row.category || undefined} /> },
    { title: "权重", width: 140, render: (_value, row, index) => <InputNumber disabled={disabled} min={0} onChange={(value) => setRow(index, { weight: value ?? undefined })} value={finiteNumber(row.weight)} /> },
    { title: "操作", width: 80, render: (_value, _row, index) => <Popconfirm disabled={disabled} onConfirm={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))} title="删除类别权重？"><Button disabled={disabled} icon={<DeleteOutlined />} /></Popconfirm> },
  ];

  return (
    <Card extra={<Button disabled={disabled} icon={<PlusOutlined />} onClick={() => onChange([...rows, {}])}>新增</Button>} size="small" title="类别权重">
      <Table<WeightRow> columns={columns} dataSource={rows} pagination={false} rowKey={(_row, index) => `weight:${index}`} size="small" />
    </Card>
  );
}

function DropRowsEditor({ disabled, itemNames, mystic, onChange, rows }: { disabled?: boolean; itemNames: string[]; mystic: MysticState; onChange: (rows: DropRow[]) => void; rows: DropRow[] }) {
  function setRow(index: number, patch: Partial<DropRow>) {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  const columns: ColumnsType<DropRow> = [
    { title: "类别", render: (_value, row, index) => <Select allowClear disabled={disabled} onChange={(value) => setRow(index, { category: value ?? "" })} options={selectOptions(mystic.categories, row.category)} value={row.category || undefined} /> },
    { title: "阶级", render: (_value, row, index) => <Select allowClear disabled={disabled} onChange={(value) => setRow(index, { tier: value ?? "" })} options={selectOptions(mystic.tiers, row.tier)} value={row.tier || undefined} /> },
    { title: "品质", render: (_value, row, index) => <Select allowClear disabled={disabled} onChange={(value) => setRow(index, { grade: value ?? "" })} options={selectOptions(mystic.grades, row.grade)} value={row.grade || undefined} /> },
    { title: "物品", render: (_value, row, index) => <Select allowClear disabled={disabled} onChange={(value) => setRow(index, { name: value ?? "" })} options={selectOptions(itemNames, row.name)} showSearch value={row.name || undefined} /> },
    { title: "权重", width: 140, render: (_value, row, index) => <InputNumber disabled={disabled} min={0} onChange={(value) => setRow(index, { weight: value ?? undefined })} value={finiteNumber(row.weight)} /> },
    { title: "操作", width: 80, render: (_value, _row, index) => <Popconfirm disabled={disabled} onConfirm={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))} title="删除固定掉落？"><Button disabled={disabled} icon={<DeleteOutlined />} /></Popconfirm> },
  ];

  return (
    <Card extra={<Button disabled={disabled} icon={<PlusOutlined />} onClick={() => onChange([...rows, {}])}>新增</Button>} size="small" title="固定掉落">
      <Table<DropRow> columns={columns} dataSource={rows} pagination={false} rowKey={(_row, index) => `drop:${index}`} scroll={{ x: 860 }} size="small" />
    </Card>
  );
}

function TypeSection({ disabled, itemNames, mystic, onChange, typeName }: { disabled?: boolean; itemNames: string[]; mystic: MysticState; onChange: (mystic: MysticState) => void; typeName: string }) {
  const weights = weightRows(mystic, typeName);
  const drops = dropRows(mystic, typeName);
  return (
    <div className="page-stack">
      <Text type="secondary">{weights.length} 条类别权重 · {drops.length} 条固定掉落</Text>
      <WeightRowsEditor categories={mystic.categories} disabled={disabled} onChange={(rows) => onChange(setWeightRows(mystic, typeName, rows))} rows={weights} />
      <DropRowsEditor disabled={disabled} itemNames={itemNames} mystic={mystic} onChange={(rows) => onChange(setDropRows(mystic, typeName, rows))} rows={drops} />
    </div>
  );
}

export function MysticPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
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
  useDirtyFlag(dirty, onDirtyChange);
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
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <Title level={3}>秘境掉落</Title>
          <Text type="secondary">配置秘境类型、概率、类别权重与固定掉落</Text>
        </div>
        <Space wrap>
          <Tag color={statusColor(dirty, saveState)}>{statusLabel(dirty, saveState)}</Tag>
          <Button disabled={saving} icon={<ReloadOutlined />} onClick={() => void reloadMystic()}>
            重载
          </Button>
          <Button disabled={!dirty || saving} icon={<SaveOutlined />} loading={saving} onClick={() => void saveMystic()} type="primary">
            保存
          </Button>
        </Space>
      </div>
      {saveError ? <ErrorState message={saveError} /> : null}
      {loading ? <LoadingState label="正在载入秘境掉落" /> : null}
      {error ? <ErrorState message={error} onRetry={() => void loadMystic()} /> : null}
      {!loading && !error ? (
        <div className="page-stack">
          <RateEditor disabled={saving} mystic={mystic} onChange={updateMystic} />
          <TypeToggles disabled={saving} mystic={mystic} onChange={updateMystic} />
          {sections.length ? (
            <Tabs
              items={sections.map((typeName) => ({
                key: typeName,
                label: typeName,
                children: <TypeSection disabled={saving} itemNames={itemNames} mystic={mystic} onChange={updateMystic} typeName={typeName} />,
              }))}
            />
          ) : (
            <EmptyState title="暂无秘境规则" detail="启用类型或保留已有规则后可编辑掉落配置。" />
          )}
        </div>
      ) : null}
    </div>
  );
}
