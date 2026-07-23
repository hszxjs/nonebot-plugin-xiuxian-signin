import {
  Card,
  Checkbox,
  Form,
  Input,
  List,
  Slider,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
} from "antd"
import { useMemo, useState } from "react"
import { ConfirmAction, PageHeader } from "@/features/shared/ui"
import { formatJson, formatNumber, sliderValueToRate } from "@/lib/format"
import type { AdminConfig } from "@/lib/types"

function parseConfig(text: string, fallback: AdminConfig) {
  try {
    const parsed = JSON.parse(text)
    return parsed && typeof parsed === "object"
      ? (parsed as AdminConfig)
      : fallback
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
  const highRiskTypes =
    mystic.high_risk_types ?? mystic.enabled_high_risk_types ?? []
  const highRiskEnabled = mystic.enabled_high_risk_types.length > 0
  const realms = useMemo(
    () =>
      Object.entries(draft.equipment_rules.realm_tier_unlocks ?? {}).map(
        ([index, tiers]) => ({
          index,
          tiers,
        }),
      ),
    [draft.equipment_rules.realm_tier_unlocks],
  )

  function updateDraft(next: AdminConfig) {
    setDraft(next)
    setJsonText(formatJson(next))
  }

  function saveFromJson() {
    onSave(parseConfig(jsonText, draft))
  }

  return (
    <div className="workspace-stack">
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
            danger
          />
        }
      />

      <Tabs
        items={[
          {
            key: "mystic",
            label: "秘境",
            children: (
              <Card title="秘境控制">
                <Form layout="vertical">
                  <Form.Item label="普通秘境">
                    <Checkbox.Group
                      value={mystic.enabled_types}
                      options={mysticTypes.map((type) => ({
                        value: type,
                        label: type,
                      }))}
                      onChange={(values) =>
                        updateDraft({
                          ...draft,
                          mystic: {
                            ...mystic,
                            enabled_types: values.map(String),
                          },
                        })
                      }
                    />
                  </Form.Item>
                  <Form.Item label="高风险秘境">
                    <Switch
                      checked={highRiskEnabled}
                      onChange={(checked) =>
                        updateDraft({
                          ...draft,
                          mystic: {
                            ...mystic,
                            enabled_high_risk_types: checked
                              ? highRiskTypes
                              : [],
                          },
                        })
                      }
                    />
                  </Form.Item>
                  <Form.Item label="高风险类型">
                    <Checkbox.Group
                      value={mystic.enabled_high_risk_types}
                      options={highRiskTypes.map((type) => ({
                        value: type,
                        label: type,
                      }))}
                      onChange={(values) =>
                        updateDraft({
                          ...draft,
                          mystic: {
                            ...mystic,
                            enabled_high_risk_types: values.map(String),
                          },
                        })
                      }
                    />
                  </Form.Item>
                  <Form.Item label="钓鱼入口概率">
                    <Slider
                      min={0}
                      max={100}
                      value={Math.round(mystic.fishing_option_rate * 100)}
                      onChange={(value) =>
                        updateDraft({
                          ...draft,
                          mystic: {
                            ...mystic,
                            fishing_option_rate: sliderValueToRate([value]),
                          },
                        })
                      }
                    />
                  </Form.Item>
                  <Form.Item label="额外钓鱼机会">
                    <Slider
                      min={0}
                      max={100}
                      value={Math.round(
                        draft.signin.extra_fishing_chance_rate * 100,
                      )}
                      onChange={(value) =>
                        updateDraft({
                          ...draft,
                          signin: {
                            ...draft.signin,
                            extra_fishing_chance_rate: sliderValueToRate([
                              value,
                            ]),
                          },
                        })
                      }
                    />
                  </Form.Item>
                </Form>
              </Card>
            ),
          },
          {
            key: "equipment",
            label: "装备",
            children: (
              <Card title="装备规则">
                <div className="two-column">
                  <List
                    dataSource={realms}
                    renderItem={(realm) => (
                      <List.Item>
                        <List.Item.Meta
                          title={`境界 #${realm.index}`}
                          description={`${realm.tiers.length} 个可用品阶`}
                        />
                        <Space wrap>
                          {realm.tiers.map((tier) => (
                            <Tag key={`${realm.index}-${tier}`}>{tier}</Tag>
                          ))}
                        </Space>
                      </List.Item>
                    )}
                  />
                  <Form layout="vertical">
                    <Form.Item label="仙阶升级概率">
                      <Slider
                        min={0}
                        max={100}
                        value={Math.round(
                          Number(
                            draft.equipment_rules
                              .artifact_immortal_upgrade_rate ?? 0,
                          ) * 100,
                        )}
                        onChange={(value) =>
                          updateDraft({
                            ...draft,
                            equipment_rules: {
                              ...draft.equipment_rules,
                              artifact_immortal_upgrade_rate: sliderValueToRate(
                                [value],
                              ),
                            },
                          })
                        }
                      />
                    </Form.Item>
                    <Tag>
                      {formatNumber(
                        Math.round(
                          Number(
                            draft.equipment_rules
                              .artifact_immortal_upgrade_rate ?? 0,
                          ) * 100,
                        ),
                      )}
                      %
                    </Tag>
                  </Form>
                </div>
              </Card>
            ),
          },
          {
            key: "beast",
            label: "兽域",
            children: (
              <Card
                title="兽域卡池"
                extra={`${Object.keys(draft.beast_realm.card_overrides).length} 个覆盖`}
              >
                <Form layout="vertical">
                  <Form.Item label="默认卡池份数">
                    <Slider
                      min={0}
                      max={50}
                      value={Number(draft.beast_realm.card_pool_copies) || 0}
                      onChange={(value) =>
                        updateDraft({
                          ...draft,
                          beast_realm: {
                            ...draft.beast_realm,
                            card_pool_copies: Number(value),
                          },
                        })
                      }
                    />
                  </Form.Item>
                  <Typography.Text type="secondary">
                    卡牌覆盖规则仍保留在完整 JSON 中，避免误删嵌套结构。
                  </Typography.Text>
                </Form>
              </Card>
            ),
          },
          {
            key: "raw",
            label: "原始 JSON",
            children: (
              <Card title="完整配置 JSON">
                <Input.TextArea
                  value={jsonText}
                  onChange={(event) => setJsonText(event.target.value)}
                  rows={22}
                />
              </Card>
            ),
          },
        ]}
      />
    </div>
  )
}
