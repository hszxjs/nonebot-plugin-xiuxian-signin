import ky from "ky"
import useSWR from "swr"

import type {
  BackupPayload,
  BeastCardsPayload,
  ConfigPayload,
  DashboardPayload,
  EquipmentPayload,
  ItemsPayload,
  MysticConfig,
  MysticPayload,
  PlayerDetailPayload,
  PlayerListPayload,
} from "@/lib/types"

const appRoutes = [
  "/players",
  "/items",
  "/equipment",
  "/mystic",
  "/beast",
  "/config",
]

export function adminBasePath() {
  if (typeof window === "undefined") {
    return ""
  }
  const path = window.location.pathname.replace(/\/+$/, "")
  const matchedRoute = appRoutes.find(
    (route) => path === route || path.endsWith(route),
  )
  if (matchedRoute) {
    const base = path.slice(0, -matchedRoute.length)
    return base || ""
  }
  return path === "/" ? "" : path
}

function apiPrefix() {
  const base = adminBasePath()
  const path = `${base}/api`.replace(/\/{2,}/g, "/")
  if (typeof window === "undefined") {
    return path
  }
  return new URL(path, window.location.origin).toString()
}

export function assetUrl(path: string) {
  const base = adminBasePath()
  return `${base}${path.startsWith("/") ? path : `/${path}`}`.replace(
    /\/{2,}/g,
    "/",
  )
}

type ApiErrorPayload = {
  error?: unknown
  detail?: unknown
  // 配置校验失败时后端返回字段级问题列表（R-07）。
  issues?: unknown
}

class ApiRequestError extends Error {
  toString() {
    return this.message
  }
}

function errorResponse(error: unknown) {
  const response = (error as { response?: unknown } | null)?.response
  return response instanceof Response ? response : null
}

function payloadMessage(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return ""
  }
  const { error, detail, issues } = payload as ApiErrorPayload
  const detailText = formatIssues(issues)
  if (typeof error === "string" && error.trim()) {
    return detailText ? `${error}：${detailText}` : error
  }
  if (typeof detail === "string" && detail.trim()) {
    return detailText ? `${detail}：${detailText}` : detail
  }
  return detailText
}

/** 把「字段路径: 说明」拼成一句，最多三条，避免提示框被刷屏。 */
function formatIssues(value: unknown) {
  if (!Array.isArray(value)) {
    return ""
  }
  return value
    .slice(0, 3)
    .map((item) => {
      if (!item || typeof item !== "object") {
        return ""
      }
      const { path, message } = item as { path?: unknown; message?: unknown }
      const pathText = typeof path === "string" ? path : ""
      const messageText = typeof message === "string" ? message : ""
      return pathText ? `${pathText}: ${messageText}` : messageText
    })
    .filter(Boolean)
    .join("；")
}

function statusMessage(response: Response) {
  const statusText = response.statusText.trim()
  return statusText
    ? `Request failed (${response.status} ${statusText})`
    : `Request failed (${response.status})`
}

export async function apiErrorMessage(error: unknown) {
  // ky v2 在抛 HTTPError 前已把响应体读成 error.data（bodyUsed 为 true），
  // 因此必须先读 data，再退回 response.clone()——否则后端返回的中文错误文案
  // 会被吞成 "Request failed (4xx)"。
  const data = (error as { data?: unknown } | null)?.data
  if (data !== undefined) {
    const message = payloadMessage(data)
    if (message) {
      return message
    }
  }
  const response = errorResponse(error)
  if (response) {
    if (!response.bodyUsed) {
      try {
        const message = payloadMessage(await response.clone().json())
        if (message) {
          return message
        }
      } catch {
        // 非 JSON 响应体：用状态码文案兜底。
      }
    }
    return statusMessage(response)
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message
  }
  return String(error || "unknown error")
}

async function apiJson<T>(request: Promise<T>) {
  try {
    return await request
  } catch (error) {
    throw new ApiRequestError(await apiErrorMessage(error))
  }
}

const sessionChangeEvent = "xiuxian:session-change"

/** 会话状态变化（失效 401/403、登录、登出、改密）时广播，AuthGate 据此重新校验。 */
function notifySessionChange() {
  if (typeof window === "undefined") {
    return
  }
  window.dispatchEvent(new Event(sessionChangeEvent))
}

export function onSessionChange(listener: () => void) {
  if (typeof window === "undefined") {
    return () => {}
  }
  window.addEventListener(sessionChangeEvent, listener)
  return () => window.removeEventListener(sessionChangeEvent, listener)
}

export const api = ky.create({
  prefix: apiPrefix(),
  timeout: 30_000,
  credentials: "include",
  hooks: {
    afterResponse: [
      ({ response, request }) => {
        // 会话失效统一上报，避免每个页面各自处理 401。
        if (response.status === 401) {
          notifySessionChange()
        }
        if (response.status === 403 && !request.url.includes("/api/password")) {
          notifySessionChange()
        }
      },
    ],
  },
})

const fetchJson = <T>(path: string) => apiJson(api.get(path).json<T>())

export type SessionPayload = {
  ok: boolean
  authenticated: boolean
  username?: string
  must_change_password?: boolean
}

export function useSession() {
  return useSWR<SessionPayload>("session", fetchJson, {
    revalidateOnFocus: false,
    shouldRetryOnError: false,
  })
}

export async function login(username: string, password: string) {
  try {
    return await apiJson(
      api
        .post("login", { json: { username, password } })
        .json<SessionPayload>(),
    )
  } finally {
    notifySessionChange()
  }
}

export async function logout() {
  try {
    await apiJson(api.post("logout").json<{ ok: boolean }>())
  } finally {
    notifySessionChange()
  }
}

export async function changePassword(oldPassword: string, newPassword: string) {
  try {
    return await apiJson(
      api
        .post("password", {
          json: { old_password: oldPassword, new_password: newPassword },
        })
        .json<{ ok: boolean; must_change_password: boolean }>(),
    )
  } finally {
    notifySessionChange()
  }
}

export function useDashboard() {
  // R-12：dashboard 后端每次全量重算（读 users.json + 逐玩家战力），
  // 10s 轮询 × 多开页面是纯浪费；降为 60s + 页头手动刷新（App.tsx mutate）。
  return useSWR<DashboardPayload>("dashboard", fetchJson, {
    refreshInterval: 60_000,
    revalidateOnFocus: false,
  })
}

export function usePlayers(query: string) {
  const search = query.trim()
  const key = search ? `players?q=${encodeURIComponent(search)}` : "players"
  return useSWR<PlayerListPayload>(key, fetchJson)
}

export function usePlayer(userId: string | null) {
  return useSWR<PlayerDetailPayload>(
    userId ? `players/${encodeURIComponent(userId)}` : null,
    fetchJson,
  )
}

export function useItems() {
  return useSWR<ItemsPayload>("items", fetchJson)
}

export function useBeastCards() {
  return useSWR<BeastCardsPayload>("beast-realm/cards", fetchJson)
}

export function useMystic() {
  return useSWR<MysticPayload>("mystic", fetchJson)
}

export function saveMysticConfig(config: MysticConfig) {
  return apiJson(api.put("mystic", { json: config }).json<MysticPayload>())
}

export function useEquipmentRules() {
  return useSWR<EquipmentPayload>("equipment-rules", fetchJson)
}

export function useConfig() {
  return useSWR<ConfigPayload>("config", fetchJson)
}

export function saveConfig(config: ConfigPayload["config"]) {
  return apiJson(api.put("config", { json: config }).json<ConfigPayload>())
}

export function savePlayer(
  userId: string,
  record: PlayerDetailPayload["record"],
) {
  return apiJson(
    api
      .put(`players/${encodeURIComponent(userId)}`, { json: record })
      .json<PlayerDetailPayload>(),
  )
}

export function createBackup() {
  return apiJson(api.post("backup").json<BackupPayload>())
}
