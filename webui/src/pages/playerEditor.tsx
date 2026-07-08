import { Plus, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Select } from "../components/ui/select";
import type { PlayerMeta } from "../lib/types";
import {
  PLAYER_SECTIONS,
  createValue,
  defaultArrayItem,
  ensureCurrentOption,
  fieldLabel,
  isBooleanField,
  isDateField,
  isJsonRecord,
  isNumberField,
  orderedKeys,
  optionsForField,
  parseFieldValue,
  type JsonRecord,
  type JsonValue,
  type ValueKind,
} from "./playerMeta";

type PlayerEditorProps = {
  disabled?: boolean;
  meta?: PlayerMeta;
  onChange: (record: JsonRecord) => void;
  record: JsonRecord;
};

type EditorNodeProps = {
  disabled?: boolean;
  fieldKey: string;
  meta?: PlayerMeta;
  onChange: (value: JsonValue) => void;
  onDelete?: () => void;
  path: string[];
  value: JsonValue;
};

const VALUE_KINDS: Array<{ label: string; value: ValueKind }> = [
  { label: "文本", value: "string" },
  { label: "数字", value: "number" },
  { label: "开关", value: "boolean" },
  { label: "对象", value: "object" },
  { label: "列表", value: "array" },
];

function setObjectValue(record: JsonRecord, key: string, value: JsonValue): JsonRecord {
  return { ...record, [key]: value };
}

function removeObjectKey(record: JsonRecord, key: string): JsonRecord {
  const next = { ...record };
  delete next[key];
  return next;
}

function setArrayValue(items: JsonValue[], index: number, value: JsonValue): JsonValue[] {
  return items.map((item, itemIndex) => (itemIndex === index ? value : item));
}

function removeArrayItem(items: JsonValue[], index: number): JsonValue[] {
  return items.filter((_, itemIndex) => itemIndex !== index);
}

function safeInputValue(value: JsonValue) {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return "";
}

function normalizeDateValue(value: JsonValue) {
  return safeInputValue(value).slice(0, 10);
}

function AddFieldControl({
  disabled,
  existingKeys,
  onAdd,
  path,
}: {
  disabled?: boolean;
  existingKeys: string[];
  onAdd: (key: string, value: JsonValue) => void;
  path: string[];
}) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<ValueKind>("string");
  const normalizedName = name.trim();
  const exists = existingKeys.includes(normalizedName);

  function addField() {
    if (!normalizedName || exists) {
      return;
    }
    onAdd(normalizedName, createValue(kind, normalizedName, path));
    setName("");
    setKind("string");
  }

  return (
    <div className="grid min-w-0 gap-2 rounded-md border border-dashed border-border p-3 sm:grid-cols-[minmax(0,1fr)_140px_auto]">
      <Input
        aria-label="新增字段名"
        disabled={disabled}
        onChange={(event) => setName(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            addField();
          }
        }}
        placeholder="新增字段名"
        value={name}
      />
      <Select
        aria-label="新增字段类型"
        disabled={disabled}
        onChange={(event) => setKind(event.target.value as ValueKind)}
        value={kind}
      >
        {VALUE_KINDS.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label}
          </option>
        ))}
      </Select>
      <Button disabled={disabled || !normalizedName || exists} onClick={addField}>
        <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>新增</span>
      </Button>
    </div>
  );
}

function FieldShell({
  children,
  fieldKey,
  onDelete,
  disabled,
}: {
  children: ReactNode;
  disabled?: boolean;
  fieldKey: string;
  onDelete?: () => void;
}) {
  return (
    <div className="grid min-w-0 gap-2 rounded-md border border-border p-3">
      <div className="flex min-w-0 items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-medium">{fieldLabel(fieldKey)}</div>
          <div className="truncate text-xs text-muted-foreground">{fieldKey}</div>
        </div>
        {onDelete ? (
          <Button aria-label={`删除 ${fieldLabel(fieldKey)}`} className="h-8 w-8 shrink-0 px-0" disabled={disabled} onClick={onDelete}>
            <Trash2 className="h-4 w-4" aria-hidden="true" />
          </Button>
        ) : null}
      </div>
      {children}
    </div>
  );
}

function ScalarEditor({ disabled, fieldKey, meta, onChange, path, value }: EditorNodeProps) {
  const options = ensureCurrentOption(optionsForField(fieldKey, path, meta), value);

  if (typeof value === "boolean" || isBooleanField(fieldKey)) {
    return (
      <label className="inline-flex min-w-0 items-center gap-2 text-sm">
        <input
          checked={Boolean(value)}
          className="h-4 w-4 shrink-0 accent-primary"
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
          type="checkbox"
        />
        <span className="truncate">{Boolean(value) ? "开启" : "关闭"}</span>
      </label>
    );
  }

  if (options.length) {
    return (
      <Select disabled={disabled} onChange={(event) => onChange(parseFieldValue(fieldKey, value, event.target.value))} value={safeInputValue(value)}>
        <option value="">未设置</option>
        {options.map((option) => (
          <option key={`${option.value}:${option.label}`} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    );
  }

  if (typeof value === "number" || isNumberField(fieldKey)) {
    return (
      <Input
        disabled={disabled}
        onChange={(event) => onChange(parseFieldValue(fieldKey, value, event.target.value))}
        type="number"
        value={safeInputValue(value)}
      />
    );
  }

  if (isDateField(fieldKey)) {
    return (
      <Input
        disabled={disabled}
        onChange={(event) => onChange(event.target.value || null)}
        type="date"
        value={normalizeDateValue(value)}
      />
    );
  }

  return (
    <Input
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
      value={safeInputValue(value)}
    />
  );
}

function ObjectEditor({ disabled, fieldKey, meta, onChange, path, value }: EditorNodeProps) {
  const record = isJsonRecord(value) ? value : {};
  const keys = orderedKeys(record);

  return (
    <div className="grid min-w-0 gap-3">
      {keys.length ? (
        <div className="grid min-w-0 gap-3">
          {keys.map((key) => (
            <EditorNode
              disabled={disabled}
              fieldKey={key}
              key={key}
              meta={meta}
              onChange={(nextValue) => onChange(setObjectValue(record, key, nextValue))}
              onDelete={() => onChange(removeObjectKey(record, key))}
              path={[...path, key]}
              value={record[key]}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">暂无字段</div>
      )}
      <AddFieldControl
        disabled={disabled}
        existingKeys={keys}
        onAdd={(key, nextValue) => onChange(setObjectValue(record, key, nextValue))}
        path={path}
      />
    </div>
  );
}

function ArrayEditor({ disabled, fieldKey, meta, onChange, path, value }: EditorNodeProps) {
  const items = Array.isArray(value) ? value : [];

  function addItem() {
    onChange([...items, defaultArrayItem(fieldKey, path)]);
  }

  return (
    <div className="grid min-w-0 gap-3">
      {items.length ? (
        <div className="grid min-w-0 gap-3">
          {items.map((item, index) => (
            <EditorNode
              disabled={disabled}
              fieldKey={`${fieldKey} ${index + 1}`}
              key={index}
              meta={meta}
              onChange={(nextValue) => onChange(setArrayValue(items, index, nextValue))}
              onDelete={() => onChange(removeArrayItem(items, index))}
              path={[...path, String(index)]}
              value={item}
            />
          ))}
        </div>
      ) : (
        <div className="rounded-md border border-dashed border-border p-3 text-sm text-muted-foreground">暂无项目</div>
      )}
      <Button className="w-fit" disabled={disabled} onClick={addItem}>
        <Plus className="h-4 w-4 shrink-0" aria-hidden="true" />
        <span>新增项目</span>
      </Button>
    </div>
  );
}

function EditorNode(props: EditorNodeProps) {
  const { disabled, fieldKey, onDelete, value } = props;

  if (Array.isArray(value)) {
    return (
      <FieldShell disabled={disabled} fieldKey={fieldKey} onDelete={onDelete}>
        <ArrayEditor {...props} />
      </FieldShell>
    );
  }

  if (isJsonRecord(value)) {
    return (
      <FieldShell disabled={disabled} fieldKey={fieldKey} onDelete={onDelete}>
        <ObjectEditor {...props} />
      </FieldShell>
    );
  }

  return (
    <FieldShell disabled={disabled} fieldKey={fieldKey} onDelete={onDelete}>
      <ScalarEditor {...props} />
    </FieldShell>
  );
}

function SectionEditor({
  disabled,
  keys,
  meta,
  onChange,
  record,
  title,
}: {
  disabled?: boolean;
  keys: string[];
  meta?: PlayerMeta;
  onChange: (record: JsonRecord) => void;
  record: JsonRecord;
  title: string;
}) {
  const presentKeys = keys.filter((key) => key in record);

  if (!presentKeys.length) {
    return null;
  }

  return (
    <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
      <h2 className="truncate text-base font-medium">{title}</h2>
      <div className="grid min-w-0 gap-3 md:grid-cols-2 2xl:grid-cols-3">
        {presentKeys.map((key) => (
          <EditorNode
            disabled={disabled}
            fieldKey={key}
            key={key}
            meta={meta}
            onChange={(nextValue) => onChange(setObjectValue(record, key, nextValue))}
            onDelete={key === "user_id" ? undefined : () => onChange(removeObjectKey(record, key))}
            path={[key]}
            value={record[key]}
          />
        ))}
      </div>
    </section>
  );
}

export function PlayerEditor({ disabled, meta, onChange, record }: PlayerEditorProps) {
  const sectionKeys = useMemo<Set<string>>(() => new Set(PLAYER_SECTIONS.flatMap((section) => [...section.keys])), []);
  const remainingKeys = orderedKeys(record).filter((key) => !sectionKeys.has(key));

  return (
    <div className="grid min-w-0 gap-4">
      <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
        <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
          <h2 className="truncate text-base font-medium">字段管理</h2>
          <span className="truncate text-xs text-muted-foreground">当前 {Object.keys(record).length} 个字段</span>
        </div>
        <AddFieldControl
          disabled={disabled}
          existingKeys={Object.keys(record)}
          onAdd={(key, value) => onChange(setObjectValue(record, key, value))}
          path={[]}
        />
      </section>

      {PLAYER_SECTIONS.map((section) => (
        <SectionEditor
          disabled={disabled}
          keys={[...section.keys]}
          key={section.title}
          meta={meta}
          onChange={onChange}
          record={record}
          title={section.title}
        />
      ))}

      {remainingKeys.length ? (
        <section className="grid min-w-0 gap-3 rounded-md border border-border bg-card p-4">
          <h2 className="truncate text-base font-medium">其他字段</h2>
          <div className="grid min-w-0 gap-3 md:grid-cols-2 2xl:grid-cols-3">
            {remainingKeys.map((key) => (
              <EditorNode
                disabled={disabled}
                fieldKey={key}
                key={key}
                meta={meta}
                onChange={(nextValue) => onChange(setObjectValue(record, key, nextValue))}
                onDelete={() => onChange(removeObjectKey(record, key))}
                path={[key]}
                value={record[key]}
              />
            ))}
          </div>
        </section>
      ) : null}

      {Object.keys(record).length === 0 ? (
        <section className="rounded-md border border-dashed border-border bg-card p-6 text-sm text-muted-foreground">
          当前玩家档案没有字段，可以从上方新增。
        </section>
      ) : null}
    </div>
  );
}
