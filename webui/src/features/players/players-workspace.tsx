import {
  Alert,
  Card,
  Collapse,
  Form,
  Input,
  InputNumber,
  List,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
} from "antd"
import { useMemo, useState } from "react"
import {
  ConfirmAction,
  EmptyPanel,
  JsonTextarea,
  PageHeader,
  SearchField,
} from "@/features/shared/ui"
import { formatCompactNumber, formatJson, formatNumber } from "@/lib/format"
import type {
  JsonRecord,
  JsonValue,
  PlayerDetailPayload,
  PlayerSummary,
} from "@/lib/types"

function playerText(player: PlayerSummary) {
  return [player.user_id, player.nickname, player.realm]
    .join("\n")
    .toLowerCase()
}

function asRecord(value: JsonValue | undefined): JsonRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as JsonRecord)
    : {}
}

function stringValue(value: JsonValue | undefined) {
  return typeof value === "string" ? value : ""
}

function numberValue(value: JsonValue | undefined) {
  return typeof value === "number" ? value : undefined
}

function booleanValue(value: JsonValue | undefined) {
  return typeof value === "boolean" ? value : false
}

function selectOptions(values: string[]) {
  return values.map((value) => ({ value, label: value }))
}

function realmOptions(meta: PlayerDetailPayload["meta"]) {
  return meta.realms.map((realm) => ({ value: realm.index, label: realm.name }))
}

export function PlayersWorkspace({
  players,
  selectedPlayer,
  query,
  onQueryChange,
  onSelectPlayer,
  onSavePlayer,
}: {
  players: PlayerSummary[]
  selectedPlayer?: PlayerDetailPayload | null
  query: string
  onQueryChange: (query: string) => void
  onSelectPlayer: (userId: string) => void
  onSavePlayer: (record: JsonRecord) => void
}) {
  const filteredPlayers = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) {
      return players
    }
    return players.filter((player) => playerText(player).includes(normalized))
  }, [players, query])

  return (
    <div className="workspace-stack">
      <PageHeader
        title="玩家管理"
        description="玩家是动态实体列表，使用搜索和结构化详情面板处理。"
      />

      <div className="player-grid">
        <Card
          title="玩家列表"
          extra={`${filteredPlayers.length} / ${players.length} 名玩家`}
        >
          <Space orientation="vertical" size="middle" className="full-width">
            <SearchField
              value={query}
              onChange={onQueryChange}
              placeholder="搜索 QQ、昵称或境界"
            />
            <div className="player-list">
              {filteredPlayers.length ? (
                <List
                  dataSource={filteredPlayers}
                  renderItem={(player) => (
                    <List.Item
                      className={
                        selectedPlayer?.record.user_id === player.user_id
                          ? "selected-list-item"
                          : ""
                      }
                      actions={[
                        <Tag key="power">
                          {formatCompactNumber(player.battle_power)}
                        </Tag>,
                      ]}
                      onClick={() => onSelectPlayer(player.user_id)}
                    >
                      <List.Item.Meta
                        title={
                          <Space wrap>
                            <span>{player.nickname || player.user_id}</span>
                            <Tag>{player.realm}</Tag>
                          </Space>
                        }
                        description={player.user_id}
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <EmptyPanel
                  title="没有匹配玩家"
                  description="调整搜索词后再查看。"
                />
              )}
            </div>
          </Space>
        </Card>

        <Card title="玩家详情" extra="核心字段使用中文表单控件">
          {selectedPlayer ? (
            <PlayerRecordEditor
              key={String(selectedPlayer.record.user_id ?? "")}
              selectedPlayer={selectedPlayer}
              onSavePlayer={onSavePlayer}
            />
          ) : (
            <EmptyPanel
              title="未选择玩家"
              description="从左侧列表选择一个玩家查看详情。"
            />
          )}
        </Card>
      </div>
    </div>
  )
}

function PlayerRecordEditor({
  selectedPlayer,
  onSavePlayer,
}: {
  selectedPlayer: PlayerDetailPayload
  onSavePlayer: (record: JsonRecord) => void
}) {
  const [record, setRecord] = useState<JsonRecord>(selectedPlayer.record)
  const [rawJsonText, setRawJsonText] = useState<string>("")
  const [rawJsonError, setRawJsonError] = useState<string>("")
  const root = asRecord(record.root)
  const meta = selectedPlayer.meta

  function updateField(key: string, value: JsonValue) {
    setRecord((current) => ({ ...current, [key]: value }))
  }

  function updateRootField(key: string, value: JsonValue) {
    setRecord((current) => ({
      ...current,
      root: {
        ...asRecord(current.root),
        [key]: value,
      },
    }))
  }

  // 当展开原始 JSON 面板时，用当前 record 初始化文本；编辑时实时回写。
  function handleRawJsonChange(text: string) {
    setRawJsonText(text)
    if (!text.trim()) {
      setRawJsonError("")
      return
    }
    try {
      const parsed = JSON.parse(text)
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        setRecord(parsed as JsonRecord)
        setRawJsonError("")
      } else {
        setRawJsonError("JSON 根节点必须是对象（{ ... }）。")
      }
    } catch (error) {
      setRawJsonError(`解析失败：${String((error as Error).message)}`)
    }
  }

  function handleRawJsonExpand(active: boolean) {
    if (active) {
      // 展开时同步当前 record 到文本框
      setRawJsonText(formatJson(record))
      setRawJsonError("")
    }
  }

  return (
    <Form layout="vertical">
      <Typography.Text type="secondary">
        未在表单中展示的存档字段会原样保留；常用字段不再需要编辑英文 JSON。
        复杂结构（装备/背包/熟练度等）使用 JSON 编辑，底部「原始
        JSON」可改任意字段。
      </Typography.Text>

      <Card size="small" title="基础信息" style={{ marginTop: 12 }}>
        <div className="catalog-grid">
          <Form.Item label="用户 ID">
            <Input value={String(record.user_id ?? "")} readOnly />
          </Form.Item>
          <Form.Item label="昵称">
            <Input
              value={stringValue(record.nickname)}
              onChange={(event) => updateField("nickname", event.target.value)}
            />
          </Form.Item>
        </div>
      </Card>

      <Card size="small" title="境界与经验" style={{ marginTop: 12 }}>
        <div className="catalog-grid">
          <Form.Item label="境界">
            <Select
              value={numberValue(record.realm_index)}
              options={realmOptions(meta)}
              onChange={(value) => updateField("realm_index", value)}
            />
          </Form.Item>
          <Form.Item label="境界经验">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.realm_exp)}
              onChange={(value) => updateField("realm_exp", Number(value ?? 0))}
            />
          </Form.Item>
          <Form.Item label="总修为 (total_exp)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.total_exp)}
              onChange={(value) => updateField("total_exp", Number(value ?? 0))}
            />
          </Form.Item>
          <Form.Item label="灵石 (spirit_stones)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.spirit_stones)}
              onChange={(value) =>
                updateField("spirit_stones", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="灵液 (spirit_liquid)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.spirit_liquid)}
              onChange={(value) =>
                updateField("spirit_liquid", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="待结修为 (pending_exp)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.pending_exp)}
              onChange={(value) =>
                updateField("pending_exp", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="待结钓鱼 (pending_fishing)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.pending_fishing)}
              onChange={(value) =>
                updateField("pending_fishing", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="瓶颈天数 (bottleneck_days)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.bottleneck_days)}
              onChange={(value) =>
                updateField("bottleneck_days", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="瓶颈境界索引 (bottleneck_realm_index)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.bottleneck_realm_index)}
              onChange={(value) =>
                updateField("bottleneck_realm_index", Number(value ?? 0))
              }
            />
          </Form.Item>
        </div>
      </Card>

      <Card size="small" title="签到与日常" style={{ marginTop: 12 }}>
        <div className="catalog-grid">
          <Form.Item label="签到次数 (sign_count)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.sign_count)}
              onChange={(value) =>
                updateField("sign_count", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="钓鱼次数 (fishing_chances)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.fishing_chances)}
              onChange={(value) =>
                updateField("fishing_chances", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="上次签到 (last_sign_date)">
            <Input
              value={stringValue(record.last_sign_date)}
              placeholder="如 2026-07-26"
              onChange={(event) =>
                updateField("last_sign_date", event.target.value)
              }
            />
          </Form.Item>
          <Form.Item label="上次奇遇 (last_encounter_date)">
            <Input
              value={stringValue(record.last_encounter_date)}
              onChange={(event) =>
                updateField("last_encounter_date", event.target.value)
              }
            />
          </Form.Item>
          <Form.Item label="上次瓶颈 (last_bottleneck_date)">
            <Input
              value={stringValue(record.last_bottleneck_date)}
              onChange={(event) =>
                updateField("last_bottleneck_date", event.target.value)
              }
            />
          </Form.Item>
          <Form.Item label="修炼锁定至 (cultivation_lock_until)">
            <Input
              value={stringValue(record.cultivation_lock_until)}
              onChange={(event) =>
                updateField("cultivation_lock_until", event.target.value)
              }
            />
          </Form.Item>
          <Form.Item label="双修日期 (dual_cultivation_date)">
            <Input
              value={stringValue(record.dual_cultivation_date)}
              onChange={(event) =>
                updateField("dual_cultivation_date", event.target.value)
              }
            />
          </Form.Item>
          <Form.Item label="双修已用次数 (dual_cultivation_used)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.dual_cultivation_used)}
              onChange={(value) =>
                updateField("dual_cultivation_used", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="仙源转化天数 (immortal_conversion_days)">
            <InputNumber
              className="full-width"
              min={0}
              value={numberValue(record.immortal_conversion_days)}
              onChange={(value) =>
                updateField("immortal_conversion_days", Number(value ?? 0))
              }
            />
          </Form.Item>
          <Form.Item label="上次仙源转化 (last_immortal_conversion_date)">
            <Input
              value={stringValue(record.last_immortal_conversion_date)}
              onChange={(event) =>
                updateField("last_immortal_conversion_date", event.target.value)
              }
            />
          </Form.Item>
          <Form.Item label="上次天机秘境 (last_tianji_mystic_date)">
            <Input
              value={stringValue(record.last_tianji_mystic_date)}
              onChange={(event) =>
                updateField("last_tianji_mystic_date", event.target.value)
              }
            />
          </Form.Item>
        </div>
      </Card>

      <Card size="small" title="身份与体质" style={{ marginTop: 12 }}>
        <div className="catalog-grid">
          <Form.Item label="修行路线 (cultivation_route)">
            <Select
              allowClear
              value={stringValue(record.cultivation_route) || undefined}
              options={selectOptions(meta.cultivation_routes)}
              onChange={(value) =>
                updateField("cultivation_route", value ?? "")
              }
            />
          </Form.Item>
          <Form.Item label="邪修 (evil_cultivator)">
            <Switch
              checked={booleanValue(record.evil_cultivator)}
              onChange={(checked) => updateField("evil_cultivator", checked)}
            />
          </Form.Item>
          <Form.Item label="门派身份 (faction_identity)">
            <Input
              value={stringValue(record.faction_identity)}
              onChange={(event) =>
                updateField("faction_identity", event.target.value)
              }
            />
          </Form.Item>
          <Form.Item label="体质 (physique)">
            <Input
              value={stringValue(record.physique)}
              onChange={(event) => updateField("physique", event.target.value)}
            />
          </Form.Item>
          <Form.Item label="战斗种族 (combat_race)">
            <Input
              value={stringValue(record.combat_race)}
              onChange={(event) =>
                updateField("combat_race", event.target.value)
              }
            />
          </Form.Item>
          <Form.Item label="筑基类型 (foundation_type)">
            <Input
              value={stringValue(record.foundation_type)}
              onChange={(event) =>
                updateField("foundation_type", event.target.value)
              }
            />
          </Form.Item>
        </div>
        <Form.Item
          label="特殊能力 (special_abilities)"
          style={{ marginTop: 8 }}
        >
          <Input.TextArea
            autoSize={{ minRows: 2 }}
            value={formatJson(record.special_abilities ?? [])}
            onChange={(event) => {
              const text = event.target.value
              try {
                const parsed = JSON.parse(text)
                updateField("special_abilities", parsed as JsonValue)
              } catch {
                /* 输入未完成时忽略解析错误，保存时由后端校验 */
              }
            }}
          />
        </Form.Item>
      </Card>

      <Card size="small" title="灵根" style={{ marginTop: 12 }}>
        <div className="catalog-grid">
          <Form.Item label="灵根属性">
            <Select
              allowClear
              value={stringValue(root.attribute) || undefined}
              options={meta.attributes.map((attribute) => ({
                value: attribute,
                label: meta.attribute_labels[attribute] || attribute,
              }))}
              onChange={(value) => updateRootField("attribute", value ?? "")}
            />
          </Form.Item>
          <Form.Item label="灵根品阶">
            <Select
              allowClear
              value={stringValue(root.tier) || undefined}
              options={selectOptions(meta.tiers)}
              onChange={(value) => updateRootField("tier", value ?? "")}
            />
          </Form.Item>
          <Form.Item label="灵根等级">
            <Select
              allowClear
              value={stringValue(root.grade) || undefined}
              options={selectOptions(meta.grades)}
              onChange={(value) => updateRootField("grade", value ?? "")}
            />
          </Form.Item>
          <Form.Item label="纯度 (purity)">
            <InputNumber
              className="full-width"
              min={1}
              max={100}
              value={numberValue(root.purity)}
              onChange={(value) =>
                updateRootField("purity", Number(value ?? 100))
              }
            />
          </Form.Item>
          <Form.Item label="异变 (mutated)">
            <Switch
              checked={booleanValue(root.mutated)}
              onChange={(checked) => updateRootField("mutated", checked)}
            />
          </Form.Item>
          <Form.Item label="天赋 (trait)">
            <Input
              value={stringValue(root.trait)}
              onChange={(event) => updateRootField("trait", event.target.value)}
            />
          </Form.Item>
        </div>
        <Form.Item label="灵根来源 (sources)" style={{ marginTop: 8 }}>
          <Input.TextArea
            autoSize={{ minRows: 2 }}
            value={formatJson(root.sources ?? [])}
            onChange={(event) => {
              const text = event.target.value
              try {
                const parsed = JSON.parse(text)
                updateRootField("sources", parsed as JsonValue)
              } catch {
                /* 忽略未完成输入 */
              }
            }}
          />
        </Form.Item>
        <Form.Item label="来源纯度 (source_purities)">
          <Input.TextArea
            autoSize={{ minRows: 2 }}
            value={formatJson(root.source_purities ?? {})}
            onChange={(event) => {
              const text = event.target.value
              try {
                const parsed = JSON.parse(text)
                updateRootField("source_purities", parsed as JsonValue)
              } catch {
                /* 忽略未完成输入 */
              }
            }}
          />
        </Form.Item>
        <JsonTextarea
          label="额外灵根 (extra_roots)"
          value={record.extra_roots ?? []}
          onChange={(text) => {
            try {
              updateField("extra_roots", JSON.parse(text) as JsonValue)
            } catch {
              /* 忽略未完成输入 */
            }
          }}
          rows={4}
        />
        <JsonTextarea
          label="获得灵根 (acquired_roots)"
          value={record.acquired_roots ?? []}
          onChange={(text) => {
            try {
              updateField("acquired_roots", JSON.parse(text) as JsonValue)
            } catch {
              /* 忽略未完成输入 */
            }
          }}
          rows={4}
        />
      </Card>

      <Card size="small" title="装备与背包" style={{ marginTop: 12 }}>
        <Typography.Text type="secondary">
          以下字段结构复杂，使用 JSON 编辑；保存时后端会做字段校验与归一化。
        </Typography.Text>
        <Space
          orientation="vertical"
          size="small"
          className="full-width"
          style={{ marginTop: 8 }}
        >
          <JsonTextarea
            label="本命法宝 (equipped_artifact)"
            value={record.equipped_artifact ?? null}
            onChange={(text) => {
              try {
                updateField("equipped_artifact", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="多槽装备 (equipped_artifacts)"
            value={record.equipped_artifacts ?? {}}
            onChange={(text) => {
              try {
                updateField("equipped_artifacts", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="符箓 (equipped_talisman)"
            value={record.equipped_talisman ?? null}
            onChange={(text) => {
              try {
                updateField("equipped_talisman", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="功法 (equipped_method)"
            value={record.equipped_method ?? null}
            onChange={(text) => {
              try {
                updateField("equipped_method", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="阵法 (equipped_array)"
            value={record.equipped_array ?? null}
            onChange={(text) => {
              try {
                updateField("equipped_array", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="傀儡 (equipped_puppet)"
            value={record.equipped_puppet ?? null}
            onChange={(text) => {
              try {
                updateField("equipped_puppet", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="已种灵植 (planted_spirit_plant)"
            value={record.planted_spirit_plant ?? null}
            onChange={(text) => {
              try {
                updateField(
                  "planted_spirit_plant",
                  JSON.parse(text) as JsonValue,
                )
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="本命器 (life_artifact)"
            value={record.life_artifact ?? null}
            onChange={(text) => {
              try {
                updateField("life_artifact", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="已装备仙种 (equipped_immortal_seed)"
            value={record.equipped_immortal_seed ?? null}
            onChange={(text) => {
              try {
                updateField(
                  "equipped_immortal_seed",
                  JSON.parse(text) as JsonValue,
                )
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="仙种列表 (immortal_seeds)"
            value={record.immortal_seeds ?? []}
            onChange={(text) => {
              try {
                updateField("immortal_seeds", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="背包奖励 (rewards)"
            value={record.rewards ?? []}
            onChange={(text) => {
              try {
                updateField("rewards", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={6}
          />
        </Space>
      </Card>

      <Card size="small" title="其它字段" style={{ marginTop: 12 }}>
        <div className="catalog-grid">
          <Form.Item label="秘境运行ID (active_mystic_run_id)">
            <Input
              value={stringValue(record.active_mystic_run_id)}
              onChange={(event) =>
                updateField("active_mystic_run_id", event.target.value)
              }
            />
          </Form.Item>
        </div>
        <Space orientation="vertical" size="small" className="full-width">
          <JsonTextarea
            label="秘境结算ID (mystic_settlement_ids)"
            value={record.mystic_settlement_ids ?? []}
            onChange={(text) => {
              try {
                updateField(
                  "mystic_settlement_ids",
                  JSON.parse(text) as JsonValue,
                )
              } catch {
                /* 忽略 */
              }
            }}
            rows={3}
          />
          <JsonTextarea
            label="每日任务 (daily_tasks)"
            value={record.daily_tasks ?? null}
            onChange={(text) => {
              try {
                updateField("daily_tasks", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={4}
          />
          <JsonTextarea
            label="身份签到 (identity_sign_days)"
            value={record.identity_sign_days ?? {}}
            onChange={(text) => {
              try {
                updateField("identity_sign_days", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={3}
          />
          <JsonTextarea
            label="功法层数 (method_layers)"
            value={record.method_layers ?? {}}
            onChange={(text) => {
              try {
                updateField("method_layers", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={3}
          />
          <JsonTextarea
            label="功法熟练度 (method_proficiency)"
            value={record.method_proficiency ?? {}}
            onChange={(text) => {
              try {
                updateField("method_proficiency", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={3}
          />
          <JsonTextarea
            label="阵法层数 (array_layers)"
            value={record.array_layers ?? {}}
            onChange={(text) => {
              try {
                updateField("array_layers", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={3}
          />
          <JsonTextarea
            label="阵法熟练度 (array_proficiency)"
            value={record.array_proficiency ?? {}}
            onChange={(text) => {
              try {
                updateField("array_proficiency", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={3}
          />
          <JsonTextarea
            label="境界印记 (realm_marks)"
            value={record.realm_marks ?? {}}
            onChange={(text) => {
              try {
                updateField("realm_marks", JSON.parse(text) as JsonValue)
              } catch {
                /* 忽略 */
              }
            }}
            rows={3}
          />
        </Space>
      </Card>

      <Collapse
        style={{ marginTop: 12 }}
        items={[
          {
            key: "raw-json",
            label: "原始存档 JSON（高级，可编辑任意字段）",
            children: (
              <>
                {rawJsonError ? (
                  <Alert
                    type="error"
                    showIcon
                    message={rawJsonError}
                    style={{ marginBottom: 8 }}
                  />
                ) : null}
                <Input.TextArea
                  value={rawJsonText}
                  onChange={(event) => handleRawJsonChange(event.target.value)}
                  rows={16}
                  spellCheck={false}
                />
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  编辑后会实时解析并覆盖上方表单值；解析失败时不会写入，保存按钮仍可点击（以表单值为准）。
                </Typography.Text>
              </>
            ),
          },
        ]}
        onChange={(keys) => handleRawJsonExpand(keys.length > 0)}
      />

      <Space wrap style={{ marginTop: 12 }}>
        <Tag>当前灵石：{formatNumber(record.spirit_stones ?? 0)}</Tag>
        <Tag>未知字段已保留</Tag>
      </Space>

      <div style={{ marginTop: 12 }}>
        <ConfirmAction
          triggerLabel="保存玩家存档"
          title="覆盖该玩家存档？"
          description="该操作会写入用户存档文件，请确认表单字段无误。"
          actionLabel="保存存档"
          onConfirm={() => onSavePlayer(record)}
          danger
        />
      </div>
    </Form>
  )
}
