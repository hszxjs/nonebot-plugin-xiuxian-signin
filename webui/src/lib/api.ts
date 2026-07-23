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

const tokenStorageKey = "xiuxian-admin-token"
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

export function getAdminToken() {
  if (typeof window === "undefined") {
    return ""
  }
  if (typeof window.localStorage?.getItem !== "function") {
    return ""
  }
  return window.localStorage.getItem(tokenStorageKey) || ""
}

export function setAdminToken(token: string) {
  if (typeof window.localStorage?.setItem !== "function") {
    return
  }
  window.localStorage.setItem(tokenStorageKey, token)
}

export function bootstrapAdminToken() {
  if (typeof window === "undefined") {
    return
  }
  const token = new URLSearchParams(window.location.search).get("token")
  if (token) {
    setAdminToken(token)
  }
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
  const normalized =
    `${base}${path.startsWith("/") ? path : `/${path}`}`.replace(/\/{2,}/g, "/")
  const token = getAdminToken()
  if (!token) {
    return normalized
  }
  const separator = normalized.includes("?") ? "&" : "?"
  return `${normalized}${separator}token=${encodeURIComponent(token)}`
}

type ApiErrorPayload = {
  error?: unknown
  detail?: unknown
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
  const { error, detail } = payload as ApiErrorPayload
  if (typeof error === "string" && error.trim()) {
    return error
  }
  if (typeof detail === "string" && detail.trim()) {
    return detail
  }
  return ""
}

function statusMessage(response: Response) {
  const statusText = response.statusText.trim()
  return statusText
    ? `Request failed (${response.status} ${statusText})`
    : `Request failed (${response.status})`
}

export async function apiErrorMessage(error: unknown) {
  const response = errorResponse(error)
  if (response) {
    try {
      const message = payloadMessage(await response.clone().json())
      if (message) {
        return message
      }
    } catch {
      return statusMessage(response)
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

export const api = ky.create({
  prefix: apiPrefix(),
  timeout: 30_000,
  hooks: {
    beforeRequest: [
      ({ request }) => {
        const token = getAdminToken()
        if (token) {
          request.headers.set("X-Xiuxian-Token", token)
        }
      },
    ],
  },
})

const fetchJson = <T>(path: string) => apiJson(api.get(path).json<T>())

export function useDashboard() {
  return useSWR<DashboardPayload>("dashboard", fetchJson, {
    refreshInterval: 10_000,
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
