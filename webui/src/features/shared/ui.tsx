import type { ReactNode } from "react"
import { IconAlertTriangle, IconSearch } from "@tabler/icons-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty"
import { Field, FieldContent, FieldDescription, FieldGroup, FieldTitle } from "@/components/ui/field"
import { InputGroup, InputGroupAddon, InputGroupInput } from "@/components/ui/input-group"
import { Skeleton } from "@/components/ui/skeleton"
import { Slider } from "@/components/ui/slider"
import { Textarea } from "@/components/ui/textarea"
import { formatJson, formatPercent, rateToSliderValue } from "@/lib/format"

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
    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div className="flex flex-col gap-1">
        <h1>{title}</h1>
        {description ? <p>{description}</p> : null}
      </div>
      {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
    </div>
  )
}

export function LoadingPanel({ label = "正在读取后台数据" }: { label?: string }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Skeleton className="h-32" />
      <Skeleton className="h-32" />
      <Skeleton className="h-32" />
      <Skeleton className="h-80 lg:col-span-3" />
      <span className="sr-only">{label}</span>
    </div>
  )
}

export function ErrorPanel({ title, error }: { title: string; error: unknown }) {
  return (
    <Alert variant="destructive">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{String(error)}</AlertDescription>
    </Alert>
  )
}

export function EmptyPanel({ title, description }: { title: string; description: string }) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent />
    </Empty>
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
    <Card size="sm">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle>{value}</CardTitle>
      </CardHeader>
      {description ? (
        <CardContent>
          <CardDescription>{description}</CardDescription>
        </CardContent>
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
    <InputGroup>
      <InputGroupAddon>
        <IconSearch />
      </InputGroupAddon>
      <InputGroupInput value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} />
    </InputGroup>
  )
}

export function BadgeList({ values, empty = "未设置" }: { values?: string[]; empty?: string }) {
  const filtered = (values ?? []).filter(Boolean)
  if (!filtered.length) {
    return <Badge variant="outline">{empty}</Badge>
  }
  return (
    <div className="flex flex-wrap gap-1">
      {filtered.map((value) => (
        <Badge key={value} variant="secondary">
          {value}
        </Badge>
      ))}
    </div>
  )
}

export function JsonTextarea({
  label,
  value,
  onChange,
  readOnly = false,
}: {
  label: string
  value: unknown
  onChange?: (value: string) => void
  readOnly?: boolean
}) {
  return (
    <FieldGroup>
      <Field>
        <FieldContent>
          <FieldTitle>{label}</FieldTitle>
          <FieldDescription>用于查看或编辑暂未结构化拆分的完整 JSON。</FieldDescription>
        </FieldContent>
        <Textarea
          value={typeof value === "string" ? value : formatJson(value)}
          onChange={(event) => onChange?.(event.target.value)}
          readOnly={readOnly}
          rows={10}
        />
      </Field>
    </FieldGroup>
  )
}

export function RateField({
  title,
  description,
  value,
  onChange,
}: {
  title: string
  description: string
  value: number
  onChange: (value: number[]) => void
}) {
  return (
    <Field orientation="responsive">
      <FieldContent>
        <FieldTitle>{title}</FieldTitle>
        <FieldDescription>{description}</FieldDescription>
      </FieldContent>
      <div className="flex min-w-56 items-center gap-3">
        <Slider value={rateToSliderValue(value)} max={100} step={1} onValueChange={onChange} />
        <Badge variant="outline">{formatPercent(value)}</Badge>
      </div>
    </Field>
  )
}

export function ConfirmAction({
  triggerLabel,
  title,
  description,
  actionLabel,
  onConfirm,
  variant = "default",
}: {
  triggerLabel: string
  title: string
  description: string
  actionLabel: string
  onConfirm: () => void
  variant?: "default" | "destructive" | "outline"
}) {
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        <Button variant={variant}>{triggerLabel}</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia>
            <IconAlertTriangle />
          </AlertDialogMedia>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>{actionLabel}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
