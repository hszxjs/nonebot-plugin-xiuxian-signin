import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldContent, FieldDescription, FieldGroup, FieldLegend, FieldSet, FieldTitle } from "@/components/ui/field"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from "@/components/ui/item"
import { Slider } from "@/components/ui/slider"
import { formatJson, formatNumber, rateToSliderValue } from "@/lib/format"
import type { MysticPayload } from "@/lib/types"
import { JsonTextarea, PageHeader, RateField } from "@/features/shared/ui"

export function MysticWorkspace({ payload }: { payload: MysticPayload }) {
  const mystic = payload.mystic

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="秘境规则" description="查看秘境入口池、类别权重和掉落覆盖。" />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card>
          <CardHeader>
            <CardTitle>入口池</CardTitle>
            <CardDescription>多选状态用 checkbox 直接表达。</CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <FieldSet>
                <FieldLegend variant="label">普通秘境</FieldLegend>
                <FieldGroup>
                  {mystic.types.map((type) => (
                    <Field key={type} orientation="horizontal">
                      <Checkbox checked={mystic.enabled_types.includes(type)} disabled />
                      <FieldContent>
                        <FieldTitle>{type}</FieldTitle>
                        <FieldDescription>{mystic.enabled_types.includes(type) ? "已启用" : "未启用"}</FieldDescription>
                      </FieldContent>
                    </Field>
                  ))}
                </FieldGroup>
              </FieldSet>
              <FieldSet>
                <FieldLegend variant="label">高风险秘境</FieldLegend>
                <FieldGroup>
                  {mystic.high_risk_types.map((type) => (
                    <Field key={type} orientation="horizontal">
                      <Checkbox checked={mystic.enabled_high_risk_types.includes(type)} disabled />
                      <FieldContent>
                        <FieldTitle>{type}</FieldTitle>
                        <FieldDescription>
                          {mystic.enabled_high_risk_types.includes(type) ? "已启用" : "未启用"}
                        </FieldDescription>
                      </FieldContent>
                    </Field>
                  ))}
                </FieldGroup>
              </FieldSet>
            </FieldGroup>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>触发概率</CardTitle>
            <CardDescription>概率字段使用 slider 表达范围。</CardDescription>
          </CardHeader>
          <CardContent>
            <FieldGroup>
              <RateField title="钓鱼入口概率" description="签到后出现钓鱼选项的概率。" value={mystic.fishing_option_rate} onChange={() => undefined} />
              <RateField title="额外钓鱼机会" description="签到后追加机会的概率。" value={mystic.extra_fishing_chance_rate} onChange={() => undefined} />
            </FieldGroup>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>类别权重</CardTitle>
          <CardDescription>数值权重作为可比较条目呈现。</CardDescription>
        </CardHeader>
        <CardContent>
          <ItemGroup>
            {Object.entries(mystic.category_weights).map(([category, weight]) => (
              <Item key={category}>
                <ItemContent>
                  <ItemTitle>{category}</ItemTitle>
                  <ItemDescription>权重 {formatNumber(weight)}</ItemDescription>
                </ItemContent>
                <ItemActions>
                  <div className="min-w-48">
                    <Slider value={rateToSliderValue(weight)} max={100} disabled />
                  </div>
                  <Badge variant="outline">{formatNumber(weight)}</Badge>
                </ItemActions>
              </Item>
            ))}
          </ItemGroup>
        </CardContent>
      </Card>

      <JsonTextarea label="秘境掉落覆盖 JSON" value={formatJson(mystic.drop_overrides)} readOnly />
    </div>
  )
}
