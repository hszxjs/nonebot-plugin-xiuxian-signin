import { RefreshCcw, Save, Search, UserRound } from "lucide-react";
import type { FormEvent } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "../components/state/LoadState";
import { Badge } from "../components/ui/badge";
import { Button, PrimaryButton } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { api } from "../lib/api";
import { formatNumber } from "../lib/format";
import type { PlayerDetailPayload, PlayerListPayload, PlayerMeta, PlayerSummary } from "../lib/types";
import type { DirtyChangeHandler } from "./pageShared";
import { useDirtyFlag } from "./pageShared";
import { PlayerEditor } from "./playerEditor";
import { sanitizeRecord, type JsonRecord } from "./playerMeta";

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

function PlayerList({
  disabled,
  players,
  selectedId,
  onSelect,
}: {
  disabled?: boolean;
  onSelect: (player: PlayerSummary) => void;
  players: PlayerSummary[];
  selectedId: string;
}) {
  return (
    <div className="min-w-0 overflow-x-auto rounded-md border border-border">
      <Table className="min-w-[560px]">
        <TableHeader>
          <TableRow>
            <TableHead>玩家</TableHead>
            <TableHead>境界</TableHead>
            <TableHead className="text-right">战力</TableHead>
            <TableHead className="text-right">灵石</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {players.map((player) => {
            const selected = player.user_id === selectedId;
            return (
              <TableRow
                aria-disabled={disabled}
                className={selected ? "bg-muted hover:bg-muted" : disabled ? "opacity-60" : "cursor-pointer"}
                key={player.user_id}
                onClick={() => {
                  if (!disabled) {
                    onSelect(player);
                  }
                }}
              >
                <TableCell className="max-w-48">
                  <div className="truncate font-medium">{playerName(player)}</div>
                  <div className="truncate text-xs text-muted-foreground">{player.user_id}</div>
                </TableCell>
                <TableCell className="max-w-40 truncate">{player.realm}</TableCell>
                <TableCell className="text-right font-medium">{formatNumber(player.battle_power)}</TableCell>
                <TableCell className="text-right">{formatNumber(player.spirit_stones)}</TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

function EditorHeader({
  dirty,
  onReload,
  onSave,
  player,
  saveError,
  saveState,
}: {
  dirty: boolean;
  onReload: () => void;
  onSave: () => void;
  player: PlayerSummary;
  saveError: string;
  saveState: SaveState;
}) {
  const status = saveState === "saving" ? "保存中" : saveState === "saved" ? "已保存" : dirty ? "未保存" : "同步";

  return (
    <div className="flex min-w-0 flex-wrap items-center justify-between gap-3">
      <div className="min-w-0">
        <div className="flex min-w-0 items-center gap-2">
          <h2 className="truncate text-lg font-semibold">{playerName(player)}</h2>
          <Badge className="shrink-0">{status}</Badge>
        </div>
        <div className="mt-1 flex min-w-0 flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span className="truncate">ID {player.user_id}</span>
          <span className="truncate">{player.realm}</span>
          <span className="truncate">战力 {formatNumber(player.battle_power)}</span>
        </div>
        {saveError ? <div className="mt-2 text-sm text-destructive">{saveError}</div> : null}
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <Button disabled={saveState === "saving"} onClick={onReload}>
          <RefreshCcw className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>重载</span>
        </Button>
        <PrimaryButton disabled={!dirty || saveState === "saving"} onClick={onSave}>
          <Save className="h-4 w-4 shrink-0" aria-hidden="true" />
          <span>保存</span>
        </PrimaryButton>
      </div>
    </div>
  );
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

  const selectedPlayer = useMemo(
    () => players.find((player) => player.user_id === selectedId) ?? null,
    [players, selectedId],
  );
  const dirty = hasUnsavedChanges(record, originalRecord);
  const saving = saveState === "saving";
  useDirtyFlag(dirty, onDirtyChange);

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
      if (!options.keepSelection && payload.players.length) {
        void selectPlayer(payload.players[0], { skipDirtyCheck: true });
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

  async function selectPlayer(player: PlayerSummary, options: { skipDirtyCheck?: boolean } = {}) {
    if (saving) {
      return;
    }
    if (!options.skipDirtyCheck && dirty && !confirmDiscard()) {
      return;
    }
    await loadPlayerDetail(player.user_id);
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
    <div className="grid min-w-0 gap-4">
      <div className="flex min-w-0 flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-2xl font-semibold tracking-normal">玩家档案</h1>
          <p className="mt-1 truncate text-sm text-muted-foreground">搜索玩家并编辑结构化档案字段</p>
        </div>
        <Badge className="shrink-0">{formatNumber(players.length)} 人</Badge>
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[420px_minmax(0,1fr)]">
        <Card className="grid min-w-0 content-start gap-4 rounded-md p-4">
          <form className="grid min-w-0 gap-2 sm:grid-cols-[minmax(0,1fr)_auto]" onSubmit={submitSearch}>
            <div className="relative min-w-0">
              <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <Input
                className="pl-9"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="玩家 ID 或昵称"
                value={query}
              />
            </div>
            <Button disabled={listLoading || saving} type="submit">
              搜索
            </Button>
          </form>

          {listLoading ? <LoadingState label="正在载入玩家" /> : null}
          {listError ? <ErrorState message={listError} onRetry={() => loadPlayers(query, { keepSelection: true })} /> : null}
          {!listLoading && !listError && players.length ? (
            <PlayerList disabled={saving} onSelect={(player) => void selectPlayer(player)} players={players} selectedId={selectedId} />
          ) : null}
          {!listLoading && !listError && !players.length ? (
            <EmptyState title="未找到玩家" detail="换一个玩家 ID 或昵称再试。" />
          ) : null}
        </Card>

        <Card className="min-w-0 rounded-md p-4">
          {!selectedPlayer && !detailLoading ? (
            <div className="grid min-h-72 place-items-center rounded-md border border-dashed border-border p-6 text-center">
              <div className="min-w-0">
                <UserRound className="mx-auto h-8 w-8 text-muted-foreground" aria-hidden="true" />
                <div className="mt-3 font-medium">选择玩家</div>
                <div className="mt-1 text-sm text-muted-foreground">从左侧列表选择一位玩家后编辑档案。</div>
              </div>
            </div>
          ) : null}

          {selectedPlayer ? (
            <div className="grid min-w-0 gap-4">
              <EditorHeader
                dirty={dirty}
                onReload={() => void reloadSelected()}
                onSave={() => void savePlayer()}
                player={selectedPlayer}
                saveError={saveError}
                saveState={saveState}
              />
              {detailLoading ? <LoadingState label="正在载入玩家档案" /> : null}
              {detailError ? <ErrorState message={detailError} onRetry={() => loadPlayerDetail(selectedPlayer.user_id)} /> : null}
              {!detailLoading && !detailError && record ? (
                <PlayerEditor disabled={saveState === "saving"} meta={meta} onChange={setRecord} record={record} />
              ) : null}
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
