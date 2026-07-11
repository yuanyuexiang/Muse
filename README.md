# MUSE — Menu Understanding & Service Engine

基于企业微信的 AI 会话处理平台，首个场景为餐饮设计公司的菜单需求整理。
架构与决策见 [ARCHITECTURE.md](ARCHITECTURE.md)。

当前为 **Phase 1 骨架**：客服逐条转发 → 收件箱 → 选客户提交 → LLM 提取 → 人工审查 → 入库。
企业微信长连接与 LLM 未接凭证时，可用 `dev/simulate-inbound` 端到端跑通。

## 目录

```
backend/        FastAPI + SQLAlchemy（网关 / 收件箱 / 提取 / 审查）
  app/
    channels/   渠道抽象（wecom_bot 长连接，待接凭证）
    routers/    inbox · customers · batches · requirements · dev
    models.py   Customer · InboxMessage · CurationBatch · MenuRequirement
    llm.py      菜单提取（单次结构化 LLM 调用；未配置则返回占位草稿）
docker-compose.yml   postgres · minio · backend
frontend/       Next.js 后台（待搭）
```

## 快速启动

### 方式 A：全 Docker

```bash
cp .env.example .env          # 按需填 LLM_API_KEY（不填也能跑通管线）
docker compose up --build     # 起 postgres + minio + backend
# 打开 http://localhost:8000/docs
```

### 方式 B：基础设施用 Docker，后端本地热重载（uv）

```bash
cp .env.example .env
docker compose up -d postgres minio
cd backend
uv run --python 3.12 --with-requirements requirements.txt \
  uvicorn app.main:app --reload
```

## 端到端自测（无需企业微信 / LLM 凭证）

```bash
# 1. 建客户
curl -s localhost:8000/api/customers -H 'content-type: application/json' \
  -d '{"name":"张三"}'

# 2. 模拟客服逐条转发进收件箱
curl -s localhost:8000/api/dev/simulate-inbound -H 'content-type: application/json' \
  -d '{"forwarded_by":"kf_zhang","messages":[
        {"msgid":"m1","seq":1,"type":"text","content":"四个人"},
        {"msgid":"m2","seq":2,"type":"text","content":"预算500，不要牛肉"}]}'

# 3. 看收件箱
curl -s localhost:8000/api/inbox

# 4. 选客户 + 提交（触发后台提取）
curl -s localhost:8000/api/inbox/submit -H 'content-type: application/json' \
  -d '{"customer_id":1,"message_ids":[1,2]}'

# 5. 看批次里生成的菜单需求草稿
curl -s localhost:8000/api/batches/1

# 6. 审查通过入库
curl -s -X POST localhost:8000/api/requirements/1/approve \
  -H 'content-type: application/json' -d '{"reviewed_by":"admin"}'
```

## 企业微信机器人联调（长连接已实现）

机器人长连接用官方 SDK `wecom-aibot-python-sdk` 实现在
[backend/app/channels/wecom_bot.py](backend/app/channels/wecom_bot.py)，跑在独立常驻进程
[backend/app/worker.py](backend/app/worker.py)（一个机器人同一时刻仅一条连接，故不塞进 uvicorn）。
鉴权握手已用真实凭证连通 `wss://openws.work.weixin.qq.com` 验证通过。

```bash
# 填好 .env 里的 WECOM_CORPID / WECOM_BOT_ID / WECOM_BOT_SECRET 后：
docker compose up --build            # 含 bot 服务，自动连长连接
# 或本地单独跑 worker（需 postgres 在跑）：
cd backend && uv run --python 3.12 --with-requirements requirements.txt python -m app.worker
```

**手动回环测试**：worker 连上后，客服在企业微信里给机器人**逐条转发**几条消息 →
`GET /api/inbox` 应能看到它们落库 → 之后走"选客户 + 提交 → 审查"。

## 待接

- **LLM**：填 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`，多模态图片链路见 [backend/app/llm.py](backend/app/llm.py) 的 TODO。
- **迁移**：当前用 `create_all` 建表，生产接 Alembic。
- **前端**：`frontend/` 下 `create-next-app`，对接 `/api`。
