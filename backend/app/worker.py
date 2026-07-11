"""企业微信机器人长连接 worker（独立进程）。

单独跑而不是塞进 uvicorn，因为：长连接是常驻的，且"每个机器人同一时刻只能一个
有效长连接"——若 uvicorn 多 worker 会开多条连接互相踢掉。

启动：
    python -m app.worker
或 docker compose 里的 `bot` 服务。
"""

import asyncio
import logging

from app.channels.wecom_bot import build_client
from app.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("muse.worker")


async def _amain() -> None:
    await init_db()  # 与 API 共用一套表；单独跑也能建
    client = build_client()
    log.info("connecting to WeCom smart-robot long connection ...")
    await client.connect()
    log.info("connected. waiting for forwarded messages (Ctrl-C to stop).")
    await asyncio.Event().wait()


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        log.info("worker stopped.")


if __name__ == "__main__":
    main()
