import { DeleteOutlined, PlusOutlined, ReloadOutlined, SaveOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Checkbox, Input, InputNumber, Popconfirm, Select, Space, Table, Tabs, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
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

const { Text, Title } = Typography;
const { TextArea } = Input;

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
    <div>
      <Text type="secondary">{label}</Text>
      {hint ? <Text className="field-hint" type="secondary">{hint}</Text> : null}
      <InputNumber disabled={disabled} max={max} min={min} onChange={(next) => onChange(next ?? undefined)} step={step} value={value} />
    </div>
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

  const columns: ColumnsType<NumberRow> = [
    {
      title: keyLabel,
      render: (_value, row, index) =>
        keyOptions?.length ? (
          <Select allowClear disabled={disabled} onChange={(value) => setRow(index, { key: value ?? "" })} options={selectOptions(keyOptions, row.key)} value={row.key || undefined} />
        ) : (
          <Input disabled={disabled} onChange={(event) => setRow(index, { key: event.target.value })} value={row.key} />
        ),
    },
    {
      title: valueLabel,
      width: 180,
      render: (_value, row, index) => <InputNumber disabled={disabled} min={0} onChange={(value) => setRow(index, { value: value ?? undefined })} step={0.01} value={row.value} />,
    },
    {
      title: "操作",
      width: 80,
      render: (_value, _row, index) => (
        <Popconfirm disabled={disabled} onConfirm={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))} title="删除该配置？">
          <Button disabled={disabled} icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <Card extra={<Button disabled={disabled} icon={<PlusOutlined />} onClick={() => onChange([...rows, { key: "", value: undefined }])}>新增</Button>} size="small" title={title}>
      <Text type="secondary">{detail}</Text>
      <Table<NumberRow> columns={columns} dataSource={rows} pagination={false} rowKey={(_row, index) => `${title}:${index}`} size="small" />
    </Card>
  );
}

function TierRealmEditor({ disabled, meta, onChange, rows }: { disabled?: boolean; meta: EquipmentMeta; onChange: (rows: NumberRow[]) => void; rows: NumberRow[] }) {
  const realms = (meta.realms ?? []).map((realm) => ({ label: realm.name, value: String(realm.index) }));
  function setRow(index: number, patch: Partial<NumberRow>) {
    onChange(rows.map((row, rowIndex) => (rowIndex === index ? { ...row, ...patch } : row)));
  }

  const columns: ColumnsType<NumberRow> = [
    { title: "阶级", render: (_value, row, index) => <Select allowClear disabled={disabled} onChange={(value) => setRow(index, { key: value ?? "" })} options={selectOptions(DEFAULT_TIERS, row.key)} value={row.key || undefined} /> },
    { title: "默认境界", render: (_value, row, index) => <Select allowClear disabled={disabled} onChange={(value) => setRow(index, { value: value === undefined ? undefined : Number(value) })} options={realms} value={row.value === undefined ? undefined : String(row.value)} /> },
    { title: "操作", width: 80, render: (_value, _row, index) => <Popconfirm disabled={disabled} onConfirm={() => onChange(rows.filter((_, rowIndex) => rowIndex !== index))} title="删除默认境界？"><Button disabled={disabled} icon={<DeleteOutlined />} /></Popconfirm> },
  ];

  return (
    <Card extra={<Button disabled={disabled} icon={<PlusOutlined />} onClick={() => onChange([...rows, { key: "", value: undefined }])}>新增</Button>} size="small" title="阶级默认境界">
      <Text type="secondary">用于缺省灵器境界推断</Text>
      <Table<NumberRow> columns={columns} dataSource={rows} locale={{ emptyText: <EmptyState title="暂无默认境界" detail="点击新增设置阶级与境界的默认对应关系。" /> }} pagination={false} rowKey={(_row, index) => `tier-realm:${index}`} size="small" />
    </Card>
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
  const normalizedUnlocks = Object.fromEntries(Object.entries(unlocks).map(([key, value]) => [key, Array.isArray(value) ? value.map(String) : []]));
  const tierOptions = uniqueValues([...(meta.tiers ?? []), ...DEFAULT_TIERS, ...Object.values(normalizedUnlocks).flatMap((value) => value)]);
  const realms = meta.realms?.length
    ? meta.realms
    : Object.keys(normalizedUnlocks).map((key) => ({ index: Number(key), name: `境界 ${key}` })).filter((realm) => Number.isFinite(realm.index));

  return (
    <Card size="small" title="境界阶级解锁">
      <div className="unlock-grid">
        {realms.map((realm) => (
          <Card key={realm.index} size="small" title={realm.name}>
            <Checkbox.Group
              disabled={disabled}
              onChange={(values) => onChange({ ...normalizedUnlocks, [String(realm.index)]: values.map(String) })}
              options={tierOptions}
              value={normalizedUnlocks[String(realm.index)] ?? []}
            />
          </Card>
        ))}
      </div>
    </Card>
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
    <Card title="专页配置概览">
      <div className="summary-grid">
        {summaries.map((item) => (
          <Card key={item.label} size="small">
            <Text type="secondary">{item.label}</Text>
            <Title level={3}>{item.value}</Title>
            <Text type="secondary">{item.detail}</Text>
          </Card>
        ))}
      </div>
      {extraKeys.length ? (
        <Space wrap>
          {extraKeys.map((key) => (
            <Tag key={key}>{key}</Tag>
          ))}
        </Space>
      ) : null}
    </Card>
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

export function ConfigPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [config, setConfig] = useState<Record<string, unknown>>({});
  const [originalConfig, setOriginalConfig] = useState<Record<string, unknown>>({});
  const [rawConfigText, setRawConfigText] = useState("{}");
  const [rawConfigError, setRawConfigError] = useState("");
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

  function setNextConfig(next: Record<string, unknown>) {
    setConfig(next);
    setRawConfigText(JSON.stringify(next, null, 2));
    setRawConfigError("");
    setSaveState("idle");
    setSaveError("");
  }

  function updateConfig(updater: (draft: Record<string, unknown>) => void) {
    const next = cloneJson(config);
    updater(next);
    setNextConfig(next);
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

  function applyRawConfig() {
    try {
      const parsed = JSON.parse(rawConfigText) as unknown;
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
        setRawConfigError("原始配置必须是 JSON 对象。");
        return;
      }
      setNextConfig(normalizeConfig(parsed as Record<string, unknown>));
    } catch (parseError) {
      setRawConfigError(parseError instanceof SyntaxError ? parseError.message : "JSON 解析失败");
    }
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
      setRawConfigText(JSON.stringify(normalized, null, 2));
      setRawConfigError("");
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

  const globalTab = (
    <div className="page-stack">
      <Card size="small" title="全局参数">
        <div className="form-grid">
          <NumberField disabled={saving} label="配置版本" min={0} onChange={(value) => setNested(["version"], value)} step={1} value={finiteNumber(config.version)} />
          <NumberField disabled={saving} hint="影响新牌池默认复制数" label="御兽默认卡池数量" min={0} onChange={(value) => setNested(["beast_realm", "card_pool_copies"], value)} step={1} value={finiteNumber(beastRealm.card_pool_copies)} />
          <NumberField disabled={saving} hint="灵器掉落时升级为仙阶的概率" label="仙阶升级概率" max={1} min={0} onChange={(value) => setNested(["equipment_rules", "artifact_immortal_upgrade_rate"], value)} step={0.01} value={finiteNumber(equipmentRules.artifact_immortal_upgrade_rate)} />
          <NumberField disabled={saving} hint="秘境中刷新增加一次垂钓次数选项" label="秘境垂钓选项概率" max={1} min={0} onChange={(value) => setNested(["mystic", "fishing_option_rate"], value)} step={0.01} value={finiteNumber(mystic.fishing_option_rate)} />
          <NumberField disabled={saving} hint="每日签到额外增加一次垂钓次数" label="签到额外垂钓概率" max={1} min={0} onChange={(value) => setNested(["signin", "extra_fishing_chance_rate"], value)} step={0.01} value={finiteNumber(signin.extra_fishing_chance_rate)} />
        </div>
      </Card>
    </div>
  );

  const powerTab = (
    <div className="page-stack">
      <TierRealmEditor disabled={saving} meta={meta} onChange={(rows) => setNested(["equipment_rules", "tier_default_realm"], rowsToRecord(rows))} rows={numberRows(equipmentRules.tier_default_realm)} />
      <RealmTierUnlockEditor disabled={saving} meta={meta} onChange={(nextUnlocks) => setNested(["equipment_rules", "realm_tier_unlocks"], nextUnlocks)} unlocks={asRecord(equipmentRules.realm_tier_unlocks)} />
      <NumberMapEditor detail="不同灵器类别的基础战力" disabled={saving} keyLabel="类别" onChange={(rows) => setNested(["equipment_rules", "artifact_power_base"], rowsToRecord(rows))} rows={numberRows(equipmentRules.artifact_power_base)} title="灵器类别基础战力" valueLabel="基础值" />
      <NumberMapEditor detail="不同境界灵器的基础战力" disabled={saving} keyLabel="境界序号" keyOptions={realmIndexOptions} onChange={(rows) => setNested(["equipment_rules", "artifact_realm_power_base"], rowsToRecord(rows))} rows={numberRows(equipmentRules.artifact_realm_power_base)} title="灵器境界基础战力" valueLabel="基础值" />
      <NumberMapEditor detail="不同阶级对战力的倍率" disabled={saving} keyLabel="阶级" keyOptions={tierOptions} onChange={(rows) => setNested(["equipment_rules", "artifact_tier_power_ratio"], rowsToRecord(rows))} rows={numberRows(equipmentRules.artifact_tier_power_ratio)} title="灵器阶级倍率" valueLabel="倍率" />
      <NumberMapEditor detail="不同品相对战力的倍率" disabled={saving} keyLabel="品相" keyOptions={gradeOptions} onChange={(rows) => setNested(["equipment_rules", "artifact_grade_ratio"], rowsToRecord(rows))} rows={numberRows(equipmentRules.artifact_grade_ratio)} title="灵器品相倍率" valueLabel="倍率" />
    </div>
  );

  const rawTab = (
    <div className="page-stack">
      <Alert message="原始配置是高级恢复入口。修改后需先应用 JSON，再点击页面右上角保存。" showIcon type="warning" />
      {rawConfigError ? <Alert message={rawConfigError} showIcon type="error" /> : null}
      <TextArea autoSize={{ minRows: 18 }} onChange={(event) => setRawConfigText(event.target.value)} value={rawConfigText} />
      <Button onClick={applyRawConfig} type="primary">应用 JSON</Button>
    </div>
  );

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <Title level={2}>系统配置</Title>
          <Text type="secondary">结构化编辑全局概率、战力倍率与解锁规则</Text>
        </div>
        <Space wrap>
          <Tag color={statusColor(dirty, saveState)}>{statusLabel(dirty, saveState)}</Tag>
          <Button disabled={saving} icon={<ReloadOutlined />} onClick={() => void reloadConfig()}>重载</Button>
          <Button disabled={!dirty || saving} icon={<SaveOutlined />} loading={saving} onClick={() => void saveConfig()} type="primary">保存</Button>
        </Space>
      </div>

      {saveError ? <ErrorState message={saveError} /> : null}
      {loading ? <LoadingState label="正在载入高级配置" /> : null}
      {error ? <ErrorState message={error} onRetry={() => void loadConfig()} /> : null}
      {!loading && !error ? (
        <Tabs
          items={[
            { key: "global", label: "全局参数", children: globalTab },
            { key: "power", label: "灵器战力模型", children: powerTab },
            { key: "summary", label: "配置概览", children: <ManagedSummary config={config} /> },
            { key: "raw", label: "原始配置", children: rawTab },
          ]}
        />
      ) : null}
    </div>
  );
}
