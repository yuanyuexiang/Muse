from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.schemas import InboxMessageOut, InboxMessageUpdate, InboxPage, SubmitRequest
from app.services import run_extraction

router = APIRouter(prefix="/inbox", tags=["inbox"])


def _inbox_conds(status: str, forwarded_by: str | None):
    """收件箱通用过滤条件：状态 + 可选转发人。列表 / ids / 计数三处共用。"""
    conds = [models.InboxMessage.status == status]
    if forwarded_by:
        conds.append(models.InboxMessage.forwarded_by == forwarded_by)
    return conds


@router.get("", response_model=InboxPage)
async def list_inbox(
    status: str = models.MSG_NEW,
    forwarded_by: str | None = None,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """待整理收件箱：默认列出未处理（new）的消息，可按转发人过滤，分页返回。"""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    conds = _inbox_conds(status, forwarded_by)
    total = await session.scalar(
        select(func.count()).select_from(models.InboxMessage).where(*conds)
    )
    rows = await session.scalars(
        select(models.InboxMessage)
        .where(*conds)
        .order_by(models.InboxMessage.seq, models.InboxMessage.id)
        .limit(limit)
        .offset(offset)
    )
    return InboxPage(
        items=[InboxMessageOut.model_validate(r) for r in rows],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/ids", response_model=list[int])
async def list_inbox_ids(
    status: str = models.MSG_NEW,
    forwarded_by: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """当前筛选下的全部消息 id（不分页），供前端「全选全部」一次拿全，跨页选中。"""
    conds = _inbox_conds(status, forwarded_by)
    rows = await session.scalars(
        select(models.InboxMessage.id)
        .where(*conds)
        .order_by(models.InboxMessage.seq, models.InboxMessage.id)
    )
    return list(rows)


@router.get("/forwarders", response_model=list[str])
async def list_forwarders(
    status: str = models.MSG_NEW,
    session: AsyncSession = Depends(get_session),
):
    """当前状态下去重的转发人（客服 userid）列表，供筛选下拉。"""
    rows = await session.scalars(
        select(models.InboxMessage.forwarded_by)
        .where(
            models.InboxMessage.status == status,
            models.InboxMessage.forwarded_by.is_not(None),
        )
        .distinct()
    )
    return [r for r in rows if r]


@router.patch("/{message_id}", response_model=InboxMessageOut)
async def update_message(
    message_id: int,
    body: InboxMessageUpdate,
    session: AsyncSession = Depends(get_session),
):
    """人工微调：改内容 / 改顺序 / 标注客户or客服 / 丢弃（status=discarded）。

    只更新显式传入的字段（exclude_unset），所以 content 可被清空为 ""，
    未传的字段保持不变。
    """
    msg = await session.get(models.InboxMessage, message_id)
    if msg is None:
        raise HTTPException(404, "message not found")
    data = body.model_dump(exclude_unset=True)
    # 首次修改 content 时留痕：把原文存进 original_content
    if "content" in data and data["content"] != msg.content and not msg.edited:
        msg.original_content = msg.content
        msg.edited = True
    for field, value in data.items():
        setattr(msg, field, value)
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
