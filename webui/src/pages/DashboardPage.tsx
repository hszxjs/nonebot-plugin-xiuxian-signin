import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, Col, List, Row, Space, Statistic, Tag, Typography, theme } from "antd";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { api } from "../lib/api";
import { compactDate, formatNumber, percent } from "../lib/format";
import type { DashboardPayload, DashboardPlayer } from "../lib/types";

const { Text, Title } = Typography;

function PlayerLine({ player, value, index }: { player: DashboardPlayer; value: string; index?: number }) {
  return (
    <List.Item>
      <List.Item.Meta
        avatar={index !== undefined ? <Tag>{index + 1}</Tag> : null}
        description={player.realm}
        title={player.nickname || player.user_id}
      />
      <Text strong>{value}</Text>
    </List.Item>
  );
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
  const { token } = theme.useToken();

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
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <Title level={2}>总览</Title>
          <Text type="secondary">快照日期 {compactDate(data.generated_date)}</Text>
        </div>
        <Tag color="blue">快照</Tag>
      </div>

      <Row gutter={[12, 12]}>
        <Col lg={4} md={8} sm={12} xs={24}>
          <Card>
            <Statistic title="玩家总数" value={data.metrics.total_players} formatter={(value) => formatNumber(value)} />
          </Card>
        </Col>
        <Col lg={4} md={8} sm={12} xs={24}>
          <Card>
            <Statistic
              suffix={<Text type="secondary">{percent(data.health_flags.today_signin_ratio)}</Text>}
              title="今日签到"
              value={data.metrics.signed_today}
              formatter={(value) => formatNumber(value)}
            />
          </Card>
        </Col>
        <Col lg={4} md={8} sm={12} xs={24}>
          <Card>
            <Statistic title="近 7 日活跃" value={data.metrics.recent_active} formatter={(value) => formatNumber(value)} />
          </Card>
        </Col>
        <Col lg={4} md={8} sm={12} xs={24}>
          <Card>
            <Statistic
              suffix={<Text type="secondary">{percent(data.health_flags.inactive_ratio)}</Text>}
              title="疑似流失"
              value={data.metrics.inactive_risk}
              formatter={(value) => formatNumber(value)}
            />
          </Card>
        </Col>
        <Col lg={4} md={8} sm={12} xs={24}>
          <Card>
            <Statistic title="平均战力" value={data.metrics.average_battle_power} formatter={(value) => formatNumber(value)} />
          </Card>
        </Col>
        <Col lg={4} md={8} sm={12} xs={24}>
          <Card>
            <Statistic title="灵石总量" value={data.metrics.total_spirit_stones} formatter={(value) => formatNumber(value)} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xl={15} xs={24}>
          <Card extra={<Tag>{formatNumber(data.realm_distribution.length)} 类</Tag>} title="境界分布">
            {realmDistribution.length ? (
              <div className="chart-panel">
                <ResponsiveContainer height="100%" width="100%">
                  <BarChart data={realmDistribution} layout="vertical" margin={{ bottom: 4, left: 4, right: 12, top: 4 }}>
                    <XAxis allowDecimals={false} tick={{ fontSize: 12 }} type="number" />
                    <YAxis dataKey="realm" tick={{ fontSize: 12 }} tickFormatter={shortRealm} type="category" width={86} />
                    <Tooltip formatter={(value) => [formatNumber(Number(value)), "人数"]} labelFormatter={String} />
                    <Bar dataKey="count" fill={token.colorPrimary} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title="暂无境界数据" />
            )}
          </Card>
        </Col>
        <Col xl={9} xs={24}>
          <Card extra={<Tag>Top {formatNumber(Math.min(data.top_battle_power.length, 8))}</Tag>} title="战力榜">
            {data.top_battle_power.slice(0, 8).length ? (
              <List
                dataSource={data.top_battle_power.slice(0, 8)}
                renderItem={(player, index) => (
                  <PlayerLine index={index} key={player.user_id} player={player} value={formatNumber(player.battle_power)} />
                )}
              />
            ) : (
              <EmptyState title="暂无战力数据" />
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xl={12} xs={24}>
          <Card extra={<Tag>{formatNumber(data.recent_signins.length)} 条</Tag>} title="最近签到">
            {data.recent_signins.length ? (
              <List
                dataSource={data.recent_signins}
                renderItem={(player) => <PlayerLine key={player.user_id} player={player} value={compactDate(player.last_sign_date)} />}
              />
            ) : (
              <EmptyState title="暂无签到记录" />
            )}
          </Card>
        </Col>
        <Col xl={12} xs={24}>
          <Card extra={<Tag>{formatNumber(data.inactive_players.length)} 人</Tag>} title="疑似流失">
            {data.inactive_players.length ? (
              <List
                dataSource={data.inactive_players}
                renderItem={(player) => <PlayerLine key={player.user_id} player={player} value={inactiveLabel(player)} />}
              />
            ) : (
              <EmptyState title="暂无疑似流失玩家" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
