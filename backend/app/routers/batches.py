from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.schemas import InboxMessageOut, MenuRequirementOut
from app.services import run_extraction

router = APIRouter(prefix="/batches", tags=["batches"])


@router.get("")
async def list_batches(session: AsyncSession = Depends(get_session)):
    """所有批次列表（供后台"菜单批次"页），带客户名/店名/菜品数/状态。"""
    batches = list(
        await session.scalars(select(models.CurationBatch).order_by(models.CurationBatch.id.desc()))
    )
    out = []
    for b in batches:
        cust = await session.get(models.Customer, b.customer_id)
        req = await session.scalar(
            select(models.MenuRequirement)
            .where(models.MenuRequirement.batch_id == b.id)
            .order_by(models.MenuRequirement.version.desc())
        )
        data = (req.data or {}) if req else {}
        dish_count = sum(len(c.get("dishes", [])) for c in data.get("categories", []))
        out.append({
            "id": b.id,
            "status": b.status,
            "customer_id": b.customer_id,
            "customer_name": cust.name if cust else None,
            "shop_name": (data.get("shop") or {}).get("name"),
            "req_id": req.id if req else None,
            "req_status": req.status if req else None,
            "dish_count": dish_count,
            "created_at": b.created_at.isoformat() if b.created_at else None,
        })
    return out


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
