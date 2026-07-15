"""企业微信智能机器人长连接 Channel（Phase 1）。

基于官方 SDK `wecom-aibot-python-sdk`（`from aibot import WSClient`）。SDK 负责：
连接 wss://openws.work.weixin.qq.com、用 bot_id+secret 发 aibot_subscribe 鉴权、
心跳保活、断线指数退避重连、AES-256-CBC 媒体解密。

本模块只做一件事：把收到的每条消息 normalize 成内部模型并 ingest 落库
（绝不在此调用 LLM——见 ARCHITECTURE.md §四）。客服逐条转发的每条消息是一次
独立回调，各自成为一条 InboxMessage；图文混排(mixed)会被拆成多条（文本 + 图片），
以便图片走多模态提取。分组/提交由人工在后台完成。
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
    """逐条转发丢失原始时间戳，用接收时刻（毫秒）保序（需 BigInteger 列）。"""
    return int(time.time() * 1000)


def _sender(body: dict) -> str | None:
    frm = body.get("from") or {}
    return frm.get("userid") if isinstance(frm, dict) else None


def _safe(fn):
    """包住 handler：单条消息处理失败只记日志，不让异常冒泡到 SDK 的 error 事件。"""

    async def wrapper(frame):  # noqa: ANN001
        try:
            await fn(frame)
        except Exception:  # noqa: BLE001
            log.exception("handler %s failed; frame=%.300s", fn.__name__, frame)

    wrapper.__name__ = fn.__name__
    return wrapper


async def _ingest(msgs: list[NormalizedMessage], from_userid: str | None) -> None:
    msgs = [m for m in msgs if m.msgid]
    if not msgs:
        return
    batch = InboundBatch(channel=CHANNEL, forwarded_by=from_userid, messages=msgs)
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
        WSClientOptions(
            bot_id=settings.wecom_bot_id,
            secret=settings.wecom_bot_secret,
            max_reconnect_attempts=-1,  # 无限重连，永不放弃
            reconnect_interval=2000,
        )
    )

    # 关键：必须注册 "error" 监听。SDK 掉线时 emit("error", ...)，若无监听 pyee 会把异常
    # 重新抛出，打断重连任务 → 机器人变僵尸（进程在但不再连）。这里吃掉并记日志即可。
    def _on_ws_error(err):  # noqa: ANN001
        log.warning("ws error (自动重连继续): %r", err)

    client.on("error", _on_ws_error)

    @client.on("message.text")
    @_safe
    async def _on_text(frame):  # noqa: ANN001
        body = frame.get("body", {}) or {}
        await _ingest(
            [NormalizedMessage(
                msgid=body.get("msgid"), seq=_seq(), type="text",
                content=(body.get("text") or {}).get("content"),
            )],
            _sender(body),
        )

    @client.on("message.image")
    @_safe
    async def _on_image(frame):  # noqa: ANN001
        body = frame.get("body", {}) or {}
        key = await _download(client, body.get("msgid"), body.get("image") or {}, "image")
        await _ingest(
            [NormalizedMessage(msgid=body.get("msgid"), seq=_seq(), type="image", object_key=key)],
            _sender(body),
        )

    @client.on("message.file")
    @_safe
    async def _on_file(frame):  # noqa: ANN001
        body = frame.get("body", {}) or {}
        key = await _download(client, body.get("msgid"), body.get("file") or {}, "file")
        await _ingest(
            [NormalizedMessage(msgid=body.get("msgid"), seq=_seq(), type="file", object_key=key)],
            _sender(body),
        )

    @client.on("message.voice")
    @_safe
    async def _on_voice(frame):  # noqa: ANN001
        body = frame.get("body", {}) or {}
        voice = body.get("voice") or {}
        content = voice.get("content")  # 单聊语音企业微信通常已转写文本
        key = None if content else await _download(client, body.get("msgid"), voice, "voice")
        await _ingest(
            [NormalizedMessage(
                msgid=body.get("msgid"), seq=_seq(), type="voice", content=content, object_key=key
            )],
            _sender(body),
        )

    @client.on("message.mixed")
    @_safe
    async def _on_mixed(frame):  # noqa: ANN001
        # 图文混排 → 拆成多条（文本 + 图片各自成一条），图片走多模态提取。
        # frame 结构：body.mixed.msg_item = [{msgtype, text/image}, ...]
        body = frame.get("body", {}) or {}
        parent = body.get("msgid") or ""
        base = _seq()
        items = (body.get("mixed") or {}).get("msg_item", []) or []
        msgs: list[NormalizedMessage] = []
        for i, it in enumerate(items):
            sub_id = f"{parent}#{i}"
            mtype = it.get("msgtype")
            if mtype == "text":
                msgs.append(NormalizedMessage(
                    msgid=sub_id, seq=base + i, type="text",
                    content=(it.get("text") or {}).get("content"),
                ))
            elif mtype == "image":
                key = await _download(client, sub_id, it.get("image") or {}, "image")
                msgs.append(NormalizedMessage(msgid=sub_id, seq=base + i, type="image", object_key=key))
            else:
                log.info("mixed: skip unhandled sub msgtype=%s", mtype)
        await _ingest(msgs, _sender(body))

    return client
