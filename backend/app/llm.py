"""菜单提取：把一批筛过的消息 → 结构化 MenuRequirementData。

Phase 1 就是**一次带结构化输出的 LLM 调用**，不需要 LangGraph。
- 纯文本：单条字符串 prompt（已验证）。
- 含图片：走多模态 content 数组，把图片以 image_url(data URL) 内联喂给 VLM
  （qwen-vl-max 直读菜单图）。图片会先下采样再 base64，控制体积。
未配置 LLM_API_KEY 时返回占位草稿，保证整条管线在没有 LLM / 凭证时也能端到端跑通。
文件（Excel/PDF）暂作占位，文档解析另行处理（Document Agent，后续）。
"""

import base64
import io
import json
import logging

from app.config import settings
from app.models import InboxMessage
from app.schemas import MenuRequirementData
from app.storage import storage

log = logging.getLogger("muse.llm")

SYSTEM_PROMPT = (
    "你是餐饮菜单需求整理助手。从客服转发的客户聊天（含图片）里，提取结构化的菜单需求。"
    "只输出与客户需求相关的信息，忽略寒暄与客服的话。严格按给定 JSON schema 输出。"
)

_MIME = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp",
}


def _schema_instruction() -> str:
    schema = MenuRequirementData.model_json_schema()
    return "请严格按此 JSON schema 输出，仅输出 JSON：\n" + json.dumps(schema, ensure_ascii=False)


def _guess_mime(object_key: str) -> str:
    ext = object_key.rsplit(".", 1)[-1].lower() if "." in object_key else ""
    return _MIME.get(ext, "image/jpeg")


def _image_data_url(object_key: str) -> str | None:
    """从存储读图片 → 下采样 → base64 data URL。失败返回 None。"""
    try:
        raw = storage.load(object_key)
    except Exception as exc:  # noqa: BLE001
        log.warning("load image failed key=%s: %s", object_key, exc)
        return None
    mime = _guess_mime(object_key)
    try:
        from PIL import Image

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        img.thumbnail((1600, 1600))  # 控制体积/token
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        raw, mime = buf.getvalue(), "image/jpeg"
    except Exception as exc:  # noqa: BLE001 — 非图片或解码失败，回退原始字节
        log.warning("image transcode fallback key=%s: %s", object_key, exc)
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _label(m: InboxMessage) -> str:
    return f"[{m.seq}]"


def _has_images(messages: list[InboxMessage]) -> bool:
    return any(m.type == "image" and m.object_key for m in messages)


def _text_prompt(messages: list[InboxMessage]) -> str:
    lines = []
    for m in sorted(messages, key=lambda x: x.seq):
        if m.type == "text" or (m.type == "voice" and m.content):
            lines.append(f"{_label(m)} {m.content or ''}")
        else:
            lines.append(f"{_label(m)} <{m.type}:{m.object_key or ''}>")
    return "聊天记录：\n" + "\n".join(lines) + "\n\n" + _schema_instruction()


def _multimodal_content(messages: list[InboxMessage]) -> list[dict]:
    parts: list[dict] = [{"type": "text", "text": "以下是客服转发的客户聊天记录（含图片）："}]
    for m in sorted(messages, key=lambda x: x.seq):
        if m.type == "image" and m.object_key:
            url = _image_data_url(m.object_key)
            if url:
                parts.append({"type": "text", "text": f"{_label(m)} 图片："})
                parts.append({"type": "image_url", "image_url": {"url": url}})
            else:
                parts.append({"type": "text", "text": f"{_label(m)} <图片下载缺失>"})
        elif m.type == "text" or (m.type == "voice" and m.content):
            parts.append({"type": "text", "text": f"{_label(m)} {m.content or ''}"})
        else:
            # file/其他：文档解析另行处理
            parts.append({"type": "text", "text": f"{_label(m)} <{m.type}:{m.object_key or ''}>"})
    parts.append({"type": "text", "text": _schema_instruction()})
    return parts


async def extract_menu_requirement(messages: list[InboxMessage]) -> MenuRequirementData:
    if not settings.llm_api_key:
        return MenuRequirementData(
            notes="⚠️ LLM 未配置（占位草稿）。原始消息：\n" + _text_prompt(messages),
            missing_fields=["head_count", "budget"],
        )

    from openai import AsyncOpenAI

    client = AsyncOpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)
    user_content = (
        _multimodal_content(messages) if _has_images(messages) else _text_prompt(messages)
    )
    try:
        resp = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        payload = json.loads(resp.choices[0].message.content or "{}")
        return MenuRequirementData.model_validate(payload)
    except Exception as exc:  # noqa: BLE001 — 提取失败不阻断，交人工审查
        log.warning("extraction failed: %s", exc)
        return MenuRequirementData(
            notes=f"⚠️ LLM 提取失败：{exc}",
            missing_fields=["head_count", "budget"],
        )
