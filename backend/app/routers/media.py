"""按消息 id 读取媒体（图片/文件），供后台收件箱预览/打开。

不直接暴露存储 key，按 InboxMessage.id 查出 object_key 再流式返回。
"""

import mimetypes
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.db import get_session
from app.storage import storage

router = APIRouter(prefix="/media", tags=["media"])


def _serve(object_key: str) -> Response:
    try:
        data = storage.load(object_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(404, f"media not found in storage: {exc}") from exc
    filename = object_key.rsplit("/", 1)[-1]
    media_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    ascii_fallback = filename.encode("ascii", "ignore").decode() or "file"
    disposition = f"inline; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"
    return Response(content=data, media_type=media_type, headers={"Content-Disposition": disposition})


@router.get("/by-key")
async def get_media_by_key(key: str):
    """按存储 key 取媒体（供编辑器给菜品配图预览用）。"""
    return _serve(key)


@router.get("/{message_id}")
async def get_media(message_id: int, session: AsyncSession = Depends(get_session)):
    msg = await session.get(models.InboxMessage, message_id)
    if msg is None or not msg.object_key:
        raise HTTPException(404, "no media for this message")
    return _serve(msg.object_key)
