"""菜单渲染：MenuSpec → HTML(模板) → 印刷 PDF（WeasyPrint，RGB）。

模板 = 一套完整版式（布局 + 配色）。每个模板是一个独立 .j2 文件；加模板只需
放一个新文件 + 在 TEMPLATES 登记。同一模板也能当网页预览（render_menu_html）。
"""

import base64
import io
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas import MenuSpec
from app.storage import storage

_DIR = Path(__file__).parent
_env = Environment(
    loader=FileSystemLoader(str(_DIR / "templates")),
    autoescape=select_autoescape(["html", "j2", "xml"]),
)

TEMPLATES: dict[str, dict] = {
    "classic": {"file": "classic.html.j2", "label": "经典密集", "desc": "分类多、菜品密、价目虚线，适合外卖店"},
    "photo":   {"file": "photo.html.j2",   "label": "图片主导", "desc": "每道菜配图卡片，适合正餐/精品店"},
    "elegant": {"file": "elegant.html.j2", "label": "高端简约", "desc": "留白多、字体讲究，适合宴会/私厨"},
}
DEFAULT_TEMPLATE = "classic"

PAGES: dict[str, dict] = {
    "A4": {"size": "A4", "cols": 3},
    "A3": {"size": "A3 landscape", "cols": 5},
    "A5": {"size": "A5", "cols": 2},
}
DEFAULT_PAGE = "A4"


def _photo_data_url(object_key: str, box: int = 480) -> str | None:
    try:
        raw = storage.load(object_key)
    except Exception:  # noqa: BLE001
        return None
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((box, box))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        raw = buf.getvalue()
    except Exception:  # noqa: BLE001
        pass
    return f"data:image/jpeg;base64,{base64.b64encode(raw).decode()}"


def _photo_urls(spec: MenuSpec) -> dict[str, str]:
    urls: dict[str, str] = {}
    for cat in spec.categories:
        for d in cat.dishes:
            if d.photo_object_key and d.photo_object_key not in urls:
                u = _photo_data_url(d.photo_object_key)
                if u:
                    urls[d.photo_object_key] = u
    return urls


def _photos_list(spec: MenuSpec, urls: dict[str, str]) -> list[dict]:
    out = []
    for cat in spec.categories:
        for d in cat.dishes:
            if d.photo_object_key and urls.get(d.photo_object_key):
                out.append({"number": d.number or "", "name": d.name, "url": urls[d.photo_object_key]})
    return out


def _template_key(v: str | None) -> str:
    return v if v in TEMPLATES else DEFAULT_TEMPLATE


def render_menu_html(spec: MenuSpec, theme: str | None = None, page: str | None = None) -> str:
    key = _template_key(theme or spec.theme or DEFAULT_TEMPLATE)
    pg = PAGES.get(page or DEFAULT_PAGE, PAGES[DEFAULT_PAGE])
    urls = _photo_urls(spec)
    tmpl = _env.get_template(TEMPLATES[key]["file"])
    return tmpl.render(spec=spec, page=pg, photos=_photos_list(spec, urls), photo_urls=urls)


def render_menu_pdf(spec: MenuSpec, theme: str | None = None, page: str | None = None) -> bytes:
    from weasyprint import HTML

    html = render_menu_html(spec, theme=theme, page=page)
    return HTML(string=html, base_url=str(_DIR)).write_pdf()
