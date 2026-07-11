from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── LLM 结构化输出：菜单需求 ───────────────────────────────
class MenuRequirementData(BaseModel):
    """Menu Extraction Agent 的产出结构；也用作 LLM 的 response schema。"""

    head_count: int | None = Field(default=None, description="人数")
    budget: float | None = Field(default=None, description="预算（元）")
    dietary_restrictions: list[str] = Field(default_factory=list, description="忌口 / 不吃")
    taste_preferences: list[str] = Field(default_factory=list, description="口味偏好")
    dishes: list[str] = Field(default_factory=list, description="明确提到的菜品")
    event_type: str | None = Field(default=None, description="场合，如婚宴 / 家宴 / 团建")
    notes: str | None = Field(default=None, description="其他要点")
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
    object_key: str | None
    download_status: str
    sender_role: str
    status: str
    customer_id: int | None
    batch_id: int | None
    created_at: datetime


class InboxMessageUpdate(BaseModel):
    """人工在收件箱里的微调：改顺序 / 标注发送者 / 丢弃。"""

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
    data: MenuRequirementData


class ApproveRequest(BaseModel):
    reviewed_by: str | None = None
