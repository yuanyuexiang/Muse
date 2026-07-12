"use client";

import { useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  Checkbox,
  Col,
  Input,
  Row,
  Select,
  Space,
  Spin,
  Tag,
  message,
} from "antd";
import { api } from "@/lib/api";
import type { Batch, Dish, MenuRequirement, MenuSpec, ShopInfo } from "@/lib/types";

const FLAG_OPTS = [
  { label: "辣", value: "hot" },
  { label: "素", value: "vegetarian" },
  { label: "坚", value: "nut" },
];
const lines = (a: string[]) => (a || []).join("\n");
const toLines = (s: string) => s.split("\n");
const emptyDish = (): Dish => ({
  number: null, name: "", description: null, price: null, flags: [], photo_object_key: null,
});
const SCALE = 0.52;
const FW = 820;

export default function BatchEditor({ params }: { params: { id: string } }) {
  const batchId = params.id;
  const [batch, setBatch] = useState<Batch | null>(null);
  const [req, setReq] = useState<MenuRequirement | null>(null);
  const [form, setForm] = useState<MenuSpec | null>(null);
  const [templates, setTemplates] = useState<{ key: string; label: string; desc: string }[]>([]);
  const [ts, setTs] = useState(0);
  const firstForm = useRef(true);

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
          setTs((t) => t || Date.now());
        } else if (tries++ < 12) setTimeout(poll, 1500);
      } catch (e) {
        if (!stop) message.error(String(e instanceof Error ? e.message : e));
      }
    }
    poll();
    return () => {
      stop = true;
    };
  }, [batchId]);

  useEffect(() => {
    api<{ key: string; label: string; desc: string }[]>("/templates").then(setTemplates).catch(() => {});
  }, []);

  const approved = req?.status === "approved";

  // 去抖自动保存 → 刷新右侧预览
  useEffect(() => {
    if (!form || !req || approved) return;
    if (firstForm.current) {
      firstForm.current = false;
      return;
    }
    const t = setTimeout(() => {
      save();
    }, 800);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form]);

  async function save(): Promise<boolean> {
    if (!req || !form || approved) return false;
    try {
      const r = await api<MenuRequirement>(`/requirements/${req.id}`, {
        method: "PATCH",
        body: JSON.stringify({ data: form }),
      });
      setReq(r);
      setTs(Date.now());
      return true;
    } catch (e) {
      message.error(String(e instanceof Error ? e.message : e));
      return false;
    }
  }
  async function saveManual() {
    if (await save()) message.success("已保存");
  }
  async function approve() {
    if (!req) return;
    await save();
    try {
      const r = await api<MenuRequirement>(`/requirements/${req.id}/approve`, {
        method: "POST",
        body: JSON.stringify({ reviewed_by: "admin" }),
      });
      setReq(r);
      message.success("已入库 ✅");
    } catch (e) {
      message.error(String(e instanceof Error ? e.message : e));
    }
  }
  function openMenu(ext: "html" | "pdf") {
    if (!req || !form) return;
    const url = `${window.location.origin}/api/requirements/${req.id}/menu.${ext}?theme=${form.theme}`;
    const w = window.open("about:blank", "_blank");
    const go = () => {
      if (w) w.location.href = url;
      else window.location.href = url;
    };
    approved ? go() : save().finally(go);
  }

  // ── 不可变更新 ──
  const updShop = (p: Partial<ShopInfo>) => setForm((f) => (f ? { ...f, shop: { ...f.shop, ...p } } : f));
  const updCat = (ci: number, name: string) =>
    setForm((f) => (f ? { ...f, categories: f.categories.map((c, i) => (i === ci ? { ...c, name } : c)) } : f));
  const addCat = () =>
    setForm((f) => (f ? { ...f, categories: [...f.categories, { name: "新分类", dishes: [] }] } : f));
  const delCat = (ci: number) =>
    setForm((f) => (f ? { ...f, categories: f.categories.filter((_, i) => i !== ci) } : f));
  const mapDish = (ci: number, fn: (ds: Dish[]) => Dish[]) =>
    setForm((f) => (f ? { ...f, categories: f.categories.map((c, i) => (i === ci ? { ...c, dishes: fn(c.dishes) } : c)) } : f));
  const updDish = (ci: number, di: number, p: Partial<Dish>) =>
    mapDish(ci, (ds) => ds.map((d, j) => (j === di ? { ...d, ...p } : d)));
  const addDish = (ci: number) => mapDish(ci, (ds) => [...ds, emptyDish()]);
  const delDish = (ci: number, di: number) => mapDish(ci, (ds) => ds.filter((_, j) => j !== di));
  const mapSM = (fn: (s: MenuSpec["set_meals"]) => MenuSpec["set_meals"]) =>
    setForm((f) => (f ? { ...f, set_meals: fn(f.set_meals) } : f));

  if (!batch) return <Spin style={{ margin: 40 }} />;
  if (!req || !form) return <Spin tip="AI 整理中…" style={{ margin: 40 }} />;

  const images = batch.messages.filter((m) => m.type === "image" && m.object_key);
  const dishCount = form.categories.reduce((n, c) => n + c.dishes.length, 0);
  const previewUrl = `/api/requirements/${req.id}/menu.html?theme=${form.theme}&t=${ts}`;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 96px)" }}>
      {/* 头部工具条 */}
      <Space style={{ marginBottom: 10 }} wrap>
        <Tag>批次 #{batch.id}</Tag>
        <span style={{ color: "#888" }}>
          {form.categories.length} 分类 · {dishCount} 菜 · {form.set_meals.length} 套餐
        </span>
        {approved ? <Tag color="green">已入库</Tag> : <Tag color="blue">草稿（自动保存）</Tag>}
        <span style={{ flex: 1 }} />
        <Button onClick={() => openMenu("html")}>新窗口预览</Button>
        <Button onClick={() => openMenu("pdf")}>导出 PDF</Button>
        <Button onClick={saveManual} disabled={approved}>保存</Button>
        <Button type="primary" onClick={approve} disabled={approved}>审校通过入库</Button>
      </Space>

      <div style={{ display: "flex", gap: 12, flex: 1, minHeight: 0 }}>
        {/* 中栏：编辑 */}
        <div style={{ flex: 1, overflow: "auto", paddingRight: 4 }}>
          {/* 模板选择 */}
          {templates.length > 0 && (
            <Card size="small" title="模板" style={{ marginBottom: 10 }}>
              <div className="tmpl-grid">
                {templates.map((t) => (
                  <div
                    key={t.key}
                    className={`tmpl-card${form.theme === t.key ? " sel" : ""}`}
                    onClick={() => setForm((f) => (f ? { ...f, theme: t.key } : f))}
                    title={t.desc}
                  >
                    <img src={`/templates/${t.key}.png`} alt={t.label} />
                    <div className="tmpl-name">{t.label}</div>
                    <div className="tmpl-desc">{t.desc}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {form.missing_fields.length > 0 && (
            <div style={{ color: "#d46b08", marginBottom: 10 }}>缺失/待确认：{form.missing_fields.join("、")}</div>
          )}

          {/* 店铺信息 */}
          <Card size="small" title="店铺信息" style={{ marginBottom: 10 }}>
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Input addonBefore="店名" value={form.shop.name ?? ""} onChange={(e) => updShop({ name: e.target.value })} />
              </Col>
              <Col span={12}>
                <Input addonBefore="标语" value={form.shop.tagline ?? ""} onChange={(e) => updShop({ tagline: e.target.value })} />
              </Col>
              <Col span={12}>
                <Input addonBefore="电话" value={form.shop.phone ?? ""} onChange={(e) => updShop({ phone: e.target.value })} />
              </Col>
              <Col span={12}>
                <Input addonBefore="网址" value={form.shop.online_order_url ?? ""} onChange={(e) => updShop({ online_order_url: e.target.value })} />
              </Col>
              <Col span={24}>
                <Input addonBefore="地址" value={form.shop.address ?? ""} onChange={(e) => updShop({ address: e.target.value })} />
              </Col>
              <Col span={8}>
                <Input.TextArea rows={2} placeholder="营业时间（每行一条）" value={lines(form.shop.opening_hours)} onChange={(e) => updShop({ opening_hours: toLines(e.target.value) })} />
              </Col>
              <Col span={8}>
                <Input.TextArea rows={2} placeholder="促销（每行一条）" value={lines(form.shop.promotions)} onChange={(e) => updShop({ promotions: toLines(e.target.value) })} />
              </Col>
              <Col span={8}>
                <Input.TextArea rows={2} placeholder="外送条款（每行一条）" value={lines(form.shop.delivery_terms)} onChange={(e) => updShop({ delivery_terms: toLines(e.target.value) })} />
              </Col>
              <Col span={24}>
                <Input.TextArea rows={1} placeholder="过敏原/声明" value={form.shop.allergen_notice ?? ""} onChange={(e) => updShop({ allergen_notice: e.target.value || null })} />
              </Col>
            </Row>
          </Card>

          {/* 分类与菜品 */}
          {form.categories.map((cat, ci) => (
            <Card
              key={ci}
              size="small"
              style={{ marginBottom: 10 }}
              title={<Input value={cat.name} onChange={(e) => updCat(ci, e.target.value)} style={{ fontWeight: 700, maxWidth: 260 }} />}
              extra={<Button danger size="small" onClick={() => delCat(ci)}>删除分类</Button>}
            >
              {cat.dishes.map((d, di) => (
                <div key={di} style={{ display: "flex", gap: 6, marginBottom: 6, alignItems: "center", flexWrap: "wrap" }}>
                  <Input style={{ width: 56 }} placeholder="编号" value={d.number ?? ""} onChange={(e) => updDish(ci, di, { number: e.target.value || null })} />
                  <Input style={{ flex: "2 1 140px" }} placeholder="菜名" value={d.name} onChange={(e) => updDish(ci, di, { name: e.target.value })} />
                  <Input style={{ width: 90 }} placeholder="价格" value={d.price ?? ""} onChange={(e) => updDish(ci, di, { price: e.target.value || null })} />
                  <Checkbox.Group options={FLAG_OPTS} value={d.flags} onChange={(v) => updDish(ci, di, { flags: v as string[] })} />
                  <Input style={{ flex: "2 1 120px" }} placeholder="描述" value={d.description ?? ""} onChange={(e) => updDish(ci, di, { description: e.target.value || null })} />
                  <Select
                    style={{ width: 120 }}
                    value={d.photo_object_key ?? ""}
                    onChange={(v) => updDish(ci, di, { photo_object_key: v || null })}
                    options={[{ value: "", label: "无图" }, ...images.map((im) => ({ value: im.object_key as string, label: im.object_key!.split("/").pop() }))]}
                  />
                  <Button danger size="small" onClick={() => delDish(ci, di)}>×</Button>
                </div>
              ))}
              <Button size="small" onClick={() => addDish(ci)}>+ 加菜</Button>
            </Card>
          ))}
          <Space style={{ marginBottom: 10 }}>
            <Button onClick={addCat}>+ 加分类</Button>
          </Space>

          {/* 套餐 */}
          <Card size="small" title="套餐" style={{ marginBottom: 10 }}>
            {form.set_meals.map((sm, si) => (
              <div key={si} style={{ display: "flex", gap: 6, marginBottom: 6 }}>
                <Input style={{ width: 140 }} placeholder="套餐名" value={sm.name} onChange={(e) => mapSM((s) => s.map((x, i) => (i === si ? { ...x, name: e.target.value } : x)))} />
                <Input style={{ width: 90 }} placeholder="价格" value={sm.price ?? ""} onChange={(e) => mapSM((s) => s.map((x, i) => (i === si ? { ...x, price: e.target.value || null } : x)))} />
                <Input style={{ flex: 1 }} placeholder="包含（顿号分隔）" value={sm.items.join("、")} onChange={(e) => mapSM((s) => s.map((x, i) => (i === si ? { ...x, items: e.target.value.split(/[、,，]/).map((y) => y.trim()).filter(Boolean) } : x)))} />
                <Button danger size="small" onClick={() => mapSM((s) => s.filter((_, i) => i !== si))}>×</Button>
              </div>
            ))}
            <Button size="small" onClick={() => mapSM((s) => [...s, { name: "", price: null, items: [] }])}>+ 加套餐</Button>
          </Card>
        </div>

        {/* 右栏：实时预览 */}
        <div style={{ width: FW * SCALE + 24, flex: "0 0 auto", display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: 6 }}>
            <b>实时预览</b>
            <span style={{ flex: 1 }} />
            <Button size="small" onClick={() => setTs(Date.now())}>刷新</Button>
          </div>
          <div className="preview-wrap" style={{ flex: 1 }}>
            <div style={{ width: FW * SCALE, height: 2400 * SCALE, overflow: "hidden" }}>
              <iframe
                title="menu-preview"
                className="preview-frame"
                src={previewUrl}
                style={{ width: FW, height: 2400, transform: `scale(${SCALE})`, transformOrigin: "top left" }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
