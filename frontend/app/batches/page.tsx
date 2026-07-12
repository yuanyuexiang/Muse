"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface BatchRow {
  id: number;
  status: string;
  customer_name: string | null;
  shop_name: string | null;
  req_status: string | null;
  dish_count: number;
  created_at: string | null;
}

export default function BatchesPage() {
  const [rows, setRows] = useState<BatchRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<BatchRow[]>("/batches")
      .then((r) => setRows(r))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p>加载中…</p>;

  return (
    <div>
      <h1>菜单批次</h1>
      <p className="muted">
        每个批次 = 一次"选客户 + 提交"生成的菜单草稿。点「打开审校」进入编辑器改内容、选主题、预览、出 PDF、入库。
      </p>
      {rows.length === 0 ? (
        <p className="muted">
          还没有批次。去 <Link href="/inbox">待整理收件箱</Link> 选客户 + 勾选消息 → 提交,即可生成。
        </p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>客户</th>
              <th>店名</th>
              <th>菜品数</th>
              <th>状态</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.id}>
                <td>{b.id}</td>
                <td>{b.customer_name ?? "—"}</td>
                <td>{b.shop_name ?? "—"}</td>
                <td>{b.dish_count}</td>
                <td>{b.req_status === "approved" ? "✅ 已入库" : b.req_status || b.status}</td>
                <td>
                  <Link href={`/batches/${b.id}`}>打开审校 →</Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
