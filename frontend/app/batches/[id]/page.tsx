"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Batch, MenuRequirement, MenuRequirementData } from "@/lib/types";

const listToStr = (a: string[]) => (a || []).join("、");
const strToList = (s: string) =>
  s
    .split(/[、,，\n]/)
    .map((x) => x.trim())
    .filter(Boolean);

export default function BatchPage({ params }: { params: { id: string } }) {
  const batchId = params.id;
  const [batch, setBatch] = useState<Batch | null>(null);
  const [req, setReq] = useState<MenuRequirement | null>(null);
  const [form, setForm] = useState<MenuRequirementData | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    let stop = false;
    let tries = 0;

    async function poll() {
      try {
        const b = await api<Batch>(`/batches/${batchId}`);
        if (stop) return;
        setBatch(b);
        const r = b.requirements[0] || null;
        if (r) {
          setReq(r);
          setForm((prev) => prev ?? r.data);
        } else if (tries++ < 10) {
          setTimeout(poll, 1500); // 提取是后台任务，草稿可能还没生成
        }
      } catch (e) {
        if (!stop) setErr(String(e instanceof Error ? e.message : e));
      }
    }

    poll();
    return () => {
      stop = true;
    };
  }, [batchId]);

  function upd(patch: Partial<MenuRequirementData>) {
    setForm((f) => (f ? { ...f, ...patch } : f));
  }

  async function save() {
    if (!req || !form) return;
    try {
      const r = await api<MenuRequirement>(`/requirements/${req.id}`, {
        method: "PATCH",
        body: JSON.stringify({ data: form }),
      });
      setReq(r);
      setForm(r.data);
      setMsg("已保存");
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
  }

  async function approve() {
    if (!req) return;
    try {
      const r = await api<MenuRequirement>(`/requirements/${req.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ reviewed_by: "admin" }),
      });
      setReq(r);
      setMsg("已入库 ✅");
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
    }
  }

  if (!batch) return <p>加载中…</p>;
  const approved = req?.status === "approved";

  return (
    <div>
      <h1>批次 #{batch.id} 审查</h1>
      <p className="muted">
        状态：{batch.status}　客户 ID：{batch.customer_id}
      </p>
      {err && <p className="err">{err}</p>}

      <h3>原始消息（{batch.messages.length}）</h3>
      <ul className="msglist">
        {batch.messages.map((m) => (
          <li key={m.id}>
            [{m.seq}] {m.type === "text" ? m.content : `<${m.type}>`}
          </li>
        ))}
      </ul>

      <h3>菜单需求草稿</h3>
      {!req || !form ? (
        <p className="muted">AI 整理中…（自动刷新）</p>
      ) : (
        <div className="form">
          <label>
            人数
            <input
              type="number"
              value={form.head_count ?? ""}
              onChange={(e) => upd({ head_count: e.target.value ? Number(e.target.value) : null })}
            />
          </label>
          <label>
            预算（元）
            <input
              type="number"
              value={form.budget ?? ""}
              onChange={(e) => upd({ budget: e.target.value ? Number(e.target.value) : null })}
            />
          </label>
          <label>
            忌口（顿号/逗号分隔）
            <input
              value={listToStr(form.dietary_restrictions)}
              onChange={(e) => upd({ dietary_restrictions: strToList(e.target.value) })}
            />
          </label>
          <label>
            口味
            <input
              value={listToStr(form.taste_preferences)}
              onChange={(e) => upd({ taste_preferences: strToList(e.target.value) })}
            />
          </label>
          <label>
            菜品
            <input
              value={listToStr(form.dishes)}
              onChange={(e) => upd({ dishes: strToList(e.target.value) })}
            />
          </label>
          <label>
            场合
            <input
              value={form.event_type ?? ""}
              onChange={(e) => upd({ event_type: e.target.value || null })}
            />
          </label>
          <label>
            备注
            <textarea
              value={form.notes ?? ""}
              onChange={(e) => upd({ notes: e.target.value || null })}
            />
          </label>
          {form.missing_fields.length > 0 && (
            <p className="warn">缺失：{form.missing_fields.join("、")}</p>
          )}
          <div className="actions">
            <button onClick={save} disabled={approved}>
              保存修改
            </button>
            <button className="primary" onClick={approve} disabled={approved}>
              审查通过入库
            </button>
            <span className="ok">{msg}</span>
          </div>
        </div>
      )}
    </div>
  );
}
