import { Bar } from "@ant-design/charts"
import { Card, List, Progress, Space, Tag, Typography } from "antd"
import { ConfirmAction, MetricCard, PageHeader } from "@/features/shared/ui"
import { formatCompactNumber, formatNumber } from "@/lib/format"
import type { DashboardPayload, PlayerSummary } from "@/lib/types"

function PlayerListCard({
  title,
  description,
  players,
  detail,
}: {
  title: string
  description: string
  players: PlayerSummary[]
  detail: (player: PlayerSummary) => string
}) {
  return (
    <Card
      title={title}
      extra={<Typography.Text type="secondary">{description}</Typography.Text>}
    >
      <List
        dataSource={players}
        renderItem={(player) => (
          <List.Item
            actions={[
              <Tag key="power">{formatCompactNumber(player.battle_power)}</Tag>,
            ]}
          >
            <List.Item.Meta
              title={
                <Space wrap>
                  <span>{player.nickname || player.user_id}</span>
                  <Tag>{player.realm}</Tag>
                </Space>
              }
              description={detail(player)}
            />
          </List.Item>
        )}
      />
    </Card>
  )
}

export function DashboardWorkspace({
  dashboard,
  onBackup,
}: {
  dashboard: DashboardPayload
  onBackup: () => void
}) {
  const signinPercent = Math.round(
    dashboard.health_flags.today_signin_ratio * 100,
  )
  const inactivePercent = Math.round(
    dashboard.health_flags.inactive_ratio * 100,
  )

  return (
    <div className="workspace-stack">
      <PageHeader
        title="修仙运维控制台"
        description={`快照日期 ${dashboard.generated_date}，当前为 ${dashboard.mode} 模式。`}
        actions={
          <ConfirmAction
            triggerLabel="创建玩家备份"
            title="创建玩家数据备份？"
            description="备份会复制当前玩家存档文件，适合在批量调整前执行。"
            actionLabel="创建备份"
            onConfirm={onBackup}
          />
        }
      />

      <div className="metric-grid">
        <MetricCard
          label="玩家总数"
          value={formatNumber(dashboard.metrics.total_players)}
        />
        <MetricCard
          label="今日签到"
          value={formatNumber(dashboard.metrics.signed_today)}
        />
        <MetricCard
          label="活跃玩家"
          value={formatNumber(dashboard.metrics.recent_active)}
        />
        <MetricCard
          label="风险沉默"
          value={formatNumber(dashboard.metrics.inactive_risk)}
        />
      </div>

      <div className="two-column">
        <Card
          className="chart-card"
          title="境界分布"
          extra="按当前玩家存档生成的境界快照"
        >
          <Bar
            data={dashboard.realm_distribution}
            xField="count"
            yField="realm"
            height={280}
            colorField="realm"
            label={{
              text: "count",
              position: "right",
            }}
            axis={{
              x: { title: "玩家数" },
              y: { title: false },
            }}
            tooltip={{
              title: "realm",
            }}
          />
        </Card>

        <Card title="健康状态" data-testid="dashboard-maintenance-card">
          <Space orientation="vertical" size="large" className="full-width">
            <div>
              <Space className="full-width" orientation="vertical">
                <Typography.Text type="secondary">今日签到率</Typography.Text>
                <Progress percent={signinPercent} />
              </Space>
            </div>
            <div>
              <Space className="full-width" orientation="vertical">
                <Typography.Text type="secondary">沉默风险</Typography.Text>
                <Progress
                  percent={inactivePercent}
                  status={inactivePercent > 25 ? "exception" : "normal"}
                />
              </Space>
            </div>
            <ConfirmAction
              triggerLabel="创建玩家备份"
              title="创建玩家数据备份？"
              description="备份会复制当前玩家存档文件，适合在批量调整前执行。"
              actionLabel="创建备份"
              onConfirm={onBackup}
            />
          </Space>
        </Card>
      </div>

      <div className="catalog-grid">
        <PlayerListCard
          title="战力排行"
          description="按实时战力计算排序。"
          players={dashboard.top_battle_power}
          detail={(player) =>
            `${formatNumber(player.spirit_stones)} 灵石 / ${player.user_id}`
          }
        />
        <PlayerListCard
          title="最近签到"
          description="展示最近发生的签到记录。"
          players={dashboard.recent_signins}
          detail={(player) =>
            `${player.last_sign_date || "未知日期"} / ${player.user_id}`
          }
        />
        <PlayerListCard
          title="沉默风险"
          description="长时间未签到的玩家优先显示。"
          players={dashboard.inactive_players}
          detail={(player) =>
            `${formatNumber(player.days_since_sign ?? 0)} 天未签到 / ${player.user_id}`
          }
        />
      </div>

      <Card
        title="资源汇总"
        extra={
          <Tag>
            {dashboard.capabilities.snapshot_dashboard ? "快照" : "实时"}
          </Tag>
        }
      >
        <div className="metric-grid">
          <MetricCard
            label="灵石总量"
            value={formatCompactNumber(dashboard.metrics.total_spirit_stones)}
          />
          <MetricCard
            label="平均灵石"
            value={formatNumber(dashboard.metrics.average_spirit_stones)}
          />
          <MetricCard
            label="平均战力"
            value={formatCompactNumber(dashboard.metrics.average_battle_power)}
          />
        </div>
      </Card>
    </div>
  )
}
