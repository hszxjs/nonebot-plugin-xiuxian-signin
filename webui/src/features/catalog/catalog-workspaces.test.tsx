import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it } from "vitest"

import { BeastRealmWorkspace } from "@/features/beast/beast-workspace"
import { ItemsWorkspace } from "@/features/items/items-workspace"
import type { BeastCardsPayload, ItemsPayload } from "@/lib/types"

const items: ItemsPayload = {
  ok: true,
  meta: {
    categories: ["丹药", "法器"],
    tiers: ["凡品", "黄阶"],
    grades: ["下品", "中品"],
    realms: ["炼气境", "筑基境"],
    attributes: ["fire", "water"],
  },
  items: [
    {
      name: "聚气丹",
      category: "丹药",
      tiers: ["凡品"],
      grades: ["下品", "中品"],
      required_realm: "炼气境",
      required_attribute: "",
      usage: "修炼资源",
      source: "签到",
      story: "用于补足早期灵气。",
      customized: false,
      icon: "丹药/聚气丹.png",
    },
  ],
}

const beastCards: BeastCardsPayload = {
  ok: true,
  meta: { kinds: ["attack", "support"], spells: ["thunder.png"] },
  cards: [
    {
      id: "thunder-cat",
      name: "雷纹灵兽",
      kind: "attack",
      attack: 12,
      defense: 5,
      health: 30,
      speed: 8,
      pool_copies: 2,
      portrait: "thunder-cat.png",
      spell_icon: "thunder.png",
      effect: "造成一次雷击。",
      story: "暴雨夜现身山门。",
      rules: { trigger: "on_attack" },
      customized: true,
    },
  ],
}

describe("catalog workspaces", () => {
  afterEach(() => cleanup())

  it("renders item catalog entries as searchable item cards", () => {
    const { container } = render(<ItemsWorkspace payload={items} />)

    expect(screen.getByRole("heading", { name: "物品图鉴" })).toBeInTheDocument()
    expect(screen.getByPlaceholderText("搜索物品或来源")).toBeInTheDocument()
    expect(screen.getByText("聚气丹")).toBeInTheDocument()
    expect(container.querySelector("table")).toBeNull()
    expect(container.querySelector('[data-slot="item-group"]')).not.toBeNull()
    expect(container.querySelector('[data-slot="select-trigger"]')).not.toBeNull()
  })

  it("renders beast cards with domain cards and an advanced rules layer", () => {
    const { container } = render(<BeastRealmWorkspace payload={beastCards} />)

    expect(screen.getByRole("heading", { name: "兽域卡池" })).toBeInTheDocument()
    expect(screen.getByText("雷纹灵兽")).toBeInTheDocument()
    expect(screen.getByText("造成一次雷击。")).toBeInTheDocument()
    expect(screen.getByText("高级规则 JSON")).toBeInTheDocument()
    expect(container.querySelector("table")).toBeNull()
    expect(container.querySelector('[data-slot="item-group"]')).not.toBeNull()
  })
})
