from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def stats(session: AsyncSession = Depends(get_session)):
    """仪表盘数字：待整理消息 / 批次 / 已入库菜单。"""
    inbox_new = await session.scalar(
        select(func.count()).select_from(models.InboxMessage).where(
            models.InboxMessage.status == models.MSG_NEW
        )
    )
    batches = await session.scalar(select(func.count()).select_from(models.CurationBatch))
    approved = await session.scalar(
        select(func.count()).select_from(models.MenuRequirement).where(
            models.MenuRequirement.status == models.REQ_APPROVED
        )
    )
    return {"inbox_new": inbox_new or 0, "batches": batches or 0, "approved": approved or 0}
