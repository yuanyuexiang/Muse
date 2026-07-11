from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.schemas import ApproveRequest, MenuRequirementOut, RequirementUpdate

router = APIRouter(prefix="/requirements", tags=["requirements"])


@router.get("/{req_id}", response_model=MenuRequirementOut)
async def get_requirement(req_id: int, session: AsyncSession = Depends(get_session)):
    req = await session.get(models.MenuRequirement, req_id)
    if req is None:
        raise HTTPException(404, "requirement not found")
    return req


@router.patch("/{req_id}", response_model=MenuRequirementOut)
async def update_requirement(
    req_id: int,
    body: RequirementUpdate,
    session: AsyncSession = Depends(get_session),
):
    """人工审查中修正 AI 草稿。"""
    req = await session.get(models.MenuRequirement, req_id)
    if req is None:
        raise HTTPException(404, "requirement not found")
    if req.status == models.REQ_APPROVED:
        raise HTTPException(409, "已入库，不能再改；如需修改请重跑提取生成新版本")
    req.data = body.data.model_dump()
    await session.commit()
    await session.refresh(req)
    return req


@router.post("/{req_id}/approve", response_model=MenuRequirementOut)
async def approve_requirement(
    req_id: int,
    body: ApproveRequest,
    session: AsyncSession = Depends(get_session),
):
    """人工审查通过 → 入库。"""
    req = await session.get(models.MenuRequirement, req_id)
    if req is None:
        raise HTTPException(404, "requirement not found")
    req.status = models.REQ_APPROVED
    req.reviewed_by = body.reviewed_by
    batch = await session.get(models.CurationBatch, req.batch_id)
    if batch is not None:
        batch.status = models.BATCH_REVIEWED
    await session.commit()
    await session.refresh(req)
    return req
