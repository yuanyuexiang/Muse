"use client";

import { useEffect, useState } from "react";
import { Button, Card, Drawer, Input, Popconfirm, Space, Switch, message } from "antd";
import { api } from "@/lib/api";

interface TmplRow {
  key: string;
  label: string;
  description: string | null;
  enabled: boolean;
  sort_order: number;
}
interface TmplDetail extends TmplRow {
  html: string;
}

const STARTER = `<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><style>
  @page { size: {{ page.size }}; margin: 12mm; }
  body { font-family: "Noto Sans CJK SC", sans-serif; color:#222; }
  h1 { text-align:center; }
  .cat { font-weight:700; border-bottom:2px solid #333; margin-top:10px; }
  .dish { display:flex; justify-content:space-between; }
</style></head><body>
  <h1>{{ spec.shop.name or "餐厅名称" }}</h1>
  {% for cat in spec.categories %}
    <div class="cat">{{ cat.name }}</div>
    {% for d in cat.dishes %}<div class="dish"><span>{{ d.number }} {{ d.name }}</span><span>{{ d.price }}</span></div>{% endfor %}
  {% endfor %}
</body></html>`;

export default function TemplatesPage() {
  const [rows, setRows] = useState<TmplRow[]>([]);
  const [editing, setEditing] = useState<TmplDetail | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [previewHtml, setPreviewHtml] = useState("");
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setRows(await api<TmplRow[]>("/templates?all=1"));
    } catch (e) {
      message.error(String(e instanceof Error ? e.message : e));
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function toggle(key: string, enabled: boolean) {
    await api(`/templates/${key}`, { method: "PUT", body: JSON.stringify({ enabled }) });
    load();
  }
  async function openEdit(key: string) {
    setEditing(await api<TmplDetail>(`/templates/${key}`));
    setIsNew(false);
  }
  function openNew() {
    setEditing({ key: "", label: "新模板", description: "", enabled: true, sort_order: rows.length, html: STARTER });
    setIsNew(true);
  }
  async function del(key: string) {
    await api(`/templates/${key}`, { method: "DELETE" });
    load();
  }

  // 编辑器实时预览：改 html 去抖 → 用样例菜单渲染
  useEffect(() => {
    if (!editing) return;
    const t = setTimeout(async () => {
      try {
        setPreviewHtml(await api<string>("/templates/preview.html", { method: "POST", body: JSON.stringify({ html: editing.html }) }));
      } catch {
        /* ignore */
      }
    }, 600);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editing?.html]);

  async function save() {
    if (!editing) return;
    if (isNew && !editing.key.trim()) return message.warning("请填 key");
    setSaving(true);
    try {
      if (isNew) await api("/templates", { method: "POST", body: JSON.stringify(editing) });
      else
        await api(`/templates/${editing.key}`, {
          method: "PUT",
          body: JSON.stringify({
            label: editing.label,
            description: editing.description,
            html: editing.html,
            enabled: editing.enabled,
            sort_order: editing.sort_order,
          }),
        });
      message.success("已保存");
      setEditing(null);
      load();
    } catch (e) {
      message.error(String(e instanceof Error ? e.message : e));
    }
    setSaving(false);
  }

  return (
    <div>
      <Space style={{ marginBottom: 14 }}>
        <Button type="primary" onClick={openNew}>
          新建模板
        </Button>
        <span style={{ color: "#888" }}>模板 = 一套菜单版式（HTML/CSS）。启用的会出现在菜单编辑器的模板选择里。</span>
      </Space>

      <div style={{ display: "flex", flexWrap: "wrap", gap: 14 }}>
        {rows.map((t) => (
          <Card
            key={t.key}
            size="small"
            style={{ width: 220, opacity: t.enabled ? 1 : 0.5 }}
            cover={
              <div className="tmpl-thumb">
                <iframe
                  title={t.key}
                  src={`/api/templates/${t.key}/sample.html`}
                  style={{ width: 800, height: 1100, border: 0, transform: "scale(0.265)", transformOrigin: "top left" }}
                />
              </div>
            }
            actions={[
              <a key="e" onClick={() => openEdit(t.key)}>
                编辑
              </a>,
              <Switch key="s" size="small" checked={t.enabled} onChange={(v) => toggle(t.key, v)} />,
              <Popconfirm key="d" title="删除该模板？" onConfirm={() => del(t.key)}>
                <a style={{ color: "#c0392b" }}>删除</a>
              </Popconfirm>,
            ]}
          >
            <Card.Meta title={`${t.label}（${t.key}）`} description={t.description} />
          </Card>
        ))}
      </div>

      <Drawer
        open={!!editing}
        width="82%"
        title={isNew ? "新建模板" : `编辑模板 · ${editing?.label}`}
        onClose={() => setEditing(null)}
        extra={
          <Button type="primary" loading={saving} onClick={save}>
            保存
          </Button>
        }
        styles={{ body: { height: "100%", overflow: "hidden" } }}
      >
        {editing && (
          <div style={{ display: "flex", gap: 12, height: "calc(100vh - 120px)" }}>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
              <Space wrap>
                {isNew && (
                  <Input addonBefore="key" value={editing.key} onChange={(e) => setEditing({ ...editing, key: e.target.value })} style={{ width: 170 }} />
                )}
                <Input addonBefore="名称" value={editing.label} onChange={(e) => setEditing({ ...editing, label: e.target.value })} style={{ width: 190 }} />
                <Input addonBefore="描述" value={editing.description ?? ""} onChange={(e) => setEditing({ ...editing, description: e.target.value })} style={{ width: 280 }} />
                <span>
                  启用 <Switch checked={editing.enabled} onChange={(v) => setEditing({ ...editing, enabled: v })} />
                </span>
              </Space>
              <Input.TextArea
                value={editing.html}
                onChange={(e) => setEditing({ ...editing, html: e.target.value })}
                spellCheck={false}
                style={{ flex: 1, fontFamily: "ui-monospace, Menlo, Consolas, monospace", fontSize: 12, resize: "none" }}
              />
              <div style={{ color: "#888", fontSize: 12 }}>
                可用变量：<code>spec.shop</code>、<code>spec.categories[].dishes[]</code>（number/name/price/description/flags）、
                <code>spec.set_meals</code>、<code>photo_urls[key]</code>、<code>page.size</code>/<code>page.cols</code>。右侧用样例菜单实时预览。
              </div>
            </div>
            <div className="preview-wrap" style={{ flex: 1, minWidth: 0 }}>
              <div style={{ width: 820 * 0.6, height: 2200 * 0.6, overflow: "hidden" }}>
                <iframe
                  title="preview"
                  srcDoc={previewHtml}
                  style={{ width: 820, height: 2200, border: 0, background: "#fff", transform: "scale(0.6)", transformOrigin: "top left" }}
                />
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
