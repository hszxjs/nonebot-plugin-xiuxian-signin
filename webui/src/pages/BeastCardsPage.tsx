import { ImageIcon, RefreshCcw, RotateCcw, Save, Search, Shield } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { Badge } from "../components/ui/badge";
import { Button, PrimaryButton } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { api, getToken } from "../lib/api";
import type { BeastCard, BeastCardPayload } from "../lib/types";
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";

type SaveState = "idle" | "saving" | "saved" | "error";
type ConfigPayload = { ok: boolean; config: Record<string, unknown> };
type BeastMeta = BeastCardPayload["meta"];
type TextFieldKey = "name" | "realm" | "faction" | "effect" | "story" | "element" | "category" | "target" | "portrait_id" | "icon_id" | "source_realm" | "archetype";
type NumberFieldKey = "tier" | "cost" | "attack" | "defense" | "pool_copies";

const MAX_VISIBLE_CARDS = 500;
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
  const values = (meta.realms ?? []).map((realm, index) => (typeof realm === "string" ? realm : realm.name || String(realm.index || index + 1))).filter(Boolean);
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

function FieldLabel({ hint, label }: { hint?: string; label: string }) {
  return (
    <div className="min-w-0">
      <div className="truncate text-sm font-medium">{label}</div>
      {hint ? <div className="truncate text-xs text-muted-foreground">{hint}</div> : null}
    </div>
  );
}

function TextField({ disabled, label, onChange, value }: { disabled?: boolean; label: string; onChange: (value: string) => void; value?: string }) {
  return (
    <label className="grid min-w-0 gap-2 rounded-md border border-border p-3">
      <FieldLabel label={label} />
      <Input disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value ?? ""} />
    </label>
  );
}

function NumberField({ disabled, label, onChange, value }: { disabled?: boolean; label: string; onChange: (value: number | undefined) => void; value?: number }) {
  function updateNumber(valueText: string) {
    if (valueText === "") {
      onChange(undefined);
      return;
    }
    const nextValue = Number(valueText);
    if (Number.isFinite(nextValue)) {
      onChange(nextValue);
    }
  }

  return (
    <label className="grid min-w-0 gap-2 rounded-md border border-border p-3">
      <FieldLabel label={label} />
      <Input disabled={disabled} onChange={(event) => updateNumber(event.target.value)} type="number" value={value ?? ""} />
    </label>
  );
}

function SelectOrInputField({ disabled, label, onChange, options, value }: { disabled?: boolean; label: string; onChange: (value: string) => void; options?: string[]; value?: string }) {
  const availableOptions = optionValues(options, value);

  return (
    <label className="grid min-w-0 gap-2 rounded-md border border-border p-3">
      <FieldLabel label={label} />
      {availableOptions.length ? (
        <Select disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value ?? ""}>
          <option value="">未设置</option>
          {availableOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </Select>
      ) : (
        <Input disabled={disabled} onChange={(event) => onChange(event.target.value)} value={value ?? ""} />
      )}
    </label>
  );
}

function TextAreaField({ disabled, label, onChange, value }: { disabled?: boolean; label: string; onChange: (value: string) => void; value?: string }) {
  return (
    <label className="grid min-w-0 gap-2 rounded-md border border-border p-3">
      <FieldLabel label={label} />
      <textarea
        className="min-h-28 w-full min-w-0 resize-y rounded-md border border-border bg-card px-3 py-2 text-sm text-card-foreground shadow-sm outline-none transition placeholder:text-muted-foreground focus:border-primary disabled:cursor-not-allowed disabled:opacity-70"
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        value={value ?? ""}
      />
    </label>
  );
}

function CardPreview({ card }: { card: BeastCard }) {
  const src = cardAssetUrl(card);
  return (
    <div className="grid h-16 w-16 shrink-0 place-items-center overflow-hidden rounded-md border border-border bg-background">
      {src ? <img alt="" className="max-h-16 max-w-16 object-contain" src={src} /> : <ImageIcon className="h-6 w-6 text-muted-foreground" aria-hidden="true" />}
    </div>
  );
}

function BeastCardRow({ card, disabled, onSelect, selected }: { card: BeastCard; disabled?: boolean; onSelect: () => void; selected: boolean }) {
  return (
    <button
      aria-disabled={disabled}
      className={[
        "grid min-w-0 grid-cols-[64px_minmax(0,1fr)] gap-3 rounded-md border border-border p-3 text-left transition",
        selected ? "bg-muted" : "bg-card hover:bg-muted/70",
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
      ].join(" ")}
      disabled={disabled}
      onClick={onSelect}
      type="button"
    >
      <CardPreview card={card} />
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <div className="min-w-0 truncate text-sm font-medium">{card.name || card.id}</div>
          <Badge className="shrink-0">{cardKindLabel(card.kind)}</Badge>
          {card.customized ? <Badge className="shrink-0">已修改</Badge> : null}
        </div>
        <div className="mt-1 flex min-w-0 flex-wrap gap-x-2 gap-y-1 text-xs text-muted-foreground">
          <span className="max-w-full truncate">{card.faction || card.category || "未分类"}</span>
          {card.realm ? <span className="max-w-full truncate">{card.realm}</span> : null}
          {card.cost !== undefined ? <span className="max-w-full truncate">消耗 {card.cost}</span> : null}
          {card.attack !== undefined ? <span className="max-w-full truncate">攻 {card.attack}</span> : null}
          {card.defense !== undefined ? <span className="max-w-full truncate">防 {card.defense}</span> : null}
        </div>
      </div>
    </button>
  );
}

function BeastCardEditor({ disabled, draft, meta, onChange, onRulesChange, rulesText }: { disabled?: boolean; draft: BeastCard; meta: BeastMeta; onChange: (card: BeastCard) => void; onRulesChange: (value: string) => void; rulesText: string }) {
  function setTextField(key: TextFieldKey, value: string) {
    onChange({ ...draft, [key]: value });
  }

  function setNumberField(key: NumberFieldKey, value: number | undefined) {
    onChange({ ...draft, [key]: value });
  }

  return (
    <div className="grid min-w-0 gap-4">
      <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-medium">基础信息</h2>
            <div className="mt-1 min-w-0 truncate text-xs text-muted-foreground">{draft.id}</div>
          </div>
          {draft.customized ? <Badge className="shrink-0">覆盖配置</Badge> : null}
        </div>
        <div className="grid min-w-0 gap-3 md:grid-cols-2 2xl:grid-cols-3">
          <TextField disabled={disabled} label="名称" onChange={(value) => setTextField("name", value)} value={draft.name} />
          <SelectOrInputField disabled={disabled} label="境界" onChange={(value) => setTextField("realm", value)} options={realmOptions(meta, draft.realm)} value={draft.realm} />
          <SelectOrInputField disabled={disabled} label="阵营" onChange={(value) => setTextField("faction", value)} options={meta.factions} value={draft.faction} />
          <NumberField disabled={disabled} label="消耗" onChange={(value) => setNumberField("cost", value)} value={draft.cost} />
          <NumberField disabled={disabled} label="攻击" onChange={(value) => setNumberField("attack", value)} value={draft.attack} />
          <NumberField disabled={disabled} label="防御" onChange={(value) => setNumberField("defense", value)} value={draft.defense} />
          <NumberField disabled={disabled} label="卡池数量" onChange={(value) => setNumberField("pool_copies", value)} value={draft.pool_copies} />
        </div>
      </section>

      <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
        <h2 className="truncate text-base font-medium">结构字段</h2>
        <div className="grid min-w-0 gap-3 md:grid-cols-2 2xl:grid-cols-3">
          <NumberField disabled={disabled} label="阶层" onChange={(value) => setNumberField("tier", value)} value={draft.tier} />
          <SelectOrInputField disabled={disabled} label="元素" onChange={(value) => setTextField("element", value)} options={meta.elements} value={draft.element} />
          <SelectOrInputField disabled={disabled} label="类别" onChange={(value) => setTextField("category", value)} options={meta.categories} value={draft.category} />
          <SelectOrInputField disabled={disabled} label="目标" onChange={(value) => setTextField("target", value)} options={meta.targets ?? DEFAULT_TARGETS} value={draft.target} />
          <TextField disabled={disabled} label="画像 ID" onChange={(value) => setTextField("portrait_id", value)} value={draft.portrait_id} />
          <TextField disabled={disabled} label="图标 ID" onChange={(value) => setTextField("icon_id", value)} value={draft.icon_id ?? draft.icon} />
          <TextField disabled={disabled} label="来源境界" onChange={(value) => setTextField("source_realm", value)} value={draft.source_realm} />
          <TextField disabled={disabled} label="原型" onChange={(value) => setTextField("archetype", value)} value={draft.archetype} />
        </div>
      </section>

      <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
        <h2 className="truncate text-base font-medium">文本与规则</h2>
        <div className="grid min-w-0 gap-3 lg:grid-cols-3">
          <TextAreaField disabled={disabled} label="效果" onChange={(value) => setTextField("effect", value)} value={draft.effect} />
          <TextAreaField disabled={disabled} label="故事" onChange={(value) => setTextField("story", value)} value={draft.story} />
          <TextAreaField disabled={disabled} label="规则 JSON" onChange={onRulesChange} value={rulesText} />
        </div>
      </section>
    </div>
  );
}

function EditorHeader({ dirty, draft, onReload, onRestore, onSave, saveError, saveState }: { dirty: boolean; draft: BeastCard; onReload: () => void; onRestore: () => void; onSave: () => void; saveError: string; saveState: SaveState }) {
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="min-w-0 truncate text-lg font-semibold">{draft.name || draft.id}</h2>
          <Badge className="shrink-0">{statusLabel(dirty, saveState)}</Badge>
        </div>
        <div className="mt-1 flex min-w-0 flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="truncate">{draft.id}</span>
          <span className="truncate">{cardKindLabel(draft.kind)}</span>
          <span className="truncate">{draft.faction || draft.category || "未分类"}</span>
          {draft.realm ? <span className="truncate">{draft.realm}</span> : null}
        </div>
        {saveError ? <div className="mt-2 text-sm text-destructive">{saveError}</div> : null}
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <Button disabled={saveState === "saving"} onClick={onReload}>
          <RefreshCcw className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>重载</span>
        </Button>
        <Button disabled={saveState === "saving" || !draft.customized} onClick={onRestore}>
          <RotateCcw className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>恢复默认</span>
        </Button>
        <PrimaryButton disabled={!dirty || saveState === "saving"} onClick={onSave}>
          <Save className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>保存</span>
        </PrimaryButton>
      </div>
    </div>
  );
}

export function BeastCardsPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [cards, setCards] = useState<BeastCard[]>([]);
  const [meta, setMeta] = useState<BeastMeta>({});
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const [faction, setFaction] = useState("");
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
  const factionOptions = useMemo(() => optionValues(meta.factions, "").concat(uniqueSorted(cards.map((card) => card.faction || card.category))).filter((value, index, values) => value && values.indexOf(value) === index), [cards, meta.factions]);
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
  const visibleCards = filteredCards.slice(0, MAX_VISIBLE_CARDS);

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
      if (!nextCards.length) {
        selectedIdRef.current = "";
        setSelectedId("");
        setDraft(null);
        setOriginalDraft(null);
        setRulesText("{}");
        return true;
      }
      const preferredId = options.keepSelectionId ?? selectedIdRef.current;
      const nextSelected = nextCards.find((card) => card.id === preferredId) ?? nextCards[0];
      const nextDraft = cloneCard(nextSelected);
      selectedIdRef.current = nextSelected.id;
      setSelectedId(nextSelected.id);
      setDraft(nextDraft);
      setOriginalDraft(cloneCard(nextSelected));
      setRulesText(JSON.stringify(nextSelected.rules ?? {}, null, 2));
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
    <div className="grid min-w-0 gap-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold tracking-normal">御兽卡牌</h1>
          <p className="mt-1 truncate text-sm text-muted-foreground">筛选卡牌并编辑御兽秘境覆盖字段</p>
        </div>
        <Badge className="shrink-0">{cards.length} 张</Badge>
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[460px_minmax(0,1fr)]">
        <Card className="grid min-w-0 content-start gap-4 rounded-md p-4">
          <div className="grid min-w-0 gap-2">
            <div className="relative min-w-0">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <Input className="pl-9" disabled={saving} onChange={(event) => setQuery(event.target.value)} placeholder="卡牌名称、ID、效果" value={query} />
            </div>
            <div className="grid min-w-0 gap-2 sm:grid-cols-2">
              <Select disabled={saving} onChange={(event) => setKind(event.target.value)} value={kind}>
                <option value="">全部类型</option>
                <option value="beast">随从</option>
                <option value="spell">法术</option>
              </Select>
              <Select disabled={saving} onChange={(event) => setFaction(event.target.value)} value={faction}>
                <option value="">全部阵营</option>
                {factionOptions.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {loading ? <LoadingState label="正在载入御兽卡牌" /> : null}
          {error ? <ErrorState message={error} onRetry={() => void loadCards({ keepSelectionId: selectedId })} /> : null}
          {!loading && !error && visibleCards.length ? (
            <div className="grid max-h-[calc(100vh-260px)] min-h-0 min-w-0 gap-2 overflow-y-auto pr-1">
              {visibleCards.map((card) => (
                <BeastCardRow card={card} disabled={saving} key={card.id} onSelect={() => selectCard(card)} selected={card.id === selectedId} />
              ))}
              {filteredCards.length > visibleCards.length ? (
                <div className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
                  已显示前 {MAX_VISIBLE_CARDS} 张，继续缩小筛选条件可查看更多结果。
                </div>
              ) : null}
            </div>
          ) : null}
          {!loading && !error && !visibleCards.length ? <EmptyState title="未找到卡牌" detail="换一个关键词、类型或阵营再试。" /> : null}
        </Card>

        <Card className="min-w-0 rounded-md p-4">
          {!draft && !loading ? (
            <div className="grid min-h-72 place-items-center rounded-md border border-dashed border-border p-6 text-center">
              <div className="min-w-0">
                <Shield className="mx-auto h-8 w-8 text-muted-foreground" aria-hidden="true" />
                <div className="mt-3 font-medium">选择卡牌</div>
                <div className="mt-1 text-sm text-muted-foreground">从左侧列表选择一张卡牌后编辑覆盖字段。</div>
              </div>
            </div>
          ) : null}

          {draft ? (
            <div className="grid min-w-0 gap-4">
              <EditorHeader dirty={dirty} draft={draft} onReload={() => void reloadSelected()} onRestore={() => void restoreDefault()} onSave={() => void saveCard()} saveError={saveError} saveState={saveState} />
              <div className="flex min-w-0 items-center gap-3 rounded-md border border-border bg-card p-3">
                <CardPreview card={draft} />
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium">{draft.name || draft.id}</div>
                  <div className="mt-1 truncate text-xs text-muted-foreground">
                    {cardKindLabel(draft.kind)} · {realmName(meta.realms, draft.realm || draft.tier) || "未设境界"}
                  </div>
                </div>
              </div>
              <BeastCardEditor disabled={saving} draft={draft} meta={meta} onChange={setDraft} onRulesChange={setRulesText} rulesText={rulesText} />
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
