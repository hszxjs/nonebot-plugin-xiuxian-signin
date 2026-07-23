import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { MysticWorkspace } from "@/features/mystic/mystic-workspace"
import type { MysticPayload } from "@/lib/types"

const payload = {
  ok: true,
  mystic: {
    types: ["ancient_sect_ruins"],
    high_risk_types: ["abyssal_battlefield"],
    enabled_types: ["ancient_sect_ruins"],
    enabled_high_risk_types: ["abyssal_battlefield"],
    map_size_rules: [
      { minimum_boss_realm_index: 0, node_count: 24 },
      { minimum_boss_realm_index: 5, node_count: 28 },
    ],
    min_map_size: 24,
    max_map_size: 48,
    normal_node_weights: { random: 0.28, combat: 0.26 },
    high_risk_node_weights: { random: 0.2, combat: 0.36 },
    normal_branch_density: 0.18,
    high_risk_branch_density: 0.3,
    high_risk_loop_count: 4,
    consecutive_combat_limit: 2,
    ordinary_monster_hp_multiplier: 1,
    boss_hp_multiplier: 1,
    reward_multiplier: 1,
    damage_growth_per_ten_rounds: 0.1,
    encounter_response_seconds: 60,
    battle_prepare_seconds: 60,
    player_action_seconds: 60,
    boss_vote_seconds: 60,
    leader_inactive_seconds: 600,
    leader_transfer_vote_seconds: 60,
    rescue_wait_seconds: 1800,
    category_weights: {},
    drop_overrides: {},
    fishing_option_rate: 0.05,
    extra_fishing_chance_rate: 0.1,
    categories: [],
    tiers: [],
    grades: [],
  },
} as unknown as MysticPayload

describe("MysticWorkspace", () => {
  afterEach(() => cleanup())

  it("edits map tiers, encounter timing, and saves a structured payload", () => {
    const onSave = vi.fn()
    render(<MysticWorkspace payload={payload} onSave={onSave} />)

    expect(
      screen.getByRole("heading", { name: "秘境规则" }),
    ).toBeInTheDocument()
    expect(screen.getAllByText("24 格").length).toBeGreaterThan(0)
    fireEvent.change(screen.getByLabelText("地图档位 1 最低 Boss 修为"), {
      target: { value: "2" },
    })
    fireEvent.change(screen.getByLabelText("普通 combat 节点权重"), {
      target: { value: "0.31" },
    })
    fireEvent.change(screen.getByLabelText("普通地图分支率"), {
      target: { value: "0.22" },
    })
    fireEvent.change(screen.getByLabelText("普通怪物血量倍率"), {
      target: { value: "1.5" },
    })
    fireEvent.change(screen.getByLabelText("玩家行动时间"), {
      target: { value: "75" },
    })
    fireEvent.change(screen.getByLabelText("普通遭遇应战时间"), {
      target: { value: "45" },
    })
    fireEvent.click(screen.getByRole("button", { name: "保存秘境配置" }))

    expect(onSave).toHaveBeenCalledWith(
      expect.objectContaining({
        map_size_rules: [
          { minimum_boss_realm_index: 2, node_count: 24 },
          { minimum_boss_realm_index: 5, node_count: 28 },
        ],
        normal_node_weights: { random: 0.28, combat: 0.31 },
        normal_branch_density: 0.22,
        ordinary_monster_hp_multiplier: 1.5,
        player_action_seconds: 75,
        encounter_response_seconds: 45,
      }),
    )
  }, 15_000)
})
