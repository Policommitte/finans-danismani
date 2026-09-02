"""Sohbet uclari - konusma listesi, mesaj gecmisi ve SSE akisi.

SSE NEDEN POST?
    Akis, uzun olabilen bir mesaj gövdesi ve `Authorization` header'i
    gerektiriyor. Tarayicinin yerlesik `EventSource` API'si YALNIZCA GET
    destekler ve header gonderemez; bu yuzden frontend `fetch` +
    `ReadableStream` (ya da `@microsoft/fetch-event-source`) kullanmalidir
    (mimari v4 bolum 4.6).
"""

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from app.auth.deps import CurrentUser
from app.core.errors import NotFoundError
from app.repositories.deps import get_chat_repository
from app.schemas.chat import (
    ChatRequest,
    Conversation,
    ConversationsResponse,
    Message,
    MessagesResponse,
)
from app.services import chat as service
from app.services import chat_attachments

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/conversations", response_model=ConversationsResponse)
async def conversations(
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> ConversationsResponse:
    """Kullanicinin sohbetleri (en son guncellenen once)."""
    rows = await get_chat_repository().list_sessions(user["id"], limit=limit)
    return ConversationsResponse(
        items=[
            Conversation(
                id=int(row["id"]),
                title=row["title"],
                created_at=str(row["created_at"]),
                updated_at=str(row["updated_at"]),
                message_count=row.get("message_count"),
            )
            for row in rows
        ]
    )


@router.get("/conversations/{conversation_id}/messages", response_model=MessagesResponse)
async def messages(user: CurrentUser, conversation_id: int) -> MessagesResponse:
    """Bir sohbetin mesajlari.

    SAHIPLIK KONTROLU: baska kullanicinin sohbeti icin 404 doner - 403 demek
    "bu id var ama senin degil" bilgisini sizdirirdi.
    """
    repository = get_chat_repository()

    if await repository.get_session(conversation_id, user["id"]) is None:
        raise NotFoundError("Sohbet bulunamadi.")

    rows = await repository.list_messages(conversation_id)
    return MessagesResponse(
        conversation_id=conversation_id,
        items=[
            Message(
                id=int(row["id"]),
                sender_role=row["sender_role"],
                message_content=row["message_content"],
                meta=row.get("meta") or {},
                created_at=str(row["created_at"]),
            )
            for row in rows
        ],
    )


@router.post("/chat/stream")
async def chat_stream(request: Request, user: CurrentUser, payload: ChatRequest):
    """Sohbet yanitini SSE olarak akitir.

    Olay sozlesmesi: `meta` · `status` · `sources` · `token` · `agent_error` ·
    `error` · `done` (mimari v4 bolum 10.1, `docs/api-sozlesmesi.md`).

    `X-Accel-Buffering: no` header'i ZORUNLU: nginx gibi ters vekiller
    varsayilan olarak yaniti tamponlar ve akis "calismiyor" gibi gorunur -
    token'lar ancak istek bitince topluca gelir.
    """
    request_id = getattr(request.state, "request_id", "")

    # Sohbet cozumu ve SAHIPLIK KONTROLU akis baslamadan once yapilir: bu
    # noktada firlayan hata normal hata sozlesmesine (404/JSON) donusur.
    # Gövde uretilirken firlasaydi durum kodu coktan 200 gonderilmis olurdu.
    session = await service.sohbet_bul_veya_ac(user["id"], payload.conversation_id, payload.message)

    # Ek boyut/format dogrulamasi da AYNI SEBEPLE akis baslamadan once yapilir
    # (422/JSON donmesi icin) - gercek cozme/analiz ek-yolunun icinde olur.
    if payload.attachment is not None:
        chat_attachments.decode_attachment(
            payload.attachment.data_base64, payload.attachment.mime_type, payload.attachment.kind
        )

    olaylar = service.stream_chat_response(
        user_id=user["id"],
        message=payload.message,
        session=session,
        request_id=request_id,
        attachment=payload.attachment,
    )

    async def govde():
        async for event in olaylar:
            yield service.sse_paketle(event)

    return StreamingResponse(
        govde(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-ID": request_id,
        },
    )
