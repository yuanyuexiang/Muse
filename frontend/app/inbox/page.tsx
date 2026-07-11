"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Customer, InboxMessage } from "@/lib/types";

export default function InboxPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<InboxMessage[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [customerId, setCustomerId] = useState<number | "">("");
  const [newName, setNewName] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true);
    setErr("");
    try {
      const [m, c] = await Promise.all([
        api<InboxMessage[]>("/inbox"),
        api<Customer[]>("/customers"),
      ]);
      setMessages(m);
      setCustomers(c);
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
    setLoading(false);
  }

  useEffect(() => {
    load();
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
    setMessages((ms) => ms.filter((m) => m.id !== id));
    setSelected((s) => {
      const n = new Set(s);
      n.delete(id);
      return n;
    });
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
        <button onClick={load}>刷新</button>
      </div>

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
                  {m.type === "text" ? (
                    m.content
                  ) : (
                    <span className="muted">
                      &lt;{m.type}
                      {m.object_key ? "" : m.download_status === "failed" ? " 下载失败" : " 下载中"}
                      &gt;
                    </span>
                  )}
                </td>
                <td>{m.forwarded_by}</td>
                <td>
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
