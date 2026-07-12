import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from "@/components/ui/item"
import { ScrollArea } from "@/components/ui/scroll-area"
import { formatJson, formatNumber } from "@/lib/format"
import type { EquipmentPayload } from "@/lib/types"
import { JsonTextarea, PageHeader } from "@/features/shared/ui"

export function EquipmentWorkspace({ payload }: { payload: EquipmentPayload }) {
  const unlocks = Object.entries(payload.rules.realm_tier_unlocks ?? {})
  const tierDefaults = Object.entries(payload.rules.tier_default_realm ?? {})

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="装备规则" description="展示境界解锁、默认境界和法器目录。" />

      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>境界解锁</CardTitle>
            <CardDescription>每个境界索引对应可出现的装备品阶。</CardDescription>
          </CardHeader>
          <CardContent>
            <ItemGroup>
              {unlocks.map(([realmIndex, tiers]) => (
                <Item key={realmIndex}>
                  <ItemContent>
                    <ItemTitle>境界 #{realmIndex}</ItemTitle>
                    <ItemDescription>{tiers.length} 个品阶</ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <div className="flex flex-wrap gap-1">
                      {tiers.map((tier) => (
                        <Badge key={`${realmIndex}-${tier}`} variant="secondary">
                          {tier}
                        </Badge>
                      ))}
                    </div>
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>品阶默认境界</CardTitle>
            <CardDescription>短映射适合条目列表，不需要表格。</CardDescription>
          </CardHeader>
          <CardContent>
            <ItemGroup>
              {tierDefaults.map(([tier, realmIndex]) => (
                <Item key={tier}>
                  <ItemContent>
                    <ItemTitle>{tier}</ItemTitle>
                    <ItemDescription>默认境界索引 {formatNumber(realmIndex)}</ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Badge variant="outline">{formatNumber(realmIndex)}</Badge>
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>法器目录</CardTitle>
          <CardDescription>{payload.meta.artifacts.length} 个境界绑定法器。</CardDescription>
        </CardHeader>
        <CardContent>
          <ScrollArea className="h-[420px]">
            <ItemGroup>
              {payload.meta.artifacts.map((artifact) => (
                <Item key={`${artifact.realm_index}-${artifact.name}`}>
                  <ItemContent>
                    <ItemTitle>
                      {artifact.name}
                      <Badge variant="outline">{artifact.realm}</Badge>
                    </ItemTitle>
                    <ItemDescription>{artifact.attribute_label || artifact.attribute}</ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Badge variant="secondary">{artifact.tier}</Badge>
                    <Badge variant="outline">{artifact.grade}</Badge>
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          </ScrollArea>
        </CardContent>
      </Card>

      <JsonTextarea label="装备完整规则 JSON" value={formatJson(payload.rules)} readOnly />
    </div>
  )
}
