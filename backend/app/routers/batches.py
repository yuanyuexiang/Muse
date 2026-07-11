from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.schemas import InboxMessageOut, MenuRequirementOut
from app.services import run_extraction

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("/{batch_id}")
async def get_batch(batch_id: int, session: AsyncSession = Depends(get_session)):
    batch = await session.get(models.CurationBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "batch not found")
    msgs = await session.scalars(
        select(models.InboxMessage)
        .where(models.InboxMessage.batch_id == batch_id)
        .order_by(models.InboxMessage.seq)
    )
    reqs = await session.scalars(
        select(models.MenuRequirement)
        .where(models.MenuRequirement.batch_id == batch_id)
        .order_by(models.MenuRequirement.version.desc())
    )
    return {
        "id": batch.id,
        "customer_id": batch.customer_id,
        "status": batch.status,
        "messages": [InboxMessageOut.model_validate(m) for m in msgs],
        "requirements": [MenuRequirementOut.model_validate(r) for r in reqs],
    }


@router.post("/{batch_id}/extract")
async def reextract(
    batch_id: int,
    background: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """手动重跑提取（例如改了筛查后）。"""
    batch = await session.get(models.CurationBatch, batch_id)
    if batch is None:
        raise HTTPException(404, "batch not found")
    background.add_task(run_extraction, batch_id)
    return {"batch_id": batch_id, "status": "extraction scheduled"}
