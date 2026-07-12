"""菜单渲染：MenuSpec + 模板源码(Jinja) → HTML → 印刷 PDF（WeasyPrint，RGB）。

模板现在存在数据库里（后台可在线编辑），渲染时传入模板源码字符串。
`seed_templates_data()` 从内置 .j2 文件读出初始 3 套模板用于首次播种。
"""

import base64
import io
from pathlib import Path

from jinja2 import Environment, select_autoescape

from app.schemas import Dish, MenuCategory, MenuSpec, SetMeal, ShopInfo
from app.storage import storage

_DIR = Path(__file__).parent
_env = Environment(autoescape=select_autoescape(["html", "j2", "xml"]))

# 内置初始模板（首次播种进数据库；之后以数据库为准）
_SEED_META = [
    ("classic", "classic.html.j2", "经典密集", "分类多、菜品密、价目虚线，适合外卖店"),
    ("photo", "photo.html.j2", "图片主导", "每道菜配图卡片，适合正餐/精品店"),
    ("elegant", "elegant.html.j2", "高端简约", "留白多、字体讲究，适合宴会/私厨"),
]

PAGES: dict[str, dict] = {
    "A4": {"size": "A4", "cols": 3},
    "A3": {"size": "A3 landscape", "cols": 5},
    "A5": {"size": "A5", "cols": 2},
}
DEFAULT_PAGE = "A4"


def seed_templates_data() -> list[dict]:
    out = []
    for i, (key, file, label, desc) in enumerate(_SEED_META):
        html = (_DIR / "templates" / file).read_text(encoding="utf-8")
        out.append({"key": key, "label": label, "description": desc, "html": html, "sort_order": i})
    return out


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


def render_html(spec: MenuSpec, template_src: str, page: str | None = None) -> str:
    pg = PAGES.get(page or DEFAULT_PAGE, PAGES[DEFAULT_PAGE])
    urls = _photo_urls(spec)
    return _env.from_string(template_src).render(
        spec=spec, page=pg, photos=_photos_list(spec, urls), photo_urls=urls
    )


def render_pdf(spec: MenuSpec, template_src: str, page: str | None = None) -> bytes:
    from weasyprint import HTML

    return HTML(string=render_html(spec, template_src, page), base_url=str(_DIR)).write_pdf()


def sample_spec() -> MenuSpec:
    """模板预览用的样例菜单（文字为主，容器内无需素材图）。"""
    return MenuSpec(
        shop=ShopInfo(
            name="Oriental Chef",
            tagline="Chinese Food to Take Away",
            phone="01622 791 368",
            address="6 Premier Parade, Aylesford, Maidstone, Kent",
            opening_hours=["周一–周四 16:45–22:00", "周五/周六 16:45–22:30", "周二休息"],
            promotions=["满 £25 免费虾片", "满 £60 送虾片和软饮"],
            allergen_notice="14 种过敏原提示：如有过敏请点餐时告知。",
        ),
        categories=[
            MenuCategory(name="Appetizer 前菜", dishes=[
                Dish(number="1", name="Mixed Hors d'oeuvres", price="£6.00"),
                Dish(number="2", name="Seaweed", price="£5.70", flags=["vegetarian"]),
                Dish(number="8", name="Chicken Wings, Salt & Chilli", price="£7.20", flags=["hot"]),
                Dish(number="6", name="Satay Chicken (4)", price="£5.20", flags=["nut"]),
            ]),
            MenuCategory(name="Curry 咖喱", dishes=[
                Dish(number="41", name="House Special Curry", price="£8.00", flags=["hot"]),
                Dish(number="44", name="Beef Curry", price="£7.80", flags=["hot"]),
                Dish(number="47", name="Mixed Vegetable Curry", price="£6.80", flags=["hot", "vegetarian"]),
            ]),
            MenuCategory(name="Chicken 鸡", dishes=[
                Dish(number="60", name="Chicken & Mushrooms", price="£8.00"),
                Dish(number="62", name="Chicken w/ Green Peppers", price="£8.00", flags=["hot"]),
                Dish(number="69", name="Chicken w/ Ginger & Spring Onion", price="£8.00"),
            ]),
        ],
        set_meals=[
            SetMeal(name="Set for 1", price="£12.00", items=["Chop Suey", "S&S Pork Balls", "Egg Fried Rice"]),
            SetMeal(name="Set A for 2", price="£27.50", items=["Spring Rolls", "Chicken w/ Mushrooms", "Fried Rice"]),
        ],
    )
