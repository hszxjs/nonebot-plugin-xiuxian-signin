import { ExclamationCircleOutlined, SearchOutlined } from "@ant-design/icons"
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  Modal,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Typography,
} from "antd"
import type { ReactNode } from "react"

import { formatJson } from "@/lib/format"

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        <Typography.Title level={2}>{title}</Typography.Title>
        {description ? (
          <Typography.Paragraph type="secondary">
            {description}
          </Typography.Paragraph>
        ) : null}
      </div>
      {actions ? <Space wrap>{actions}</Space> : null}
    </div>
  )
}

export function LoadingPanel({
  label = "正在读取后台数据",
}: {
  label?: string
}) {
  return (
    <Space
      orientation="vertical"
      size="large"
      className="full-width"
      aria-label={label}
    >
      <Skeleton active paragraph={{ rows: 3 }} />
      <Skeleton active paragraph={{ rows: 8 }} />
    </Space>
  )
}

export function ErrorPanel({
  title,
  error,
}: {
  title: string
  error: unknown
}) {
  return (
    <Alert type="error" showIcon message={title} description={String(error)} />
  )
}

export function EmptyPanel({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <span>
          {title}：{description}
        </span>
      }
    />
  )
}

export function MetricCard({
  label,
  value,
  description,
}: {
  label: string
  value: ReactNode
  description?: string
}) {
  return (
    <Card size="small">
      <Statistic title={label} value={String(value)} />
      {description ? (
        <Typography.Text type="secondary">{description}</Typography.Text>
      ) : null}
    </Card>
  )
}

export function SearchField({
  value,
  onChange,
  placeholder,
}: {
  value: string
  onChange: (value: string) => void
  placeholder: string
}) {
  return (
    <Input
      allowClear
      prefix={<SearchOutlined />}
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
    />
  )
}

export function TagList({
  values,
  empty = "未设置",
}: {
  values?: string[]
  empty?: string
}) {
  const filtered = (values ?? []).filter(Boolean)
  if (!filtered.length) {
    return <Tag>{empty}</Tag>
  }
  return (
    <Space size={[4, 4]} wrap>
      {filtered.map((value) => (
        <Tag key={value}>{value}</Tag>
      ))}
    </Space>
  )
}

export function JsonTextarea({
  label,
  value,
  onChange,
  readOnly = false,
  rows = 10,
}: {
  label: string
  value: unknown
  onChange?: (value: string) => void
  readOnly?: boolean
  rows?: number
}) {
  return (
    <Card title={label} size="small">
      <Input.TextArea
        value={typeof value === "string" ? value : formatJson(value)}
        onChange={(event) => onChange?.(event.target.value)}
        readOnly={readOnly}
        rows={rows}
      />
    </Card>
  )
}

export function ConfirmAction({
  triggerLabel,
  title,
  description,
  actionLabel,
  onConfirm,
  danger = false,
}: {
  triggerLabel: string
  title: string
  description: string
  actionLabel: string
  onConfirm: () => void
  danger?: boolean
}) {
  return (
    <Button
      type={danger ? "primary" : "default"}
      danger={danger}
      onClick={() =>
        Modal.confirm({
          title,
          icon: <ExclamationCircleOutlined />,
          content: description,
          okText: actionLabel,
          cancelText: "取消",
          onOk: onConfirm,
        })
      }
    >
      {triggerLabel}
    </Button>
  )
}
