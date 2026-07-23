import { Button, Card, Checkbox, Form, InputNumber, Select, Space } from "antd"
import { useState } from "react"

import { JsonTextarea, PageHeader } from "@/features/shared/ui"
import { formatJson } from "@/lib/format"
import type {
  MysticConfig,
  MysticMapSizeRule,
  MysticPayload,
} from "@/lib/types"

const supportedMapSizes = [24, 28, 32, 36, 40, 44, 48] as const
const nodeKinds = ["random", "combat", "resource", "trap", "rest"] as const

export function MysticWorkspace({
  payload,
  onSave,
}: {
  payload: MysticPayload
  onSave?: (config: MysticConfig) => void
}) {
  const [draft, setDraft] = useState<MysticConfig>(payload.mystic)
  const mapRules = draft.map_size_rules ?? []
  const normalTypes = draft.types ?? draft.enabled_types
  const highRiskTypes = draft.high_risk_types ?? draft.enabled_high_risk_types

  function update(next: Partial<MysticConfig>) {
    setDraft((current) => ({ ...current, ...next }))
  }

  function updateMapRule(index: number, next: Partial<MysticMapSizeRule>) {
    update({
      map_size_rules: mapRules.map((rule, ruleIndex) =>
        ruleIndex === index ? { ...rule, ...next } : rule,
      ),
    })
  }

  function updateNodeWeight(
    key: "normal_node_weights" | "high_risk_node_weights",
    kind: string,
    value: number | null,
  ) {
    setDraft((current) => ({
      ...current,
      [key]: {
        ...(current[key] ?? {}),
        [kind]: value ?? 0,
      },
    }))
  }

  const mapSizeOptions = supportedMapSizes.map((value) => ({
    value,
    label: `${value} 格`,
  }))

  return (
    <div className="workspace-stack">
      <PageHeader
        title="秘境规则"
        description="编辑固定地图档位、遭遇时限、节点权重和主题绑定。"
        actions={
          <Button type="primary" onClick={() => onSave?.(draft)}>
            保存秘境配置
          </Button>
        }
      />

      <div className="catalog-grid">
        <Card title="地图档位">
          <Form layout="vertical">
            <Form.Item label="最小地图格数">
              <Select
                aria-label="最小地图格数"
                value={draft.min_map_size ?? 24}
                options={mapSizeOptions}
                onChange={(value) => update({ min_map_size: value })}
              />
            </Form.Item>
            <Form.Item label="最大地图格数">
              <Select
                aria-label="最大地图格数"
                value={draft.max_map_size ?? 48}
                options={mapSizeOptions}
                onChange={(value) => update({ max_map_size: value })}
              />
            </Form.Item>
          </Form>
          <Space orientation="vertical">
            {mapRules.map((rule, index) => (
              <Space key={rule.minimum_boss_realm_index} wrap>
                <InputNumber
                  aria-label={`地图档位 ${index + 1} 最低 Boss 修为`}
                  min={0}
                  max={10_000}
                  value={rule.minimum_boss_realm_index}
                  onChange={(value) =>
                    updateMapRule(index, {
                      minimum_boss_realm_index: value ?? 0,
                    })
                  }
                />
                <span>阶起</span>
                <Select
                  aria-label={`地图档位 ${index + 1} 格数`}
                  value={rule.node_count}
                  options={mapSizeOptions}
                  onChange={(value) =>
                    updateMapRule(index, { node_count: value })
                  }
                />
              </Space>
            ))}
          </Space>
        </Card>
        <Card title="普通秘境主题">
          <Checkbox.Group
            value={draft.enabled_types}
            options={normalTypes.map((type) => ({ value: type, label: type }))}
            onChange={(values) => update({ enabled_types: values.map(String) })}
          />
        </Card>
        <Card title="高风险秘境主题">
          <Checkbox.Group
            value={draft.enabled_high_risk_types}
            options={highRiskTypes.map((type) => ({
              value: type,
              label: type,
            }))}
            onChange={(values) =>
              update({ enabled_high_risk_types: values.map(String) })
            }
          />
        </Card>
      </div>

      <Card title="节点权重">
        <Form layout="vertical" className="two-column">
          {nodeKinds.map((kind) => (
            <Form.Item key={`normal-${kind}`} label={`普通 ${kind}`}>
              <InputNumber
                aria-label={`普通 ${kind} 节点权重`}
                min={0}
                max={1}
                step={0.01}
                precision={3}
                value={draft.normal_node_weights?.[kind] ?? 0}
                onChange={(value) =>
                  updateNodeWeight("normal_node_weights", kind, value)
                }
              />
            </Form.Item>
          ))}
          {nodeKinds.map((kind) => (
            <Form.Item key={`high-${kind}`} label={`高风险 ${kind}`}>
              <InputNumber
                aria-label={`高风险 ${kind} 节点权重`}
                min={0}
                max={1}
                step={0.01}
                precision={3}
                value={draft.high_risk_node_weights?.[kind] ?? 0}
                onChange={(value) =>
                  updateNodeWeight("high_risk_node_weights", kind, value)
                }
              />
            </Form.Item>
          ))}
        </Form>
      </Card>

      <Card title="地图路线参数">
        <Form layout="vertical" className="two-column">
          <Form.Item label="普通地图分支率">
            <InputNumber
              aria-label="普通地图分支率"
              min={0}
              max={1}
              step={0.01}
              precision={3}
              value={draft.normal_branch_density ?? 0.18}
              onChange={(value) =>
                update({ normal_branch_density: value ?? 0.18 })
              }
            />
          </Form.Item>
          <Form.Item label="高风险地图分支率">
            <InputNumber
              aria-label="高风险地图分支率"
              min={0}
              max={1}
              step={0.01}
              precision={3}
              value={draft.high_risk_branch_density ?? 0.3}
              onChange={(value) =>
                update({ high_risk_branch_density: value ?? 0.3 })
              }
            />
          </Form.Item>
          <Form.Item label="高风险地图环路数">
            <InputNumber
              aria-label="高风险地图环路数"
              min={0}
              max={100}
              value={draft.high_risk_loop_count ?? 4}
              onChange={(value) => update({ high_risk_loop_count: value ?? 4 })}
            />
          </Form.Item>
          <Form.Item label="连续战斗节点上限">
            <InputNumber
              aria-label="连续战斗节点上限"
              min={1}
              max={100}
              value={draft.consecutive_combat_limit ?? 2}
              onChange={(value) =>
                update({ consecutive_combat_limit: value ?? 2 })
              }
            />
          </Form.Item>
        </Form>
      </Card>

      <Card title="战斗与奖励倍率">
        <Form layout="vertical" className="two-column">
          <Form.Item label="普通怪物血量倍率">
            <InputNumber
              aria-label="普通怪物血量倍率"
              min={0.01}
              step={0.1}
              precision={2}
              value={draft.ordinary_monster_hp_multiplier ?? 1}
              onChange={(value) =>
                update({ ordinary_monster_hp_multiplier: value ?? 1 })
              }
            />
          </Form.Item>
          <Form.Item label="Boss 血量倍率">
            <InputNumber
              aria-label="Boss 血量倍率"
              min={0.01}
              step={0.1}
              precision={2}
              value={draft.boss_hp_multiplier ?? 1}
              onChange={(value) => update({ boss_hp_multiplier: value ?? 1 })}
            />
          </Form.Item>
          <Form.Item label="奖励倍率">
            <InputNumber
              aria-label="奖励倍率"
              min={0.01}
              step={0.1}
              precision={2}
              value={draft.reward_multiplier ?? 1}
              onChange={(value) => update({ reward_multiplier: value ?? 1 })}
            />
          </Form.Item>
          <Form.Item label="每十回合伤害成长率">
            <InputNumber
              aria-label="每十回合伤害成长率"
              min={0.01}
              step={0.01}
              precision={3}
              value={draft.damage_growth_per_ten_rounds ?? 0.1}
              onChange={(value) =>
                update({ damage_growth_per_ten_rounds: value ?? 0.1 })
              }
            />
          </Form.Item>
        </Form>
      </Card>

      <Card title="战斗与队伍时限">
        <Form layout="vertical" className="two-column">
          <Form.Item label="普通遭遇应战时间">
            <InputNumber
              aria-label="普通遭遇应战时间"
              min={10}
              max={3600}
              value={draft.encounter_response_seconds ?? 60}
              onChange={(value) =>
                update({ encounter_response_seconds: value ?? 60 })
              }
            />
          </Form.Item>
          <Form.Item label="配装准备时间">
            <InputNumber
              aria-label="配装准备时间"
              min={10}
              max={3600}
              value={draft.battle_prepare_seconds ?? 60}
              onChange={(value) =>
                update({ battle_prepare_seconds: value ?? 60 })
              }
            />
          </Form.Item>
          <Form.Item label="玩家行动时间">
            <InputNumber
              aria-label="玩家行动时间"
              min={10}
              max={3600}
              value={draft.player_action_seconds ?? 60}
              onChange={(value) =>
                update({ player_action_seconds: value ?? 60 })
              }
            />
          </Form.Item>
          <Form.Item label="Boss 续战投票时间">
            <InputNumber
              aria-label="Boss 续战投票时间"
              min={10}
              max={3600}
              value={draft.boss_vote_seconds ?? 60}
              onChange={(value) => update({ boss_vote_seconds: value ?? 60 })}
            />
          </Form.Item>
          <Form.Item label="队长无操作判定时间">
            <InputNumber
              aria-label="队长无操作判定时间"
              min={10}
              max={3600}
              value={draft.leader_inactive_seconds ?? 600}
              onChange={(value) =>
                update({ leader_inactive_seconds: value ?? 600 })
              }
            />
          </Form.Item>
          <Form.Item label="队长转移投票时间">
            <InputNumber
              aria-label="队长转移投票时间"
              min={10}
              max={3600}
              value={draft.leader_transfer_vote_seconds ?? 60}
              onChange={(value) =>
                update({ leader_transfer_vote_seconds: value ?? 60 })
              }
            />
          </Form.Item>
          <Form.Item label="救援等待时间">
            <InputNumber
              aria-label="救援等待时间"
              min={10}
              max={3600}
              value={draft.rescue_wait_seconds ?? 1800}
              onChange={(value) =>
                update({ rescue_wait_seconds: value ?? 1800 })
              }
            />
          </Form.Item>
        </Form>
      </Card>

      <JsonTextarea
        label="秘境主题绑定"
        value={formatJson(draft.themes ?? [])}
        readOnly
      />
      <JsonTextarea
        label="秘境掉落覆盖 JSON"
        value={formatJson(draft.drop_overrides ?? {})}
        readOnly
      />
    </div>
  )
}
