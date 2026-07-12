"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Batch, Dish, MenuRequirement, MenuSpec, ShopInfo } from "@/lib/types";

const FLAGS: [string, string][] = [
  ["hot", "辣"],
  ["vegetarian", "素"],
  ["nut", "坚"],
];

const lines = (a: string[]) => (a || []).join("\n");
const toLines = (s: string) => s.split("\n");

const emptyDish = (): Dish => ({
  number: null, name: "", description: null, price: null, flags: [], photo_object_key: null,
});

export default function BatchPage({ params }: { params: { id: string } }) {
  const batchId = params.id;
  const [batch, setBatch] = useState<Batch | null>(null);
  const [req, setReq] = useState<MenuRequirement | null>(null);
  const [form, setForm] = useState<MenuSpec | null>(null);
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
        } else if (tries++ < 12) {
          setTimeout(poll, 1500);
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

  // ── 不可变更新辅助 ──
  const updShop = (patch: Partial<ShopInfo>) =>
    setForm((f) => (f ? { ...f, shop: { ...f.shop, ...patch } } : f));
  const updCat = (ci: number, name: string) =>
    setForm((f) =>
      f ? { ...f, categories: f.categories.map((c, i) => (i === ci ? { ...c, name } : c)) } : f
    );
  const addCat = () =>
    setForm((f) => (f ? { ...f, categories: [...f.categories, { name: "新分类", dishes: [] }] } : f));
  const delCat = (ci: number) =>
    setForm((f) => (f ? { ...f, categories: f.categories.filter((_, i) => i !== ci) } : f));
  const updDish = (ci: number, di: number, patch: Partial<Dish>) =>
    setForm((f) =>
      f
        ? {
            ...f,
            categories: f.categories.map((c, i) =>
              i === ci ? { ...c, dishes: c.dishes.map((d, j) => (j === di ? { ...d, ...patch } : d)) } : c
            ),
          }
        : f
    );
  const addDish = (ci: number) =>
    setForm((f) =>
      f
        ? {
            ...f,
            categories: f.categories.map((c, i) =>
              i === ci ? { ...c, dishes: [...c.dishes, emptyDish()] } : c
            ),
          }
        : f
    );
  const delDish = (ci: number, di: number) =>
    setForm((f) =>
      f
        ? {
            ...f,
            categories: f.categories.map((c, i) =>
              i === ci ? { ...c, dishes: c.dishes.filter((_, j) => j !== di) } : c
            ),
          }
        : f
    );
  const toggleFlag = (ci: number, di: number, flag: string) =>
    setForm((f) =>
      f
        ? {
            ...f,
            categories: f.categories.map((c, i) =>
              i === ci
                ? {
                    ...c,
                    dishes: c.dishes.map((d, j) =>
                      j === di
                        ? {
                            ...d,
                            flags: d.flags.includes(flag)
                              ? d.flags.filter((x) => x !== flag)
                              : [...d.flags, flag],
                          }
                        : d
                    ),
                  }
                : c
            ),
          }
        : f
    );

  async function save(): Promise<boolean> {
    if (!req || !form) return false;
    try {
      const r = await api<MenuRequirement>(`/requirements/${req.id}`, {
        method: "PATCH",
        body: JSON.stringify({ data: form }),
      });
      setReq(r);
      setForm(r.data);
      setMsg("已保存");
      return true;
    } catch (e) {
      setErr(String(e instanceof Error ? e.message : e));
      return false;
    }
  }

  function saveThenOpen(path: string) {
    // 在点击手势内**同步**开一个空白标签，避开弹窗拦截；填地址前尽量先保存。
    const url = window.location.origin + path;
    const w = window.open("about:blank", "_blank");
    const go = () => {
      if (w) w.location.href = url;
      else window.location.href = url; // 万一被拦截，退化为当前页跳转
    };
    // 已入库无需保存；未入库先保存再预览（即便保存失败也展示已存版本，不吞掉预览）。
    if (req?.status === "approved") go();
    else save().finally(go);
  }

  async function approve() {
    if (!req) return;
    if (!(await save())) return;
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
  const dishCount = form ? form.categories.reduce((n, c) => n + c.dishes.length, 0) : 0;
  const images = batch.messages.filter((m) => m.type === "image" && m.object_key);
  const THEMES = ["classic", "crimson", "ink"];

  return (
    <div>
      <h1>批次 #{batch.id} · 菜单审校</h1>
      <p className="muted">状态：{batch.status}　客户 ID：{batch.customer_id}</p>
      {err && <p className="err">{err}</p>}

      {!req || !form ? (
        <p className="muted">AI 整理中…（自动刷新）</p>
      ) : (
        <>
          <div className="toolbar">
            <span className="muted">{form.categories.length} 个分类 · {dishCount} 道菜 · {form.set_meals.length} 套餐</span>
            <label>主题：
              <select value={form.theme} onChange={(e) => setForm((f) => (f ? { ...f, theme: e.target.value } : f))}>
                {THEMES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <span className="spacer" />
            <button onClick={() => saveThenOpen(`/api/requirements/${req.id}/menu.html?theme=${form.theme}`)}>预览网页</button>
            <button onClick={() => saveThenOpen(`/api/requirements/${req.id}/menu.pdf?theme=${form.theme}`)}>预览 PDF</button>
            <button onClick={save} disabled={approved}>保存</button>
            <button className="primary" onClick={approve} disabled={approved}>审校通过入库</button>
            <span className="ok">{approved ? "已入库" : ""} {msg}</span>
          </div>

          {form.missing_fields.length > 0 && (
            <p className="warn">缺失/待确认：{form.missing_fields.join("、")}</p>
          )}

          {/* 店铺信息 */}
          <h3>店铺信息</h3>
          <div className="shopgrid">
            <label>店名<input value={form.shop.name ?? ""} onChange={(e) => updShop({ name: e.target.value })} /></label>
            <label>标语<input value={form.shop.tagline ?? ""} onChange={(e) => updShop({ tagline: e.target.value })} /></label>
            <label>电话<input value={form.shop.phone ?? ""} onChange={(e) => updShop({ phone: e.target.value })} /></label>
            <label>网址<input value={form.shop.online_order_url ?? ""} onChange={(e) => updShop({ online_order_url: e.target.value })} /></label>
            <label className="wide">地址<input value={form.shop.address ?? ""} onChange={(e) => updShop({ address: e.target.value })} /></label>
            <label>营业时间（每行一条）<textarea value={lines(form.shop.opening_hours)} onChange={(e) => updShop({ opening_hours: toLines(e.target.value) })} /></label>
            <label>促销（每行一条）<textarea value={lines(form.shop.promotions)} onChange={(e) => updShop({ promotions: toLines(e.target.value) })} /></label>
            <label>外送条款（每行一条）<textarea value={lines(form.shop.delivery_terms)} onChange={(e) => updShop({ delivery_terms: toLines(e.target.value) })} /></label>
            <label className="wide">过敏原/声明<textarea value={form.shop.allergen_notice ?? ""} onChange={(e) => updShop({ allergen_notice: e.target.value || null })} /></label>
          </div>

          {/* 分类与菜品 */}
          <h3>分类与菜品</h3>
          {form.categories.map((cat, ci) => (
            <div className="cat-block" key={ci}>
              <div className="cat-head">
                <input className="cat-name" value={cat.name} onChange={(e) => updCat(ci, e.target.value)} />
                <span className="muted">{cat.dishes.length} 道</span>
                <button onClick={() => delCat(ci)}>删除分类</button>
              </div>
              <table className="dish-table">
                <thead>
                  <tr><th>编号</th><th>菜名</th><th>价格</th><th>标记</th><th>描述</th><th>图片</th><th></th></tr>
                </thead>
                <tbody>
                  {cat.dishes.map((d, di) => (
                    <tr key={di}>
                      <td><input className="w-num" value={d.number ?? ""} onChange={(e) => updDish(ci, di, { number: e.target.value || null })} /></td>
                      <td><input className="w-name" value={d.name} onChange={(e) => updDish(ci, di, { name: e.target.value })} /></td>
                      <td><input className="w-price" value={d.price ?? ""} onChange={(e) => updDish(ci, di, { price: e.target.value || null })} /></td>
                      <td className="flags">
                        {FLAGS.map(([f, label]) => (
                          <label key={f} className="flagchk">
                            <input type="checkbox" checked={d.flags.includes(f)} onChange={() => toggleFlag(ci, di, f)} />{label}
                          </label>
                        ))}
                      </td>
                      <td><input className="w-desc" value={d.description ?? ""} onChange={(e) => updDish(ci, di, { description: e.target.value || null })} /></td>
                      <td className="photo-cell">
                        <select
                          value={d.photo_object_key ?? ""}
                          onChange={(e) => updDish(ci, di, { photo_object_key: e.target.value || null })}
                        >
                          <option value="">无</option>
                          {images.map((im) => (
                            <option key={im.id} value={im.object_key as string}>
                              {im.object_key!.split("/").pop()}
                            </option>
                          ))}
                        </select>
                        {d.photo_object_key && (
                          <img
                            className="thumb-mini"
                            src={`/api/media/by-key?key=${encodeURIComponent(d.photo_object_key)}`}
                            alt=""
                          />
                        )}
                      </td>
                      <td><button onClick={() => delDish(ci, di)}>×</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button onClick={() => addDish(ci)}>+ 加菜</button>
            </div>
          ))}
          <button onClick={addCat}>+ 加分类</button>

          {/* 套餐 */}
          <h3>套餐</h3>
          {form.set_meals.map((sm, si) => (
            <div className="setmeal-row" key={si}>
              <input className="w-name" placeholder="套餐名" value={sm.name} onChange={(e) =>
                setForm((f) => f ? { ...f, set_meals: f.set_meals.map((s, i) => i === si ? { ...s, name: e.target.value } : s) } : f)} />
              <input className="w-price" placeholder="价格" value={sm.price ?? ""} onChange={(e) =>
                setForm((f) => f ? { ...f, set_meals: f.set_meals.map((s, i) => i === si ? { ...s, price: e.target.value || null } : s) } : f)} />
              <input className="w-desc" placeholder="包含（顿号/逗号分隔）" value={sm.items.join("、")} onChange={(e) =>
                setForm((f) => f ? { ...f, set_meals: f.set_meals.map((s, i) => i === si ? { ...s, items: e.target.value.split(/[、,，]/).map((x) => x.trim()).filter(Boolean) } : s) } : f)} />
              <button onClick={() => setForm((f) => f ? { ...f, set_meals: f.set_meals.filter((_, i) => i !== si) } : f)}>×</button>
            </div>
          ))}
          <button onClick={() => setForm((f) => f ? { ...f, set_meals: [...f.set_meals, { name: "", price: null, items: [] }] } : f)}>+ 加套餐</button>

          <h3>原始消息（{batch.messages.length}）</h3>
          <ul className="msglist">
            {batch.messages.map((m) => (
              <li key={m.id}>[{m.seq}] {m.type === "text" ? m.content : `<${m.type}>`}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
