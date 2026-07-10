import { DeleteOutlined, PlusOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { Button, Card, Flex, Input, InputNumber, Popconfirm, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { api } from "../lib/api";
import type { EquipmentPayload } from "../lib/types";
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";

const { Text, Title } = Typography;

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

function selectOptions(options?: string[], current?: string) {
  return optionValues(options, current).map((value) => ({ label: value, value }));
}

function EditableSelect({ disabled, onChange, options, value }: { disabled?: boolean; onChange: (value: string) => void; options?: string[]; value?: string }) {
  const availableOptions = selectOptions(options, value);
  if (!availableOptions.length) {
    return <Input disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value ?? ""} />;
  }
  return <Select allowClear disabled={disabled} onChange={(next) => onChange(next ?? "")} options={availableOptions} value={value || undefined} />;
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

  function deleteRow(index: number) {
    onRowsChange(rows.filter((_, rowIndex) => rowIndex !== index));
  }

  const columns: ColumnsType<EquipmentRow> = [
    { title: "最低阶级", render: (_value, row, index) => <EditableSelect disabled={disabled} onChange={(value) => setRow(index, { tier_min: value })} options={meta.tiers} value={row.tier_min} /> },
    { title: "最高阶级", render: (_value, row, index) => <EditableSelect disabled={disabled} onChange={(value) => setRow(index, { tier_max: value })} options={meta.tiers} value={row.tier_max} /> },
    { title: "品质", render: (_value, row, index) => <EditableSelect disabled={disabled} onChange={(value) => setRow(index, { grade: value })} options={meta.grades} value={row.grade} /> },
    { title: "灵根", render: (_value, row, index) => <EditableSelect disabled={disabled} onChange={(value) => setRow(index, { attribute: value })} options={meta.attributes} value={row.attribute} /> },
    { title: "灵器", render: (_value, row, index) => <EditableSelect disabled={disabled} onChange={(value) => setRow(index, { name: value })} options={artifactOptions} value={row.name} /> },
    { title: "权重", width: 140, render: (_value, row, index) => <InputNumber disabled={disabled} min={0} onChange={(value) => setRow(index, { weight: value ?? undefined })} value={finiteNumber(row.weight)} /> },
    {
      title: "操作",
      width: 80,
      render: (_value, _row, index) => (
        <Popconfirm disabled={disabled} onConfirm={() => deleteRow(index)} title="删除该规则？">
          <Button disabled={disabled} icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <Card
      extra={
        <Button disabled={disabled} icon={<PlusOutlined />} onClick={() => onRowsChange([...rows, {}])} type="primary">
          新增
        </Button>
      }
      title={
        <Space direction="vertical" size={0}>
          <Text strong>{realm.name}</Text>
          <Text type="secondary">境界序号 {realm.index} · {rows.length} 条规则</Text>
        </Space>
      }
    >
      <Table<EquipmentRow>
        columns={columns}
        dataSource={rows}
        locale={{ emptyText: <EmptyState title="暂无规则" detail="点击新增为该境界配置灵器掉落池。" /> }}
        pagination={false}
        rowKey={(_row, index) => `${realm.index}:${index}`}
        scroll={{ x: 980 }}
        size="small"
      />
    </Card>
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
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <Title level={3}>灵器掉落</Title>
          <Text type="secondary">按境界编辑灵器掉落池</Text>
        </div>
        <Space wrap>
          <Tag color={statusColor(dirty, saveState)}>{statusLabel(dirty, saveState)}</Tag>
          <Button disabled={saving} icon={<ReloadOutlined />} onClick={() => void reloadEquipment()}>
            重载
          </Button>
          <Button disabled={!dirty || saving} icon={<SaveOutlined />} loading={saving} onClick={() => void saveEquipment()} type="primary">
            保存
          </Button>
        </Space>
      </div>
      {saveError ? <ErrorState message={saveError} /> : null}
      {loading ? <LoadingState label="正在载入灵器规则" /> : null}
      {error ? <ErrorState message={error} onRetry={() => void loadEquipment()} /> : null}
      {!loading && !error && !realms.length ? <EmptyState title="暂无境界" detail="后端未返回可编辑的境界列表。" /> : null}
      {!loading && !error && realms.length ? (
        <Tabs
          items={realms.map((realm) => ({
            key: String(realm.index),
            label: realm.name,
            children: (
              <RealmTable
                disabled={saving}
                meta={meta}
                onRowsChange={(rows) => {
                  setRules(writeRowsToRules(rules, realm.index, rows));
                  setSaveState("idle");
                  setSaveError("");
                }}
                realm={realm}
                rows={rowsFromRules(rules, realm.index)}
              />
            ),
          }))}
        />
      ) : null}
    </div>
  );
}

