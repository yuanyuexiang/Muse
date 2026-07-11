# MUSE 后台（Next.js）

Phase 1 后台，App Router + TypeScript。两页：

- **`/inbox`** 待整理收件箱 — 列出 `new` 消息，选客户（可新建）、勾选消息、丢弃无关，一键提交 → 跳转批次页
- **`/batches/[id]`** 批次审查 — 展示原始消息 + AI 菜单需求草稿（后台提取，页面自动轮询），可编辑字段，审查通过入库

`/api/*` 由 [next.config.mjs](next.config.mjs) 反代到后端（默认 `http://localhost:8000`，同源免 CORS）。

## 运行

```bash
cd frontend
npm install
npm run dev          # http://localhost:3000
```

后端需同时在跑（`docker compose up` 或本地 uvicorn）。如后端不在 8000，用
`BACKEND_ORIGIN=http://host:port npm run dev` 覆盖反代目标。

## 无凭证也能点通

后端 `POST /api/dev/simulate-inbound` 可灌入测试消息（见根目录 README），
然后在 `/inbox` 里选客户 → 提交 → `/batches/[id]` 审查入库，全程走一遍。
