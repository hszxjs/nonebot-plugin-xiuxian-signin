import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { assetUrl } from "@/lib/api"
import { formatJson, formatNumber } from "@/lib/format"
import type { BeastCard, BeastCardsPayload } from "@/lib/types"
import { EmptyPanel, PageHeader, SearchField } from "@/features/shared/ui"

function cardMatches(card: BeastCard, query: string, kind: string) {
  const text = [card.name, card.id, card.kind, card.effect, card.story].join("\n").toLowerCase()
  const matchesQuery = !query.trim() || text.includes(query.trim().toLowerCase())
  const matchesKind = kind === "all" || card.kind === kind
  return matchesQuery && matchesKind
}

function statBadges(card: BeastCard) {
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
    <div className="flex flex-col gap-4">
      <PageHeader title="兽域卡池" description="展示兽域卡牌、战斗数值、卡池份数与规则覆盖状态。" />

      <Card>
        <CardHeader>
          <CardTitle>筛选</CardTitle>
          <CardDescription>卡池实体以可搜索条目展示，规则 JSON 放在高级层。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
            <SearchField value={query} onChange={setQuery} placeholder="搜索卡牌、效果或故事" />
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger>
                <SelectValue placeholder="全部类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">全部类型</SelectItem>
                  {kinds.map((value) => (
                    <SelectItem key={value} value={value}>
                      {value}
                    </SelectItem>
                  ))}
                </SelectGroup>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>卡牌条目</CardTitle>
          <CardDescription>{filteredCards.length} / {payload.cards.length} 张卡牌。</CardDescription>
        </CardHeader>
        <CardContent>
          {filteredCards.length ? (
            <ItemGroup>
              {filteredCards.map((card) => (
                <Item key={card.id} variant={card.customized ? "outline" : "default"}>
                  {card.spell_icon ? (
                    <ItemMedia variant="image">
                      <img
                        src={assetUrl(`/assets/beast-spell-icons/${encodeURIComponent(card.spell_icon)}`)}
                        alt={card.name}
                      />
                    </ItemMedia>
                  ) : null}
                  <ItemContent>
                    <ItemTitle>
                      {card.name}
                      {card.kind ? <Badge variant="outline">{card.kind}</Badge> : null}
                      {card.customized ? <Badge variant="secondary">已覆盖</Badge> : null}
                    </ItemTitle>
                    <ItemDescription>{card.effect || card.story || card.id}</ItemDescription>
                    <div className="flex flex-wrap gap-1">
                      {statBadges(card).map(([label, value]) => (
                        <Badge key={`${card.id}-${label}`} variant="secondary">
                          {label} {formatNumber(value)}
                        </Badge>
                      ))}
                    </div>
                  </ItemContent>
                  <ItemActions>
                    {typeof card.pool_copies === "number" ? (
                      <Badge variant="outline">池 {formatNumber(card.pool_copies)}</Badge>
                    ) : null}
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          ) : (
            <EmptyPanel title="没有匹配卡牌" description="调整搜索词或类型后再查看。" />
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>高级规则 JSON</CardTitle>
          <CardDescription>用于核查卡牌规则结构，后续可拆成更细粒度规则编辑器。</CardDescription>
        </CardHeader>
        <CardContent>
          <Textarea readOnly value={formatJson(payload.cards.map((card) => ({ id: card.id, rules: card.rules })))} rows={8} />
        </CardContent>
      </Card>
    </div>
  )
}
