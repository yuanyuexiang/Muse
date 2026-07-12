from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.menu.render import render_html, sample_spec
from app.schemas import PreviewIn, TemplateCreate, TemplateDetail, TemplateOut, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["templates"])


async def _get(session: AsyncSession, key: str) -> models.MenuTemplate:
    t = await session.scalar(select(models.MenuTemplate).where(models.MenuTemplate.key == key))
    if t is None:
        raise HTTPException(404, "template not found")
    return t


@router.get("", response_model=list[TemplateOut])
async def list_templates(all: bool = False, session: AsyncSession = Depends(get_session)):
    """默认只列启用的（给编辑器模板选择用）；?all=1 列全部（给管理页用）。"""
    q = select(models.MenuTemplate).order_by(models.MenuTemplate.sort_order, models.MenuTemplate.id)
    if not all:
        q = q.where(models.MenuTemplate.enabled.is_(True))
    return list(await session.scalars(q))


@router.post("/preview.html", response_class=HTMLResponse)
async def preview_source(body: PreviewIn):
    """用样例菜单渲染给定模板源码（编辑时实时预览，未保存也能看）。"""
    try:
        return HTMLResponse(render_html(sample_spec(), body.html))
    except Exception as exc:  # noqa: BLE001 — 模板语法错误直接显示
        return HTMLResponse(f"<pre style='color:#b00020;padding:12px'>模板渲染错误：\n{exc}</pre>")


@router.get("/{key}/sample.html", response_class=HTMLResponse)
async def sample_html(key: str, session: AsyncSession = Depends(get_session)):
    """已存模板用样例菜单渲染（缩略图/预览用）。"""
    t = await _get(session, key)
    try:
        return HTMLResponse(render_html(sample_spec(), t.html))
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<pre style='color:#b00020;padding:12px'>{exc}</pre>")


@router.get("/{key}", response_model=TemplateDetail)
async def get_template(key: str, session: AsyncSession = Depends(get_session)):
    return await _get(session, key)


@router.post("", response_model=TemplateDetail, status_code=201)
async def create_template(body: TemplateCreate, session: AsyncSession = Depends(get_session)):
    exists = await session.scalar(select(models.MenuTemplate).where(models.MenuTemplate.key == body.key))
    if exists:
        raise HTTPException(409, f"key「{body.key}」已存在")
    t = models.MenuTemplate(**body.model_dump())
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return t


@router.put("/{key}", response_model=TemplateDetail)
async def update_template(key: str, body: TemplateUpdate, session: AsyncSession = Depends(get_session)):
    t = await _get(session, key)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(t, field, value)
    await session.commit()
    await session.refresh(t)
    return t


@router.delete("/{key}")
async def delete_template(key: str, session: AsyncSession = Depends(get_session)):
    t = await _get(session, key)
    await session.delete(t)
    await session.commit()
    return {"ok": True}
