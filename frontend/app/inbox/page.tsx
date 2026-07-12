"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Customer, InboxMessage, InboxPage } from "@/lib/types";

export default function InboxPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [customerId, setCustomerId] = useState<number | "">("");
  const [newName, setNewName] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [draft, setDraft] = useState("");
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const PAGE = 50;

  async function loadInbox(off = 0) {
    setLoading(true);
    setErr("");
    try {
      const page = await api<InboxPage>(`/inbox?limit=${PAGE}&offset=${off}`);
      setMessages(page.items);
      setTotal(page.total);
      setOffset(page.offset);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
    setLoading(false);
  }

  async function loadCustomers() {
    try {
      setCustomers(await api<Customer[]>("/customers"));
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
  }

  useEffect(() => {
    loadInbox(0);
    loadCustomers();
  }, []);

  function toggle(id: number) {
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function createCustomer() {
    if (!newName.trim()) return;
    try {
      const c = await api<Customer>("/customers", {
        method: "POST",
        body: JSON.stringify({ name: newName.trim() }),
      });
      setCustomers((cs) => [c, ...cs]);
      setCustomerId(c.id);
      setNewName("");
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
  }

  async function discard(id: number) {
    await api(`/inbox/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "discarded" }),
    });
    setSelected((s) => {
      const n = new Set(s);
      n.delete(id);
      return n;
    });
    loadInbox(offset);
  }

  async function submit() {
    if (!customerId || selected.size === 0) return;
    try {
      const r = await api<{ batch_id: number }>("/inbox/submit", {
        method: "POST",
        body: JSON.stringify({ customer_id: customerId, message_ids: [...selected] }),
      });
      router.push(`/batches/${r.batch_id}`);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
  }

  function renderMedia(m: InboxMessage) {
    if (!m.object_key) {
      return (
        <span className="muted">
          &lt;{m.type} {m.download_status === "failed" ? "下载失败" : "下载中"}&gt;
        </span>
      );
    }
    const src = `/api/media/${m.id}`;
    if (m.type === "image") {
      return (
        <a href={src} target="_blank" rel="noreferrer">
          <img src={src} alt="" className="thumb" />
        </a>
      );
    }
    return (
      <a href={src} target="_blank" rel="noreferrer">
        📎 {m.object_key.split("/").pop()}
      </a>
    );
  }

  function editedBadge(m: InboxMessage) {
    if (!m.edited) return null;
    return (
      <span className="badge" title={m.original_content ? `原文：${m.original_content}` : "原内容为空"}>
        已编辑
      </span>
    );
  }

  function renderContent(m: InboxMessage) {
    if (m.type === "text" || (m.type === "voice" && m.content)) {
      return (
        <span>
          {m.content} {editedBadge(m)}
        </span>
      );
    }
    return (
      <div>
        {renderMedia(m)}
        {m.content && (
          <div className="note">
            📝 {m.content} {editedBadge(m)}
          </div>
        )}
        {m.edited && !m.content && <div>{editedBadge(m)}</div>}
      </div>
    );
  }

  function startEdit(m: InboxMessage) {
    setEditingId(m.id);
    setDraft(m.content || "");
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft("");
  }

  async function saveEdit(id: number) {
    try {
      const updated = await api<InboxMessage>(`/inbox/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ content: draft }),
      });
      setMessages((ms) => ms.map((m) => (m.id === id ? updated : m)));
      cancelEdit();
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
  }

  if (loading) return <p>加载中…</p>;

  return (
    <div>
      <h1>待整理收件箱</h1>
      {err && <p className="err">{err}</p>}

      <div className="toolbar">
        <label>
          客户：{" "}
          <select
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">选择客户…</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
        <input
          placeholder="新建客户名"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />
        <button onClick={createCustomer}>新建</button>
        <span className="spacer" />
        <button className="primary" disabled={!customerId || selected.size === 0} onClick={submit}>
          提交选中 {selected.size} 条 → AI 整理
        </button>
        <button onClick={() => loadInbox(offset)}>刷新</button>
      </div>
      <p className="muted hint">
        ① 选或新建客户　② 勾选要整理的消息（菜单图 / 文字 / 文件）　③ 点「提交」→ 自动进入菜单审校编辑器
      </p>

      {total > 0 && (
        <div className="toolbar pager">
          <span className="muted">
            共 {total} 条，显示 {offset + 1}–{offset + messages.length}
          </span>
          <span className="spacer" />
          <button disabled={offset === 0} onClick={() => loadInbox(Math.max(0, offset - PAGE))}>
            上一页
          </button>
          <button
            disabled={offset + messages.length >= total}
            onClick={() => loadInbox(offset + PAGE)}
          >
            下一页
          </button>
        </div>
      )}

      {messages.length === 0 ? (
        <p className="muted">暂无待整理消息。客服在企业微信里逐条转发后会出现在这里。</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th></th>
              <th>#</th>
              <th>类型</th>
              <th>内容</th>
              <th>转发人</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {messages.map((m) => (
              <tr key={m.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selected.has(m.id)}
                    onChange={() => toggle(m.id)}
                  />
                </td>
                <td>{m.seq}</td>
                <td>{m.type}</td>
                <td>
                  {editingId === m.id ? (
                    <div className="editbox">
                      {m.type !== "text" && renderMedia(m)}
                      <textarea
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        rows={3}
                        placeholder={m.type === "text" ? "修正文本…" : "为该图片/文件加文字说明…"}
                      />
                      <div className="actions">
                        <button className="primary" onClick={() => saveEdit(m.id)}>
                          保存
                        </button>
                        <button onClick={cancelEdit}>取消</button>
                      </div>
                    </div>
                  ) : (
                    renderContent(m)
                  )}
                </td>
                <td>{m.forwarded_by}</td>
                <td>
                  <button onClick={() => startEdit(m)}>编辑</button>{" "}
                  <button onClick={() => discard(m.id)}>丢弃</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
