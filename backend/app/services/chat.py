"""Sohbet servisi - orchestrator ile HTTP arasindaki tek koprü.

SORUMLULUK AYRIMI
    Orchestrator DB'ye DOKUNMAZ (mimari v4 bolum 1.1); yalnizca olay uretir.
    Kalicilik, sahiplik kontrolu ve `message_id` uretimi bu servistedir.

AKIS
    1. Sohbet oturumu bulunur ya da acilir (sahiplik kontrolu ile).
    2. Kullanici mesaji kaydedilir.
    3. Orchestrator olaylari akitilir; token'lar biriktirilir.
    4. `done` olayindan HEMEN ONCE asistan mesaji kaydedilir ve olaya
       `message_id` eklenir - frontend mesaji bu id ile kalici hale getirir.

`done` olayi en son gider: mesaj kaydedilmeden gonderilseydi frontend elinde
id olmayan bir mesajla kalirdi.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from app.core.errors import AppError, NotFoundError
from app.engine.factory import get_orchestrator
from app.mcp.context import set_current_user_id, set_request_context
from app.repositories.deps import get_chat_repository
from app.schemas.chat import ChatAttachment
from app.services import chat_attachments

logger = logging.getLogger(__name__)

#: Yeni sohbetin basligi ilk mesajdan uretilir (DB'de VARCHAR(100)).
TITLE_MAX_LENGTH = 60


async def sohbet_bul_veya_ac(user_id: int, conversation_id: int | None, ilk_mesaj: str) -> dict:
    """Var olan sohbeti dogrular ya da yeni bir sohbet acar.

    Sahiplik kontrolu ZORUNLU: baska kullanicinin `conversation_id`'si
    gonderilirse 404 doner (varligini bile dogrulamayiz - "yetkisiz konusma
    erisimi" tehdidi, mimari v4 bolum 11).
    """
    repository = get_chat_repository()

    if conversation_id is not None:
        session = await repository.get_session(conversation_id, user_id)
        if session is None:
            raise NotFoundError("Sohbet bulunamadi.")
        return session

    baslik = ilk_mesaj.strip().splitlines()[0][:TITLE_MAX_LENGTH] or "Yeni Sohbet"
    return await repository.create_session(user_id, baslik)


async def stream_chat_response(
    user_id: int,
    message: str,
    session: dict,
    request_id: str,
    attachment: ChatAttachment | None = None,
) -> AsyncGenerator[dict, None]:
    """Sohbet olaylarini uretir (SSE'ye cevrilmek uzere).

    Donen sozlukler `docs/api-sozlesmesi.md` icindeki SSE sozlesmesine birebir
    karsilik gelir; HTTP katmani yalnizca `data: {json}` sarmasi yapar.

    `session` PARAMETRE olarak alinir, burada acilmaz: sohbet cozumu (ve
    sahiplik kontrolu) akis BASLAMADAN once yapilmalidir. Aksi halde
    `NotFoundError` gövde uretilirken firlar; o noktada HTTP durum kodu 200
    olarak gonderilmis olur ve global hata isleyicisi devreye giremez -
    istemci "404" yerine yarim bir akis gorur.

    `attachment` VARSA cok-ajanli orkestratoru (`get_orchestrator()`) HIC
    CAGIRMAYIZ - bkz. `app/services/chat_attachments.py` modul docstring'i
    (mimari karar). Bunun yerine `_stream_attachment_response` calisir.
    """
    if attachment is not None:
        async for event in _stream_attachment_response(
            user_id, message, session, request_id, attachment
        ):
            yield event
        return

    repository = get_chat_repository()
    thread_id = int(session["id"])

    # MCP tool'lari kimligi ve denetim baglamini buradan okur. SSE gövdesi
    # endpoint'ten SONRA calistigi icin (StreamingResponse) contextvar'lar
    # burada TEKRAR yazilir; aksi halde akis sirasinda bos olabilirler.
    set_current_user_id(user_id)
    set_request_context(request_id=request_id, session_id=thread_id)

    await repository.add_message(
        session_id=thread_id,
        sender_role="user",
        content=message,
        request_id=request_id,
    )

    parcalar: list[str] = []
    kaynaklar: list[dict] = []
    ajan_hatalari: list[dict] = []

    async for event in get_orchestrator().stream_request(
        query=message,
        user_id=user_id,
        thread_id=thread_id,
        request_id=request_id,
    ):
        tur = event.get("type")

        if tur == "token":
            parcalar.append(event.get("content", ""))
        elif tur == "sources":
            kaynaklar = event.get("items") or []
        elif tur == "agent_error":
            ajan_hatalari.append({"agent": event.get("agent"), "type": event.get("error_type")})
        elif tur == "done":
            mesaj = await _asistan_mesajini_kaydet(
                thread_id, "".join(parcalar), kaynaklar, ajan_hatalari, request_id
            )
            if mesaj is not None:
                event = {**event, "message_id": mesaj["id"]}

        yield event


async def _stream_attachment_response(
    user_id: int,
    message: str,
    session: dict,
    request_id: str,
    attachment: ChatAttachment,
) -> AsyncGenerator[dict, None]:
    """Ek'li mesajlar icin basit, TEK PARCA yanit akisi (mimari karar:
    modul docstring'i). Orkestratorun aksine `sources`/`agent_error`
    uretmez - saf model yorumu doner.
    """
    repository = get_chat_repository()
    thread_id = int(session["id"])
    set_current_user_id(user_id)
    set_request_context(request_id=request_id, session_id=thread_id)

    # Orkestratorun kendisi normalde bu olayi ilk yayinlar (bkz.
    # `app/engine/orchestrator.py`) - bu yol orkestratoru atladigi icin
    # kendimiz uretiriz, aksi halde frontend `conversation_id`'yi hic ogrenmez.
    yield {"type": "meta", "request_id": request_id, "conversation_id": thread_id}

    kayit_icerigi = f"[Ek: {attachment.filename}]\n{message}"
    await repository.add_message(
        session_id=thread_id,
        sender_role="user",
        content=kayit_icerigi,
        request_id=request_id,
    )

    yield {"type": "status", "stage": "attachment", "message": "Dosya inceleniyor"}

    try:
        veri = chat_attachments.decode_attachment(
            attachment.data_base64, attachment.mime_type, attachment.kind
        )
        if attachment.kind == "image":
            yanit_metni = await chat_attachments.analyze_image(message, veri, attachment.mime_type)
        elif attachment.mime_type == chat_attachments.SUPPORTED_PDF_MIME_TYPE:
            metin = chat_attachments.extract_pdf_text(veri)
            yanit_metni = await chat_attachments.analyze_document(message, metin)
        else:
            metin = veri.decode("utf-8", errors="replace")
            yanit_metni = await chat_attachments.analyze_document(message, metin)
    except AppError as hata:
        yield {"type": "error", "code": hata.code, "message": hata.message}
        yield {"type": "done", "latency_ms": 0}
        return
    except Exception:  # noqa: BLE001 - beklenmeyen hata akisi cokertmesin
        logger.exception(
            "ek analizi beklenmeyen sekilde basarisiz oldu", extra={"thread_id": thread_id}
        )
        yield {"type": "error", "code": "internal_error", "message": "Beklenmeyen bir hata olustu."}
        yield {"type": "done", "latency_ms": 0}
        return

    yield {"type": "token", "content": yanit_metni}

    mesaj = await _asistan_mesajini_kaydet(thread_id, yanit_metni, [], [], request_id)
    done_event: dict = {"type": "done", "latency_ms": 0}
    if mesaj is not None:
        done_event["message_id"] = mesaj["id"]
    yield done_event


async def _asistan_mesajini_kaydet(
    thread_id: int,
    metin: str,
    kaynaklar: list[dict],
    ajan_hatalari: list[dict],
    request_id: str,
) -> dict | None:
    """Asistan yanitini kaydeder.

    Kayit basarisiz olursa akis DUSMEZ: kullanici yanitini zaten aldi, yalnizca
    gecmise yazilamadi. Hata loglanir ve `message_id` gonderilmez.
    """
    if not metin:
        return None

    try:
        return await get_chat_repository().add_message(
            session_id=thread_id,
            sender_role="assistant",
            content=metin,
            meta={"sources": kaynaklar, "agent_errors": ajan_hatalari},
            request_id=request_id,
        )
    except Exception:  # noqa: BLE001 - kalicilik hatasi yaniti gecersiz kilmaz
        logger.exception("asistan mesaji kaydedilemedi", extra={"thread_id": thread_id})
        return None


def sse_paketle(event: dict) -> str:
    """Olayi SSE cerceve bicimine cevirir.

    `ensure_ascii=False`: Turkce karakterler `\\u00e7` olarak kacilirsa gövde
    sismesinin yani sira loglarda okunmaz hale gelir.
    """
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
