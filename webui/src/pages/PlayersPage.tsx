import { ReloadOutlined, SaveOutlined, SearchOutlined, UserOutlined } from "@ant-design/icons";
import { Button, Card, Drawer, Flex, Form, Input, Space, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import type { FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { api } from "../lib/api";
import { formatNumber } from "../lib/format";
import type { PlayerDetailPayload, PlayerListPayload, PlayerMeta, PlayerSummary } from "../lib/types";
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";
import { PlayerEditor } from "./playerEditor";
import { sanitizeRecord, type JsonRecord } from "./playerMeta";

const { Text, Title } = Typography;

type SaveState = "idle" | "saving" | "saved" | "error";

function playerName(player: PlayerSummary) {
  return player.nickname || player.user_id;
}

function hasUnsavedChanges(record: JsonRecord | null, originalRecord: JsonRecord | null) {
  if (!record || !originalRecord) {
    return false;
  }
  return JSON.stringify(record) !== JSON.stringify(originalRecord);
}

function confirmDiscard() {
  if (typeof window === "undefined") {
    return true;
  }
  return window.confirm("当前玩家档案有未保存修改，确认切换吗？");
}

function statusColor(dirty: boolean, saveState: SaveState) {
  if (saveState === "saving") {
    return "processing";
  }
  if (saveState === "saved") {
    return "success";
  }
  if (saveState === "error") {
    return "error";
  }
  return dirty ? "warning" : "default";
}

function statusLabel(dirty: boolean, saveState: SaveState) {
  if (saveState === "saving") {
    return "保存中";
  }
  if (saveState === "saved") {
    return "已保存";
  }
  return dirty ? "未保存" : "同步";
}

export function PlayersPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [query, setQuery] = useState("");
  const [players, setPlayers] = useState<PlayerSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [record, setRecord] = useState<JsonRecord | null>(null);
  const [originalRecord, setOriginalRecord] = useState<JsonRecord | null>(null);
  const [meta, setMeta] = useState<PlayerMeta | undefined>();
  const [listLoading, setListLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [listError, setListError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [saveError, setSaveError] = useState("");
  const detailRequestId = useRef(0);
  const saveRequestId = useRef(0);
  const selectedIdRef = useRef("");

  const selectedPlayer = useMemo(() => players.find((player) => player.user_id === selectedId) ?? null, [players, selectedId]);
  const dirty = hasUnsavedChanges(record, originalRecord);
  const saving = saveState === "saving";
  useDirtyFlag(dirty, onDirtyChange);

  const columns: ColumnsType<PlayerSummary> = [
    {
      title: "玩家",
      dataIndex: "nickname",
      render: (_value, player) => (
        <Space direction="vertical" size={0}>
          <Text strong>{playerName(player)}</Text>
          <Text type="secondary">{player.user_id}</Text>
        </Space>
      ),
    },
    { title: "境界", dataIndex: "realm" },
    { title: "战力", dataIndex: "battle_power", align: "right", render: formatNumber },
    { title: "灵石", dataIndex: "spirit_stones", align: "right", render: formatNumber },
  ];

  async function loadPlayers(nextQuery = query, options: { keepSelection?: boolean } = {}) {
    setListLoading(true);
    setListError("");
    try {
      const params = new URLSearchParams();
      if (nextQuery.trim()) {
        params.set("q", nextQuery.trim());
      }
      const queryString = params.toString();
      const payload = await api<PlayerListPayload>(`/api/players${queryString ? `?${queryString}` : ""}`);
      setPlayers(payload.players);
      if (!options.keepSelection) {
        selectedIdRef.current = "";
        setSelectedId("");
        setRecord(null);
        setOriginalRecord(null);
      }
      if (!payload.players.length) {
        selectedIdRef.current = "";
        setSelectedId("");
        setRecord(null);
        setOriginalRecord(null);
      }
    } catch (error) {
      setListError(error instanceof Error ? error.message : "玩家列表载入失败");
    } finally {
      setListLoading(false);
    }
  }

  async function loadPlayerDetail(userId: string) {
    const requestId = detailRequestId.current + 1;
    detailRequestId.current = requestId;
    selectedIdRef.current = userId;
    setSelectedId(userId);
    setDetailLoading(true);
    setDetailError("");
    setSaveError("");
    setSaveState("idle");
    try {
      const payload = await api<PlayerDetailPayload>(`/api/players/${encodeURIComponent(userId)}`);
      if (detailRequestId.current !== requestId) {
        return;
      }
      const nextRecord = sanitizeRecord(payload.record);
      setRecord(nextRecord);
      setOriginalRecord(nextRecord);
      setMeta(payload.meta);
    } catch (error) {
      if (detailRequestId.current === requestId) {
        setDetailError(error instanceof Error ? error.message : "玩家详情载入失败");
      }
    } finally {
      if (detailRequestId.current === requestId) {
        setDetailLoading(false);
      }
    }
  }

  async function selectPlayer(player: PlayerSummary) {
    if (saving) {
      return;
    }
    if (dirty && !confirmDiscard()) {
      return;
    }
    await loadPlayerDetail(player.user_id);
  }

  async function closeDrawer() {
    if (saving) {
      return;
    }
    if (dirty && !confirmDiscard()) {
      return;
    }
    selectedIdRef.current = "";
    setSelectedId("");
    setRecord(null);
    setOriginalRecord(null);
    setDetailError("");
  }

  async function reloadSelected() {
    if (saving || !selectedId) {
      return;
    }
    if (dirty && !confirmDiscard()) {
      return;
    }
    await loadPlayerDetail(selectedId);
  }

  async function savePlayer() {
    if (!selectedId || !record) {
      return;
    }
    const userId = selectedId;
    const requestId = saveRequestId.current + 1;
    saveRequestId.current = requestId;
    setSaveState("saving");
    setSaveError("");
    try {
      const payload = await api<PlayerDetailPayload>(`/api/players/${encodeURIComponent(userId)}`, {
        body: JSON.stringify(record),
        method: "PUT",
      });
      if (saveRequestId.current !== requestId || selectedIdRef.current !== userId) {
        return;
      }
      const nextRecord = sanitizeRecord(payload.record);
      setRecord(nextRecord);
      setOriginalRecord(nextRecord);
      setMeta(payload.meta);
      setSaveState("saved");
      await loadPlayers(query, { keepSelection: true });
    } catch (error) {
      if (saveRequestId.current === requestId && selectedIdRef.current === userId) {
        setSaveState("error");
        setSaveError(error instanceof Error ? error.message : "保存失败");
      }
    }
  }

  useEffect(() => {
    void loadPlayers("", { keepSelection: false });
  }, []);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (saving) {
      return;
    }
    if (dirty && !confirmDiscard()) {
      return;
    }
    void loadPlayers(query, { keepSelection: false });
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <Title level={2}>玩家档案</Title>
          <Text type="secondary">搜索玩家并编辑结构化档案字段</Text>
        </div>
        <Tag>{formatNumber(players.length)} 人</Tag>
      </div>

      <Card>
        <form onSubmit={submitSearch}>
          <Flex gap={8} wrap="wrap">
            <Input
              allowClear
              className="search-input"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="玩家 ID 或昵称"
              prefix={<SearchOutlined />}
              value={query}
            />
            <Button disabled={listLoading || saving} htmlType="submit" type="primary">
              搜索
            </Button>
          </Flex>
        </form>
      </Card>

      {listError ? <ErrorState message={listError} onRetry={() => loadPlayers(query, { keepSelection: true })} /> : null}

      <Card>
        <Table<PlayerSummary>
          columns={columns}
          dataSource={players}
          loading={listLoading}
          locale={{ emptyText: <EmptyState title="未找到玩家" detail="换一个玩家 ID 或昵称再试。" /> }}
          onRow={(player) => ({
            onClick: () => void selectPlayer(player),
          })}
          pagination={{ pageSize: 15, showSizeChanger: true }}
          rowKey="user_id"
          rowSelection={undefined}
          scroll={{ x: 720 }}
          size="middle"
        />
      </Card>

      <Drawer
        destroyOnClose
        extra={selectedPlayer ? <Tag color={statusColor(dirty, saveState)}>{statusLabel(dirty, saveState)}</Tag> : null}
        footer={
          selectedPlayer ? (
            <Flex justify="space-between" wrap="wrap">
              <Space>
                <Button disabled={saving} icon={<ReloadOutlined />} onClick={() => void reloadSelected()}>
                  重载
                </Button>
              </Space>
              <Button disabled={!dirty || saving} icon={<SaveOutlined />} loading={saving} onClick={() => void savePlayer()} type="primary">
                保存
              </Button>
            </Flex>
          ) : null
        }
        onClose={() => void closeDrawer()}
        open={Boolean(selectedPlayer)}
        title={selectedPlayer ? playerName(selectedPlayer) : "玩家档案"}
        width={980}
      >
        {selectedPlayer ? (
          <div className="page-stack">
            <Card size="small">
              <Space direction="vertical" size={2}>
                <Text type="secondary">ID {selectedPlayer.user_id}</Text>
                <Text>
                  {selectedPlayer.realm} · 战力 {formatNumber(selectedPlayer.battle_power)} · 灵石 {formatNumber(selectedPlayer.spirit_stones)}
                </Text>
              </Space>
            </Card>
            {saveError ? <ErrorState message={saveError} /> : null}
            {detailLoading ? <LoadingState label="正在载入玩家档案" /> : null}
            {detailError ? <ErrorState message={detailError} onRetry={() => loadPlayerDetail(selectedPlayer.user_id)} /> : null}
            {!detailLoading && !detailError && record ? (
              <Form layout="vertical">
                <PlayerEditor disabled={saveState === "saving"} meta={meta} onChange={setRecord} record={record} />
              </Form>
            ) : null}
          </div>
        ) : (
          <EmptyState title="选择玩家" detail="从列表选择一位玩家后编辑档案。" />
        )}
      </Drawer>
    </div>
  );
}
