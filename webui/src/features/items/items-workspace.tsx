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
import { assetUrl } from "@/lib/api"
import type { ItemEntry, ItemsPayload } from "@/lib/types"
import { BadgeList, EmptyPanel, PageHeader, SearchField } from "@/features/shared/ui"

function encodeAssetPath(path: string) {
  return path
    .split("/")
    .map((part) => encodeURIComponent(part))
    .join("/")
}

function itemMatches(item: ItemEntry, query: string, category: string) {
  const text = [item.name, item.category, item.source, item.usage, item.story].join("\n").toLowerCase()
  const matchesQuery = !query.trim() || text.includes(query.trim().toLowerCase())
  const matchesCategory = category === "all" || item.category === category
  return matchesQuery && matchesCategory
}

export function ItemsWorkspace({ payload }: { payload: ItemsPayload }) {
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState("all")
  const filteredItems = useMemo(
    () => payload.items.filter((item) => itemMatches(item, query, category)),
    [category, payload.items, query]
  )

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="物品图鉴"
        description="展示签到、秘境、商店等玩法中可出现的物品，支持按领域含义筛选。"
      />

      <Card>
        <CardHeader>
          <CardTitle>筛选</CardTitle>
          <CardDescription>动态列表使用搜索输入和枚举选择，避免长表格。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_240px]">
            <SearchField value={query} onChange={setQuery} placeholder="搜索物品或来源" />
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger>
                <SelectValue placeholder="全部类别" />
              </SelectTrigger>
              <SelectContent>
                <SelectGroup>
                  <SelectItem value="all">全部类别</SelectItem>
                  {payload.meta.categories.map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
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
          <CardTitle>物品条目</CardTitle>
          <CardDescription>{filteredItems.length} / {payload.items.length} 个条目。</CardDescription>
        </CardHeader>
        <CardContent>
          {filteredItems.length ? (
            <ItemGroup>
              {filteredItems.map((item) => (
                <Item key={item.name} variant={item.customized ? "outline" : "default"}>
                  {item.icon ? (
                    <ItemMedia variant="image">
                      <img src={assetUrl(`/assets/item-icons/${encodeAssetPath(item.icon)}`)} alt={item.name} />
                    </ItemMedia>
                  ) : null}
                  <ItemContent>
                    <ItemTitle>
                      {item.name}
                      {item.category ? <Badge variant="outline">{item.category}</Badge> : null}
                      {item.customized ? <Badge variant="secondary">已覆盖</Badge> : null}
                    </ItemTitle>
                    <ItemDescription>{item.usage || item.story || item.source || "暂无描述"}</ItemDescription>
                    <div className="flex flex-wrap gap-2">
                      <BadgeList values={item.tiers} />
                      <BadgeList values={item.grades} />
                    </div>
                  </ItemContent>
                  <ItemActions>
                    {item.required_realm ? <Badge variant="outline">{item.required_realm}</Badge> : null}
                    {item.source ? <Badge variant="secondary">{item.source}</Badge> : null}
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          ) : (
            <EmptyPanel title="没有匹配物品" description="调整搜索词或类别后再查看。" />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
