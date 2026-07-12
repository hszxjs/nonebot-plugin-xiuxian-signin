import { useState } from "react"
import {
  IconAdjustments,
  IconBackpack,
  IconCards,
  IconChartBar,
  IconDatabase,
  IconMap,
  IconShieldHalf,
  IconUsers,
} from "@tabler/icons-react"
import { NavLink, Route, Routes } from "react-router-dom"
import { toast } from "sonner"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from "@/components/ui/sidebar"
import { BeastRealmWorkspace } from "@/features/beast/beast-workspace"
import { ConfigWorkspace } from "@/features/config/config-workspace"
import { DashboardWorkspace } from "@/features/dashboard/dashboard-workspace"
import { EquipmentWorkspace } from "@/features/equipment/equipment-workspace"
import { ItemsWorkspace } from "@/features/items/items-workspace"
import { MysticWorkspace } from "@/features/mystic/mystic-workspace"
import { PlayersWorkspace } from "@/features/players/players-workspace"
import { EmptyPanel, ErrorPanel, LoadingPanel } from "@/features/shared/ui"
import {
  createBackup,
  saveConfig,
  savePlayer,
  useBeastCards,
  useConfig,
  useDashboard,
  useEquipmentRules,
  useItems,
  useMystic,
  usePlayer,
  usePlayers,
} from "@/lib/api"
import type { JsonRecord } from "@/lib/types"

const navItems = [
  { to: "/", label: "运维控制台", icon: IconChartBar, end: true },
  { to: "/players", label: "玩家", icon: IconUsers },
  { to: "/items", label: "物品", icon: IconBackpack },
  { to: "/equipment", label: "装备", icon: IconShieldHalf },
  { to: "/mystic", label: "秘境", icon: IconMap },
  { to: "/beast", label: "兽域", icon: IconCards },
  { to: "/config", label: "配置", icon: IconAdjustments },
]

function AppSidebar() {
  return (
    <Sidebar>
      <SidebarHeader>修仙签到后台</SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Admin</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.to}>
                  <SidebarMenuButton asChild>
                    <NavLink to={item.to} end={item.end}>
                      <item.icon />
                      <span>{item.label}</span>
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}

function DashboardPage() {
  const { data, error, isLoading, mutate } = useDashboard()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取运维快照" error={error} />
  }
  if (!data) {
    return <EmptyPanel title="暂无运维数据" description="等待后台生成 dashboard payload。" />
  }
  return (
    <DashboardWorkspace
      dashboard={data}
      onBackup={() => {
        createBackup()
          .then((result) => {
            toast.success(`备份已创建：${result.path}`)
            return mutate()
          })
          .catch((backupError: unknown) => toast.error(String(backupError)))
      }}
    />
  )
}

function PlayersPage() {
  const [query, setQuery] = useState("")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data, error, isLoading } = usePlayers(query)
  const activeSelectedId = selectedId ?? data?.players[0]?.user_id ?? null
  const detail = usePlayer(activeSelectedId)

  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取玩家列表" error={error} />
  }
  return (
    <PlayersWorkspace
      players={data?.players ?? []}
      selectedPlayer={detail.data}
      query={query}
      onQueryChange={setQuery}
      onSelectPlayer={setSelectedId}
      onSavePlayer={(record: JsonRecord) => {
        if (!activeSelectedId) {
          return
        }
        savePlayer(activeSelectedId, record)
          .then(() => {
            toast.success("玩家存档已保存")
            return detail.mutate()
          })
          .catch((saveError: unknown) => toast.error(String(saveError)))
      }}
    />
  )
}

function ItemsPage() {
  const { data, error, isLoading } = useItems()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取物品图鉴" error={error} />
  }
  return data ? <ItemsWorkspace payload={data} /> : <EmptyPanel title="暂无物品数据" description="后台未返回物品图鉴。" />
}

function EquipmentPage() {
  const { data, error, isLoading } = useEquipmentRules()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取装备规则" error={error} />
  }
  return data ? <EquipmentWorkspace payload={data} /> : <EmptyPanel title="暂无装备规则" description="后台未返回装备规则。" />
}

function MysticPage() {
  const { data, error, isLoading } = useMystic()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取秘境规则" error={error} />
  }
  return data ? <MysticWorkspace payload={data} /> : <EmptyPanel title="暂无秘境规则" description="后台未返回秘境规则。" />
}

function BeastPage() {
  const { data, error, isLoading } = useBeastCards()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取兽域卡池" error={error} />
  }
  return data ? <BeastRealmWorkspace payload={data} /> : <EmptyPanel title="暂无兽域卡池" description="后台未返回卡牌数据。" />
}

function ConfigPage() {
  const { data, error, isLoading, mutate } = useConfig()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取配置" error={error} />
  }
  if (!data) {
    return <EmptyPanel title="暂无配置" description="后台未返回 admin_config.json。" />
  }
  return (
    <ConfigWorkspace
      key={JSON.stringify(data.config)}
      config={data.config}
      onSave={(config) => {
        saveConfig(config)
          .then(() => {
            toast.success("全局配置已保存")
            return mutate()
          })
          .catch((saveError: unknown) => toast.error(String(saveError)))
      }}
    />
  )
}

function NotFoundPage() {
  return (
    <Alert>
      <IconDatabase />
      <AlertTitle>页面不存在</AlertTitle>
      <AlertDescription>请从左侧导航选择一个后台模块。</AlertDescription>
    </Alert>
  )
}

export function App() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <main className="p-4 md:p-6">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/players" element={<PlayersPage />} />
            <Route path="/items" element={<ItemsPage />} />
            <Route path="/equipment" element={<EquipmentPage />} />
            <Route path="/mystic" element={<MysticPage />} />
            <Route path="/beast" element={<BeastPage />} />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
