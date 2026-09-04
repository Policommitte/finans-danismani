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

import base64
import binascii
import json
import logging
import random
import uuid
from collections.abc import AsyncGenerator

from app.config import settings
from app.core.errors import BusinessRuleError, NotFoundError
from app.documents.parser import BelgeAyristirmaHatasi, belge_turu
from app.engine.factory import get_orchestrator
from app.mcp.context import set_current_user_id, set_request_context
from app.repositories.deps import get_chat_repository
from app.schemas.chat import ChatAttachment
from app.services import report_cache

logger = logging.getLogger(__name__)

#: Yeni sohbetin basligi ilk mesajdan uretilir (DB'de VARCHAR(100)).
TITLE_MAX_LENGTH = 60


async def find_or_open_conversation(
    user_id: int, conversation_id: int | None, ilk_mesaj: str
) -> dict:
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


def decode_attachment(attachment: ChatAttachment) -> bytes:
    """Ek'in base64 govdesini cozer; boyut/format sinirlarini dogrular.

    Akis BASLAMADAN ONCE cagrilmasi ZORUNLUDUR (routes/chat.py): boylece
    bozuk/asiri buyuk/desteklenmeyen bir dosya 422 JSON hatasi olarak doner,
    yarim bir SSE akisi degil.

    NOT: format kontrolu `app.documents.parser.belge_turu()` uzerinden
    yapilir - yani PDF/Excel/gorsel destegi TEK bir yerde (parser modulu)
    tanimlidir; burada ayri bir MIME beyaz listesi TUTULMAZ, ikisi
    birbirinden sapabilirdi.
    """
    try:
        veri = base64.b64decode(attachment.data_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BusinessRuleError("Ek dosya okunamadi, lutfen tekrar deneyin.") from exc

    if len(veri) == 0:
        raise BusinessRuleError("Ek dosya bos gorunuyor.")

    azami_bayt = settings.document_max_upload_mb * 1024 * 1024
    if len(veri) > azami_bayt:
        raise BusinessRuleError(
            f"Dosya {settings.document_max_upload_mb}MB sinirini asiyor, "
            "lutfen daha kucuk bir dosya deneyin."
        )

    try:
        belge_turu(attachment.filename)
    except BelgeAyristirmaHatasi as exc:
        raise BusinessRuleError(str(exc)) from exc

    return veri


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

    `attachment` VARSA orkestratore `belge=` olarak GECER - bypass YAPILMAZ.
    Boylece `route_node` (`app/engine/orchestrator.py`) ekli dosyayi gorup
    `document_analysis` ajanini kosulsuz calistirir; ayni ajan katmani,
    ayni guvenlik kapisi, ayni sentez akisi - iki farkli "sohbet motoru"
    olusmaz.
    """
    repository = get_chat_repository()
    thread_id = int(session["id"])

    # MCP tool'lari kimligi ve denetim baglamini buradan okur. SSE gövdesi
    # endpoint'ten SONRA calistigi icin (StreamingResponse) contextvar'lar
    # burada TEKRAR yazilir; aksi halde akis sirasinda bos olabilirler.
    set_current_user_id(user_id)
    set_request_context(request_id=request_id, session_id=thread_id)

    kayit_icerigi = f"[Ek: {attachment.filename}]\n{message}" if attachment else message
    await repository.add_message(
        session_id=thread_id,
        sender_role="user",
        content=kayit_icerigi,
        request_id=request_id,
    )

    belge_govdesi = None
    if attachment is not None:
        # Boyut/format DOGRULAMASI routes/chat.py'de akis baslamadan once
        # zaten yapildi; burada YALNIZCA cozme tekrarlanir (govde bu katmana
        # kadar tasinmaz, request/response sinirini asmamak icin).
        belge_govdesi = {
            "dosya_adi": attachment.filename,
            "icerik": decode_attachment(attachment),
        }

    parcalar: list[str] = []
    kaynaklar: list[dict] = []
    ajan_hatalari: list[dict] = []

    async for event in get_orchestrator().stream_request(
        query=message,
        user_id=user_id,
        thread_id=thread_id,
        request_id=request_id,
        belge=belge_govdesi,
    ):
        tur = event.get("type")

        if tur == "token":
            parcalar.append(event.get("content", ""))
        elif tur == "sources":
            kaynaklar = event.get("items") or []
        elif tur == "agent_error":
            ajan_hatalari.append({"agent": event.get("agent"), "type": event.get("error_type")})
        elif tur == "done":
            # `_dahili_pdf_bytes`: SSE'ye ASLA gitmemeli (bkz. orchestrator.py
            # yorumu) - onbellege yazilir yazilmaz olaydan POPLANIR.
            pdf_baytlari = event.pop("_dahili_pdf_bytes", None)

            mesaj = await _save_assistant_message(
                thread_id,
                "".join(parcalar),
                kaynaklar,
                ajan_hatalari,
                request_id,
                mentioned_assets=event.get("mentioned_assets") or [],
            )
            if mesaj is not None:
                event = {**event, "message_id": mesaj["id"]}
                if pdf_baytlari:
                    # Anahtar message_id: indirme ucu (`GET
                    # /api/chat/reports/{message_id}`) ayni id'yi kullanir.
                    report_cache.kaydet(
                        str(mesaj["id"]),
                        pdf_baytlari,
                        (event.get("rapor") or {}).get("dosya_adi", "rapor.pdf"),
                    )
            elif "rapor" in event:
                # Mesaj kaydedilemediyse (bkz. _save_assistant_message)
                # indirme anahtari (message_id) HIC olusmayacak - metadata'yi
                # de gonderme, aksi halde frontend kirik bir indirme
                # baglantisi cizer.
                event.pop("rapor", None)

        yield event


async def stream_quick_analysis(user_id: int, symbol: str) -> AsyncGenerator[dict, None]:
    """Varlik kartindaki "Polifin AI Analizi" kutusu icin TEK SEFERLIK,
    KALICI OLMAYAN bir orkestrator cagrisi.

    ⚠️ `stream_chat_response`'TAN BILEREK FARKLI: hicbir chat_sessions/
    chat_messages satiri YAZMAZ. Onceki davranista varlik kartı acilinca
    `ChatContext` (widget/kart arasinda PAYLASIMLI) uzerinden GERCEK bir
    sohbet mesaji gonderiliyordu - kullanici hic yazmadigi "X hakkinda
    kisa bir yatirim analizi yap" sorusunu, dakikalar sonra sohbet
    penceresini actiginda kendi gecmisinde goruyordu. Bu fonksiyon ayni
    orkestratoru, kalici bir sohbet OTURUMU ACMADAN dogrudan cagirir.

    `thread_id` NEGATIF ve rastgele secilir: gercek `chat_sessions.id`
    degerleri (Postgres serial) HER ZAMAN pozitiftir, yani bu deger hicbir
    gercek oturumla CAKISAMAZ - LangGraph'in bellek ici checkpointer'i
    (MemorySaver) bu sayede ne gercek bir konusmanin durumunu okur ne de
    ona yazar.
    """
    request_id = str(uuid.uuid4())
    thread_id = -random.randint(1, 2_000_000_000)

    # MCP tool'lari kimligi buradan okur (bkz. stream_chat_response'daki ayni
    # notlar) - SSE gövdesi endpoint'ten SONRA calisir, contextvar'lar burada
    # TEKRAR yazilmali.
    set_current_user_id(user_id)
    set_request_context(request_id=request_id, session_id=thread_id)

    async for event in get_orchestrator().stream_request(
        query=f"{symbol} hakkında kısa bir yatırım analizi yap.",
        user_id=user_id,
        thread_id=thread_id,
        request_id=request_id,
    ):
        yield event


async def _save_assistant_message(
    thread_id: int,
    metin: str,
    kaynaklar: list[dict],
    ajan_hatalari: list[dict],
    request_id: str,
    mentioned_assets: list[str] | None = None,
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
            meta={
                "sources": kaynaklar,
                "agent_errors": ajan_hatalari,
                "mentioned_assets": mentioned_assets or [],
            },
            request_id=request_id,
        )
    except Exception:  # noqa: BLE001 - kalicilik hatasi yaniti gecersiz kilmaz
        logger.exception("asistan mesaji kaydedilemedi", extra={"thread_id": thread_id})
        return None


def format_sse(event: dict) -> str:
    """Olayi SSE cerceve bicimine cevirir.

    `ensure_ascii=False`: Turkce karakterler `\\u00e7` olarak kacilirsa gövde
    sismesinin yani sira loglarda okunmaz hale gelir.
    """
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
