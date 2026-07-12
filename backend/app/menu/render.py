"""菜单渲染：MenuSpec → HTML(模板) → 印刷 PDF（WeasyPrint，RGB）。

印刷厂接受高清 RGB PDF，所以不需要 CMYK/PDF-X —— 直接 HTML/CSS 渲染即可。
支持：多主题（CSS 变量）、页面尺寸、菜品照片（从存储读出内联为 data URI）。
同一模板也能在后台当网页预览（render_menu_html）。
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

# 主题：一套 CSS 变量。设计师加主题只需在这里加一项 + 备好配色。
THEMES: dict[str, dict] = {
    "classic": {"brand": "#1e5b3e", "accent": "#b8860b", "band_text": "#ffffff",
                "serif": '"Noto Serif CJK SC", "Songti SC", "DejaVu Serif", serif'},
    "crimson": {"brand": "#8c1c2b", "accent": "#c9a227", "band_text": "#ffffff",
                "serif": '"Noto Serif CJK SC", "Songti SC", "DejaVu Serif", serif'},
    "ink":     {"brand": "#232323", "accent": "#a67c00", "band_text": "#ffffff",
                "serif": '"Noto Serif CJK SC", "Songti SC", "DejaVu Serif", serif'},
}
DEFAULT_THEME = "classic"

PAGES: dict[str, dict] = {
    "A4": {"size": "A4", "cols": 3},
    "A3": {"size": "A3 landscape", "cols": 5},
    "A5": {"size": "A5", "cols": 2},
}
DEFAULT_PAGE = "A4"


def _photo_data_url(object_key: str, box: int = 360) -> str | None:
    try:
        raw = storage.load(object_key)
    except Exception:  # noqa: BLE001
        return None
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((box, box))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        raw = buf.getvalue()
    except Exception:  # noqa: BLE001
        pass
    return f"data:image/jpeg;base64,{base64.b64encode(raw).decode()}"


def _photos(spec: MenuSpec) -> list[dict]:
    out = []
    for cat in spec.categories:
        for d in cat.dishes:
            if d.photo_object_key:
                url = _photo_data_url(d.photo_object_key)
                if url:
                    out.append({"number": d.number or "", "name": d.name, "url": url})
    return out


def render_menu_html(spec: MenuSpec, theme: str | None = None, page: str | None = None) -> str:
    name = theme or spec.theme or DEFAULT_THEME
    t = THEMES.get(name, THEMES[DEFAULT_THEME])
    pg = PAGES.get(page or DEFAULT_PAGE, PAGES[DEFAULT_PAGE])
    return _env.get_template("menu.html.j2").render(spec=spec, theme=t, page=pg, photos=_photos(spec))


def render_menu_pdf(spec: MenuSpec, theme: str | None = None, page: str | None = None) -> bytes:
    from weasyprint import HTML

    html = render_menu_html(spec, theme=theme, page=page)
    return HTML(string=html, base_url=str(_DIR)).write_pdf()
