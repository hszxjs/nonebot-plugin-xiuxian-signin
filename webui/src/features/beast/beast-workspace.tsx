import { useMemo, useState } from "react"
import { Avatar, Card, List, Select, Space, Tag, Typography } from "antd"

import { assetUrl } from "@/lib/api"
import { formatJson, formatNumber } from "@/lib/format"
import type { BeastCard, BeastCardsPayload } from "@/lib/types"
import { EmptyPanel, JsonTextarea, PageHeader, SearchField } from "@/features/shared/ui"

function cardMatches(card: BeastCard, query: string, kind: string) {
  const text = [card.name, card.id, card.kind, card.effect, card.story].join("\n").toLowerCase()
  const matchesQuery = !query.trim() || text.includes(query.trim().toLowerCase())
  const matchesKind = kind === "all" || card.kind === kind
  return matchesQuery && matchesKind
}

function statTags(card: BeastCard) {
  return [
    ["攻", card.attack],
    ["防", card.defense],
    ["血", card.health],
    ["速", card.speed],
  ].filter((entry): entry is [string, number] => typeof entry[1] === "number")
}

export function BeastRealmWorkspace({ payload }: { payload: BeastCardsPayload }) {
  const [query, setQuery] = useState("")
  const [kind, setKind] = useState("all")
  const kinds = useMemo(
    () => Array.from(new Set(payload.cards.map((card) => String(card.kind || "")).filter(Boolean))),
    [payload.cards]
  )
  const filteredCards = useMemo(
    () => payload.cards.filter((card) => cardMatches(card, query, kind)),
    [kind, payload.cards, query]
  )

  return (
    <div className="workspace-stack">
      <PageHeader title="兽域卡池" description="展示兽域卡牌、战斗数值、卡池份数与规则覆盖状态。" />

      <Card title="筛选">
        <div className="two-column">
          <SearchField value={query} onChange={setQuery} placeholder="搜索卡牌、效果或故事" />
          <Select
            value={kind}
            onChange={setKind}
            options={[
              { value: "all", label: "全部类型" },
              ...kinds.map((value) => ({ value, label: value })),
            ]}
          />
        </div>
      </Card>

      <Card title="卡牌条目" extra={`${filteredCards.length} / ${payload.cards.length} 张卡牌`}>
        {filteredCards.length ? (
          <List
            dataSource={filteredCards}
            renderItem={(card) => (
              <List.Item
                actions={[
                  typeof card.pool_copies === "number" ? (
                    <Tag key="pool">池 {formatNumber(card.pool_copies)}</Tag>
                  ) : null,
                ].filter(Boolean)}
              >
                <List.Item.Meta
                  avatar={
                    card.spell_icon ? (
                      <Avatar shape="square" src={assetUrl(`/assets/beast-spell-icons/${encodeURIComponent(card.spell_icon)}`)} />
                    ) : undefined
                  }
                  title={
                    <Space wrap>
                      <span>{card.name}</span>
                      {card.kind ? <Tag>{card.kind}</Tag> : null}
                      {card.customized ? <Tag color="processing">已覆盖</Tag> : null}
                    </Space>
                  }
                  description={
                    <Space orientation="vertical">
                      <Typography.Text type="secondary">{card.effect || card.story || card.id}</Typography.Text>
                      <Space wrap>
                        {statTags(card).map(([label, value]) => (
                          <Tag key={`${card.id}-${label}`}>
                            {label} {formatNumber(value)}
                          </Tag>
                        ))}
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <EmptyPanel title="没有匹配卡牌" description="调整搜索词或类型后再查看。" />
        )}
      </Card>

      <JsonTextarea
        label="高级规则 JSON"
        value={formatJson(payload.cards.map((card) => ({ id: card.id, rules: card.rules })))}
        readOnly
        rows={8}
      />
    </div>
  )
}
