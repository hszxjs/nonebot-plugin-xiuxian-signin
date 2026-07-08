import { ImageIcon, PackageOpen, Plus, RefreshCcw, RotateCcw, Save, Search, Trash2 } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { Badge } from "../components/ui/badge";
import { Button, PrimaryButton } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import { api, getToken } from "../lib/api";
import type { AdminItem, ItemPayload } from "../lib/types";
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";

type SaveState = "idle" | "saving" | "saved" | "error";
type ConfigPayload = { ok: boolean; config: Record<string, unknown> };
type ItemMeta = ItemPayload["meta"];
type TextFieldKey = "category" | "required_realm" | "required_attribute" | "usage" | "source" | "story";
type ListFieldKey = "tiers" | "grades";

const MAX_VISIBLE_ITEMS = 600;

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

function StatusBadge({ dirty, saveState }: { dirty: boolean; saveState: SaveState }) {
  const status = saveState === "saving" ? "保存中" : saveState === "saved" ? "已保存" : dirty ? "未保存" : "同步";
  return <Badge className="shrink-0">{status}</Badge>;
}

function FieldLabel({ label, hint }: { hint?: string; label: string }) {
  return (
    <div className="min-w-0">
      <div className="truncate text-sm font-medium">{label}</div>
      {hint ? <div className="truncate text-xs text-muted-foreground">{hint}</div> : null}
    </div>
  );
}

function TextAreaField({
  disabled,
  label,
  onChange,
  readOnly,
  value,
}: {
  disabled?: boolean;
  label: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  value?: string;
}) {
  return (
    <label className="grid min-w-0 gap-2 rounded-md border border-border p-3">
      <FieldLabel label={label} />
      <textarea
        className="min-h-24 w-full min-w-0 resize-y rounded-md border border-border bg-card px-3 py-2 text-sm text-card-foreground shadow-sm outline-none transition placeholder:text-muted-foreground focus:border-primary disabled:cursor-not-allowed disabled:opacity-70"
        disabled={disabled || readOnly}
        onChange={(event) => onChange?.(event.target.value)}
        value={value ?? ""}
      />
    </label>
  );
}

function SelectOrInputField({
  disabled,
  label,
  onChange,
  options,
  value,
}: {
  disabled?: boolean;
  label: string;
  onChange: (value: string) => void;
  options?: string[];
  value?: string;
}) {
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

function RepeatableListField({
  disabled,
  label,
  onChange,
  options,
  values,
}: {
  disabled?: boolean;
  label: string;
  onChange: (values: string[]) => void;
  options?: string[];
  values?: string[];
}) {
  const items = values ?? [];

  function setItem(index: number, value: string) {
    onChange(items.map((item, itemIndex) => (itemIndex === index ? value : item)));
  }

  function addItem() {
    const fallback = options?.find((option) => !items.includes(option)) ?? "";
    onChange([...items, fallback]);
  }

  function removeItem(index: number) {
    onChange(items.filter((_, itemIndex) => itemIndex !== index));
  }

  return (
    <div className="grid min-w-0 gap-2 rounded-md border border-border p-3">
      <div className="flex min-w-0 flex-wrap items-center justify-between gap-2">
        <FieldLabel hint={`当前 ${items.length} 项`} label={label} />
        <Button className="shrink-0" disabled={disabled} onClick={addItem}>
          <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>新增</span>
        </Button>
      </div>
      {items.length ? (
        <div className="grid min-w-0 gap-2">
          {items.map((item, index) => {
            const availableOptions = optionValues(options, item);
            return (
              <div className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto]" key={`${label}:${index}`}>
                {availableOptions.length ? (
                  <Select disabled={disabled} onChange={(event) => setItem(index, event.target.value)} value={item}>
                    <option value="">未设置</option>
                    {availableOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </Select>
                ) : (
                  <Input disabled={disabled} onChange={(event) => setItem(index, event.target.value)} value={item} />
                )}
                <Button aria-label={`删除${label}${index + 1}`} className="h-9 w-9 shrink-0 px-0" disabled={disabled} onClick={() => removeItem(index)}>
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">暂无项目</div>
      )}
    </div>
  );
}

function ItemRow({ disabled, item, onSelect, selected }: { disabled?: boolean; item: AdminItem; onSelect: () => void; selected: boolean }) {
  const src = iconUrl(item.icon);
  const tiers = compactList(item.tiers);
  const grades = compactList(item.grades);

  return (
    <button
      aria-disabled={disabled}
      className={[
        "grid min-w-0 grid-cols-[48px_minmax(0,1fr)] gap-3 rounded-md border border-border p-3 text-left transition",
        selected ? "bg-muted" : "bg-card hover:bg-muted/70",
        disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer",
      ].join(" ")}
      disabled={disabled}
      onClick={onSelect}
      type="button"
    >
      <div className="grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-md border border-border bg-background">
        {src ? <img alt="" className="max-h-11 max-w-11 object-contain" src={src} /> : <ImageIcon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />}
      </div>
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <div className="min-w-0 truncate text-sm font-medium">{item.name}</div>
          {item.customized ? <Badge className="shrink-0">已修改</Badge> : null}
        </div>
        <div className="mt-1 flex min-w-0 flex-wrap gap-x-2 gap-y-1 text-xs text-muted-foreground">
          <span className="max-w-full truncate">{item.category || "未分类"}</span>
          {tiers.length ? <span className="max-w-full truncate">{tiers.join(" / ")}</span> : null}
          {grades.length ? <span className="max-w-full truncate">{grades.join(" / ")}</span> : null}
        </div>
      </div>
    </button>
  );
}

function ItemEditor({
  disabled,
  draft,
  meta,
  onChange,
}: {
  disabled?: boolean;
  draft: AdminItem;
  meta: ItemMeta;
  onChange: (item: AdminItem) => void;
}) {
  function setField(key: TextFieldKey, value: string) {
    onChange({ ...draft, [key]: value });
  }

  function setListField(key: ListFieldKey, values: string[]) {
    onChange({ ...draft, [key]: values });
  }

  const requiredRealm = draft.required_realm ?? draft.realm ?? "";

  return (
    <div className="grid min-w-0 gap-4">
      <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-medium">基础信息</h2>
            <div className="mt-1 min-w-0 truncate text-xs text-muted-foreground">{draft.name}</div>
          </div>
          {draft.customized ? <Badge className="shrink-0">覆盖配置</Badge> : null}
        </div>
        <div className="grid min-w-0 gap-3 md:grid-cols-2 2xl:grid-cols-3">
          <SelectOrInputField disabled={disabled} label="类别" onChange={(value) => setField("category", value)} options={meta.categories} value={draft.category} />
          <SelectOrInputField disabled={disabled} label="需求境界" onChange={(value) => setField("required_realm", value)} options={meta.realms} value={requiredRealm} />
          <SelectOrInputField disabled={disabled} label="需求灵根" onChange={(value) => setField("required_attribute", value)} options={meta.attributes} value={draft.required_attribute} />
          <RepeatableListField disabled={disabled} label="阶级" onChange={(values) => setListField("tiers", values)} options={meta.tiers} values={draft.tiers} />
          <RepeatableListField disabled={disabled} label="品质" onChange={(values) => setListField("grades", values)} options={meta.grades} values={draft.grades} />
        </div>
      </section>

      <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
        <h2 className="truncate text-base font-medium">说明文本</h2>
        <div className="grid min-w-0 gap-3 lg:grid-cols-3">
          <TextAreaField disabled={disabled} label="用途" onChange={(value) => setField("usage", value)} value={draft.usage} />
          <TextAreaField disabled={disabled} label="来源" onChange={(value) => setField("source", value)} value={draft.source} />
          <TextAreaField disabled={disabled} label="故事" onChange={(value) => setField("story", value)} value={draft.story} />
        </div>
        {draft.parameter_note ? <TextAreaField disabled={disabled} label="参数说明" readOnly value={draft.parameter_note} /> : null}
      </section>
    </div>
  );
}

function EditorHeader({
  dirty,
  draft,
  onReload,
  onRestore,
  onSave,
  saveError,
  saveState,
}: {
  dirty: boolean;
  draft: AdminItem;
  onReload: () => void;
  onRestore: () => void;
  onSave: () => void;
  saveError: string;
  saveState: SaveState;
}) {
  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="min-w-0 truncate text-lg font-semibold">{draft.name}</h2>
          <StatusBadge dirty={dirty} saveState={saveState} />
        </div>
        <div className="mt-1 flex min-w-0 flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="truncate">{draft.category || "未分类"}</span>
          {compactList(draft.tiers).length ? <span className="truncate">{compactList(draft.tiers).join(" / ")}</span> : null}
          {compactList(draft.grades).length ? <span className="truncate">{compactList(draft.grades).join(" / ")}</span> : null}
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

export function ItemsPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [items, setItems] = useState<AdminItem[]>([]);
  const [meta, setMeta] = useState<ItemMeta>({});
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [tier, setTier] = useState("");
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
  const visibleItems = filteredItems.slice(0, MAX_VISIBLE_ITEMS);

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
      if (!nextItems.length) {
        selectedNameRef.current = "";
        setSelectedName("");
        setDraft(null);
        setOriginalDraft(null);
        return true;
      }
      const preferredName = options.keepSelectionName ?? selectedNameRef.current;
      const nextSelected = nextItems.find((item) => item.name === preferredName) ?? nextItems[0];
      const nextDraft = cloneItem(nextSelected);
      selectedNameRef.current = nextSelected.name;
      setSelectedName(nextSelected.name);
      setDraft(nextDraft);
      setOriginalDraft(cloneItem(nextSelected));
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
    <div className="grid min-w-0 gap-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold tracking-normal">物品图鉴</h1>
          <p className="mt-1 truncate text-sm text-muted-foreground">筛选物品并编辑结构化覆盖字段</p>
        </div>
        <Badge className="shrink-0">{items.length} 件</Badge>
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[440px_minmax(0,1fr)]">
        <Card className="grid min-w-0 content-start gap-4 rounded-md p-4">
          <div className="grid min-w-0 gap-2">
            <div className="relative min-w-0">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <Input className="pl-9" disabled={saving} onChange={(event) => setQuery(event.target.value)} placeholder="物品名称、用途、来源" value={query} />
            </div>
            <div className="grid min-w-0 gap-2 sm:grid-cols-2">
              <Select disabled={saving} onChange={(event) => setCategory(event.target.value)} value={category}>
                <option value="">全部类别</option>
                {(meta.categories ?? []).map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
              <Select disabled={saving} onChange={(event) => setTier(event.target.value)} value={tier}>
                <option value="">全部阶级</option>
                {(meta.tiers ?? []).map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </Select>
            </div>
          </div>

          {loading ? <LoadingState label="正在载入物品图鉴" /> : null}
          {error ? <ErrorState message={error} onRetry={() => void loadItems({ keepSelectionName: selectedName })} /> : null}
          {!loading && !error && visibleItems.length ? (
            <div className="grid max-h-[calc(100vh-260px)] min-h-0 min-w-0 gap-2 overflow-y-auto pr-1">
              {visibleItems.map((item) => (
                <ItemRow disabled={saving} item={item} key={item.name} onSelect={() => selectItem(item)} selected={item.name === selectedName} />
              ))}
              {filteredItems.length > visibleItems.length ? (
                <div className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">
                  已显示前 {MAX_VISIBLE_ITEMS} 件，继续缩小筛选条件可查看更多结果。
                </div>
              ) : null}
            </div>
          ) : null}
          {!loading && !error && !visibleItems.length ? <EmptyState title="未找到物品" detail="换一个关键词、类别或阶级再试。" /> : null}
        </Card>

        <Card className="min-w-0 rounded-md p-4">
          {!draft && !loading ? (
            <div className="grid min-h-72 place-items-center rounded-md border border-dashed border-border p-6 text-center">
              <div className="min-w-0">
                <PackageOpen className="mx-auto h-8 w-8 text-muted-foreground" aria-hidden="true" />
                <div className="mt-3 font-medium">选择物品</div>
                <div className="mt-1 text-sm text-muted-foreground">从左侧列表选择一个物品后编辑图鉴字段。</div>
              </div>
            </div>
          ) : null}

          {draft ? (
            <div className="grid min-w-0 gap-4">
              <EditorHeader
                dirty={dirty}
                draft={draft}
                onReload={() => void reloadSelected()}
                onRestore={() => void restoreDefault()}
                onSave={() => void saveItem()}
                saveError={saveError}
                saveState={saveState}
              />
              <ItemEditor disabled={saving} draft={draft} meta={meta} onChange={setDraft} />
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
