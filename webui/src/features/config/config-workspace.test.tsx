import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { ConfigWorkspace } from "@/features/config/config-workspace"
import type { AdminConfig } from "@/lib/types"

const config: AdminConfig = {
  version: 1,
  equipment_rules: {
    realm_tier_unlocks: {
      "0": ["凡品", "黄阶"],
      "1": ["凡品", "黄阶", "玄阶"],
    },
    tier_default_realm: { 凡品: 0, 黄阶: 0, 玄阶: 1 },
    artifact_drop_pools: {
      "0": [{ name: "青竹剑", tier: "凡品", grade: "下品" }],
    },
    artifact_power_base: { 凡品: 100 },
    artifact_realm_power_base: { "0": 100 },
    artifact_tier_power_ratio: { 凡品: 1 },
    artifact_grade_ratio: { 下品: 1 },
    artifact_immortal_upgrade_rate: 0.05,
  },
  mystic: {
    enabled_types: ["上古宗门遗址"],
    enabled_high_risk_types: ["兽潮"],
    category_weights: { 丹药: 0.4, 法器: 0.6 },
    drop_overrides: {},
    fishing_option_rate: 0.05,
  },
  signin: { extra_fishing_chance_rate: 0.1 },
  item_overrides: {},
  beast_realm: { card_pool_copies: 10, card_overrides: {} },
}

describe("ConfigWorkspace", () => {
  afterEach(() => cleanup())

  it("uses shape-aware controls for gameplay configuration", () => {
    const { container } = render(
      <ConfigWorkspace config={config} onSave={vi.fn()} />,
    )

    expect(
      screen.getByRole("heading", { name: "配置管理" }),
    ).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "秘境" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "装备" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "兽域" })).toBeInTheDocument()
    expect(
      container.querySelectorAll(".ant-checkbox-wrapper").length,
    ).toBeGreaterThan(1)
    expect(container.querySelectorAll(".ant-slider").length).toBeGreaterThan(1)
    expect(container.querySelector(".ant-switch")).not.toBeNull()
    expect(container.querySelector("table")).toBeNull()
    fireEvent.click(screen.getByRole("tab", { name: "原始 JSON" }))
    expect(container.querySelector("textarea")).not.toBeNull()
  })

  it("requires an alert dialog before saving the global config", () => {
    const { container } = render(
      <ConfigWorkspace config={config} onSave={vi.fn()} />,
    )

    expect(
      screen.getByRole("button", { name: "保存全局配置" }),
    ).toBeInTheDocument()
    expect(container.querySelector(".ant-btn")).not.toBeNull()
  })
})
