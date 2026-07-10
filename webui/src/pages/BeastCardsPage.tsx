import { FileImageOutlined, ReloadOutlined, SaveOutlined, SearchOutlined, UndoOutlined } from "@ant-design/icons";
import { Avatar, Button, Card, Collapse, Drawer, Flex, Form, Image, Input, InputNumber, Popconfirm, Select, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { api, getToken } from "../lib/api";
import type { BeastCard, BeastCardPayload } from "../lib/types";
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";

const { Text, Title } = Typography;
const { TextArea } = Input;

type SaveState = "idle" | "saving" | "saved" | "error";
type ConfigPayload = { ok: boolean; config: Record<string, unknown> };
type BeastMeta = BeastCardPayload["meta"];
type TextFieldKey = "name" | "realm" | "faction" | "effect" | "story" | "element" | "category" | "target" | "portrait_id" | "icon_id" | "source_realm" | "archetype";
type NumberFieldKey = "tier" | "cost" | "attack" | "defense" | "pool_copies";

const TEXT_FIELD_KEYS: TextFieldKey[] = ["name", "realm", "faction", "effect", "story", "element", "category", "target", "portrait_id", "icon_id", "source_realm", "archetype"];
const NUMBER_FIELD_KEYS: NumberFieldKey[] = ["tier", "cost", "attack", "defense", "pool_copies"];
const DEFAULT_TARGETS = ["ally", "team", "enemy"];

function cloneCard(card: BeastCard): BeastCard {
  return { ...card, rules: cloneRules(card.rules) };
}

function cloneRules(rules: unknown) {
  if (rules === undefined) {
    return undefined;
  }
  try {
    return JSON.parse(JSON.stringify(rules)) as unknown;
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof TypeError) {
      return rules;
    }
    throw error;
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function hasUnsavedChanges(draft: BeastCard | null, original: BeastCard | null, rulesText: string) {
  if (!draft || !original) {
    return false;
  }
  const originalRulesText = JSON.stringify(original.rules ?? {}, null, 2);
  return JSON.stringify(draft) !== JSON.stringify(original) || rulesText !== originalRulesText;
}

function confirmDiscard() {
  if (typeof window === "undefined") {
    return true;
  }
  return window.confirm("当前卡牌有未保存修改，确认切换吗？");
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

function assetTokenQuery() {
  const token = getToken();
  return token ? `?token=${encodeURIComponent(token)}` : "";
}

function pngFilename(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.toLowerCase().endsWith(".png") ? trimmed : `${trimmed}.png`;
}

function cardAssetUrl(card: BeastCard) {
  if (card.kind === "spell") {
    if (card.icon) {
      return `${adminBasePath()}/assets/beast-spell-icons/${encodeURIComponent(card.icon)}${assetTokenQuery()}`;
    }
    const iconId = pngFilename(String(card.icon_id ?? ""));
    if (iconId) {
      return `${adminBasePath()}/assets/beast-spell-icons/${encodeURIComponent(iconId)}${assetTokenQuery()}`;
    }
  }
  const portraitFilename = pngFilename(String(card.portrait_id ?? ""));
  if (!portraitFilename) {
    return "";
  }
  return `${adminBasePath()}/assets/character-portraits/${encodeURIComponent(portraitFilename)}${assetTokenQuery()}`;
}

function realmName(realm: BeastMeta["realms"] extends infer Realms ? Realms : never, value?: string | number) {
  if (value === undefined || value === null || value === "") {
    return "";
  }
  if (!Array.isArray(realm)) {
    return String(value);
  }
  const match = realm.find((item, index) => {
    if (typeof item === "string") {
      return item === value || index + 1 === Number(value);
    }
    return item.index === Number(value) || item.name === value;
  });
  if (typeof match === "string") {
    return match;
  }
  return match?.name ?? String(value);
}

function realmOptions(meta: BeastMeta, current?: string) {
  const values = (meta.realms ?? [])
    .map((realm, index) => (typeof realm === "string" ? realm : realm.name || String(realm.index || index + 1)))
    .filter(Boolean);
  return optionValues(values, current);
}

function optionValues(options: string[] | undefined, current?: string) {
  const values = [...(options ?? [])];
  const currentValue = String(current ?? "").trim();
  if (currentValue && !values.includes(currentValue)) {
    values.unshift(currentValue);
  }
  return values;
}

function uniqueSorted(values: Array<string | undefined>) {
  return [...new Set(values.map((value) => String(value ?? "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b));
}

function cardMatchesQuery(card: BeastCard, query: string) {
  const text = query.trim().toLowerCase();
  if (!text) {
    return true;
  }
  return [card.id, card.name, card.kind, card.faction, card.category, card.realm, card.element, card.effect, card.story]
    .filter(Boolean)
    .some((value) => String(value).toLowerCase().includes(text));
}

function parseRules(rulesText: string) {
  const text = rulesText.trim();
  if (!text) {
    return {};
  }
  return JSON.parse(text) as unknown;
}

function cleanCardOverride(card: BeastCard, rules: unknown) {
  const override: Record<string, unknown> = {};
  for (const key of TEXT_FIELD_KEYS) {
    override[key] = card[key] ?? "";
  }
  for (const key of NUMBER_FIELD_KEYS) {
    override[key] = card[key] ?? null;
  }
  override.rules = rules;
  return override;
}

function cardKindLabel(kind: BeastCard["kind"]) {
  return kind === "spell" ? "法术" : "随从";
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

function CardPreview({ card, size = 48 }: { card: BeastCard; size?: number }) {
  const src = cardAssetUrl(card);
  if (!src) {
    return <Avatar icon={<FileImageOutlined />} shape="square" size={size} />;
  }
  return <Image alt="" preview={false} src={src} width={size} />;
}

function BeastCardEditor({
  disabled,
  draft,
  meta,
  onChange,
  onRulesChange,
  rulesText,
}: {
  disabled?: boolean;
  draft: BeastCard;
  meta: BeastMeta;
  onChange: (card: BeastCard) => void;
  onRulesChange: (value: string) => void;
  rulesText: string;
}) {
  function setTextField(key: TextFieldKey, value: string) {
    onChange({ ...draft, [key]: value });
  }

  function setNumberField(key: NumberFieldKey, value: number | null) {
    onChange({ ...draft, [key]: value === null ? undefined : value });
  }

  return (
    <Form disabled={disabled} layout="vertical">
      <Card size="small" title="基础信息">
        <div className="form-grid">
          <Form.Item label="名称">
            <Input onChange={(event) => setTextField("name", event.target.value)} value={draft.name} />
          </Form.Item>
          <Form.Item label="境界">
            <Select allowClear onChange={(value) => setTextField("realm", value ?? "")} options={selectOptions(realmOptions(meta, draft.realm))} value={draft.realm || undefined} />
          </Form.Item>
          <Form.Item label="阵营">
            <Select allowClear onChange={(value) => setTextField("faction", value ?? "")} options={selectOptions(meta.factions, draft.faction)} value={draft.faction || undefined} />
          </Form.Item>
          <Form.Item label="消耗">
            <InputNumber onChange={(value) => setNumberField("cost", value)} value={draft.cost} />
          </Form.Item>
          <Form.Item label="攻击">
            <InputNumber onChange={(value) => setNumberField("attack", value)} value={draft.attack} />
          </Form.Item>
          <Form.Item label="防御">
            <InputNumber onChange={(value) => setNumberField("defense", value)} value={draft.defense} />
          </Form.Item>
          <Form.Item label="卡池数量">
            <InputNumber min={0} onChange={(value) => setNumberField("pool_copies", value)} value={draft.pool_copies} />
          </Form.Item>
        </div>
      </Card>

      <Card size="small" title="结构字段">
        <div className="form-grid">
          <Form.Item label="阶层">
            <InputNumber onChange={(value) => setNumberField("tier", value)} value={draft.tier} />
          </Form.Item>
          <Form.Item label="元素">
            <Select allowClear onChange={(value) => setTextField("element", value ?? "")} options={selectOptions(meta.elements, draft.element)} value={draft.element || undefined} />
          </Form.Item>
          <Form.Item label="类别">
            <Select allowClear onChange={(value) => setTextField("category", value ?? "")} options={selectOptions(meta.categories, draft.category)} value={draft.category || undefined} />
          </Form.Item>
          <Form.Item label="目标">
            <Select allowClear onChange={(value) => setTextField("target", value ?? "")} options={selectOptions(meta.targets ?? DEFAULT_TARGETS, draft.target)} value={draft.target || undefined} />
          </Form.Item>
          <Form.Item label="画像 ID">
            <Input onChange={(event) => setTextField("portrait_id", event.target.value)} value={draft.portrait_id ?? ""} />
          </Form.Item>
          <Form.Item label="图标 ID">
            <Input onChange={(event) => setTextField("icon_id", event.target.value)} value={draft.icon_id ?? draft.icon ?? ""} />
          </Form.Item>
          <Form.Item label="来源境界">
            <Input onChange={(event) => setTextField("source_realm", event.target.value)} value={draft.source_realm ?? ""} />
          </Form.Item>
          <Form.Item label="原型">
            <Input onChange={(event) => setTextField("archetype", event.target.value)} value={draft.archetype ?? ""} />
          </Form.Item>
        </div>
      </Card>

      <Card size="small" title="文本">
        <div className="form-grid form-grid-two">
          <Form.Item label="效果">
            <TextArea autoSize={{ minRows: 4 }} onChange={(event) => setTextField("effect", event.target.value)} value={draft.effect ?? ""} />
          </Form.Item>
          <Form.Item label="故事">
            <TextArea autoSize={{ minRows: 4 }} onChange={(event) => setTextField("story", event.target.value)} value={draft.story ?? ""} />
          </Form.Item>
        </div>
      </Card>

      <Collapse
        items={[
          {
            key: "rules",
            label: "高级：规则 JSON",
            children: <TextArea autoSize={{ minRows: 8 }} onChange={(event) => onRulesChange(event.target.value)} value={rulesText} />,
          },
        ]}
      />
    </Form>
  );
}

export function BeastCardsPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [cards, setCards] = useState<BeastCard[]>([]);
  const [meta, setMeta] = useState<BeastMeta>({});
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState<string | undefined>();
  const [faction, setFaction] = useState<string | undefined>();
  const [selectedId, setSelectedId] = useState("");
  const [draft, setDraft] = useState<BeastCard | null>(null);
  const [originalDraft, setOriginalDraft] = useState<BeastCard | null>(null);
  const [rulesText, setRulesText] = useState("{}");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState("");
  const loadRequestId = useRef(0);
  const saveRequestId = useRef(0);
  const selectedIdRef = useRef("");

  const dirty = hasUnsavedChanges(draft, originalDraft, rulesText);
  const saving = saveState === "saving";
  useDirtyFlag(dirty, onDirtyChange);

  const factionOptions = useMemo(
    () => uniqueSorted([...(meta.factions ?? []), ...cards.map((card) => card.faction || card.category)]).map((value) => ({ label: value, value })),
    [cards, meta.factions],
  );
  const filteredCards = useMemo(
    () =>
      cards.filter((card) => {
        if (!cardMatchesQuery(card, query)) {
          return false;
        }
        if (kind && card.kind !== kind) {
          return false;
        }
        if (faction && (card.faction || card.category) !== faction) {
          return false;
        }
        return true;
      }),
    [cards, faction, kind, query],
  );

  const columns: ColumnsType<BeastCard> = [
    {
      title: "卡牌",
      dataIndex: "name",
      render: (_value, card) => (
        <Space>
          <CardPreview card={card} />
          <Space direction="vertical" size={0}>
            <Text strong>{card.name || card.id}</Text>
            <Text type="secondary">{card.id}</Text>
          </Space>
        </Space>
      ),
    },
    { title: "类型", dataIndex: "kind", render: (value: BeastCard["kind"]) => <Tag>{cardKindLabel(value)}</Tag> },
    { title: "阵营", render: (_value, card) => card.faction || card.category || "未分类" },
    { title: "境界", render: (_value, card) => realmName(meta.realms, card.realm || card.tier) || "未设置" },
    { title: "消耗", dataIndex: "cost", align: "right" },
    { title: "攻/防", render: (_value, card) => `${card.attack ?? "-"} / ${card.defense ?? "-"}` },
    { title: "状态", dataIndex: "customized", render: (value?: boolean) => (value ? <Tag color="blue">已修改</Tag> : <Tag>默认</Tag>) },
  ];

  function selectCard(card: BeastCard, options: { skipDirtyCheck?: boolean } = {}) {
    if (saving) {
      return;
    }
    if (!options.skipDirtyCheck && dirty && !confirmDiscard()) {
      return;
    }
    const nextDraft = cloneCard(card);
    selectedIdRef.current = card.id;
    setSelectedId(card.id);
    setDraft(nextDraft);
    setOriginalDraft(cloneCard(card));
    setRulesText(JSON.stringify(card.rules ?? {}, null, 2));
    setSaveError("");
    setSaveState("idle");
  }

  async function loadCards(options: { keepSelectionId?: string } = {}) {
    const requestId = loadRequestId.current + 1;
    loadRequestId.current = requestId;
    setLoading(true);
    setError("");
    try {
      const payload = await api<BeastCardPayload>("/api/beast-realm/cards");
      if (loadRequestId.current !== requestId) {
        return false;
      }
      const nextCards = payload.cards ?? [];
      setCards(nextCards);
      setMeta(payload.meta ?? {});
      const preferredId = options.keepSelectionId ?? selectedIdRef.current;
      const nextSelected = preferredId ? nextCards.find((card) => card.id === preferredId) : undefined;
      if (nextSelected) {
        selectCard(nextSelected, { skipDirtyCheck: true });
      } else if (!options.keepSelectionId) {
        selectedIdRef.current = "";
        setSelectedId("");
        setDraft(null);
        setOriginalDraft(null);
        setRulesText("{}");
      }
      return true;
    } catch (loadError) {
      if (loadRequestId.current === requestId) {
        setError(loadError instanceof Error ? loadError.message : "御兽卡牌载入失败");
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
    selectedIdRef.current = "";
    setSelectedId("");
    setDraft(null);
    setOriginalDraft(null);
    setRulesText("{}");
    setSaveError("");
  }

  async function reloadSelected() {
    if (saving) {
      return;
    }
    if (dirty && !confirmDiscard()) {
      return;
    }
    await loadCards({ keepSelectionId: selectedId });
  }

  async function saveCard() {
    if (!draft) {
      return;
    }
    let rules: unknown;
    try {
      rules = parseRules(rulesText);
    } catch (parseError) {
      setSaveState("error");
      setSaveError(parseError instanceof SyntaxError ? `规则 JSON 解析失败：${parseError.message}` : "规则 JSON 解析失败");
      return;
    }

    const id = draft.id;
    const requestId = saveRequestId.current + 1;
    saveRequestId.current = requestId;
    setSaveState("saving");
    setSaveError("");
    try {
      const payload = await api<ConfigPayload>("/api/config");
      const config = asRecord(payload.config);
      const beastRealm = { ...asRecord(config.beast_realm) };
      const overrides = { ...asRecord(beastRealm.card_overrides) };
      overrides[id] = { ...asRecord(overrides[id]), ...cleanCardOverride(draft, rules) };
      beastRealm.card_overrides = overrides;
      config.beast_realm = beastRealm;
      await api<ConfigPayload>("/api/config", { body: JSON.stringify(config, null, 2), method: "PUT" });
      if (saveRequestId.current !== requestId || selectedIdRef.current !== id) {
        return;
      }
      const reloaded = await loadCards({ keepSelectionId: id });
      if (saveRequestId.current === requestId && selectedIdRef.current === id) {
        if (reloaded) {
          setSaveState("saved");
        } else {
          setSaveState("error");
          setSaveError("配置已保存，但御兽卡牌重新载入失败。请重试载入。");
        }
      }
    } catch (saveErrorValue) {
      if (saveRequestId.current === requestId && selectedIdRef.current === id) {
        setSaveState("error");
        setSaveError(saveErrorValue instanceof Error ? saveErrorValue.message : "保存失败");
      }
    }
  }

  async function restoreDefault() {
    if (!draft) {
      return;
    }
    const id = draft.id;
    const requestId = saveRequestId.current + 1;
    saveRequestId.current = requestId;
    setSaveState("saving");
    setSaveError("");
    try {
      const payload = await api<ConfigPayload>("/api/config");
      const config = asRecord(payload.config);
      const beastRealm = { ...asRecord(config.beast_realm) };
      const overrides = { ...asRecord(beastRealm.card_overrides) };
      delete overrides[id];
      beastRealm.card_overrides = overrides;
      config.beast_realm = beastRealm;
      await api<ConfigPayload>("/api/config", { body: JSON.stringify(config, null, 2), method: "PUT" });
      if (saveRequestId.current !== requestId || selectedIdRef.current !== id) {
        return;
      }
      const reloaded = await loadCards({ keepSelectionId: id });
      if (saveRequestId.current === requestId && selectedIdRef.current === id) {
        if (reloaded) {
          setSaveState("saved");
        } else {
          setSaveState("error");
          setSaveError("默认配置已恢复，但御兽卡牌重新载入失败。请重试载入。");
        }
      }
    } catch (saveErrorValue) {
      if (saveRequestId.current === requestId && selectedIdRef.current === id) {
        setSaveState("error");
        setSaveError(saveErrorValue instanceof Error ? saveErrorValue.message : "恢复默认失败");
      }
    }
  }

  useEffect(() => {
    void loadCards();
  }, []);

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <Title level={2}>御兽卡牌</Title>
          <Text type="secondary">筛选卡牌并编辑御兽秘境覆盖字段</Text>
        </div>
        <Tag>{cards.length} 张</Tag>
      </div>

      <Card>
        <Flex gap={8} wrap="wrap">
          <Input allowClear className="search-input" onChange={(event) => setQuery(event.target.value)} placeholder="卡牌名称、ID、效果" prefix={<SearchOutlined />} value={query} />
          <Select
            allowClear
            className="filter-select"
            onChange={setKind}
            options={[
              { label: "随从", value: "beast" },
              { label: "法术", value: "spell" },
            ]}
            placeholder="全部类型"
            value={kind}
          />
          <Select allowClear className="filter-select" onChange={setFaction} options={factionOptions} placeholder="全部阵营" value={faction} />
        </Flex>
      </Card>

      {error ? <ErrorState message={error} onRetry={() => void loadCards({ keepSelectionId: selectedId })} /> : null}

      <Card>
        <Table<BeastCard>
          columns={columns}
          dataSource={filteredCards}
          loading={loading}
          locale={{ emptyText: loading ? null : <EmptyState title="未找到卡牌" detail="换一个关键词、类型或阵营再试。" /> }}
          onRow={(card) => ({ onClick: () => selectCard(card) })}
          pagination={{ pageSize: 15, showSizeChanger: true }}
          rowKey="id"
          scroll={{ x: 1080 }}
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
              <Button disabled={!dirty || saving} icon={<SaveOutlined />} loading={saving} onClick={() => void saveCard()} type="primary">
                保存
              </Button>
            </Flex>
          ) : null
        }
        onClose={() => void closeDrawer()}
        open={Boolean(draft)}
        title={draft?.name || draft?.id || "卡牌详情"}
        width={980}
      >
        {draft ? (
          <div className="page-stack">
            <Card size="small">
              <Space>
                <CardPreview card={draft} size={56} />
                <Space direction="vertical" size={0}>
                  <Text strong>{draft.name || draft.id}</Text>
                  <Text type="secondary">
                    {cardKindLabel(draft.kind)} · {realmName(meta.realms, draft.realm || draft.tier) || "未设境界"}
                  </Text>
                </Space>
              </Space>
            </Card>
            {saveError ? <ErrorState message={saveError} /> : null}
            <BeastCardEditor disabled={saving} draft={draft} meta={meta} onChange={setDraft} onRulesChange={setRulesText} rulesText={rulesText} />
          </div>
        ) : null}
      </Drawer>

      {loading && !cards.length ? <LoadingState label="正在载入御兽卡牌" /> : null}
    </div>
  );
}
