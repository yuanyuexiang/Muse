from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# ── 状态常量 ──────────────────────────────────────────────
# InboxMessage.status
MSG_NEW = "new"            # 刚到达，未处理
MSG_SUBMITTED = "submitted"  # 已并入某个 CurationBatch
MSG_DISCARDED = "discarded"  # 人工判定不相干

# InboxMessage.download_status
DL_OK = "ok"
DL_PENDING = "pending"
DL_FAILED = "failed"       # 媒体 URL 5 分钟过期 / 下载失败 → 前端标红提示重发

# InboxMessage.sender_role（逐条转发拿不到，人工可选标注）
ROLE_UNKNOWN = "unknown"
ROLE_CUSTOMER = "customer"
ROLE_AGENT = "agent"

# CurationBatch.status
BATCH_PROCESSING = "processing"
BATCH_EXTRACTED = "extracted"
BATCH_REVIEWED = "reviewed"

# MenuRequirement.status
REQ_DRAFT = "draft"
REQ_APPROVED = "approved"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 企业微信外部联系人 id（后续）
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class InboxMessage(Base):
    """待整理收件箱里的一条原始转发消息（逐条转发 / 会话存档拆解出的单条）。"""

    __tablename__ = "inbox_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    msgid: Mapped[str] = mapped_column(String(128), unique=True, index=True)  # 去重
    seq: Mapped[int] = mapped_column(BigInteger, default=0)  # 保序：用接收时刻(epoch ms)，需 BigInteger
    channel: Mapped[str] = mapped_column(String(32))       # wecom_bot | wecom_archive | ...
    forwarded_by: Mapped[str | None] = mapped_column(String(128), nullable=True)  # 转发的客服

    type: Mapped[str] = mapped_column(String(16))          # text | image | file | voice | video | mixed
    content: Mapped[str | None] = mapped_column(Text, nullable=True)             # 文本内容 / 转写文本（可被人工编辑）
    original_content: Mapped[str | None] = mapped_column(Text, nullable=True)    # 首次编辑前的原文（留痕）
    edited: Mapped[bool] = mapped_column(Boolean, default=False)                 # 是否被人工编辑过
    object_key: Mapped[str | None] = mapped_column(String(256), nullable=True)   # 媒体在存储里的 key
    download_status: Mapped[str] = mapped_column(String(16), default=DL_OK)

    sender_role: Mapped[str] = mapped_column(String(16), default=ROLE_UNKNOWN)
    status: Mapped[str] = mapped_column(String(16), default=MSG_NEW, index=True)

    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("curation_batches.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CurationBatch(Base):
    """一次人工把关后提交给 LLM 的消息集合。"""

    __tablename__ = "curation_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    submitted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=BATCH_PROCESSING, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MenuRequirement(Base):
    """LLM 提取出的结构化菜单需求（草稿→审查→入库），带版本。"""

    __tablename__ = "menu_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("curation_batches.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    data: Mapped[dict] = mapped_column(JSONB)  # 见 schemas.MenuRequirementData
    status: Mapped[str] = mapped_column(String(16), default=REQ_DRAFT, index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
