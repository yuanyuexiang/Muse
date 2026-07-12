"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Table, Tag } from "antd";
import type { ColumnsType } from "antd/es/table";
import { api } from "@/lib/api";

interface BatchRow {
  id: number;
  status: string;
  customer_name: string | null;
  shop_name: string | null;
  req_status: string | null;
  dish_count: number;
}

export default function BatchesPage() {
  const router = useRouter();
  const [rows, setRows] = useState<BatchRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<BatchRow[]>("/batches")
      .then(setRows)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const columns: ColumnsType<BatchRow> = [
    { title: "#", dataIndex: "id", width: 60 },
    { title: "客户", dataIndex: "customer_name", render: (v) => v ?? "—" },
    { title: "店名", dataIndex: "shop_name", render: (v) => v ?? "—" },
    { title: "菜品数", dataIndex: "dish_count", width: 90 },
    {
      title: "状态",
      width: 110,
      render: (_, b) =>
        b.req_status === "approved" ? <Tag color="green">已入库</Tag> : <Tag>{b.req_status || b.status}</Tag>,
    },
    {
      title: "操作",
      width: 120,
      render: (_, b) => (
        <Button type="link" onClick={() => router.push(`/batches/${b.id}`)}>
          打开审校 →
        </Button>
      ),
    },
  ];

  return (
    <div>
      <p style={{ color: "#888", marginTop: 0 }}>
        每个批次 = 一次"选客户 + 提交"生成的菜单草稿。打开审校可改内容、选模板、右侧实时预览、导出 PDF、入库。
      </p>
      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={rows}
        locale={{ emptyText: "还没有批次。去待整理收件箱选客户 + 勾选消息 → 提交即可生成。" }}
      />
    </div>
  );
}
