import ky from "ky"
import useSWR from "swr"

import type {
  BackupPayload,
  BeastCardsPayload,
  ConfigPayload,
  DashboardPayload,
  EquipmentPayload,
  ItemsPayload,
  MysticPayload,
  PlayerDetailPayload,
  PlayerListPayload,
} from "@/lib/types"

const tokenStorageKey = "xiuxian-admin-token"
const appRoutes = ["/players", "/items", "/equipment", "/mystic", "/beast", "/config"]

export function adminBasePath() {
  if (typeof window === "undefined") {
    return ""
  }
  const path = window.location.pathname.replace(/\/+$/, "")
  const matchedRoute = appRoutes.find((route) => path === route || path.endsWith(route))
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
  return `${base}/api`.replace(/\/{2,}/g, "/")
}

export function assetUrl(path: string) {
  const base = adminBasePath()
  const normalized = `${base}${path.startsWith("/") ? path : `/${path}`}`.replace(/\/{2,}/g, "/")
  const token = getAdminToken()
  if (!token) {
    return normalized
  }
  const separator = normalized.includes("?") ? "&" : "?"
  return `${normalized}${separator}token=${encodeURIComponent(token)}`
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

const fetchJson = <T>(path: string) => api.get(path).json<T>()

export function useDashboard() {
  return useSWR<DashboardPayload>("dashboard", fetchJson, { refreshInterval: 10_000 })
}

export function usePlayers(query: string) {
  const search = query.trim()
  const key = search ? `players?q=${encodeURIComponent(search)}` : "players"
  return useSWR<PlayerListPayload>(key, fetchJson)
}

export function usePlayer(userId: string | null) {
  return useSWR<PlayerDetailPayload>(userId ? `players/${encodeURIComponent(userId)}` : null, fetchJson)
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

export function useEquipmentRules() {
  return useSWR<EquipmentPayload>("equipment-rules", fetchJson)
}

export function useConfig() {
  return useSWR<ConfigPayload>("config", fetchJson)
}

export function saveConfig(config: ConfigPayload["config"]) {
  return api.put("config", { json: config }).json<ConfigPayload>()
}

export function savePlayer(userId: string, record: PlayerDetailPayload["record"]) {
  return api.put(`players/${encodeURIComponent(userId)}`, { json: record }).json<PlayerDetailPayload>()
}

export function createBackup() {
  return api.post("backup").json<BackupPayload>()
}
