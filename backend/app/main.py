from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import init_db
from app.routers import batches, customers, dev, inbox, media, requirements, stats, templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()  # 开发期建表；生产迁移待接入 Alembic
    yield


app = FastAPI(title="MUSE", version="0.1.0", lifespan=lifespan)

# 供后续 Next.js 后台（localhost:3000）调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api"
app.include_router(inbox.router, prefix=API_PREFIX)
app.include_router(media.router, prefix=API_PREFIX)
app.include_router(customers.router, prefix=API_PREFIX)
app.include_router(batches.router, prefix=API_PREFIX)
app.include_router(requirements.router, prefix=API_PREFIX)
app.include_router(templates.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(dev.router, prefix=API_PREFIX)


@app.get("/health")
async def health():
    return {"status": "ok"}
