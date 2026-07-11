"""企业微信智能机器人长连接 Channel（Phase 1）。

基于官方 SDK `wecom-aibot-python-sdk`（`from aibot import WSClient`）。SDK 负责：
连接 wss://openws.work.weixin.qq.com、用 bot_id+secret 发 aibot_subscribe 鉴权、
心跳保活、断线指数退避重连、AES-256-CBC 媒体解密。

本模块只做一件事：把收到的每条消息 normalize 成内部模型并 ingest 落库
（绝不在此调用 LLM——见 ARCHITECTURE.md §四）。客服逐条转发的每条消息是一次
独立回调，各自成为一条 InboxMessage；分组/提交由人工在后台完成。
"""

import logging
import time

from aibot import WSClient, WSClientOptions

from app.channels.base import InboundBatch, NormalizedMessage
from app.config import settings
from app.db import SessionLocal
from app.services import ingest_batch
from app.storage import storage

log = logging.getLogger("muse.wecom_bot")

CHANNEL = "wecom_bot"


def _seq() -> int:
    """逐条转发丢失原始时间戳，用接收时刻（毫秒）保序。"""
    return int(time.time() * 1000)


def _sender(body: dict) -> str | None:
    frm = body.get("from") or {}
    return frm.get("userid") if isinstance(frm, dict) else None


async def _ingest(msg: NormalizedMessage, from_userid: str | None) -> None:
    batch = InboundBatch(channel=CHANNEL, forwarded_by=from_userid, messages=[msg])
    async with SessionLocal() as session:
        await ingest_batch(session, batch)


async def _download(client: WSClient, msgid: str, media: dict, kind: str) -> str | None:
    """下载并解密媒体存入存储，返回 object_key。失败返回 None（媒体 URL 仅 5 分钟有效）。"""
    url, aeskey = media.get("url"), media.get("aeskey")
    if not url:
        return None
    try:
        data, filename = await client.download_file(url, aeskey)
        key = f"wecom/{msgid}/{filename or kind}"
        storage.save(key, data)
        return key
    except Exception as exc:  # noqa: BLE001 — 下载失败不阻断，收件箱后续标缺失
        log.warning("media download failed msgid=%s kind=%s: %s", msgid, kind, exc)
        return None


def build_client() -> WSClient:
    if not (settings.wecom_bot_id and settings.wecom_bot_secret):
        raise RuntimeError("WECOM_BOT_ID / WECOM_BOT_SECRET 未配置（见 .env）")

    client = WSClient(
        WSClientOptions(bot_id=settings.wecom_bot_id, secret=settings.wecom_bot_secret)
    )

    @client.on("message.text")
    async def _on_text(frame):  # noqa: ANN001
        body = frame.get("body", {}) or {}
        await _ingest(
            NormalizedMessage(
                msgid=body.get("msgid"),
                seq=_seq(),
                type="text",
                content=(body.get("text") or {}).get("content"),
            ),
            _sender(body),
        )

    @client.on("message.image")
    async def _on_image(frame):  # noqa: ANN001
        body = frame.get("body", {}) or {}
        key = await _download(client, body.get("msgid"), body.get("image") or {}, "image")
        await _ingest(
            NormalizedMessage(msgid=body.get("msgid"), seq=_seq(), type="image", object_key=key),
            _sender(body),
        )

    @client.on("message.file")
    async def _on_file(frame):  # noqa: ANN001
        body = frame.get("body", {}) or {}
        key = await _download(client, body.get("msgid"), body.get("file") or {}, "file")
        await _ingest(
            NormalizedMessage(msgid=body.get("msgid"), seq=_seq(), type="file", object_key=key),
            _sender(body),
        )

    @client.on("message.voice")
    async def _on_voice(frame):  # noqa: ANN001
        body = frame.get("body", {}) or {}
        voice = body.get("voice") or {}
        content = voice.get("content")  # 单聊语音企业微信通常已转写文本
        key = None if content else await _download(client, body.get("msgid"), voice, "voice")
        await _ingest(
            NormalizedMessage(
                msgid=body.get("msgid"), seq=_seq(), type="voice", content=content, object_key=key
            ),
            _sender(body),
        )

    @client.on("message.mixed")
    async def _on_mixed(frame):  # noqa: ANN001
        # 图文混排：拼接文本 + 下载图片，合并成一条 InboxMessage。
        # TODO: msg_item 结构以联调实测为准，必要时拆成多条。
        body = frame.get("body", {}) or {}
        items = (body.get("mixed") or {}).get("msg_item", []) or []
        texts, keys = [], []
        for i, it in enumerate(items):
            if it.get("msgtype") == "text":
                texts.append((it.get("text") or {}).get("content", ""))
            elif it.get("msgtype") == "image":
                k = await _download(client, f"{body.get('msgid')}#{i}", it.get("image") or {}, "image")
                if k:
                    keys.append(k)
        content = "\n".join(t for t in texts if t)
        if keys:
            content = (content + "\n[图片] " + ", ".join(keys)).strip()
        await _ingest(
            NormalizedMessage(msgid=body.get("msgid"), seq=_seq(), type="mixed", content=content),
            _sender(body),
        )

    return client
