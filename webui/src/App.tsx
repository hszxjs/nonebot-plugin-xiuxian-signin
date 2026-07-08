import { useState } from "react";
import { AppShell, type PageKey } from "./components/layout/AppShell";
import { EmptyState } from "./components/state/LoadState";
import { Badge } from "./components/ui/badge";
import { Card } from "./components/ui/card";
import { initializeTokenFromUrl, setToken } from "./lib/api";

const pageTitles: Record<PageKey, string> = {
  dashboard: "总览",
  players: "玩家档案",
  items: "物品图鉴",
  beast: "御兽卡牌",
  equipment: "灵器规则",
  mystic: "秘境掉落",
  config: "原始配置",
};

function CurrentPage({ page }: { page: PageKey }) {
  return (
    <Card className="grid gap-4 p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">{pageTitles[page]}</h1>
          <p className="mt-1 text-sm text-muted-foreground">待配置</p>
        </div>
        <Badge>暂无数据</Badge>
      </div>
      <EmptyState title="暂无数据" detail="当前模块暂无数据。" />
    </Card>
  );
}

export default function App() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const [token, setTokenState] = useState(initializeTokenFromUrl);

  function updateToken(value: string) {
    setTokenState(value);
    setToken(value);
  }

  return (
    <AppShell page={page} onPageChange={setPage} onTokenChange={updateToken} token={token}>
      <CurrentPage page={page} />
    </AppShell>
  );
}
