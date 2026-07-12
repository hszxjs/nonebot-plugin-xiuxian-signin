import { Card, Checkbox, List, Progress, Space, Tag } from "antd"

import { formatJson, formatNumber, formatPercent } from "@/lib/format"
import type { MysticPayload } from "@/lib/types"
import { JsonTextarea, PageHeader } from "@/features/shared/ui"

export function MysticWorkspace({ payload }: { payload: MysticPayload }) {
  const mystic = payload.mystic

  return (
    <div className="workspace-stack">
      <PageHeader title="秘境规则" description="查看秘境入口池、类别权重和掉落覆盖。" />

      <div className="catalog-grid">
        <Card title="普通秘境">
          <Checkbox.Group value={mystic.enabled_types}>
            <Space orientation="vertical">
              {mystic.types.map((type) => (
                <Checkbox key={type} value={type} disabled>
                  {type}
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        </Card>

        <Card title="高风险秘境">
          <Checkbox.Group value={mystic.enabled_high_risk_types}>
            <Space orientation="vertical">
              {mystic.high_risk_types.map((type) => (
                <Checkbox key={type} value={type} disabled>
                  {type}
                </Checkbox>
              ))}
            </Space>
          </Checkbox.Group>
        </Card>

        <Card title="触发概率">
          <Space orientation="vertical" className="full-width">
            <div>
              <span>钓鱼入口概率</span>
              <Progress percent={Math.round(mystic.fishing_option_rate * 100)} />
            </div>
            <div>
              <span>额外钓鱼机会</span>
              <Progress percent={Math.round(mystic.extra_fishing_chance_rate * 100)} />
            </div>
            <Tag>{formatPercent(mystic.fishing_option_rate)}</Tag>
          </Space>
        </Card>
      </div>

      <Card title="类别权重">
        <List
          dataSource={Object.entries(mystic.category_weights)}
          renderItem={([category, weight]) => (
            <List.Item actions={[<Tag key="weight">{formatNumber(weight)}</Tag>]}>
              <List.Item.Meta title={category} description={`权重 ${formatNumber(weight)}`} />
            </List.Item>
          )}
        />
      </Card>

      <JsonTextarea label="秘境掉落覆盖 JSON" value={formatJson(mystic.drop_overrides)} readOnly />
    </div>
  )
}
