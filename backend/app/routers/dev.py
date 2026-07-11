"""开发/联调用：在没有企业微信凭证时，模拟一次入站，走通后续管线。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.base import InboundBatch, NormalizedMessage
from app.db import get_session
from app.schemas import InboxMessageOut, SimulateInboundRequest
from app.services import ingest_batch

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/simulate-inbound", response_model=list[InboxMessageOut])
async def simulate_inbound(
    body: SimulateInboundRequest,
    session: AsyncSession = Depends(get_session),
):
    batch = InboundBatch(
        channel=body.channel,
        forwarded_by=body.forwarded_by,
        messages=[
            NormalizedMessage(
                msgid=m.msgid, seq=m.seq, type=m.type, content=m.content, object_key=m.object_key
            )
            for m in body.messages
        ],
    )
    return await ingest_batch(session, batch)
