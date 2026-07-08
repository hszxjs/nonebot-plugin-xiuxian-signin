import { useCallback, useState } from "react";
import { AppShell, type DirtyPageMap, type PageKey } from "./components/layout/AppShell";
import { EmptyState } from "./components/state/LoadState";
import { Badge } from "./components/ui/badge";
import { Card } from "./components/ui/card";
import { initializeTokenFromUrl, setToken } from "./lib/api";
import { ConfigPage } from "./pages/ConfigPage";
import { DashboardPage } from "./pages/DashboardPage";
import { BeastCardsPage } from "./pages/BeastCardsPage";
import { EquipmentPage } from "./pages/EquipmentPage";
import { ItemsPage } from "./pages/ItemsPage";
import { MysticPage } from "./pages/MysticPage";
import { PlayersPage } from "./pages/PlayersPage";
import { confirmDiscard, type DirtyChangeHandler } from "./pages/pageShared";

const pageTitles: Record<PageKey, string> = {
  dashboard: "总览",
  players: "玩家档案",
  items: "物品图鉴",
  beast: "御兽卡牌",
  equipment: "灵器规则",
  mystic: "秘境掉落",
  config: "高级配置",
};

function CurrentPage({ onDirtyChange, page }: { onDirtyChange: DirtyChangeHandler; page: PageKey }) {
  if (page === "dashboard") {
    return <DashboardPage />;
  }
  if (page === "players") {
    return <PlayersPage onDirtyChange={onDirtyChange} />;
  }
  if (page === "items") {
    return <ItemsPage onDirtyChange={onDirtyChange} />;
  }
  if (page === "beast") {
    return <BeastCardsPage onDirtyChange={onDirtyChange} />;
  }
  if (page === "equipment") {
    return <EquipmentPage onDirtyChange={onDirtyChange} />;
  }
  if (page === "mystic") {
    return <MysticPage onDirtyChange={onDirtyChange} />;
  }

  if (page === "config") {
    return <ConfigPage onDirtyChange={onDirtyChange} />;
  }

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
  const [dirtyPages, setDirtyPages] = useState<DirtyPageMap>({});
  const [token, setTokenState] = useState(initializeTokenFromUrl);

  function updateToken(value: string) {
    setTokenState(value);
    setToken(value);
  }

  const updatePageDirty = useCallback((pageKey: PageKey, dirty: boolean) => {
    setDirtyPages((current) => ({ ...current, [pageKey]: dirty }));
  }, []);

  function changePage(nextPage: PageKey) {
    if (nextPage === page) {
      return;
    }
    if (dirtyPages[page] && !confirmDiscard()) {
      return;
    }
    setPage(nextPage);
  }

  return (
    <AppShell dirtyPages={dirtyPages} page={page} onPageChange={changePage} onTokenChange={updateToken} token={token}>
      <CurrentPage onDirtyChange={(dirty) => updatePageDirty(page, dirty)} page={page} />
    </AppShell>
  );
}
