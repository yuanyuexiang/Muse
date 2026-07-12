from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.menu.render import render_menu_html, render_menu_pdf
from app.schemas import ApproveRequest, MenuRequirementOut, MenuSpec, RequirementUpdate

router = APIRouter(prefix="/requirements", tags=["requirements"])


async def _spec(req_id: int, session: AsyncSession) -> MenuSpec:
    req = await session.get(models.MenuRequirement, req_id)
    if req is None:
        raise HTTPException(404, "requirement not found")
    return MenuSpec.model_validate(req.data or {})


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


@router.get("/{req_id}/menu.html", response_class=HTMLResponse)
async def preview_menu_html(
    req_id: int,
    theme: str | None = None,
    page: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """把菜单渲染成网页，供后台内嵌/新标签预览（无需 PDF 依赖）。"""
    return HTMLResponse(render_menu_html(await _spec(req_id, session), theme=theme, page=page))


@router.get("/{req_id}/menu.pdf")
async def preview_menu_pdf(
    req_id: int,
    theme: str | None = None,
    page: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    """印刷级 PDF（WeasyPrint）。渲染依赖缺失时返回 503 而非 500。"""
    spec = await _spec(req_id, session)
    try:
        pdf = render_menu_pdf(spec, theme=theme, page=page)
    except Exception as exc:  # noqa: BLE001 — WeasyPrint 原生库未装等
        raise HTTPException(503, f"PDF 渲染依赖未就绪：{exc}") from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'inline; filename="menu.pdf"'},
    )
