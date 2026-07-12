"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ConfigProvider, Layout, Menu } from "antd";
import zhCN from "antd/locale/zh_CN";
import { BgColorsOutlined, DashboardOutlined, InboxOutlined, ProfileOutlined } from "@ant-design/icons";

const { Sider, Header, Content } = Layout;

const NAV = [
  { key: "/", icon: <DashboardOutlined />, label: <Link href="/">仪表盘</Link> },
  { key: "/inbox", icon: <InboxOutlined />, label: <Link href="/inbox">待整理收件箱</Link> },
  { key: "/batches", icon: <ProfileOutlined />, label: <Link href="/batches">菜单批次</Link> },
  { key: "/templates", icon: <BgColorsOutlined />, label: <Link href="/templates">模板管理</Link> },
];

function pageMeta(pathname: string): { selected: string; title: string } {
  if (pathname.startsWith("/batches/") && pathname !== "/batches")
    return { selected: "/batches", title: "菜单审校" };
  if (pathname.startsWith("/batches")) return { selected: "/batches", title: "菜单批次" };
  if (pathname.startsWith("/inbox")) return { selected: "/inbox", title: "待整理收件箱" };
  if (pathname.startsWith("/templates")) return { selected: "/templates", title: "模板管理" };
  return { selected: "/", title: "仪表盘" };
}

export default function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const { selected, title } = pageMeta(usePathname() || "/");

  return (
    <ConfigProvider locale={zhCN} theme={{ token: { colorPrimary: "#1e5b3e" } }}>
      <Layout style={{ minHeight: "100vh" }}>
        <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} theme="light">
          <div
            style={{
              height: 48,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontWeight: 700,
              fontSize: 18,
              letterSpacing: 1,
              color: "#1e5b3e",
            }}
          >
            {collapsed ? "M" : "MUSE"}
          </div>
          <Menu mode="inline" selectedKeys={[selected]} items={NAV} style={{ borderInlineEnd: 0 }} />
        </Sider>
        <Layout>
          <Header
            style={{
              background: "#fff",
              padding: "0 20px",
              borderBottom: "1px solid #f0f0f0",
              fontSize: 16,
              fontWeight: 600,
              lineHeight: "64px",
            }}
          >
            {title}
          </Header>
          <Content style={{ margin: 16 }}>{children}</Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}
