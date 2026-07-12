# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

**Phase 1 skeleton, verified end-to-end.** A FastAPI + PostgreSQL backend implements the core pipeline (forward → inbox → submit → LLM extraction → review → approve). It runs and the full flow passes without any WeCom or LLM credentials (placeholder draft + a dev simulate endpoint). The WeCom smart-robot **long connection is implemented** (official `wecom-aibot-python-sdk`) and its **auth handshake is verified against the live server**; the message round-trip awaits a real forwarded message from 客服. The Next.js admin (`frontend/`) is **scaffolded** (Next 14 App Router, typechecks clean): `/inbox` (select customer + submit) and `/batches/[id]` (review + approve). LLM extraction is wired and **verified working** against the Aliyun MaaS OpenAI-compatible endpoint (`.../compatible-mode/v1`, model `qwen-vl-max`) — real structured drafts. Note: use the console's `openAiCompatible` URL, **not** the `dashScope` (`/api/v1`) one. **Image inputs are forwarded to the VLM** (downscaled → data URL `image_url` part) and verified: `qwen-vl-max` reads menu photos and extracts fields. Files (Excel/PDF) are still placeholder for **extraction** — document parsing is the next gap. The inbox previews images and opens files via `GET /api/media/{message_id}` (streams from storage by message id).

**[ARCHITECTURE.md](ARCHITECTURE.md) is the canonical design doc** (Chinese) — read it before changing architecture. This file is the operational summary; when the two disagree, ARCHITECTURE.md wins and should be updated.

## What this is

**MUSE** (Menu Understanding & Service Engine) — an internal AI tool for a catering-design company: 客服 (customer-service staff) forward customer chat records to a WeCom bot, an LLM drafts a structured menu requirement, a human reviews it, and it's saved. Framed long-term as a general **AI Conversation Platform** (menu extraction is the first plugin); channels stay pluggable. **Do not hard-code WeCom specifics past the `channels/` boundary.**

Two facts that overturned the original design (both settled in ARCHITECTURE.md §四):
- The bot is **internal-facing** — WeCom smart robots only receive messages from internal members, so 客服 forward customer chats to it. It never talks to external customers directly.
- **逐条转发 (forward-individually) is Phase 1**; the convenient **合并转发 (merge-forward)** is unparseable by the bot and needs **会话存档 (chat archive)** — deferred to Phase 2.

## Commands

Local host Python is 3.9 (too old); the backend targets 3.12 via Docker or `uv`.

```bash
# Full stack (postgres + minio + backend)
docker compose up --build           # → http://localhost:8000/docs

# Backend with hot reload, infra in Docker
docker compose up -d postgres minio
cd backend && uv run --python 3.12 --with-requirements requirements.txt uvicorn app.main:app --reload

# WeCom bot long-connection worker (separate long-running process; needs WECOM_* in .env)
cd backend && uv run --python 3.12 --with-requirements requirements.txt python -m app.worker

# Frontend admin (Next.js; rewrites /api/* → backend, so run the backend too)
cd frontend && npm install && npm run dev   # http://localhost:3000
# typecheck: cd frontend && npx tsc --noEmit

# Import / syntax check (no DB needed)
cd backend && uv run --python 3.12 --with-requirements requirements.txt python -c "import app.main"
```

**Port note:** host `5432` (and `5433`) are already occupied on this machine, so Compose maps Postgres to host **`55432`** (containers still use internal `postgres:5432`). `.env`'s `DATABASE_URL` matches (`localhost:55432`) for local uvicorn/worker runs.

**No automated test suite yet.** Verify changes by driving the dev flow end-to-end (see the curl sequence in [README.md](README.md#端到端自测无需企业微信--llm-凭证)) via `POST /api/dev/simulate-inbound`, which injects inbox messages without WeCom.

## Code map & data flow

Single FastAPI app under [backend/app/](backend/app/) (no microservices at this stage):

```
channels/           渠道抽象 — base.py (NormalizedMessage/InboundBatch) + wecom_bot.py (WeCom 长连接，官方 SDK，已实现)
worker.py           机器人长连接常驻进程入口 (python -m app.worker)，独立于 API（一个机器人同一时刻仅一条连接）
services.py         ingest_batch() 落库+去重 · run_extraction() 后台提取
llm.py              extract_menu_requirement() — single structured LLM call; placeholder draft if LLM_API_KEY unset
routers/            inbox · customers · batches · requirements · dev   (all mounted under /api)
models.py           Customer · InboxMessage · CurationBatch · MenuRequirement   (the 4 Phase-1 tables)
storage.py          Storage protocol — LocalStorage now, MinioStorage TODO
```

Pipeline: `channel/dev → services.ingest_batch → InboxMessage(new)` → human `POST /api/inbox/submit` (select customer + messages) → `CurationBatch` + **BackgroundTask** `run_extraction` → `llm.extract_menu_requirement` → `MenuRequirement(draft)` → human `PATCH`/`POST .../approve` → `approved`.

Frontend ([frontend/](frontend/)): Next 14 App Router client components — `app/inbox/page.tsx` and `app/batches/[id]/page.tsx` call `/api` via `lib/api.ts`; `next.config.mjs` rewrites `/api/*` to the backend (same-origin, no CORS). The batch page polls because extraction is async. The inbox supports media preview (`GET /api/media/{id}`), inline content edit with provenance (`InboxMessage.original_content`/`edited`, captured on first edit), and offset pagination (`GET /api/inbox?limit=&offset=` → `{items,total,limit,offset}`).

## Invariants (don't break these)

- **Gateway acks in 5 s, never calls the LLM inline.** Extraction is always a FastAPI BackgroundTask (WeCom long-connection requires a 5-second ack; media URLs expire in 5 min — download immediately). See ARCHITECTURE.md §四.
- **Channel-agnostic downstream.** Everything past `channels/` speaks the normalized message model; adding Feishu/会话存档 = a new channel, nothing else.
- **YAGNI boundary is deliberate.** Redis Streams, LangGraph, PaddleOCR, and the second human gate (筛查) are intentionally deferred (ARCHITECTURE.md §五). Don't reintroduce them without a concrete need — Phase 1 uses BackgroundTasks, a single LLM call, VLM-direct image reading, and one review gate.
- **Runs without credentials.** Keep the pipeline working when `LLM_API_KEY` / `WECOM_*` are empty (placeholder draft, dev simulate) — this is the primary dev loop until creds arrive.
- **Secrets only in `.env`** (git-ignored); `.env.example` documents keys. Schema changes currently rely on `create_all` on startup — no Alembic yet, so destructive model edits need a DB reset in dev.

## Roadmap (see ARCHITECTURE.md §十一)

1. **Phase 1 (current)** — 逐条转发 + single review gate, end-to-end minimal loop
2. **Phase 2** — 会话存档 channel (合并转发), harden platform (Redis when volume warrants)
3. **Phase 3** — LangGraph multi-agent, richer OCR / doc parsing
4. **Phase 4** — menu confirmation, quoting, posters, orders
5. **Phase 5** — Qdrant, RAG, customer profiles, template recommendations
