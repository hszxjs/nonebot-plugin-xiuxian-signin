import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react"
import { App as AntdApp } from "antd"
import { SWRConfig } from "swr"
import { afterEach, describe, expect, it, vi } from "vitest"

import { AuthGate } from "@/features/auth/auth-gate"

type SessionState = {
  authenticated: boolean
  username?: string
  must_change_password?: boolean
}

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "content-type": "application/json" },
  })
}

/**
 * 用状态机模拟后台：/api/session 反映当前会话，登录与改密会推进状态。
 */
function installFetch(initial: SessionState) {
  const state = { ...initial }
  const calls: Array<{ url: string; method: string; body: string }> = []

  const fetchMock = vi.fn(async (input: Request) => {
    const request = input as Request
    const url = new URL(request.url)
    const body = request.method === "GET" ? "" : await request.clone().text()
    calls.push({ url: url.pathname, method: request.method, body })

    if (url.pathname.endsWith("/api/session")) {
      return jsonResponse({
        ok: true,
        authenticated: state.authenticated,
        username: state.username,
        must_change_password: state.must_change_password ?? false,
      })
    }
    if (url.pathname.endsWith("/api/login")) {
      const credentials = JSON.parse(body || "{}") as {
        username?: string
        password?: string
      }
      if (credentials.password !== "correct-horse-battery") {
        return jsonResponse({ ok: false, error: "账号或密码不正确" }, 401)
      }
      state.authenticated = true
      state.username = credentials.username
      return jsonResponse({
        ok: true,
        username: credentials.username,
        must_change_password: state.must_change_password ?? false,
      })
    }
    if (url.pathname.endsWith("/api/password")) {
      state.must_change_password = false
      return jsonResponse({ ok: true, must_change_password: false })
    }
    return jsonResponse({ ok: false, error: "unexpected request" }, 404)
  })

  vi.stubGlobal("fetch", fetchMock)
  return { calls, state }
}

function renderGate() {
  return render(
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      <AntdApp>
        <AuthGate>
          <div>后台主体</div>
        </AuthGate>
      </AntdApp>
    </SWRConfig>,
  )
}

describe("AuthGate", () => {
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it("shows the login form when there is no session, then enters the admin shell", async () => {
    const { calls } = installFetch({ authenticated: false })
    renderGate()

    expect(
      await screen.findByText("请输入账号与密码登录。登录状态会保持 7 天。"),
    ).toBeTruthy()

    fireEvent.change(screen.getByLabelText("账号"), {
      target: { value: "admin" },
    })
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "correct-horse-battery" },
    })
    fireEvent.click(screen.getByRole("button", { name: /登\s*录/ }))

    expect(await screen.findByText("后台主体")).toBeTruthy()

    const loginCall = calls.find((call) => call.url.endsWith("/api/login"))
    expect(loginCall?.method).toBe("POST")
    expect(JSON.parse(loginCall?.body || "{}")).toEqual({
      username: "admin",
      password: "correct-horse-battery",
    })
  })

  it("keeps the user on the login form when the password is wrong", async () => {
    installFetch({ authenticated: false })
    renderGate()

    fireEvent.change(await screen.findByLabelText("账号"), {
      target: { value: "admin" },
    })
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "wrong-password" },
    })
    fireEvent.click(screen.getByRole("button", { name: /登\s*录/ }))

    expect(await screen.findByText("账号或密码不正确")).toBeTruthy()
    expect(screen.queryByText("后台主体")).toBeNull()
  })

  it("forces a password change before rendering the admin shell", async () => {
    installFetch({
      authenticated: true,
      username: "admin",
      must_change_password: true,
    })
    renderGate()

    expect(await screen.findByText("首次登录需要修改密码")).toBeTruthy()
    expect(screen.queryByText("后台主体")).toBeNull()

    fireEvent.change(screen.getByLabelText("当前密码"), {
      target: { value: "correct-horse-battery" },
    })
    fireEvent.change(screen.getByLabelText("新密码"), {
      target: { value: "a-very-long-new-password" },
    })
    fireEvent.change(screen.getByLabelText("确认新密码"), {
      target: { value: "a-very-long-new-password" },
    })
    fireEvent.click(screen.getByRole("button", { name: "保存新密码" }))

    await waitFor(() => expect(screen.getByText("后台主体")).toBeTruthy())
  })

  it("renders the admin shell directly for a valid session", async () => {
    installFetch({ authenticated: true, username: "admin" })
    renderGate()

    expect(await screen.findByText("后台主体")).toBeTruthy()
  })
})
