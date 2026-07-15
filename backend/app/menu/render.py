"""菜单渲染：MenuSpec + 模板源码(Jinja) → HTML → 印刷 PDF（WeasyPrint，RGB）。

页面尺寸/朝向/出血来自 spec.page（可预设或自定义），注入 @page；模板用自动分栏
自适应任意尺寸。传给模板的上下文：spec / page / photos / photo_urls / qr_url /
logo_url / hero_url。模板存数据库，可后台在线编辑。
"""

import base64
import io
from pathlib import Path

from jinja2 import Environment, select_autoescape

from app.schemas import Dish, MenuCategory, MenuSpec, PageSpec, SetMeal, ShopInfo
from app.storage import storage

_DIR = Path(__file__).parent
_env = Environment(autoescape=select_autoescape(["html", "j2", "xml"]))

# 内置初始模板（首次/缺失时播种进数据库；之后以数据库为准）
_SEED_META = [
    ("takeaway", "takeaway.html.j2", "外卖折页", "双面、信息密集，含 logo/主视觉/二维码/营业外送区，餐厅外卖标准版"),
    ("classic", "classic.html.j2", "经典密集", "分类多、菜品密、价目虚线，适合外卖店"),
    ("photo", "photo.html.j2", "图片主导", "每道菜配图卡片，适合正餐/精品店"),
    ("elegant", "elegant.html.j2", "高端简约", "留白多、字体讲究，适合宴会/私厨"),
]

# 预设尺寸（宽 mm, 高 mm）
_PRESET_MM = {
    "a4": (210, 297),
    "a4-landscape": (297, 210),
    "a3": (297, 420),
    "a3-landscape": (420, 297),
    "a5": (148, 210),
    "a5-landscape": (210, 148),
}
DEFAULT_PRESET = "a4-landscape"


def seed_templates_data() -> list[dict]:
    out = []
    for i, (key, file, label, desc) in enumerate(_SEED_META):
        html = (_DIR / "templates" / file).read_text(encoding="utf-8")
        out.append({"key": key, "label": label, "description": desc, "html": html, "sort_order": i})
    return out


def _page_ctx(ps: PageSpec) -> dict:
    if ps.preset == "custom" and ps.width_mm and ps.height_mm:
        w, h = float(ps.width_mm), float(ps.height_mm)
    else:
        w, h = _PRESET_MM.get(ps.preset, _PRESET_MM[DEFAULT_PRESET])
    cols = max(2, round(w / 68))  # 老模板用固定列数（自适应）
    return {
        "size": f"{w:g}mm {h:g}mm",  # @page size:
        "width_mm": w,
        "height_mm": h,
        "landscape": w > h,
        "cols": cols,
        "col_width": 60,  # 新模板用 column-width，自动算列数
        "bleed": ps.bleed_mm or 0,
    }


def _data_url(object_key: str | None, box: int = 480) -> str | None:
    if not object_key:
        return None
    try:
        raw = storage.load(object_key)
    except Exception:  # noqa: BLE001
        return None
    mime = "image/jpeg"
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((box, box))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=82)
        raw = buf.getvalue()
    except Exception:  # noqa: BLE001
        pass
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _qr_data_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        import segno

        buf = io.BytesIO()
        segno.make(url, error="m").save(buf, kind="png", scale=4, border=1)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:  # noqa: BLE001
        return None


def _photo_urls(spec: MenuSpec) -> dict[str, str]:
    urls: dict[str, str] = {}
    for cat in spec.categories:
        for d in cat.dishes:
            if d.photo_object_key and d.photo_object_key not in urls:
                u = _data_url(d.photo_object_key)
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
    ps = PageSpec(preset=page) if page else spec.page
    urls = _photo_urls(spec)
    return _env.from_string(template_src).render(
        spec=spec,
        page=_page_ctx(ps),
        photos=_photos_list(spec, urls),
        photo_urls=urls,
        qr_url=_qr_data_url(spec.shop.online_order_url),
        logo_url=_data_url(spec.shop.logo_object_key),
        hero_url=_data_url(spec.shop.hero_object_key, box=700),
    )


def render_pdf(spec: MenuSpec, template_src: str, page: str | None = None) -> bytes:
    from weasyprint import HTML

    return HTML(string=render_html(spec, template_src, page), base_url=str(_DIR)).write_pdf()


def sample_spec() -> MenuSpec:
    """模板预览用的样例菜单。"""
    return MenuSpec(
        shop=ShopInfo(
            name="Oriental Chef",
            tagline="Chinese Food to Take Away",
            phone="01622 791 368",
            address="6 Premier Parade, The Avenue, Greenacres, Aylesford, Maidstone, Kent, ME20 7LN",
            online_order_url="orientalchefaylesford.com",
            opening_hours=["Open 6 Days A Week", "周一–周四 16:45–22:00", "周五/周六 16:45–22:30", "周二休息"],
            delivery_terms=["外送起送 £18.00", "外送费 £1.50 起", "£18 以下加收 £2"],
            promotions=["满 £25 免费虾片", "满 £60 送虾片和软饮"],
            allergen_notice="14 种过敏原提示：如对花生/麸质/海鲜等过敏，请点餐时告知。",
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
            MenuCategory(name="Duck 鸭", dishes=[
                Dish(number="81", name="Roast Duck with Mushrooms", price="£8.80"),
                Dish(number="82", name="Duck with Pineapple", price="£8.80"),
            ]),
        ],
        set_meals=[
            SetMeal(name="Set for 1", price="£12.00", items=["Chop Suey", "S&S Pork Balls", "Egg Fried Rice"]),
            SetMeal(name="Set A for 2", price="£27.50", items=["Spring Rolls", "Chicken w/ Mushrooms", "Fried Rice"]),
        ],
    )
