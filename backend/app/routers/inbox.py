from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.schemas import InboxMessageOut, InboxMessageUpdate, SubmitRequest
from app.services import run_extraction

router = APIRouter(prefix="/inbox", tags=["inbox"])


@router.get("", response_model=list[InboxMessageOut])
async def list_inbox(
    status: str = models.MSG_NEW,
    session: AsyncSession = Depends(get_session),
):
    """待整理收件箱：默认列出未处理（new）的消息。"""
    rows = await session.scalars(
        select(models.InboxMessage)
        .where(models.InboxMessage.status == status)
        .order_by(models.InboxMessage.seq, models.InboxMessage.id)
    )
    return list(rows)


@router.patch("/{message_id}", response_model=InboxMessageOut)
async def update_message(
    message_id: int,
    body: InboxMessageUpdate,
    session: AsyncSession = Depends(get_session),
):
    """人工微调：改顺序 / 标注客户or客服 / 丢弃（status=discarded）。"""
    msg = await session.get(models.InboxMessage, message_id)
    if msg is None:
        raise HTTPException(404, "message not found")
    if body.seq is not None:
        msg.seq = body.seq
    if body.sender_role is not None:
        msg.sender_role = body.sender_role
    if body.status is not None:
        msg.status = body.status
    await session.commit()
    await session.refresh(msg)
    return msg


@router.post("/submit")
async def submit_batch(
    body: SubmitRequest,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """选客户 + 一键提交：把选中的消息并成一个 CurationBatch，后台触发 LLM 提取。"""
    customer = await session.get(models.Customer, body.customer_id)
    if customer is None:
        raise HTTPException(404, "customer not found")

    msgs = list(
        await session.scalars(
            select(models.InboxMessage).where(models.InboxMessage.id.in_(body.message_ids))
        )
    )
    if not msgs:
        raise HTTPException(400, "no messages selected")

    batch = models.CurationBatch(
        customer_id=body.customer_id,
        submitted_by=body.submitted_by,
        status=models.BATCH_PROCESSING,
    )
    session.add(batch)
    await session.flush()  # 拿到 batch.id

    for msg in msgs:
        msg.batch_id = batch.id
        msg.customer_id = body.customer_id
        msg.status = models.MSG_SUBMITTED
    await session.commit()

    background.add_task(run_extraction, batch.id)
    return {"batch_id": batch.id, "message_count": len(msgs)}
