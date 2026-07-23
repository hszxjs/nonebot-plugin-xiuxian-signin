import {
  Card,
  Form,
  Input,
  InputNumber,
  List,
  Select,
  Space,
  Tag,
  Typography,
} from "antd"
import { useMemo, useState } from "react"
import {
  ConfirmAction,
  EmptyPanel,
  PageHeader,
  SearchField,
} from "@/features/shared/ui"
import { formatCompactNumber, formatNumber } from "@/lib/format"
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

  return (
    <Form layout="vertical">
      <Typography.Text type="secondary">
        未在表单中展示的存档字段会原样保留；常用字段不再需要编辑英文 JSON。
      </Typography.Text>

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
        <Form.Item label="境界">
          <Select
            value={numberValue(record.realm_index)}
            options={realmOptions(meta)}
            onChange={(value) => updateField("realm_index", value)}
          />
        </Form.Item>
        <Form.Item label="修行路线">
          <Select
            allowClear
            value={stringValue(record.cultivation_route) || undefined}
            options={selectOptions(meta.cultivation_routes)}
            onChange={(value) => updateField("cultivation_route", value ?? "")}
          />
        </Form.Item>
        <Form.Item label="灵石">
          <InputNumber
            className="full-width"
            min={0}
            value={numberValue(record.spirit_stones)}
            onChange={(value) =>
              updateField("spirit_stones", Number(value ?? 0))
            }
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
        <Form.Item label="签到次数">
          <InputNumber
            className="full-width"
            min={0}
            value={numberValue(record.sign_count)}
            onChange={(value) => updateField("sign_count", Number(value ?? 0))}
          />
        </Form.Item>
        <Form.Item label="钓鱼次数">
          <InputNumber
            className="full-width"
            min={0}
            value={numberValue(record.fishing_chances)}
            onChange={(value) =>
              updateField("fishing_chances", Number(value ?? 0))
            }
          />
        </Form.Item>
      </div>

      <Card size="small" title="灵根">
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
        </div>
      </Card>

      <Space wrap>
        <Tag>当前灵石：{formatNumber(record.spirit_stones ?? 0)}</Tag>
        <Tag>未知字段已保留</Tag>
      </Space>

      <div>
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
