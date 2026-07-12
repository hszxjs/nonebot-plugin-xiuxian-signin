import { Badge } from "@/components/ui/badge"
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from "@/components/ui/item"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { formatCompactNumber, formatNumber, formatPercent } from "@/lib/format"
import type { DashboardPayload, PlayerSummary } from "@/lib/types"
import { ConfirmAction, MetricCard, PageHeader } from "@/features/shared/ui"

function PlayerItem({ player, detail }: { player: PlayerSummary; detail: string }) {
  return (
    <Item variant={player.inactive_risk ? "outline" : "default"}>
      <ItemContent>
        <ItemTitle>
          {player.nickname || player.user_id}
          <Badge variant="outline">{player.realm}</Badge>
        </ItemTitle>
        <ItemDescription>{detail}</ItemDescription>
      </ItemContent>
      <ItemActions>
        <Badge variant="secondary">{formatCompactNumber(player.battle_power)}</Badge>
      </ItemActions>
    </Item>
  )
}

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
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ItemGroup>
          {players.map((player) => (
            <PlayerItem key={`${title}-${player.user_id}`} player={player} detail={detail(player)} />
          ))}
        </ItemGroup>
      </CardContent>
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
  const signinPercent = dashboard.health_flags.today_signin_ratio * 100
  const inactivePercent = dashboard.health_flags.inactive_ratio * 100

  return (
    <div className="flex flex-col gap-4">
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
            variant="outline"
          />
        }
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="玩家总数" value={formatNumber(dashboard.metrics.total_players)} />
        <MetricCard label="今日签到" value={formatNumber(dashboard.metrics.signed_today)} />
        <MetricCard label="活跃玩家" value={formatNumber(dashboard.metrics.recent_active)} />
        <MetricCard label="风险沉默" value={formatNumber(dashboard.metrics.inactive_risk)} />
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Card>
          <CardHeader>
            <CardTitle>境界分布</CardTitle>
            <CardDescription>按当前玩家存档生成的境界快照。</CardDescription>
          </CardHeader>
          <CardContent>
            <ItemGroup>
              {dashboard.realm_distribution.map((item) => (
                <Item key={item.realm}>
                  <ItemContent>
                    <ItemTitle>{item.realm}</ItemTitle>
                    <ItemDescription>{formatNumber(item.count)} 名玩家</ItemDescription>
                  </ItemContent>
                  <ItemActions>
                    <Badge variant="outline">{formatNumber(item.count)}</Badge>
                  </ItemActions>
                </Item>
              ))}
            </ItemGroup>
          </CardContent>
        </Card>

        <Card data-testid="dashboard-maintenance-card">
          <CardHeader>
            <CardTitle>健康状态</CardTitle>
            <CardDescription>签到率和沉默风险用于判断活动状态。</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-3">
                  <CardDescription>今日签到率</CardDescription>
                  <Badge variant="secondary">{formatPercent(dashboard.health_flags.today_signin_ratio)}</Badge>
                </div>
                <Progress value={signinPercent} />
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between gap-3">
                  <CardDescription>沉默风险</CardDescription>
                  <Badge variant={dashboard.health_flags.inactive_ratio > 0.25 ? "destructive" : "outline"}>
                    {formatPercent(dashboard.health_flags.inactive_ratio)}
                  </Badge>
                </div>
                <Progress value={inactivePercent} />
              </div>
              <Separator />
              <ConfirmAction
                triggerLabel="创建玩家备份"
                title="创建玩家数据备份？"
                description="备份会复制当前玩家存档文件，适合在批量调整前执行。"
                actionLabel="创建备份"
                onConfirm={onBackup}
                variant="outline"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <PlayerListCard
          title="战力排行"
          description="按实时战力计算排序。"
          players={dashboard.top_battle_power}
          detail={(player) => `${formatNumber(player.spirit_stones)} 灵石 / ${player.user_id}`}
        />
        <PlayerListCard
          title="最近签到"
          description="展示最近发生的签到记录。"
          players={dashboard.recent_signins}
          detail={(player) => `${player.last_sign_date || "未知日期"} / ${player.user_id}`}
        />
        <PlayerListCard
          title="沉默风险"
          description="长时间未签到的玩家优先显示。"
          players={dashboard.inactive_players}
          detail={(player) => `${formatNumber(player.days_since_sign ?? 0)} 天未签到 / ${player.user_id}`}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>资源汇总</CardTitle>
          <CardDescription>用于判断经济规模和平均养成强度。</CardDescription>
          <CardAction>
            <Badge variant="outline">{dashboard.capabilities.snapshot_dashboard ? "快照" : "实时"}</Badge>
          </CardAction>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <MetricCard label="灵石总量" value={formatCompactNumber(dashboard.metrics.total_spirit_stones)} />
            <MetricCard label="平均灵石" value={formatNumber(dashboard.metrics.average_spirit_stones)} />
            <MetricCard label="平均战力" value={formatCompactNumber(dashboard.metrics.average_battle_power)} />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
