import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { Badge } from "../components/ui/badge";
import { Card } from "../components/ui/card";
import { api } from "../lib/api";
import { compactDate, formatNumber, percent } from "../lib/format";
import type { DashboardPayload, DashboardPlayer } from "../lib/types";

function MetricTile({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return (
    <Card className="min-w-0 rounded-md p-4">
      <div className="truncate text-xs font-medium text-muted-foreground">{label}</div>
      <div className="mt-2 truncate text-2xl font-semibold tracking-normal">{value}</div>
      {detail ? <div className="mt-1 truncate text-xs text-muted-foreground">{detail}</div> : null}
    </Card>
  );
}

function PlayerLine({
  player,
  value,
  index,
}: {
  player: DashboardPlayer;
  value: string;
  index?: number;
}) {
  return (
    <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-md border border-border px-3 py-2 text-sm">
      <div className="flex min-w-0 items-center gap-3">
        {index !== undefined ? (
          <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md bg-muted text-xs font-medium text-muted-foreground">
            {index + 1}
          </span>
        ) : null}
        <div className="min-w-0">
          <div className="truncate font-medium">{player.nickname || player.user_id}</div>
          <div className="truncate text-xs text-muted-foreground">{player.realm}</div>
        </div>
      </div>
      <div className="max-w-28 truncate text-right font-medium">{value}</div>
    </div>
  );
}

function SectionEmpty({ label }: { label: string }) {
  return <div className="rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">{label}</div>;
}

function shortRealm(value: string) {
  return value.length > 6 ? `${value.slice(0, 6)}...` : value;
}

function inactiveLabel(player: DashboardPlayer) {
  if (player.days_since_sign === null) {
    return "未签到";
  }
  return `${formatNumber(player.days_since_sign)} 天`;
}

export function DashboardPage() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      setData(await api<DashboardPayload>("/api/dashboard"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "总览载入失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const realmDistribution = useMemo(() => data?.realm_distribution.slice(0, 10) ?? [], [data]);

  if (loading) {
    return <LoadingState label="正在载入总览" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={load} />;
  }

  if (!data || !data.health_flags.has_players) {
    return <EmptyState title="暂无玩家数据" detail="玩家签到后会显示活跃、境界与留存数据。" />;
  }

  return (
    <div className="grid min-w-0 gap-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold tracking-normal">总览</h1>
          <p className="mt-1 truncate text-sm text-muted-foreground">快照日期 {compactDate(data.generated_date)}</p>
        </div>
        <Badge className="shrink-0">快照</Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <MetricTile label="玩家总数" value={formatNumber(data.metrics.total_players)} />
        <MetricTile
          detail={percent(data.health_flags.today_signin_ratio)}
          label="今日签到"
          value={formatNumber(data.metrics.signed_today)}
        />
        <MetricTile label="近 7 日活跃" value={formatNumber(data.metrics.recent_active)} />
        <MetricTile
          detail={percent(data.health_flags.inactive_ratio)}
          label="疑似流失"
          value={formatNumber(data.metrics.inactive_risk)}
        />
        <MetricTile label="平均战力" value={formatNumber(data.metrics.average_battle_power)} />
        <MetricTile label="灵石总量" value={formatNumber(data.metrics.total_spirit_stones)} />
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
        <Card className="min-w-0 rounded-md p-4">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <h2 className="truncate font-medium">境界分布</h2>
            <Badge className="shrink-0">{formatNumber(data.realm_distribution.length)} 类</Badge>
          </div>
          {realmDistribution.length ? (
            <div className="mt-4 h-[320px] min-w-0 overflow-hidden">
              <ResponsiveContainer height="100%" width="100%">
                <BarChart data={realmDistribution} layout="vertical" margin={{ bottom: 4, left: 4, right: 12, top: 4 }}>
                  <XAxis allowDecimals={false} tick={{ fontSize: 12 }} type="number" />
                  <YAxis
                    dataKey="realm"
                    tick={{ fontSize: 12 }}
                    tickFormatter={shortRealm}
                    type="category"
                    width={86}
                  />
                  <Tooltip formatter={(value) => [formatNumber(Number(value)), "人数"]} labelFormatter={String} />
                  <Bar dataKey="count" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="mt-4">
              <SectionEmpty label="暂无境界数据" />
            </div>
          )}
        </Card>

        <Card className="min-w-0 rounded-md p-4">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <h2 className="truncate font-medium">战力榜</h2>
            <Badge className="shrink-0">Top {formatNumber(Math.min(data.top_battle_power.length, 8))}</Badge>
          </div>
          <div className="mt-3 grid gap-2">
            {data.top_battle_power.slice(0, 8).length ? (
              data.top_battle_power
                .slice(0, 8)
                .map((player, index) => (
                  <PlayerLine
                    index={index}
                    key={player.user_id}
                    player={player}
                    value={formatNumber(player.battle_power)}
                  />
                ))
            ) : (
              <SectionEmpty label="暂无战力数据" />
            )}
          </div>
        </Card>
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <Card className="min-w-0 rounded-md p-4">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <h2 className="truncate font-medium">最近签到</h2>
            <Badge className="shrink-0">{formatNumber(data.recent_signins.length)} 条</Badge>
          </div>
          <div className="mt-3 grid gap-2">
            {data.recent_signins.length ? (
              data.recent_signins.map((player) => (
                <PlayerLine key={player.user_id} player={player} value={compactDate(player.last_sign_date)} />
              ))
            ) : (
              <SectionEmpty label="暂无签到记录" />
            )}
          </div>
        </Card>

        <Card className="min-w-0 rounded-md p-4">
          <div className="flex min-w-0 items-center justify-between gap-3">
            <h2 className="truncate font-medium">疑似流失</h2>
            <Badge className="shrink-0">{formatNumber(data.inactive_players.length)} 人</Badge>
          </div>
          <div className="mt-3 grid gap-2">
            {data.inactive_players.length ? (
              data.inactive_players.map((player) => (
                <PlayerLine key={player.user_id} player={player} value={inactiveLabel(player)} />
              ))
            ) : (
              <SectionEmpty label="暂无疑似流失玩家" />
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
