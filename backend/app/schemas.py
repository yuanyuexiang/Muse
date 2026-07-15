from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── 餐厅菜单内容（MenuSpec）：设计一张菜单所需的完整结构 ──────
# 客户是餐厅老板，要为其设计并印刷一张菜单。这才是"菜单需求"的真实结构，
# 也是喂给 HTML/CSS 模板渲染成印刷 PDF 的数据源。
class Dish(BaseModel):
    number: str | None = Field(default=None, description="菜品编号，如 7a / 31")
    name: str = Field(description="菜名")
    description: str | None = Field(default=None, description="描述/做法/配料")
    price: str | None = Field(default=None, description="价格，保留原样字符串，如 £6.00；可含区间")
    flags: list[str] = Field(default_factory=list, description="标记：hot / vegetarian / nut")
    photo_object_key: str | None = Field(default=None, description="关联菜品图在存储里的 key")


class MenuCategory(BaseModel):
    name: str = Field(description="分类名，如 Appetizer / 米饭 / 咖喱")
    dishes: list[Dish] = Field(default_factory=list)


class SetMeal(BaseModel):
    name: str
    price: str | None = None
    items: list[str] = Field(default_factory=list, description="套餐包含的菜")


class ShopInfo(BaseModel):
    name: str | None = Field(default=None, description="店名")
    tagline: str | None = Field(default=None, description="标语/副标题")
    phone: str | None = None
    address: str | None = None
    online_order_url: str | None = None
    opening_hours: list[str] = Field(default_factory=list, description="营业时间，每行一条")
    delivery_terms: list[str] = Field(default_factory=list, description="外送/起送/满减等条款")
    promotions: list[str] = Field(default_factory=list, description="促销/赠品")
    allergen_notice: str | None = Field(default=None, description="过敏原/声明")
    style_notes: str | None = Field(default=None, description="风格/配色偏好（供设计参考）")
    logo_object_key: str | None = Field(default=None, description="店招 logo 图在存储里的 key")
    hero_object_key: str | None = Field(default=None, description="主视觉/招牌大图在存储里的 key")


class PageSpec(BaseModel):
    """成品页面：预设或自定义尺寸 + 朝向 + 出血。菜单常见 A4 横排，也有非标尺寸。"""

    preset: str = Field(default="a4-landscape", description="a4 / a4-landscape / a3 / a3-landscape / a5 / custom")
    width_mm: float | None = Field(default=None, description="自定义宽（mm），preset=custom 时用")
    height_mm: float | None = Field(default=None, description="自定义高（mm）")
    bleed_mm: float = Field(default=0.0, description="出血（mm），印刷常用 3")


class MenuSpec(BaseModel):
    """一整份餐厅菜单的内容结构（提取产出 + 模板渲染输入）。"""

    shop: ShopInfo = Field(default_factory=ShopInfo)
    categories: list[MenuCategory] = Field(default_factory=list)
    set_meals: list[SetMeal] = Field(default_factory=list)
    page: PageSpec = Field(default_factory=PageSpec)
    theme: str = Field(default="classic", description="模板 key（渲染用哪套版式）")
    notes: str | None = None
    missing_fields: list[str] = Field(default_factory=list, description="仍缺失、需补充的字段")


# ── 客户 ──────────────────────────────────────────────────
class CustomerCreate(BaseModel):
    name: str
    external_id: str | None = None
    note: str | None = None


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    external_id: str | None
    note: str | None
    created_at: datetime


# ── 收件箱消息 ────────────────────────────────────────────
class InboxMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    msgid: str
    seq: int
    channel: str
    forwarded_by: str | None
    type: str
    content: str | None
    original_content: str | None
    edited: bool
    object_key: str | None
    download_status: str
    sender_role: str
    status: str
    customer_id: int | None
    batch_id: int | None
    created_at: datetime


class InboxPage(BaseModel):
    items: list["InboxMessageOut"]
    total: int
    limit: int
    offset: int


class InboxMessageUpdate(BaseModel):
    """人工在收件箱里的微调：改内容 / 改顺序 / 标注发送者 / 丢弃。

    只有显式传入的字段会被更新（后端用 exclude_unset 判断）。
    """

    content: str | None = None  # 文本行修正；媒体行则作为人工注释
    seq: int | None = None
    sender_role: str | None = None
    status: str | None = None  # 传 "discarded" 丢弃


class SubmitRequest(BaseModel):
    """选客户 + 一键提交：把选中的消息并成一个 CurationBatch 交给 LLM。"""

    customer_id: int
    message_ids: list[int]
    submitted_by: str | None = None


# ── 提交入站（渠道 / 开发模拟共用）─────────────────────────
class InboundMessageIn(BaseModel):
    msgid: str
    seq: int = 0
    type: str = "text"
    content: str | None = None
    object_key: str | None = None


class SimulateInboundRequest(BaseModel):
    channel: str = "wecom_bot"
    forwarded_by: str | None = "kf_dev"
    messages: list[InboundMessageIn]


# ── 菜单需求 ──────────────────────────────────────────────
class MenuRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    customer_id: int
    version: int
    data: dict
    status: str
    reviewed_by: str | None
    created_at: datetime


class RequirementUpdate(BaseModel):
    data: MenuSpec


class ApproveRequest(BaseModel):
    reviewed_by: str | None = None


# ── 模板管理 ──────────────────────────────────────────────
class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    description: str | None
    enabled: bool
    sort_order: int


class TemplateDetail(TemplateOut):
    html: str


class TemplateCreate(BaseModel):
    key: str
    label: str
    description: str | None = None
    html: str
    enabled: bool = True
    sort_order: int = 0


class TemplateUpdate(BaseModel):
    label: str | None = None
    description: str | None = None
    html: str | None = None
    enabled: bool | None = None
    sort_order: int | None = None


class PreviewIn(BaseModel):
    html: str
