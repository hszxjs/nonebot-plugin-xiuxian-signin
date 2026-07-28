import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

import { PlayersWorkspace } from "@/features/players/players-workspace"
import type {
  JsonRecord,
  PlayerDetailPayload,
  PlayerSummary,
} from "@/lib/types"

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
    tiers: ["凡品", "黄阶", "玄阶", "地阶", "天阶", "变异灵根"],
    grades: ["下品", "中品"],
    categories: ["丹药"],
    mystic_types: ["普通秘境"],
    cultivation_routes: ["剑修", "术修"],
    foundation_quality_titles: ["普通筑基"],
    realm_quality_titles: {},
    quality_titles: ["普通筑基"],
  },
}

function renderWorkspace(
  overrides: { onSavePlayer?: (record: JsonRecord) => void } = {},
) {
  const onSavePlayer = overrides.onSavePlayer ?? vi.fn()
  render(
    <PlayersWorkspace
      players={players}
      selectedPlayer={selectedPlayer}
      query=""
      onQueryChange={vi.fn()}
      onSelectPlayer={vi.fn()}
      onSavePlayer={onSavePlayer}
    />,
  )
  return { onSavePlayer }
}

describe("PlayersWorkspace", () => {
  afterEach(() => cleanup())

  it("renders structured form sections covering the previously hidden fields", () => {
    const { container } = render(
      <PlayersWorkspace
        players={players}
        selectedPlayer={selectedPlayer}
        query=""
        onQueryChange={vi.fn()}
        onSelectPlayer={vi.fn()}
        onSavePlayer={vi.fn()}
      />,
    )

    expect(
      screen.getByRole("heading", { name: "玩家管理" }),
    ).toBeInTheDocument()
    // 原有分区仍在
    expect(screen.getByText("灵根属性")).toBeInTheDocument()
    // 新增分区标题
    expect(screen.getByText("境界与经验")).toBeInTheDocument()
    expect(screen.getByText("签到与日常")).toBeInTheDocument()
    expect(screen.getByText("身份与体质")).toBeInTheDocument()
    expect(screen.getByText("装备与背包")).toBeInTheDocument()
    // 新增字段标签（含英文 key）
    expect(screen.getByText("邪修 (evil_cultivator)")).toBeInTheDocument()
    expect(screen.getByText("总修为 (total_exp)")).toBeInTheDocument()
    expect(screen.getByText("纯度 (purity)")).toBeInTheDocument()
    expect(
      container.querySelectorAll(".ant-select").length,
    ).toBeGreaterThanOrEqual(4)
    // 折叠的高级 JSON 面板标题存在
    expect(
      screen.getByText("原始存档 JSON（高级，可编辑任意字段）"),
    ).toBeInTheDocument()
  }, 10_000)

  it("saves the complete record so unmodeled fields are preserved", async () => {
    const { onSavePlayer } = renderWorkspace()

    fireEvent.click(screen.getByRole("button", { name: "保存玩家存档" }))
    fireEvent.click(await screen.findByRole("button", { name: "保存存档" }))

    expect(onSavePlayer).toHaveBeenCalledWith(
      expect.objectContaining({ custom_note: "保留" }),
    )
  }, 10_000)

  it("renders an editable raw JSON panel that can be expanded", async () => {
    renderWorkspace()

    // 展开「原始存档 JSON」折叠面板
    fireEvent.click(screen.getByText("原始存档 JSON（高级，可编辑任意字段）"))

    // 展开后出现 textarea
    const textareas = await screen.findAllByRole("textbox")
    const rawJsonArea = textareas.find((node) =>
      (node as HTMLTextAreaElement).value.includes('"custom_note"'),
    )
    expect(rawJsonArea).toBeTruthy()
  }, 10_000)
})
