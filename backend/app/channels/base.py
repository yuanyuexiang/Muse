from dataclasses import dataclass, field


@dataclass
class NormalizedMessage:
    """网关标准化后的内部消息模型（与渠道无关）。"""

    msgid: str
    seq: int
    type: str  # text | image | file | voice | video | mixed
    content: str | None = None
    object_key: str | None = None


@dataclass
class InboundBatch:
    """一次入站（某客服转发过来的一批消息）。"""

    channel: str
    forwarded_by: str | None
    messages: list[NormalizedMessage] = field(default_factory=list)
