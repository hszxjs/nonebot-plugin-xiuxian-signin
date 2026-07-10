import { Alert, Button, Empty, Spin } from "antd";

export function LoadingState({ label = "正在载入数据" }: { label?: string }) {
  return (
    <div className="state-block">
      <Spin tip={`${label}...`}>
        <div className="state-spin-space" />
      </Spin>
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return <Empty description={detail ? `${title}：${detail}` : title} image={Empty.PRESENTED_IMAGE_SIMPLE} />;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <Alert
      action={
        onRetry ? (
          <Button onClick={onRetry} size="small">
            重试
          </Button>
        ) : null
      }
      message={message}
      showIcon
      type="error"
    />
  );
}
