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


CHECK_INTERVAL = 20        # 秒：健康检查间隔
DOWN_LIMIT = 9             # 连续掉线次数上限（≈3 分钟）后退出让 Docker 重启


async def _amain() -> None:
    await init_db()  # 与 API 共用一套表；单独跑也能建
    client = build_client()
    log.info("connecting to WeCom smart-robot long connection ...")
    await client.connect()
    log.info("connected. supervising (check every %ds).", CHECK_INTERVAL)

    # 看门狗：SDK 已负责心跳+无限重连，但若其内部重连任务彻底卡死（曾见连接挂起数十分钟），
    # 进程会变僵尸（在跑但不连不听）。这里连续掉线超过阈值就退出，交给 Docker
    # `restart: unless-stopped` 拉起全新进程（全新连接最可靠）。
    down = 0
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        if getattr(client, "is_connected", True):
            down = 0
            continue
        down += 1
        log.warning("long connection down (%d/%d)", down, DOWN_LIMIT)
        if down >= DOWN_LIMIT:
            log.error("down too long; exiting so Docker restarts a fresh process.")
            return


def main() -> None:
    try:
        asyncio.run(_amain())
    except KeyboardInterrupt:
        log.info("worker stopped.")


if __name__ == "__main__":
    main()
