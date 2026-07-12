import { useMemo, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldContent, FieldDescription, FieldGroup, FieldTitle } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemTitle,
} from "@/components/ui/item"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { formatCompactNumber, formatJson, formatNumber } from "@/lib/format"
import type { JsonRecord, PlayerDetailPayload, PlayerSummary } from "@/lib/types"
import { ConfirmAction, EmptyPanel, PageHeader, SearchField } from "@/features/shared/ui"

function playerText(player: PlayerSummary) {
  return [player.user_id, player.nickname, player.realm].join("\n").toLowerCase()
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
    <div className="flex flex-col gap-4">
      <PageHeader title="玩家管理" description="玩家是动态实体列表，使用搜索和详情面板处理。" />

      <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle>玩家列表</CardTitle>
            <CardDescription>{filteredPlayers.length} / {players.length} 名玩家。</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-3">
              <SearchField value={query} onChange={onQueryChange} placeholder="搜索 QQ、昵称或境界" />
              <ScrollArea className="h-[560px]">
                {filteredPlayers.length ? (
                  <ItemGroup>
                    {filteredPlayers.map((player) => (
                      <Item key={player.user_id} asChild variant={selectedPlayer?.record.user_id === player.user_id ? "outline" : "default"}>
                        <button type="button" onClick={() => onSelectPlayer(player.user_id)}>
                          <ItemContent>
                            <ItemTitle>
                              {player.nickname || player.user_id}
                              <Badge variant="outline">{player.realm}</Badge>
                            </ItemTitle>
                            <ItemDescription>{player.user_id}</ItemDescription>
                          </ItemContent>
                          <ItemActions>
                            <Badge variant="secondary">{formatCompactNumber(player.battle_power)}</Badge>
                          </ItemActions>
                        </button>
                      </Item>
                    ))}
                  </ItemGroup>
                ) : (
                  <EmptyPanel title="没有匹配玩家" description="调整搜索词后再查看。" />
                )}
              </ScrollArea>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>玩家详情</CardTitle>
            <CardDescription>常见标量字段独立展示，完整存档通过高级 JSON 覆盖。</CardDescription>
          </CardHeader>
          <CardContent>
            {selectedPlayer ? (
              <PlayerRecordEditor
                key={String(selectedPlayer.record.user_id ?? "")}
                selectedPlayer={selectedPlayer}
                onSavePlayer={onSavePlayer}
              />
            ) : (
              <EmptyPanel title="未选择玩家" description="从左侧列表选择一个玩家查看详情。" />
            )}
          </CardContent>
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
  const [jsonText, setJsonText] = useState(formatJson(selectedPlayer.record))

  function saveRecord() {
    try {
      const parsed = JSON.parse(jsonText)
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        onSavePlayer(parsed as JsonRecord)
      }
    } catch {
      return
    }
  }

  return (
    <FieldGroup>
      <div className="grid gap-3 md:grid-cols-3">
        <Field>
          <FieldContent>
            <FieldTitle>用户 ID</FieldTitle>
            <FieldDescription>玩家唯一键。</FieldDescription>
          </FieldContent>
          <Input value={String(selectedPlayer.record.user_id ?? "")} readOnly />
        </Field>
        <Field>
          <FieldContent>
            <FieldTitle>境界索引</FieldTitle>
            <FieldDescription>精确数值使用输入框。</FieldDescription>
          </FieldContent>
          <Input value={String(selectedPlayer.record.realm_index ?? "")} readOnly />
        </Field>
        <Field>
          <FieldContent>
            <FieldTitle>灵石</FieldTitle>
            <FieldDescription>{formatNumber(selectedPlayer.record.spirit_stones ?? 0)}</FieldDescription>
          </FieldContent>
          <Input value={String(selectedPlayer.record.spirit_stones ?? "")} readOnly />
        </Field>
      </div>
      <Field>
        <FieldContent>
          <FieldTitle>高级存档 JSON</FieldTitle>
          <FieldDescription>保存会覆盖该玩家存档，请先确认结构无误。</FieldDescription>
        </FieldContent>
        <Textarea value={jsonText} onChange={(event) => setJsonText(event.target.value)} rows={22} />
      </Field>
      <ConfirmAction
        triggerLabel="保存玩家存档"
        title="覆盖该玩家存档？"
        description="该操作会写入用户存档文件，错误 JSON 可能影响玩家数据。"
        actionLabel="保存存档"
        onConfirm={saveRecord}
      />
    </FieldGroup>
  )
}
