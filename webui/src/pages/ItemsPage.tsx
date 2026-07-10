import { FileImageOutlined, ReloadOutlined, SaveOutlined, SearchOutlined, UndoOutlined } from "@ant-design/icons";
import { Avatar, Button, Card, Drawer, Flex, Form, Image, Input, Popconfirm, Select, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { api, getToken } from "../lib/api";
import type { AdminItem, ItemPayload } from "../lib/types";
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";

const { Text, Title } = Typography;
const { TextArea } = Input;

type SaveState = "idle" | "saving" | "saved" | "error";
type ConfigPayload = { ok: boolean; config: Record<string, unknown> };
type ItemMeta = ItemPayload["meta"];
type TextFieldKey = "category" | "required_realm" | "required_attribute" | "usage" | "source" | "story";
type ListFieldKey = "tiers" | "grades";

const TEXT_FIELD_KEYS: TextFieldKey[] = ["category", "required_realm", "required_attribute", "usage", "source", "story"];
const LIST_FIELD_KEYS: ListFieldKey[] = ["tiers", "grades"];

function cloneItem(item: AdminItem): AdminItem {
  return {
    ...item,
    grades: item.grades ? [...item.grades] : undefined,
    tiers: item.tiers ? [...item.tiers] : undefined,
  };
}

function compactList(values?: string[]) {
  return (values ?? []).map((value) => value.trim()).filter(Boolean);
}

function hasUnsavedChanges(draft: AdminItem | null, original: AdminItem | null) {
  if (!draft || !original) {
    return false;
  }
  return JSON.stringify(draft) !== JSON.stringify(original);
}

function confirmDiscard() {
  if (typeof window === "undefined") {
    return true;
  }
  return window.confirm("当前物品有未保存修改，确认切换吗？");
}

function adminBasePath() {
  if (typeof window === "undefined") {
    return "";
  }
  const pathname = window.location.pathname.replace(/\/$/, "");
  if (!pathname || pathname === "/") {
    return "";
  }
  const assetIndex = pathname.indexOf("/assets/");
  return assetIndex >= 0 ? pathname.slice(0, assetIndex) : pathname;
}

function iconUrl(icon?: string) {
  if (!icon) {
    return "";
  }
  const normalized = icon.replace(/\\/g, "/").split("/").filter(Boolean).map(encodeURIComponent).join("/");
  if (!normalized) {
    return "";
  }
  const token = getToken();
  const query = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${adminBasePath()}/assets/item-icons/${normalized}${query}`;
}

function optionValues(options: string[] | undefined, current?: string) {
  const values = [...(options ?? [])];
  const currentValue = String(current ?? "").trim();
  if (currentValue && !values.includes(currentValue)) {
    values.unshift(currentValue);
  }
  return values;
}

function itemMatchesQuery(item: AdminItem, query: string) {
  const text = query.trim().toLowerCase();
  if (!text) {
    return true;
  }
  return [item.name, item.category, item.usage, item.source, item.story]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(text));
}

function cleanItemOverride(item: AdminItem) {
  const override: Record<string, unknown> = { name: item.name };
  for (const key of TEXT_FIELD_KEYS) {
    override[key] = key === "required_realm" ? item.required_realm ?? item.realm ?? "" : item[key] ?? "";
  }
  for (const key of LIST_FIELD_KEYS) {
    override[key] = compactList(item[key]);
  }
  if (item.parameter_note) {
    override.parameter_note = item.parameter_note;
  }
  return override;
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
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

function tagOptions(options?: string[]) {
  return (options ?? []).map((value) => ({ label: value, value }));
}

function ItemIcon({ item, size = 40 }: { item: AdminItem; size?: number }) {
  const src = iconUrl(item.icon);
  if (!src) {
    return <Avatar icon={<FileImageOutlined />} shape="square" size={size} />;
  }
  return <Image alt="" preview={false} src={src} width={size} />;
}

function ItemEditor({ disabled, draft, meta, onChange }: { disabled?: boolean; draft: AdminItem; meta: ItemMeta; onChange: (item: AdminItem) => void }) {
  function setField(key: TextFieldKey, value: string) {
    onChange({ ...draft, [key]: value });
  }

  function setListField(key: ListFieldKey, values: string[]) {
    onChange({ ...draft, [key]: values });
  }

  const requiredRealm = draft.required_realm ?? draft.realm ?? "";

  return (
    <Form disabled={disabled} layout="vertical">
      <Card size="small" title="基础信息">
        <div className="form-grid">
          <Form.Item label="类别">
            <Select allowClear onChange={(value) => setField("category", value ?? "")} options={selectOptions(meta.categories, draft.category)} value={draft.category || undefined} />
          </Form.Item>
          <Form.Item label="需求境界">
            <Select allowClear onChange={(value) => setField("required_realm", value ?? "")} options={selectOptions(meta.realms, requiredRealm)} value={requiredRealm || undefined} />
          </Form.Item>
          <Form.Item label="需求灵根">
            <Select allowClear onChange={(value) => setField("required_attribute", value ?? "")} options={selectOptions(meta.attributes, draft.required_attribute)} value={draft.required_attribute || undefined} />
          </Form.Item>
          <Form.Item label="阶级">
            <Select mode="tags" onChange={(values) => setListField("tiers", values)} options={tagOptions(meta.tiers)} value={draft.tiers ?? []} />
          </Form.Item>
          <Form.Item label="品质">
            <Select mode="tags" onChange={(values) => setListField("grades", values)} options={tagOptions(meta.grades)} value={draft.grades ?? []} />
          </Form.Item>
        </div>
      </Card>

      <Card size="small" title="说明文本">
        <div className="form-grid form-grid-three">
          <Form.Item label="用途">
            <TextArea autoSize={{ minRows: 4 }} onChange={(event) => setField("usage", event.target.value)} value={draft.usage ?? ""} />
          </Form.Item>
          <Form.Item label="来源">
            <TextArea autoSize={{ minRows: 4 }} onChange={(event) => setField("source", event.target.value)} value={draft.source ?? ""} />
          </Form.Item>
          <Form.Item label="故事">
            <TextArea autoSize={{ minRows: 4 }} onChange={(event) => setField("story", event.target.value)} value={draft.story ?? ""} />
          </Form.Item>
        </div>
        {draft.parameter_note ? (
          <Form.Item label="参数说明">
            <TextArea autoSize={{ minRows: 3 }} readOnly value={draft.parameter_note} />
          </Form.Item>
        ) : null}
      </Card>
    </Form>
  );
}

export function ItemsPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [items, setItems] = useState<AdminItem[]>([]);
  const [meta, setMeta] = useState<ItemMeta>({});
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | undefined>();
  const [tier, setTier] = useState<string | undefined>();
  const [selectedName, setSelectedName] = useState("");
  const [draft, setDraft] = useState<AdminItem | null>(null);
  const [originalDraft, setOriginalDraft] = useState<AdminItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState("");
  const loadRequestId = useRef(0);
  const saveRequestId = useRef(0);
  const selectedNameRef = useRef("");

  const dirty = hasUnsavedChanges(draft, originalDraft);
  const saving = saveState === "saving";
  useDirtyFlag(dirty, onDirtyChange);

  const filteredItems = useMemo(
    () =>
      items.filter((item) => {
        if (!itemMatchesQuery(item, query)) {
          return false;
        }
        if (category && item.category !== category) {
          return false;
        }
        if (tier && !compactList(item.tiers).includes(tier)) {
          return false;
        }
        return true;
      }),
    [category, items, query, tier],
  );

  const columns: ColumnsType<AdminItem> = [
    {
      title: "物品",
      dataIndex: "name",
      render: (_value, item) => (
        <Space>
          <ItemIcon item={item} />
          <Space direction="vertical" size={0}>
            <Text strong>{item.name}</Text>
            <Text type="secondary">{item.category || "未分类"}</Text>
          </Space>
        </Space>
      ),
    },
    { title: "阶级", dataIndex: "tiers", render: (values?: string[]) => compactList(values).map((value) => <Tag key={value}>{value}</Tag>) },
    { title: "品质", dataIndex: "grades", render: (values?: string[]) => compactList(values).map((value) => <Tag key={value}>{value}</Tag>) },
    { title: "需求", render: (_value, item) => item.required_realm || item.realm || item.required_attribute || "未设置" },
    { title: "状态", dataIndex: "customized", render: (value?: boolean) => (value ? <Tag color="blue">已修改</Tag> : <Tag>默认</Tag>) },
  ];

  function selectItem(item: AdminItem, options: { skipDirtyCheck?: boolean } = {}) {
    if (saving) {
      return;
    }
    if (!options.skipDirtyCheck && dirty && !confirmDiscard()) {
      return;
    }
    const nextDraft = cloneItem(item);
    selectedNameRef.current = item.name;
    setSelectedName(item.name);
    setDraft(nextDraft);
    setOriginalDraft(cloneItem(item));
    setSaveError("");
    setSaveState("idle");
  }

  async function loadItems(options: { keepSelectionName?: string } = {}) {
    const requestId = loadRequestId.current + 1;
    loadRequestId.current = requestId;
    setLoading(true);
    setError("");
    try {
      const payload = await api<ItemPayload>("/api/items");
      if (loadRequestId.current !== requestId) {
        return false;
      }
      const nextItems = payload.items ?? [];
      setItems(nextItems);
      setMeta(payload.meta ?? {});
      const preferredName = options.keepSelectionName ?? selectedNameRef.current;
      const nextSelected = preferredName ? nextItems.find((item) => item.name === preferredName) : undefined;
      if (nextSelected) {
        selectItem(nextSelected, { skipDirtyCheck: true });
      } else if (!options.keepSelectionName) {
        selectedNameRef.current = "";
        setSelectedName("");
        setDraft(null);
        setOriginalDraft(null);
      }
      return true;
    } catch (loadError) {
      if (loadRequestId.current === requestId) {
        setError(loadError instanceof Error ? loadError.message : "物品图鉴载入失败");
      }
      return false;
    } finally {
      if (loadRequestId.current === requestId) {
        setLoading(false);
      }
    }
  }

  async function closeDrawer() {
    if (saving) {
      return;
    }
    if (dirty && !confirmDiscard()) {
      return;
    }
    selectedNameRef.current = "";
    setSelectedName("");
    setDraft(null);
    setOriginalDraft(null);
    setSaveError("");
  }

  async function reloadSelected() {
    if (saving) {
      return;
    }
    if (dirty && !confirmDiscard()) {
      return;
    }
    await loadItems({ keepSelectionName: selectedName });
  }

  async function saveItem() {
    if (!draft) {
      return;
    }
    const name = draft.name;
    const requestId = saveRequestId.current + 1;
    saveRequestId.current = requestId;
    setSaveState("saving");
    setSaveError("");
    try {
      const payload = await api<ConfigPayload>("/api/config");
      const config = asRecord(payload.config);
      const itemOverrides = { ...asRecord(config.item_overrides) };
      itemOverrides[name] = { ...asRecord(itemOverrides[name]), ...cleanItemOverride(draft) };
      config.item_overrides = itemOverrides;
      await api<ConfigPayload>("/api/config", { body: JSON.stringify(config, null, 2), method: "PUT" });
      if (saveRequestId.current !== requestId || selectedNameRef.current !== name) {
        return;
      }
      const reloaded = await loadItems({ keepSelectionName: name });
      if (saveRequestId.current === requestId && selectedNameRef.current === name) {
        if (reloaded) {
          setSaveState("saved");
        } else {
          setSaveState("error");
          setSaveError("配置已保存，但物品图鉴重新载入失败。请重试载入。");
        }
      }
    } catch (saveErrorValue) {
      if (saveRequestId.current === requestId && selectedNameRef.current === name) {
        setSaveState("error");
        setSaveError(saveErrorValue instanceof Error ? saveErrorValue.message : "保存失败");
      }
    }
  }

  async function restoreDefault() {
    if (!draft) {
      return;
    }
    const name = draft.name;
    const requestId = saveRequestId.current + 1;
    saveRequestId.current = requestId;
    setSaveState("saving");
    setSaveError("");
    try {
      const payload = await api<ConfigPayload>("/api/config");
      const config = asRecord(payload.config);
      const itemOverrides = { ...asRecord(config.item_overrides) };
      delete itemOverrides[name];
      config.item_overrides = itemOverrides;
      await api<ConfigPayload>("/api/config", { body: JSON.stringify(config, null, 2), method: "PUT" });
      if (saveRequestId.current !== requestId || selectedNameRef.current !== name) {
        return;
      }
      const reloaded = await loadItems({ keepSelectionName: name });
      if (saveRequestId.current === requestId && selectedNameRef.current === name) {
        if (reloaded) {
          setSaveState("saved");
        } else {
          setSaveState("error");
          setSaveError("默认配置已恢复，但物品图鉴重新载入失败。请重试载入。");
        }
      }
    } catch (saveErrorValue) {
      if (saveRequestId.current === requestId && selectedNameRef.current === name) {
        setSaveState("error");
        setSaveError(saveErrorValue instanceof Error ? saveErrorValue.message : "恢复默认失败");
      }
    }
  }

  useEffect(() => {
    void loadItems();
  }, []);

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <Title level={2}>物品图鉴</Title>
          <Text type="secondary">筛选物品并编辑结构化覆盖字段</Text>
        </div>
        <Tag>{items.length} 件</Tag>
      </div>

      <Card>
        <Flex gap={8} wrap="wrap">
          <Input allowClear className="search-input" onChange={(event) => setQuery(event.target.value)} placeholder="物品名称、用途、来源" prefix={<SearchOutlined />} value={query} />
          <Select allowClear className="filter-select" onChange={setCategory} options={tagOptions(meta.categories)} placeholder="全部类别" value={category} />
          <Select allowClear className="filter-select" onChange={setTier} options={tagOptions(meta.tiers)} placeholder="全部阶级" value={tier} />
        </Flex>
      </Card>

      {error ? <ErrorState message={error} onRetry={() => void loadItems({ keepSelectionName: selectedName })} /> : null}

      <Card>
        <Table<AdminItem>
          columns={columns}
          dataSource={filteredItems}
          loading={loading}
          locale={{ emptyText: loading ? null : <EmptyState title="未找到物品" detail="换一个关键词、类别或阶级再试。" /> }}
          onRow={(item) => ({ onClick: () => selectItem(item) })}
          pagination={{ pageSize: 15, showSizeChanger: true }}
          rowKey="name"
          scroll={{ x: 920 }}
        />
      </Card>

      <Drawer
        destroyOnClose
        extra={draft ? <Tag color={statusColor(dirty, saveState)}>{statusLabel(dirty, saveState)}</Tag> : null}
        footer={
          draft ? (
            <Flex justify="space-between" wrap="wrap">
              <Space>
                <Button disabled={saving} icon={<ReloadOutlined />} onClick={() => void reloadSelected()}>
                  重载
                </Button>
                <Popconfirm disabled={!draft.customized || saving} onConfirm={() => void restoreDefault()} title="确认恢复默认配置？">
                  <Button disabled={!draft.customized || saving} icon={<UndoOutlined />}>
                    恢复默认
                  </Button>
                </Popconfirm>
              </Space>
              <Button disabled={!dirty || saving} icon={<SaveOutlined />} loading={saving} onClick={() => void saveItem()} type="primary">
                保存
              </Button>
            </Flex>
          ) : null
        }
        onClose={() => void closeDrawer()}
        open={Boolean(draft)}
        title={draft?.name ?? "物品详情"}
        width={900}
      >
        {draft ? (
          <div className="page-stack">
            <Card size="small">
              <Space>
                <ItemIcon item={draft} size={48} />
                <Space direction="vertical" size={0}>
                  <Text strong>{draft.name}</Text>
                  <Text type="secondary">{draft.category || "未分类"}</Text>
                </Space>
              </Space>
            </Card>
            {saveError ? <ErrorState message={saveError} /> : null}
            <ItemEditor disabled={saving} draft={draft} meta={meta} onChange={setDraft} />
          </div>
        ) : null}
      </Drawer>

      {loading && !items.length ? <LoadingState label="正在载入物品图鉴" /> : null}
    </div>
  );
}
