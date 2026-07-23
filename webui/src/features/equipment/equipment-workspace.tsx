import { Card, List, Space, Tag, Typography } from "antd"
import { JsonTextarea, PageHeader, TagList } from "@/features/shared/ui"
import { formatJson, formatNumber } from "@/lib/format"
import type { EquipmentPayload } from "@/lib/types"

export function EquipmentWorkspace({ payload }: { payload: EquipmentPayload }) {
  const unlocks = Object.entries(payload.rules.realm_tier_unlocks ?? {})
  const tierDefaults = Object.entries(payload.rules.tier_default_realm ?? {})

  return (
    <div className="workspace-stack">
      <PageHeader
        title="装备规则"
        description="展示境界解锁、默认境界和法器目录。"
      />

      <div className="catalog-grid">
        <Card title="境界解锁">
          <List
            dataSource={unlocks}
            renderItem={([realmIndex, tiers]) => (
              <List.Item>
                <List.Item.Meta
                  title={`境界 #${realmIndex}`}
                  description={`${tiers.length} 个品阶`}
                />
                <TagList values={tiers} />
              </List.Item>
            )}
          />
        </Card>

        <Card title="品阶默认境界">
          <List
            dataSource={tierDefaults}
            renderItem={([tier, realmIndex]) => (
              <List.Item
                actions={[<Tag key="realm">{formatNumber(realmIndex)}</Tag>]}
              >
                <List.Item.Meta
                  title={tier}
                  description={`默认境界索引 ${formatNumber(realmIndex)}`}
                />
              </List.Item>
            )}
          />
        </Card>
      </div>

      <Card
        title="法器目录"
        extra={`${payload.meta.artifacts.length} 个境界绑定法器`}
      >
        <List
          dataSource={payload.meta.artifacts}
          renderItem={(artifact) => (
            <List.Item
              actions={[
                <Tag key="tier">{artifact.tier}</Tag>,
                <Tag key="grade">{artifact.grade}</Tag>,
              ]}
            >
              <List.Item.Meta
                title={
                  <Space wrap>
                    <span>{artifact.name}</span>
                    <Tag>{artifact.realm}</Tag>
                  </Space>
                }
                description={
                  <Typography.Text type="secondary">
                    {artifact.attribute_label || artifact.attribute}
                  </Typography.Text>
                }
              />
            </List.Item>
          )}
        />
      </Card>

      <JsonTextarea
        label="装备完整规则 JSON"
        value={formatJson(payload.rules)}
        readOnly
      />
    </div>
  )
}
