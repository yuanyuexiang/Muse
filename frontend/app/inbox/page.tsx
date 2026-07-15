"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Image, Input, Modal, Select, Space, Table, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { api } from "@/lib/api";
import type { Customer, InboxMessage, InboxPage } from "@/lib/types";

const PAGE_OPTIONS = [20, 50, 100, 200];

export default function InboxPage() {
  const router = useRouter();
  const [rows, setRows] = useState<InboxMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<number[]>([]);
  const [forwardedBy, setForwardedBy] = useState<string | undefined>();
  const [forwarders, setForwarders] = useState<string[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [customerId, setCustomerId] = useState<number | undefined>();
  const [newName, setNewName] = useState("");
  const [editing, setEditing] = useState<InboxMessage | null>(null);
  const [draft, setDraft] = useState("");

  function qs(fb = forwardedBy, extra: Record<string, string> = {}) {
    const q = new URLSearchParams({ status: "new", ...extra });
    if (fb) q.set("forwarded_by", fb);
    return q.toString();
  }

  async function load(p = page, ps = pageSize, fb = forwardedBy) {
    setLoading(true);
    try {
      const d = await api<InboxPage>(`/inbox?${qs(fb, { limit: String(ps), offset: String((p - 1) * ps) })}`);
      setRows(d.items);
      setTotal(d.total);
      setPage(p);
      setPageSize(ps);
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
  async function loadForwarders() {
    try {
      setForwarders(await api<string[]>("/inbox/forwarders"));
    } catch {
      /* ignore */
    }
  }
  useEffect(() => {
    load(1);
    loadCustomers();
    loadForwarders();
  }, []);

  // 切换转发人筛选：清空跨页选择（避免把不同客服/客户的消息误并成一批），重载第一页。
  function changeForwarder(fb: string | undefined) {
    setForwardedBy(fb);
    setSelected([]);
    load(1, pageSize, fb);
  }

  // 全选「当前筛选下的全部未整理」——向后端取全量 id，一次跨页选中。
  async function selectAllPending() {
    try {
      const ids = await api<number[]>(`/inbox/ids?${qs()}`);
      setSelected(ids);
      message.success(`已选中全部 ${ids.length} 条`);
    } catch (e) {
      message.error(String(e instanceof Error ? e.message : e));
    }
  }

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
    loadForwarders();
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

      <Space style={{ marginBottom: 10 }} wrap>
        <span>按转发人筛选：</span>
        <Select
          allowClear
          showSearch
          placeholder="全部转发人"
          style={{ width: 200 }}
          value={forwardedBy}
          onChange={changeForwarder}
          options={forwarders.map((f) => ({ value: f, label: f }))}
        />
        <Button onClick={selectAllPending}>全选全部未整理（{total} 条）</Button>
        {selected.length > 0 && (
          <span style={{ color: "#1e5b3e" }}>
            已选 <b>{selected.length}</b> 条（跨页）
            <a style={{ marginLeft: 8 }} onClick={() => setSelected([])}>
              清空
            </a>
          </span>
        )}
      </Space>

      <div style={{ color: "#888", marginBottom: 10, fontSize: 13 }}>
        ① 选 / 建客户　② 勾选要整理的消息（可按转发人筛选后「全选全部」，或调大每页条数一次全选本页）　③ 提交 → 自动进入菜单审校
      </div>
      <Table
        rowKey="id"
        size="middle"
        loading={loading}
        columns={columns}
        dataSource={rows}
        rowSelection={{
          selectedRowKeys: selected,
          onChange: (k) => setSelected(k as number[]),
          selections: [
            Table.SELECTION_ALL,
            Table.SELECTION_INVERT,
            Table.SELECTION_NONE,
            { key: "all-pending", text: `全选全部未整理（${total} 条）`, onSelect: selectAllPending },
          ],
        }}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: PAGE_OPTIONS,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => load(p, ps),
        }}
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
