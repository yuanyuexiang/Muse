"""模板存取：首次播种内置模板 + 按 key 取模板源码。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.menu.render import seed_templates_data


async def seed_templates(session: AsyncSession) -> None:
    n = await session.scalar(select(func.count()).select_from(models.MenuTemplate))
    if n:
        return
    for t in seed_templates_data():
        session.add(models.MenuTemplate(**t))
    await session.commit()


async def resolve_template_src(session: AsyncSession, key: str | None) -> str | None:
    """取模板源码：先按 key；找不到则退回第一个启用的模板。"""
    t = None
    if key:
        t = await session.scalar(select(models.MenuTemplate).where(models.MenuTemplate.key == key))
    if t is None:
        t = await session.scalar(
            select(models.MenuTemplate)
            .where(models.MenuTemplate.enabled.is_(True))
            .order_by(models.MenuTemplate.sort_order, models.MenuTemplate.id)
        )
    return t.html if t else None
