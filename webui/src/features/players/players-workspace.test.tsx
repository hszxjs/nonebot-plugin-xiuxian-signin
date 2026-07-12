import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { PlayersWorkspace } from "@/features/players/players-workspace"
import type { PlayerDetailPayload, PlayerSummary } from "@/lib/types"

const players: PlayerSummary[] = [
  {
    user_id: "10001",
    nickname: "青衡",
    realm: "筑基境",
    realm_index: 2,
    battle_power: 3200,
    spirit_stones: 1200,
  },
]

const selectedPlayer: PlayerDetailPayload = {
  ok: true,
  record: {
    user_id: "10001",
    nickname: "青衡",
    realm_index: 2,
    spirit_stones: 1200,
    cultivation_route: "剑修",
    root: {
      attribute: "metal",
      tier: "凡品",
      grade: "中品",
    },
    custom_note: "保留",
  },
  meta: {
    realms: [{ index: 2, name: "筑基境" }],
    attributes: ["metal", "wood"],
    attribute_labels: { metal: "金灵根", wood: "木灵根" },
    tiers: ["凡品", "黄阶"],
    grades: ["下品", "中品"],
    categories: ["丹药"],
    mystic_types: ["普通秘境"],
    cultivation_routes: ["剑修", "术修"],
    foundation_quality_titles: ["普通筑基"],
    realm_quality_titles: {},
    quality_titles: ["普通筑基"],
  },
}

describe("PlayersWorkspace", () => {
  afterEach(() => cleanup())

  it("uses Ant Design form controls instead of exposing player JSON by default", () => {
    const { container } = render(
      <PlayersWorkspace
        players={players}
        selectedPlayer={selectedPlayer}
        query=""
        onQueryChange={vi.fn()}
        onSelectPlayer={vi.fn()}
        onSavePlayer={vi.fn()}
      />
    )

    expect(screen.getByRole("heading", { name: "玩家管理" })).toBeInTheDocument()
    expect(screen.getByText("灵根属性")).toBeInTheDocument()
    expect(screen.getByText("修行路线")).toBeInTheDocument()
    expect(container.querySelectorAll(".ant-select").length).toBeGreaterThanOrEqual(4)
    expect(container.querySelector("textarea")).toBeNull()
    expect(screen.queryByText("高级存档 JSON")).toBeNull()
  })

  it("saves the complete record so unmodeled fields are preserved", async () => {
    const onSavePlayer = vi.fn()
    render(
      <PlayersWorkspace
        players={players}
        selectedPlayer={selectedPlayer}
        query=""
        onQueryChange={vi.fn()}
        onSelectPlayer={vi.fn()}
        onSavePlayer={onSavePlayer}
      />
    )

    fireEvent.click(screen.getByRole("button", { name: "保存玩家存档" }))
    fireEvent.click(await screen.findByRole("button", { name: "保存存档" }))

    expect(onSavePlayer).toHaveBeenCalledWith(expect.objectContaining({ custom_note: "保留" }))
  })
})
