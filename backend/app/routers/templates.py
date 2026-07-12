from fastapi import APIRouter

from app.menu.render import TEMPLATES

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
async def list_templates():
    """可选模板列表（供后台可视化模板库）。"""
    return [{"key": k, "label": v["label"], "desc": v["desc"]} for k, v in TEMPLATES.items()]
