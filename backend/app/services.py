"""服务层：入站落库 + 后台提取。路由只做校验，逻辑集中在这里。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.channels.base import InboundBatch
from app.db import SessionLocal
from app.llm import extract_menu_requirement


async def ingest_batch(session: AsyncSession, batch: InboundBatch) -> list[models.InboxMessage]:
    """把一次入站的消息落到收件箱，按 msgid 去重。媒体下载另行处理。"""
    created: list[models.InboxMessage] = []
    for m in batch.messages:
        exists = await session.scalar(
            select(models.InboxMessage).where(models.InboxMessage.msgid == m.msgid)
        )
        if exists:
            continue
        needs_download = m.type != "text" and not m.object_key
        msg = models.InboxMessage(
            msgid=m.msgid,
            seq=m.seq,
            channel=batch.channel,
            forwarded_by=batch.forwarded_by,
            type=m.type,
            content=m.content,
            object_key=m.object_key,
            download_status=models.DL_PENDING if needs_download else models.DL_OK,
            status=models.MSG_NEW,
        )
        session.add(msg)
        created.append(msg)
    await session.commit()
    return created


async def run_extraction(batch_id: int) -> None:
    """后台任务：对一个 CurationBatch 跑 LLM 提取，产出 MenuRequirement 草稿。

    独立开 session（在响应返回后运行）。
    """
    async with SessionLocal() as session:
        batch = await session.get(models.CurationBatch, batch_id)
        if batch is None:
            return
        msgs = list(
            await session.scalars(
                select(models.InboxMessage)
                .where(models.InboxMessage.batch_id == batch_id)
                .order_by(models.InboxMessage.seq)
            )
        )
        data = await extract_menu_requirement(msgs)
        req = models.MenuRequirement(
            batch_id=batch_id,
            customer_id=batch.customer_id,
            version=1,
            data=data.model_dump(),
            status=models.REQ_DRAFT,
        )
        session.add(req)
        batch.status = models.BATCH_EXTRACTED
        await session.commit()
