"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, Col, Row, Statistic } from "antd";
import { CheckCircleOutlined, InboxOutlined, ProfileOutlined } from "@ant-design/icons";
import { api } from "@/lib/api";

export default function Dashboard() {
  const [s, setS] = useState({ inbox_new: 0, batches: 0, approved: 0 });

  useEffect(() => {
    api<typeof s>("/stats").then(setS).catch(() => {});
  }, []);

  return (
    <div>
      <Row gutter={16}>
        <Col span={8}>
          <Link href="/inbox">
            <Card hoverable>
              <Statistic title="待整理消息" value={s.inbox_new} prefix={<InboxOutlined />} />
            </Card>
          </Link>
        </Col>
        <Col span={8}>
          <Link href="/batches">
            <Card hoverable>
              <Statistic title="菜单批次" value={s.batches} prefix={<ProfileOutlined />} />
            </Card>
          </Link>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="已入库菜单"
              value={s.approved}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: "#1e5b3e" }}
            />
          </Card>
        </Col>
      </Row>

      <Card style={{ marginTop: 16 }} title="快速开始">
        <ol style={{ lineHeight: 2, margin: 0, paddingLeft: 18 }}>
          <li>
            客服在企业微信把餐厅菜单（图片 / 文字 / Excel）逐条转发给机器人 → 进{" "}
            <Link href="/inbox">待整理收件箱</Link>
          </li>
          <li>收件箱里选客户 + 勾选消息 → 提交，AI 提取成结构化菜单</li>
          <li>
            <Link href="/batches">菜单批次</Link> → 打开审校：改内容、选模板、右侧实时预览 → 导出 PDF / 入库
          </li>
        </ol>
      </Card>
    </div>
  );
}
