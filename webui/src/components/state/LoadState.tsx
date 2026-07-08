import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "../ui/button";

export function LoadingState({ label = "正在载入数据" }: { label?: string }) {
  return (
    <div className="flex min-h-32 items-center gap-3 rounded-md border border-border bg-card p-6 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      <span>{label}...</span>
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div className="rounded-md border border-dashed border-border bg-card p-6">
      <div className="font-medium">{title}</div>
      {detail ? <div className="mt-1 text-sm text-muted-foreground">{detail}</div> : null}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-md border border-destructive/30 bg-card p-6">
      <div className="flex items-start gap-2 text-sm font-medium text-destructive">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        <span>{message}</span>
      </div>
      {onRetry ? (
        <Button className="mt-3" onClick={onRetry}>
          重试
        </Button>
      ) : null}
    </div>
  );
}
