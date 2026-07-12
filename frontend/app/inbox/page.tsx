"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Image, Input, Modal, Select, Space, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { api } from "@/lib/api";
import type { Customer, InboxMessage, InboxPage } from "@/lib/types";

const PAGE = 20;

export default function InboxPage() {
  const router = useRouter();
  const [rows, setRows] = useState<InboxMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [newName, setNewName] = useState("");
  const [editing, setEditing] = useState<InboxMessage | null>(null);
  const [draft, setDraft] = useState("");

  async function load(p = page) {
    setLoading(true);
    try {
      const d = await api<InboxPage>(`/inbox?limit=${PAGE}&offset=${(p - 1) * PAGE}`);
      setRows(d.items);
      setTotal(d.total);
      setPage(p);
    } catch (e) {
      message.error(String(e instanceof Error ? e.message : e));
    }
    setLoading(false);
  }
  async function loadCustomers() {
    try {
      setCustomers(await api<Customer[]>("/customers"));
    } catch {
      /* ignore */
    }
  }
  useEffect(() => {
    load(1);
    loadCustomers();
  }, []);

  async function createCustomer() {
    if (!newName.trim()) return;
    const c = await api<Customer>("/customers", {
      method: "POST",
      body: JSON.stringify({ name: newName.trim() }),
    });
    setCustomers((cs) => [c, ...cs]);
    setCustomerId(c.id);
    setNewName("");
    message.success("已新建客户并选中");
  }
  async function discard(id: number) {
    await api(`/inbox/${id}`, { method: "PATCH", body: JSON.stringify({ status: "discarded" }) });
    setSelected((s) => s.filter((x) => x !== id));
    load(page);
  }
  async function submit() {
    if (!customerId || selected.length === 0) return;
    const r = await api<{ batch_id: number }>("/inbox/submit", {
      method: "POST",
      body: JSON.stringify({ customer_id: customerId, message_ids: selected }),
    });
    router.push(`/batches/${r.batch_id}`);
  }
  async function saveEdit() {
    if (!editing) return;
    const u = await api<InboxMessage>(`/inbox/${editing.id}`, {
      method: "PATCH",
      body: JSON.stringify({ content: draft }),
    });
    setRows((rs) => rs.map((m) => (m.id === u.id ? u : m)));
    setEditing(null);
    message.success("已保存");
  }

  function content(m: InboxMessage) {
    if (m.type === "text" || (m.type === "voice" && m.content))
      return (
        <span>
          {m.content}
          {m.edited && (
            <Tag color="orange" style={{ marginLeft: 6 }} title={m.original_content ?? "原为空"}>
              已编辑
            </Tag>
          )}
        </span>
      );
    if (!m.object_key)
      return (
        <span style={{ color: "#999" }}>
          &lt;{m.type} {m.download_status === "failed" ? "下载失败" : "下载中"}&gt;
        </span>
      );
    if (m.type === "image")
      return <Image src={`/api/media/${m.id}`} width={64} height={48} style={{ objectFit: "cover", borderRadius: 4 }} />;
    return (
      <a href={`/api/media/${m.id}`} target="_blank" rel="noreferrer">
        📎 {m.object_key.split("/").pop()}
      </a>
    );
  }

  const columns: ColumnsType<InboxMessage> = [
    { title: "类型", dataIndex: "type", width: 72, render: (t: string) => <Tag>{t}</Tag> },
    { title: "内容", render: (_, m) => content(m) },
    { title: "转发人", dataIndex: "forwarded_by", width: 130 },
    {
      title: "操作",
      width: 120,
      render: (_, m) => (
        <Space>
          <a
            onClick={() => {
              setEditing(m);
              setDraft(m.content || "");
            }}
          >
            编辑
          </a>
          <a onClick={() => discard(m.id)} style={{ color: "#c0392b" }}>
            丢弃
          </a>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 10 }} wrap>
        <span>客户：</span>
        <Select
          showSearch
          placeholder="选择客户"
          style={{ width: 180 }}
          value={customerId}
          onChange={setCustomerId}
          optionFilterProp="label"
          options={customers.map((c) => ({ value: c.id, label: c.name }))}
        />
        <Input
          placeholder="新建客户名"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          style={{ width: 140 }}
          onPressEnter={createCustomer}
        />
        <Button onClick={createCustomer}>新建</Button>
        <Button type="primary" disabled={!customerId || selected.length === 0} onClick={submit}>
          提交选中 {selected.length} 条 → AI 整理
        </Button>
        <Button onClick={() => load(page)}>刷新</Button>
      </Space>
      <div style={{ color: "#888", marginBottom: 10, fontSize: 13 }}>
        ① 选 / 建客户　② 勾选要整理的消息　③ 提交 → 自动进入菜单审校
      </div>
      <Table
        rowKey="id"
        size="middle"
        loading={loading}
        columns={columns}
        dataSource={rows}
        rowSelection={{ selectedRowKeys: selected, onChange: (k) => setSelected(k as number[]) }}
        pagination={{ current: page, pageSize: PAGE, total, onChange: (p) => load(p), showSizeChanger: false }}
      />
      <Modal open={!!editing} title="编辑内容" onCancel={() => setEditing(null)} onOk={saveEdit} okText="保存">
        {editing && editing.type !== "text" && <div style={{ marginBottom: 8 }}>{content(editing)}</div>}
        <Input.TextArea
          rows={4}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={editing?.type === "text" ? "修正文本…" : "为该图片 / 文件加文字说明…"}
        />
      </Modal>
    </div>
  );
}
