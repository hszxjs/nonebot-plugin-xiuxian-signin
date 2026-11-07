import { LockOutlined, UserOutlined } from "@ant-design/icons"
import {
  Alert,
  App as AntdApp,
  Button,
  Card,
  Form,
  Input,
  Spin,
  Typography,
} from "antd"
import type { ReactNode } from "react"
import { createContext, useContext, useEffect, useState } from "react"

import { changePassword, login, onSessionChange, useSession } from "@/lib/api"

const MIN_PASSWORD_LENGTH = 16

const AuthContext = createContext<{ username: string }>({ username: "" })

export function useAuthUsername() {
  return useContext(AuthContext).username
}

function AuthShell({
  title,
  description,
  children,
}: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <div className="auth-page">
      <Card className="auth-card">
        <Typography.Title level={3}>{title}</Typography.Title>
        <Typography.Paragraph type="secondary">
          {description}
        </Typography.Paragraph>
        {children}
      </Card>
    </div>
  )
}

function LoginForm({ onDone }: { onDone: () => void }) {
  const { message } = AntdApp.useApp()
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  return (
    <AuthShell
      title="修仙签到后台"
      description="请输入账号与密码登录。登录状态会保持 7 天。"
    >
      {error ? (
        <Alert className="auth-alert" type="error" showIcon message={error} />
      ) : null}
      <Form
        layout="vertical"
        requiredMark={false}
        onFinish={(values: { username: string; password: string }) => {
          setSubmitting(true)
          setError("")
          login(values.username.trim(), values.password)
            .then(() => onDone())
            .catch((loginError: unknown) => {
              setError(String(loginError))
              message.error("登录失败")
            })
            .finally(() => setSubmitting(false))
        }}
      >
        <Form.Item
          name="username"
          label="账号"
          rules={[{ required: true, message: "请输入账号" }]}
        >
          <Input
            prefix={<UserOutlined />}
            autoComplete="username"
            placeholder="admin"
            size="large"
          />
        </Form.Item>
        <Form.Item
          name="password"
          label="密码"
          rules={[{ required: true, message: "请输入密码" }]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            autoComplete="current-password"
            size="large"
          />
        </Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          block
          size="large"
          loading={submitting}
        >
          登录
        </Button>
      </Form>
    </AuthShell>
  )
}

function ChangePasswordForm({ onDone }: { onDone: () => void }) {
  const { message } = AntdApp.useApp()
  const [error, setError] = useState("")
  const [submitting, setSubmitting] = useState(false)

  return (
    <AuthShell
      title="首次登录需要修改密码"
      description={`初始密码只在启动日志里显示一次。新密码至少 ${MIN_PASSWORD_LENGTH} 位，改完会立即生效并让其它设备上的登录失效。`}
    >
      {error ? (
        <Alert className="auth-alert" type="error" showIcon message={error} />
      ) : null}
      <Form
        layout="vertical"
        requiredMark={false}
        onFinish={(values: { old_password: string; new_password: string }) => {
          setSubmitting(true)
          setError("")
          changePassword(values.old_password, values.new_password)
            .then(() => {
              message.success("密码已修改")
              onDone()
            })
            .catch((changeError: unknown) => setError(String(changeError)))
            .finally(() => setSubmitting(false))
        }}
      >
        <Form.Item
          name="old_password"
          label="当前密码"
          rules={[{ required: true, message: "请输入当前密码" }]}
        >
          <Input.Password autoComplete="current-password" size="large" />
        </Form.Item>
        <Form.Item
          name="new_password"
          label="新密码"
          rules={[
            { required: true, message: "请输入新密码" },
            {
              min: MIN_PASSWORD_LENGTH,
              message: `密码长度至少 ${MIN_PASSWORD_LENGTH} 位`,
            },
          ]}
        >
          <Input.Password autoComplete="new-password" size="large" />
        </Form.Item>
        <Form.Item
          name="confirm_password"
          label="确认新密码"
          dependencies={["new_password"]}
          rules={[
            { required: true, message: "请再次输入新密码" },
            ({ getFieldValue }) => ({
              validator(_rule, value: string) {
                if (!value || getFieldValue("new_password") === value) {
                  return Promise.resolve()
                }
                return Promise.reject(new Error("两次输入的密码不一致"))
              },
            }),
          ]}
        >
          <Input.Password autoComplete="new-password" size="large" />
        </Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          block
          size="large"
          loading={submitting}
        >
          保存新密码
        </Button>
      </Form>
    </AuthShell>
  )
}

/**
 * 会话闸门：未登录显示登录页，首次登录强制改密，通过后渲染后台主体。
 *
 * 后端在会话失效时返回 401，`api` 会广播 session-change，这里重新校验会话，
 * 因此过期后任意一次请求失败都会把用户带回登录页，而不是各页面各自报错。
 */
export function AuthGate({ children }: { children: ReactNode }) {
  const session = useSession()
  const { mutate } = session

  useEffect(() => onSessionChange(() => void mutate()), [mutate])

  if (session.isLoading) {
    return (
      <div className="auth-page">
        <Spin size="large" />
      </div>
    )
  }

  if (session.error && !session.data) {
    // 会话接口本身报错（服务未就绪/网络断）：给重试，不擅自判定为未登录。
    return (
      <AuthShell
        title="无法连接后台"
        description="会话校验请求失败，请稍后重试。"
      >
        <Alert
          className="auth-alert"
          type="error"
          showIcon
          message={String(session.error)}
        />
        <Button onClick={() => void mutate()} block size="large">
          重试
        </Button>
      </AuthShell>
    )
  }

  const data = session.data
  if (!data?.authenticated) {
    return <LoginForm onDone={() => void mutate()} />
  }
  if (data.must_change_password) {
    return <ChangePasswordForm onDone={() => void mutate()} />
  }
  return (
    <AuthContext.Provider value={{ username: data.username ?? "" }}>
      {children}
    </AuthContext.Provider>
  )
}
