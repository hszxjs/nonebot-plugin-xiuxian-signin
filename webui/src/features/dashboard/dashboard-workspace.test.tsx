import { cleanup, render, screen, within } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { DashboardWorkspace } from "@/features/dashboard/dashboard-workspace"
import type { DashboardPayload } from "@/lib/types"

const dashboard: DashboardPayload = {
  ok: true,
  mode: "snapshot",
  generated_date: "2026-07-12",
  metrics: {
    total_players: 3,
    signed_today: 2,
    recent_active: 3,
    inactive_risk: 1,
    total_spirit_stones: 900,
    average_spirit_stones: 300,
    average_battle_power: 12345,
  },
  realm_distribution: [
    { realm: "筑基境", count: 2 },
    { realm: "金丹境", count: 1 },
  ],
  top_battle_power: [
    {
      user_id: "10001",
      nickname: "云行",
      realm: "金丹境",
      realm_index: 4,
      battle_power: 20000,
      spirit_stones: 400,
      last_sign_date: "2026-07-12",
      days_since_sign: 0,
      signed_today: true,
      recent_active: true,
      inactive_risk: false,
    },
  ],
  recent_signins: [
    {
      user_id: "10002",
      nickname: "照夜",
      realm: "筑基境",
      realm_index: 2,
      battle_power: 8000,
      spirit_stones: 260,
      last_sign_date: "2026-07-11",
      days_since_sign: 1,
      signed_today: false,
      recent_active: true,
      inactive_risk: false,
    },
  ],
  inactive_players: [
    {
      user_id: "10003",
      nickname: "沉舟",
      realm: "炼气境",
      realm_index: 1,
      battle_power: 1000,
      spirit_stones: 240,
      last_sign_date: "2026-06-01",
      days_since_sign: 41,
      signed_today: false,
      recent_active: false,
      inactive_risk: true,
    },
  ],
  health_flags: {
    has_players: true,
    inactive_ratio: 0.3333,
    today_signin_ratio: 0.6667,
  },
  capabilities: {
    historical_trends: false,
    snapshot_dashboard: true,
  },
}

describe("DashboardWorkspace", () => {
  afterEach(() => cleanup())

  it("renders snapshot operations data with cards and item groups instead of tables", () => {
    const { container } = render(<DashboardWorkspace dashboard={dashboard} onBackup={vi.fn()} />)

    expect(screen.getByRole("heading", { name: "修仙运维控制台" })).toBeInTheDocument()
    expect(screen.getByText("玩家总数")).toBeInTheDocument()
    expect(screen.getAllByText("筑基境").length).toBeGreaterThan(0)
    expect(screen.getByText("云行")).toBeInTheDocument()
    expect(screen.getByText("沉舟")).toBeInTheDocument()
    expect(container.querySelector("table")).toBeNull()
    expect(container.querySelectorAll('[data-slot="card"]').length).toBeGreaterThan(3)
    expect(container.querySelectorAll('[data-slot="item-group"]').length).toBeGreaterThan(2)
  })

  it("keeps the backup action behind an alert dialog trigger", () => {
    const { container } = render(<DashboardWorkspace dashboard={dashboard} onBackup={vi.fn()} />)
    const actionCard = screen.getByTestId("dashboard-maintenance-card")

    expect(within(actionCard).getByRole("button", { name: "创建玩家备份" })).toBeInTheDocument()
    expect(container.querySelector('[data-slot="alert-dialog-trigger"]')).not.toBeNull()
  })
})
