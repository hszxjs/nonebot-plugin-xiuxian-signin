import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import { Button, Card, Empty, Input, InputNumber, Select, Space, Switch, Tabs, Typography } from "antd";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
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

const { Text } = Typography;

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
    <Space.Compact block>
      <Input
        aria-label="新增字段名"
        disabled={disabled}
        onChange={(event) => setName(event.target.value)}
        onPressEnter={addField}
        placeholder="新增字段名"
        status={exists ? "error" : undefined}
        value={name}
      />
      <Select<ValueKind>
        aria-label="新增字段类型"
        disabled={disabled}
        onChange={setKind}
        options={VALUE_KINDS}
        value={kind}
      />
      <Button disabled={disabled || !normalizedName || exists} icon={<PlusOutlined />} onClick={addField} type="primary">
        新增
      </Button>
    </Space.Compact>
  );
}

function FieldShell({ children, fieldKey, onDelete, disabled }: { children: ReactNode; disabled?: boolean; fieldKey: string; onDelete?: () => void }) {
  return (
    <Card
      extra={
        onDelete ? (
          <Button aria-label={`删除 ${fieldLabel(fieldKey)}`} disabled={disabled} icon={<DeleteOutlined />} onClick={onDelete} size="small" />
        ) : null
      }
      size="small"
      title={
        <Space direction="vertical" size={0}>
          <Text strong>{fieldLabel(fieldKey)}</Text>
          <Text type="secondary">{fieldKey}</Text>
        </Space>
      }
    >
      {children}
    </Card>
  );
}

function ScalarEditor({ disabled, fieldKey, meta, onChange, path, value }: EditorNodeProps) {
  const options = ensureCurrentOption(optionsForField(fieldKey, path, meta), value);

  if (typeof value === "boolean" || isBooleanField(fieldKey)) {
    return <Switch checked={Boolean(value)} checkedChildren="开启" disabled={disabled} onChange={onChange} unCheckedChildren="关闭" />;
  }

  if (options.length) {
    return (
      <Select
        allowClear
        disabled={disabled}
        onChange={(nextValue) => onChange(parseFieldValue(fieldKey, value, nextValue ?? ""))}
        options={options.map((option) => ({ label: option.label, value: option.value }))}
        placeholder="未设置"
        value={safeInputValue(value) || undefined}
      />
    );
  }

  if (typeof value === "number" || isNumberField(fieldKey)) {
    const numberValue = Number(safeInputValue(value));
    return (
      <InputNumber
        disabled={disabled}
        onChange={(nextValue) => onChange(parseFieldValue(fieldKey, value, String(nextValue ?? "")))}
        value={Number.isFinite(numberValue) ? numberValue : undefined}
      />
    );
  }

  if (isDateField(fieldKey)) {
    return <Input disabled={disabled} onChange={(event) => onChange(event.target.value || null)} type="date" value={normalizeDateValue(value)} />;
  }

  return <Input disabled={disabled} onChange={(event) => onChange(event.target.value)} value={safeInputValue(value)} />;
}

function ObjectEditor({ disabled, fieldKey, meta, onChange, path, value }: EditorNodeProps) {
  const record = isJsonRecord(value) ? value : {};
  const keys = orderedKeys(record);

  return (
    <Space className="field-stack" direction="vertical" size={12}>
      {keys.length ? (
        keys.map((key) => (
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
        ))
      ) : (
        <Empty description="暂无字段" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}
      <AddFieldControl disabled={disabled} existingKeys={keys} onAdd={(key, nextValue) => onChange(setObjectValue(record, key, nextValue))} path={path} />
    </Space>
  );
}

function ArrayEditor({ disabled, fieldKey, meta, onChange, path, value }: EditorNodeProps) {
  const items = Array.isArray(value) ? value : [];

  function addItem() {
    onChange([...items, defaultArrayItem(fieldKey, path)]);
  }

  return (
    <Space className="field-stack" direction="vertical" size={12}>
      {items.length ? (
        items.map((item, index) => (
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
        ))
      ) : (
        <Empty description="暂无项目" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      )}
      <Button disabled={disabled} icon={<PlusOutlined />} onClick={addItem}>
        新增项目
      </Button>
    </Space>
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
}: {
  disabled?: boolean;
  keys: string[];
  meta?: PlayerMeta;
  onChange: (record: JsonRecord) => void;
  record: JsonRecord;
}) {
  const presentKeys = keys.filter((key) => key in record);

  if (!presentKeys.length) {
    return <Empty description="当前分组暂无字段" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <div className="editor-grid">
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
  );
}

export function PlayerEditor({ disabled, meta, onChange, record }: PlayerEditorProps) {
  const sectionKeys = useMemo<Set<string>>(() => new Set(PLAYER_SECTIONS.flatMap((section) => [...section.keys])), []);
  const remainingKeys = orderedKeys(record).filter((key) => !sectionKeys.has(key));

  const items = [
    {
      key: "fields",
      label: "字段管理",
      children: (
        <Space className="field-stack" direction="vertical" size={12}>
          <Text type="secondary">当前 {Object.keys(record).length} 个字段</Text>
          <AddFieldControl disabled={disabled} existingKeys={Object.keys(record)} onAdd={(key, value) => onChange(setObjectValue(record, key, value))} path={[]} />
        </Space>
      ),
    },
    ...PLAYER_SECTIONS.map((section) => ({
      key: section.title,
      label: section.title,
      children: (
        <SectionEditor disabled={disabled} keys={[...section.keys]} meta={meta} onChange={onChange} record={record} />
      ),
    })),
    {
      key: "other",
      label: "其他字段",
      children: remainingKeys.length ? (
        <div className="editor-grid">
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
      ) : (
        <Empty description="暂无其他字段" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      ),
    },
  ];

  if (Object.keys(record).length === 0) {
    return <Empty description="当前玩家档案没有字段，可以从字段管理新增。" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return <Tabs items={items} />;
}
