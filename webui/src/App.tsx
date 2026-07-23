import {
  AppstoreOutlined,
  BarChartOutlined,
  ControlOutlined,
  DatabaseOutlined,
  GoldOutlined,
  SettingOutlined,
  TeamOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons"
import {
  App as AntdApp,
  ConfigProvider,
  Layout,
  Menu,
  Result,
  theme,
} from "antd"
import { useState } from "react"
import { Route, Routes, useLocation, useNavigate } from "react-router-dom"

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
  saveMysticConfig,
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
  { key: "/", label: "运维控制台", icon: <BarChartOutlined /> },
  { key: "/players", label: "玩家", icon: <TeamOutlined /> },
  { key: "/items", label: "物品", icon: <AppstoreOutlined /> },
  { key: "/equipment", label: "装备", icon: <GoldOutlined /> },
  { key: "/mystic", label: "秘境", icon: <ThunderboltOutlined /> },
  { key: "/beast", label: "兽域", icon: <DatabaseOutlined /> },
  { key: "/config", label: "配置", icon: <ControlOutlined /> },
]

function selectedMenuKey(pathname: string) {
  const match = navItems.find(
    (item) => item.key !== "/" && pathname.startsWith(item.key),
  )
  return match?.key ?? "/"
}

function DashboardPage() {
  const { message } = AntdApp.useApp()
  const { data, error, isLoading, mutate } = useDashboard()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取运维快照" error={error} />
  }
  if (!data) {
    return (
      <EmptyPanel
        title="暂无运维数据"
        description="等待后台生成 dashboard payload。"
      />
    )
  }
  return (
    <DashboardWorkspace
      dashboard={data}
      onBackup={() => {
        createBackup()
          .then((result) => {
            message.success(`备份已创建：${result.path}`)
            return mutate()
          })
          .catch((backupError: unknown) => message.error(String(backupError)))
      }}
    />
  )
}

function PlayersPage() {
  const { message } = AntdApp.useApp()
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
            message.success("玩家存档已保存")
            return detail.mutate()
          })
          .catch((saveError: unknown) => message.error(String(saveError)))
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
  return data ? (
    <ItemsWorkspace payload={data} />
  ) : (
    <EmptyPanel title="暂无物品数据" description="后台未返回物品图鉴。" />
  )
}

function EquipmentPage() {
  const { data, error, isLoading } = useEquipmentRules()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取装备规则" error={error} />
  }
  return data ? (
    <EquipmentWorkspace payload={data} />
  ) : (
    <EmptyPanel title="暂无装备规则" description="后台未返回装备规则。" />
  )
}

function MysticPage() {
  const { message } = AntdApp.useApp()
  const { data, error, isLoading } = useMystic()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取秘境规则" error={error} />
  }
  return data ? (
    <MysticWorkspace
      payload={data}
      onSave={(config) => {
        saveMysticConfig(config)
          .then(() => message.success("秘境配置已保存"))
          .catch((saveError: unknown) => message.error(String(saveError)))
      }}
    />
  ) : (
    <EmptyPanel title="暂无秘境规则" description="后台未返回秘境规则。" />
  )
}

function BeastPage() {
  const { data, error, isLoading } = useBeastCards()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取兽域卡池" error={error} />
  }
  return data ? (
    <BeastRealmWorkspace payload={data} />
  ) : (
    <EmptyPanel title="暂无兽域卡池" description="后台未返回卡牌数据。" />
  )
}

function ConfigPage() {
  const { message } = AntdApp.useApp()
  const { data, error, isLoading, mutate } = useConfig()
  if (isLoading) {
    return <LoadingPanel />
  }
  if (error) {
    return <ErrorPanel title="无法读取配置" error={error} />
  }
  if (!data) {
    return (
      <EmptyPanel
        title="暂无配置"
        description="后台未返回 admin_config.json。"
      />
    )
  }
  return (
    <ConfigWorkspace
      key={JSON.stringify(data.config)}
      config={data.config}
      onSave={(config) => {
        saveConfig(config)
          .then(() => {
            message.success("全局配置已保存")
            return mutate()
          })
          .catch((saveError: unknown) => message.error(String(saveError)))
      }}
    />
  )
}

function NotFoundPage() {
  return (
    <Result
      status="404"
      title="页面不存在"
      subTitle="请从左侧导航选择一个后台模块。"
    />
  )
}

function AdminShell() {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <Layout className="admin-layout">
      <Layout.Sider width={240} breakpoint="lg" collapsedWidth={0}>
        <div className="admin-logo">
          <SettingOutlined />
          <span>修仙签到后台</span>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedMenuKey(location.pathname)]}
          items={navItems}
          onClick={(event) => navigate(event.key)}
        />
      </Layout.Sider>
      <Layout>
        <Layout.Content className="admin-content">
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
        </Layout.Content>
      </Layout>
    </Layout>
  )
}

export function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          borderRadius: 6,
          colorPrimary: "#1f6f68",
        },
      }}
    >
      <AntdApp>
        <AdminShell />
      </AntdApp>
    </ConfigProvider>
  )
}

export default App
