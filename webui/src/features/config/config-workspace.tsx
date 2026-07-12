import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Checkbox } from "@/components/ui/checkbox"
import { Field, FieldContent, FieldDescription, FieldGroup, FieldLegend, FieldSet, FieldTitle } from "@/components/ui/field"
import { Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemTitle } from "@/components/ui/item"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { formatJson, formatNumber, sliderValueToRate } from "@/lib/format"
import type { AdminConfig } from "@/lib/types"
import { ConfirmAction, PageHeader, RateField } from "@/features/shared/ui"

function toggleValue(values: string[], value: string, checked: boolean) {
  if (checked) {
    return values.includes(value) ? values : [...values, value]
  }
  return values.filter((item) => item !== value)
}

function parseConfig(text: string, fallback: AdminConfig) {
  try {
    const parsed = JSON.parse(text)
    return parsed && typeof parsed === "object" ? (parsed as AdminConfig) : fallback
  } catch {
    return fallback
  }
}

export function ConfigWorkspace({
  config,
  onSave,
}: {
  config: AdminConfig
  onSave: (config: AdminConfig) => void
}) {
  const [draft, setDraft] = useState(config)
  const [jsonText, setJsonText] = useState(formatJson(config))
  const mystic = draft.mystic
  const mysticTypes = mystic.types ?? mystic.enabled_types ?? []
  const highRiskTypes = mystic.high_risk_types ?? mystic.enabled_high_risk_types ?? []
  const highRiskEnabled = mystic.enabled_high_risk_types.length > 0
  const realms = useMemo(
    () =>
      Object.entries(draft.equipment_rules.realm_tier_unlocks ?? {}).map(([index, tiers]) => ({
        index,
        tiers,
      })),
    [draft.equipment_rules.realm_tier_unlocks]
  )

  function updateDraft(next: AdminConfig) {
    setDraft(next)
    setJsonText(formatJson(next))
  }

  function updateEnabledType(type: string, checked: boolean) {
    updateDraft({
      ...draft,
      mystic: {
        ...mystic,
        enabled_types: toggleValue(mystic.enabled_types, type, checked),
      },
    })
  }

  function updateHighRiskType(type: string, checked: boolean) {
    updateDraft({
      ...draft,
      mystic: {
        ...mystic,
        enabled_high_risk_types: toggleValue(mystic.enabled_high_risk_types, type, checked),
      },
    })
  }

  function saveFromJson() {
    onSave(parseConfig(jsonText, draft))
  }

  return (
    <div className="flex flex-col gap-4">
      <PageHeader
        title="配置管理"
        description="按玩法领域编辑全局规则，复杂覆盖项保留在高级 JSON 层。"
        actions={
          <ConfirmAction
            triggerLabel="保存全局配置"
            title="保存全局玩法配置？"
            description="保存后会立即应用到修仙签到逻辑，请确认当前配置已检查。"
            actionLabel="保存配置"
            onConfirm={saveFromJson}
          />
        }
      />

      <Tabs defaultValue="mystic">
        <TabsList>
          <TabsTrigger value="mystic">秘境</TabsTrigger>
          <TabsTrigger value="equipment">装备</TabsTrigger>
          <TabsTrigger value="beast">兽域</TabsTrigger>
          <TabsTrigger value="raw">原始 JSON</TabsTrigger>
        </TabsList>

        <TabsContent value="mystic" forceMount>
          <Card>
            <CardHeader>
              <CardTitle>秘境控制</CardTitle>
              <CardDescription>秘境入口、钓鱼触发和奖励权重属于高频调参项。</CardDescription>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <FieldSet>
                  <FieldLegend variant="label">普通秘境</FieldLegend>
                  <FieldDescription>多选列表使用 checkbox 组，避免不可见的逗号文本。</FieldDescription>
                  <FieldGroup>
                    {mysticTypes.map((type) => (
                      <Field key={type} orientation="horizontal">
                        <Checkbox
                          checked={mystic.enabled_types.includes(type)}
                          onCheckedChange={(checked) => updateEnabledType(type, Boolean(checked))}
                        />
                        <FieldContent>
                          <FieldTitle>{type}</FieldTitle>
                          <FieldDescription>允许玩家抽到该秘境入口。</FieldDescription>
                        </FieldContent>
                      </Field>
                    ))}
                  </FieldGroup>
                </FieldSet>

                <Field orientation="responsive">
                  <FieldContent>
                    <FieldTitle>高风险秘境</FieldTitle>
                    <FieldDescription>关闭后会清空高风险入口池；开启时恢复全部高风险类型。</FieldDescription>
                  </FieldContent>
                  <Switch
                    checked={highRiskEnabled}
                    onCheckedChange={(checked) =>
                      updateDraft({
                        ...draft,
                        mystic: {
                          ...mystic,
                          enabled_high_risk_types: checked ? highRiskTypes : [],
                        },
                      })
                    }
                  />
                </Field>

                <FieldSet>
                  <FieldLegend variant="label">高风险类型</FieldLegend>
                  <FieldGroup>
                    {highRiskTypes.map((type) => (
                      <Field key={type} orientation="horizontal">
                        <Checkbox
                          checked={mystic.enabled_high_risk_types.includes(type)}
                          onCheckedChange={(checked) => updateHighRiskType(type, Boolean(checked))}
                        />
                        <FieldContent>
                          <FieldTitle>{type}</FieldTitle>
                          <FieldDescription>保留该类高风险探索事件。</FieldDescription>
                        </FieldContent>
                      </Field>
                    ))}
                  </FieldGroup>
                </FieldSet>

                <RateField
                  title="钓鱼入口概率"
                  description="控制签到后出现钓鱼选项的概率。"
                  value={mystic.fishing_option_rate}
                  onChange={(value) =>
                    updateDraft({
                      ...draft,
                      mystic: { ...mystic, fishing_option_rate: sliderValueToRate(value) },
                    })
                  }
                />
                <RateField
                  title="额外钓鱼机会"
                  description="控制签到后额外获得钓鱼机会的概率。"
                  value={draft.signin.extra_fishing_chance_rate}
                  onChange={(value) =>
                    updateDraft({
                      ...draft,
                      signin: { ...draft.signin, extra_fishing_chance_rate: sliderValueToRate(value) },
                    })
                  }
                />
              </FieldGroup>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="equipment" forceMount>
          <Card>
            <CardHeader>
              <CardTitle>装备规则</CardTitle>
              <CardDescription>境界解锁以矩阵条目呈现，完整掉落池保留在原始 JSON。</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
                <ItemGroup>
                  {realms.map((realm) => (
                    <Item key={realm.index} variant="outline">
                      <ItemContent>
                        <ItemTitle>境界 #{realm.index}</ItemTitle>
                        <ItemDescription>{realm.tiers.length} 个可用品阶</ItemDescription>
                      </ItemContent>
                      <ItemActions>
                        <div className="flex flex-wrap gap-1">
                          {realm.tiers.map((tier) => (
                            <Badge key={`${realm.index}-${tier}`} variant="secondary">
                              {tier}
                            </Badge>
                          ))}
                        </div>
                      </ItemActions>
                    </Item>
                  ))}
                </ItemGroup>
                <FieldGroup>
                  <Field>
                    <FieldContent>
                      <FieldTitle>仙阶升级概率</FieldTitle>
                      <FieldDescription>小范围概率使用 slider 调整。</FieldDescription>
                    </FieldContent>
                    <div className="flex items-center gap-3">
                      <Slider
                        value={[Math.round(Number(draft.equipment_rules.artifact_immortal_upgrade_rate ?? 0) * 100)]}
                        max={100}
                        step={1}
                        onValueChange={(value) =>
                          updateDraft({
                            ...draft,
                            equipment_rules: {
                              ...draft.equipment_rules,
                              artifact_immortal_upgrade_rate: sliderValueToRate(value),
                            },
                          })
                        }
                      />
                      <Badge variant="outline">
                        {formatNumber(Math.round(Number(draft.equipment_rules.artifact_immortal_upgrade_rate ?? 0) * 100))}%
                      </Badge>
                    </div>
                  </Field>
                </FieldGroup>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="beast" forceMount>
          <Card>
            <CardHeader>
              <CardTitle>兽域卡池</CardTitle>
              <CardDescription>全局池份数是小范围整数，使用 slider 比文本输入更清楚。</CardDescription>
              <CardAction>
                <Badge variant="outline">{Object.keys(draft.beast_realm.card_overrides).length} 个覆盖</Badge>
              </CardAction>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <Field orientation="responsive">
                  <FieldContent>
                    <FieldTitle>默认卡池份数</FieldTitle>
                    <FieldDescription>控制未单独覆盖卡牌的默认抽取份数。</FieldDescription>
                  </FieldContent>
                  <div className="flex min-w-56 items-center gap-3">
                    <Slider
                      value={[Number(draft.beast_realm.card_pool_copies) || 0]}
                      max={50}
                      step={1}
                      onValueChange={(value) =>
                        updateDraft({
                          ...draft,
                          beast_realm: { ...draft.beast_realm, card_pool_copies: Number(value[0] ?? 0) },
                        })
                      }
                    />
                    <Badge variant="outline">{formatNumber(draft.beast_realm.card_pool_copies)}</Badge>
                  </div>
                </Field>
                <Field>
                  <FieldContent>
                    <FieldTitle>卡牌覆盖</FieldTitle>
                    <FieldDescription>嵌套覆盖规则在高级 JSON 中编辑，避免误删结构。</FieldDescription>
                  </FieldContent>
                  <Textarea readOnly value={formatJson(draft.beast_realm.card_overrides)} rows={8} />
                </Field>
              </FieldGroup>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="raw" forceMount>
          <Card>
            <CardHeader>
              <CardTitle>完整配置 JSON</CardTitle>
              <CardDescription>用于处理尚未拆成结构化控件的嵌套规则。</CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea value={jsonText} onChange={(event) => setJsonText(event.target.value)} rows={22} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
