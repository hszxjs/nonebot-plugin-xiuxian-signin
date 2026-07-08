import {
  Activity,
  Boxes,
  ChartNoAxesCombined,
  Database,
  Menu,
  ScrollText,
  Settings,
  Shield,
  Users,
} from "lucide-react";
import type { ReactNode } from "react";
import { Input } from "../ui/input";

export type PageKey = "dashboard" | "players" | "items" | "beast" | "equipment" | "mystic" | "config";

const nav = [
  { key: "dashboard", label: "总览", icon: ChartNoAxesCombined },
  { key: "players", label: "玩家档案", icon: Users },
  { key: "items", label: "物品图鉴", icon: Boxes },
  { key: "beast", label: "御兽卡牌", icon: Shield },
  { key: "equipment", label: "灵器规则", icon: Activity },
  { key: "mystic", label: "秘境掉落", icon: ScrollText },
  { key: "config", label: "原始配置", icon: Database },
] as const;

function NavButton({
  item,
  selected,
  onClick,
  compact = false,
}: {
  item: (typeof nav)[number];
  selected: boolean;
  onClick: () => void;
  compact?: boolean;
}) {
  const Icon = item.icon;
  return (
    <button
      className={[
        "flex h-9 max-w-full items-center gap-2 overflow-hidden rounded-md px-3 text-left text-sm transition",
        compact ? "shrink-0 border border-border" : "w-full",
        selected ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
      ].join(" ")}
      onClick={onClick}
      type="button"
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="truncate">{item.label}</span>
    </button>
  );
}

export function AppShell({
  page,
  onPageChange,
  token,
  onTokenChange,
  children,
}: {
  page: PageKey;
  onPageChange: (page: PageKey) => void;
  token: string;
  onTokenChange: (token: string) => void;
  children: ReactNode;
}) {
  return (
    <div className="grid min-h-screen grid-cols-[240px_minmax(0,1fr)] bg-background text-foreground max-lg:grid-cols-1">
      <aside className="border-r border-border bg-card max-lg:hidden">
        <div className="border-b border-border p-4">
          <div className="truncate text-base font-semibold">修仙签到后台</div>
          <div className="mt-1 truncate text-xs text-muted-foreground">运营指挥台</div>
        </div>
        <nav className="grid gap-1 p-3" aria-label="后台导航">
          {nav.map((item) => (
            <NavButton item={item} key={item.key} onClick={() => onPageChange(item.key)} selected={page === item.key} />
          ))}
        </nav>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-10 border-b border-border bg-background/95 backdrop-blur">
          <div className="flex min-h-16 items-center justify-between gap-3 px-4 py-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-sm font-medium">
                <Menu className="h-4 w-4 lg:hidden" aria-hidden="true" />
                <span className="truncate">修仙签到后台</span>
              </div>
              <div className="truncate text-xs text-muted-foreground">运营控制台</div>
            </div>
            <div className="flex min-w-0 max-w-full items-center gap-2">
              <Input
                aria-label="管理 Token"
                className="w-40 sm:w-56"
                onChange={(event) => onTokenChange(event.target.value)}
                placeholder="管理 Token"
                type="password"
                value={token}
              />
              <div className="inline-flex h-9 shrink-0 items-center gap-2 rounded-md border border-border bg-card px-3 text-sm text-muted-foreground shadow-sm">
                <Settings className="h-4 w-4" aria-hidden="true" />
                <span className="hidden sm:inline">Token</span>
              </div>
            </div>
          </div>
          <nav className="flex gap-2 overflow-x-auto border-t border-border bg-card p-2 lg:hidden" aria-label="移动导航">
            {nav.map((item) => (
              <NavButton
                compact
                item={item}
                key={item.key}
                onClick={() => onPageChange(item.key)}
                selected={page === item.key}
              />
            ))}
          </nav>
        </header>
        <main className="mx-auto max-w-[1680px] p-4">{children}</main>
      </div>
    </div>
  );
}
