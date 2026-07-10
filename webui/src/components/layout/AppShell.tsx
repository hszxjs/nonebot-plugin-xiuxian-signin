import {
  AppstoreOutlined,
  BarChartOutlined,
  BookOutlined,
  DatabaseOutlined,
  KeyOutlined,
  MenuOutlined,
  SettingOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Badge, Grid, Input, Layout, Menu, Space, Typography } from "antd";
import type { ReactNode } from "react";

export type PageKey = "dashboard" | "players" | "items" | "beast" | "rules" | "config";
export type DirtyPageMap = Partial<Record<PageKey, boolean>>;

const nav = [
  { key: "dashboard", label: "总览", icon: <BarChartOutlined /> },
  { key: "players", label: "玩家档案", icon: <UserOutlined /> },
  { key: "items", label: "物品图鉴", icon: <AppstoreOutlined /> },
  { key: "beast", label: "御兽卡牌", icon: <BookOutlined /> },
  { key: "rules", label: "规则中心", icon: <SettingOutlined /> },
  { key: "config", label: "系统配置", icon: <DatabaseOutlined /> },
] as const;

const { Content, Header, Sider } = Layout;
const { Text, Title } = Typography;

export function AppShell({
  page,
  onPageChange,
  token,
  onTokenChange,
  children,
  dirtyPages,
}: {
  page: PageKey;
  onPageChange: (page: PageKey) => void;
  token: string;
  onTokenChange: (token: string) => void;
  dirtyPages?: DirtyPageMap;
  children: ReactNode;
}) {
  const screens = Grid.useBreakpoint();
  const menuItems = nav.map((item) => ({
    key: item.key,
    icon: item.icon,
    label: (
      <Space size={8}>
        <span>{item.label}</span>
        {dirtyPages?.[item.key] ? <Badge color="red" /> : null}
      </Space>
    ),
  }));

  return (
    <Layout className="app-layout">
      {screens.lg ? (
        <Sider className="app-sider" theme="light" width={232}>
          <div className="app-brand">
            <Title level={5}>修仙签到后台</Title>
            <Text type="secondary">运营控制台</Text>
          </div>
          <Menu
            items={menuItems}
            mode="inline"
            onClick={({ key }) => onPageChange(key as PageKey)}
            selectedKeys={[page]}
          />
        </Sider>
      ) : null}
      <Layout>
        <Header className="app-header">
          <Space align="center" className="app-header-title" size={8}>
            {!screens.lg ? <MenuOutlined /> : null}
            <div>
              <Text strong>修仙签到后台</Text>
              <br />
              <Text type="secondary">运营控制台</Text>
            </div>
          </Space>
          <Input.Password
            allowClear
            aria-label="管理 Token"
            onChange={(event) => onTokenChange(event.target.value)}
            placeholder="管理 Token"
            prefix={<KeyOutlined />}
            value={token}
          />
        </Header>
        {!screens.lg ? (
          <Menu
            className="mobile-nav"
            items={menuItems}
            mode="horizontal"
            onClick={({ key }) => onPageChange(key as PageKey)}
            selectedKeys={[page]}
          />
        ) : null}
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
