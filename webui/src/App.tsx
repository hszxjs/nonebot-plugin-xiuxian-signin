import { useCallback, useState } from "react";
import { App as AntApp, ConfigProvider, Empty } from "antd";
import zhCN from "antd/locale/zh_CN";
import { AppShell, type DirtyPageMap, type PageKey } from "./components/layout/AppShell";
import { initializeTokenFromUrl, setToken } from "./lib/api";
import { ConfigPage } from "./pages/ConfigPage";
import { DashboardPage } from "./pages/DashboardPage";
import { BeastCardsPage } from "./pages/BeastCardsPage";
import { ItemsPage } from "./pages/ItemsPage";
import { PlayersPage } from "./pages/PlayersPage";
import { RulesPage } from "./pages/RulesPage";
import { confirmDiscard, type DirtyChangeHandler } from "./pages/pageShared";

const pageTitles: Record<PageKey, string> = {
  dashboard: "总览",
  players: "玩家档案",
  items: "物品图鉴",
  beast: "御兽卡牌",
  rules: "规则中心",
  config: "系统配置",
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
  if (page === "rules") {
    return <RulesPage onDirtyChange={onDirtyChange} />;
  }
  if (page === "config") {
    return <ConfigPage onDirtyChange={onDirtyChange} />;
  }

  return <Empty description={`${pageTitles[page]}暂无数据`} />;
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
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          borderRadius: 6,
          colorPrimary: "#1677ff",
          fontFamily:
            "-apple-system, BlinkMacSystemFont, \"Segoe UI\", \"Microsoft YaHei\", \"PingFang SC\", sans-serif",
        },
        components: {
          Card: { borderRadiusLG: 6 },
          Layout: { bodyBg: "#f5f7fb", headerBg: "#ffffff", siderBg: "#ffffff" },
          Menu: { itemBorderRadius: 6 },
        },
      }}
    >
      <AntApp>
        <AppShell dirtyPages={dirtyPages} page={page} onPageChange={changePage} onTokenChange={updateToken} token={token}>
          <CurrentPage onDirtyChange={(dirty) => updatePageDirty(page, dirty)} page={page} />
        </AppShell>
      </AntApp>
    </ConfigProvider>
  );
}
