# -*- coding: utf-8 -*-
"""Sohbet eki (PDF/Excel/gorsel) boru hatti testleri.

⚠️ `db` ISARETI KULLANILMAZ - kullanicinin `backend/.env` dosyasi PAYLASILAN
Supabase'e baglidir (`settings.database_url` dolu); bu dosyadaki testler
`get_chat_repository`/`get_orchestrator`'i SAHTE nesnelerle degistirir ki
gercek veritabanina TEK SATIR bile yazilmasin.
"""

from __future__ import annotations

import base64
import time

import pytest

from app.core.errors import BusinessRuleError, NotFoundError
from app.repositories.in_memory import InMemoryChatRepository
from app.schemas.chat import ChatAttachment
from app.services import chat as chat_service
from app.services import report_cache


def _ek(dosya_adi: str, icerik: bytes = b"x", kind: str = "file") -> ChatAttachment:
    return ChatAttachment(
        kind=kind,
        filename=dosya_adi,
        mime_type="application/octet-stream",
        data_base64=base64.b64encode(icerik).decode("ascii"),
    )


# ---------------------------------------------------------------------------
# decode_attachment - boyut/format dogrulamasi
# ---------------------------------------------------------------------------


def test_pdf_ve_excel_kabul_edilir():
    """Efe'nin `chat_attachments.decode_attachment`'inda Excel YOKTU - bizim
    boru hattimiz destekliyor, bu regresyonu korur."""
    assert chat_service.decode_attachment(_ek("rapor.pdf")) == b"x"
    assert chat_service.decode_attachment(_ek("bilanco.xlsx")) == b"x"
    assert chat_service.decode_attachment(_ek("makro.xlsm")) == b"x"


def test_legacy_xls_format_rejected():
    """openpyxl BIFF (.xls) okuyamaz; kabul edip sonra "acilamadi" demek
    yerine kapida reddedilir (bkz. parser.EXCEL_UZANTILARI notu)."""
    with pytest.raises(BusinessRuleError):
        chat_service.decode_attachment(_ek("eski.xls"))


def test_desteklenmeyen_uzanti_reddedilir():
    with pytest.raises(BusinessRuleError):
        chat_service.decode_attachment(_ek("belge.docx"))


def test_bozuk_base64_reddedilir():
    ek = ChatAttachment(
        kind="file", filename="a.pdf", mime_type="application/pdf", data_base64="!!!gecersiz!!!"
    )
    with pytest.raises(BusinessRuleError):
        chat_service.decode_attachment(ek)


def test_bos_dosya_reddedilir():
    ek = ChatAttachment(kind="file", filename="a.pdf", mime_type="application/pdf", data_base64="")
    with pytest.raises(BusinessRuleError):
        chat_service.decode_attachment(ek)


def test_azami_boyutu_asan_dosya_reddedilir(monkeypatch):
    monkeypatch.setattr(chat_service.settings, "document_max_upload_mb", 1)
    buyuk = b"a" * (2 * 1024 * 1024)
    with pytest.raises(BusinessRuleError):
        chat_service.decode_attachment(_ek("buyuk.pdf", buyuk))


# ---------------------------------------------------------------------------
# report_cache
# ---------------------------------------------------------------------------


def test_rapor_onbellegi_yaz_oku():
    report_cache.kaydet("msg-1", b"%PDF-baytlari", "rapor.pdf")

    kayit = report_cache.al("msg-1")

    assert kayit == (b"%PDF-baytlari", "rapor.pdf")


def test_rapor_onbellegi_olmayan_anahtar_none_doner():
    assert report_cache.al("hic-yok-12345") is None


def test_rapor_onbellegi_suresi_dolan_kayit_silinir(monkeypatch):
    monkeypatch.setattr(report_cache, "AZAMI_OMUR_SANIYE", 0.05)
    report_cache.kaydet("msg-suresi-dolan", b"x", "a.pdf")

    time.sleep(0.1)

    assert report_cache.al("msg-suresi-dolan") is None


def test_rapor_onbellegi_fifo_tahliye(monkeypatch):
    monkeypatch.setattr(report_cache, "AZAMI_KAYIT", 2)
    report_cache.kaydet("fifo-1", b"1", "a.pdf")
    report_cache.kaydet("fifo-2", b"2", "b.pdf")
    report_cache.kaydet("fifo-3", b"3", "c.pdf")  # fifo-1'i tahliye etmeli

    assert report_cache.al("fifo-1") is None
    assert report_cache.al("fifo-2") is not None
    assert report_cache.al("fifo-3") is not None


# ---------------------------------------------------------------------------
# InMemoryChatRepository.message_owner_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mesaj_sahibi_dogru_donuyor():
    repo = InMemoryChatRepository()
    oturum = await repo.create_session(user_id=7, title="Test")
    mesaj = await repo.add_message(session_id=oturum["id"], sender_role="user", content="merhaba")

    assert await repo.message_owner_id(mesaj["id"]) == 7


@pytest.mark.asyncio
async def test_olmayan_mesajin_sahibi_none():
    repo = InMemoryChatRepository()
    assert await repo.message_owner_id(999999) is None


# ---------------------------------------------------------------------------
# stream_chat_response - ekli mesaj ORKESTRATORE gider, PDF baytlari SSE'ye
# SIZMAZ (regresyon korumasi)
# ---------------------------------------------------------------------------


class _SahteOrchestrator:
    """`stream_request`in belge/PDF ureten kismini taklit eder."""

    def __init__(self, pdf_bytes: bytes | None = b"%PDF-sahte-rapor"):
        self.son_cagri_kwargs: dict | None = None
        self._pdf_bytes = pdf_bytes

    async def stream_request(self, **kwargs):
        self.son_cagri_kwargs = kwargs
        yield {"type": "meta", "request_id": "r1", "conversation_id": 1}
        yield {"type": "token", "content": "Rapor hazirlandi."}
        bitis = {"type": "done", "latency_ms": 12.3}
        if self._pdf_bytes is not None:
            bitis["rapor"] = {"dosya_adi": "analiz_raporu.pdf", "boyut": len(self._pdf_bytes)}
            bitis["_dahili_pdf_bytes"] = self._pdf_bytes
        yield bitis


@pytest.fixture
def sahte_repo(monkeypatch):
    """`get_chat_repository`'yi bellek ici, GERCEK-DB-DOKUNMAYAN bir ornekle degistirir.

    ⚠️ IKI AYRI BAGLAMA YAMALANIR: `app.services.chat` VE
    `app.api.routes.chat` ayni fonksiyonu KENDI isim uzaylarina ayri ayri
    import eder (`from ... import get_chat_repository`); birini yamalamak
    digerini ETKILEMEZ.
    """
    from app.api.routes import chat as chat_route

    repo = InMemoryChatRepository()
    monkeypatch.setattr(chat_service, "get_chat_repository", lambda: repo)
    monkeypatch.setattr(chat_route, "get_chat_repository", lambda: repo)
    return repo


@pytest.mark.asyncio
async def test_ekli_mesaj_orkestratore_belge_parametresiyle_gider(sahte_repo, monkeypatch):
    """Efe'nin mimarisi orkestratoru ATLIYORDU - bizimki ATLAMAMALI."""
    sahte = _SahteOrchestrator()
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    session = await sahte_repo.create_session(user_id=1, title="Test")
    olaylar = [
        e
        async for e in chat_service.stream_chat_response(
            user_id=1,
            message="Bu dosyayı analiz et.",
            session=session,
            request_id="req-1",
            attachment=_ek("rapor.pdf", b"%PDF-1-4"),
        )
    ]

    assert sahte.son_cagri_kwargs["belge"] == {
        "dosya_adi": "rapor.pdf",
        "icerik": b"%PDF-1-4",
    }
    assert olaylar[0]["type"] == "meta"
    assert olaylar[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_pdf_baytlari_sse_olayina_hic_sizmaz(sahte_repo, monkeypatch):
    """REGRESYON KORUMASI - EN KRITIK TEST.

    `_dahili_pdf_bytes` orchestrator.py icinde BILEREK eklenir ve
    `stream_chat_response` tarafindan POPLANMASI gerekir; sizarsa ikili
    icerik JSON'a gomulup istemciye/SSE'ye gider.
    """
    sahte = _SahteOrchestrator(pdf_bytes=b"\x89PNG-degil-ama-binary-gibi-davransin")
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    session = await sahte_repo.create_session(user_id=1, title="Test")
    olaylar = [
        e
        async for e in chat_service.stream_chat_response(
            user_id=1,
            message="analiz et",
            session=session,
            request_id="req-2",
            attachment=_ek("veri.xlsx"),
        )
    ]

    bitis = olaylar[-1]
    assert "_dahili_pdf_bytes" not in bitis
    assert bitis["rapor"]["dosya_adi"] == "analiz_raporu.pdf"
    assert bitis["message_id"] is not None


@pytest.mark.asyncio
async def test_pdf_uretilince_onbellege_yazilir_ve_sahiple_eslesir(sahte_repo, monkeypatch):
    sahte = _SahteOrchestrator(pdf_bytes=b"%PDF-icerik")
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    session = await sahte_repo.create_session(user_id=42, title="Test")
    olaylar = [
        e
        async for e in chat_service.stream_chat_response(
            user_id=42,
            message="analiz et",
            session=session,
            request_id="req-3",
            attachment=_ek("bilanco.xlsx"),
        )
    ]

    message_id = olaylar[-1]["message_id"]
    kayit = report_cache.al(str(message_id))
    assert kayit == (b"%PDF-icerik", "analiz_raporu.pdf")
    # Sahiplik: mesaj GERCEKTEN kullanici 42'ye ait mi?
    assert await sahte_repo.message_owner_id(message_id) == 42


@pytest.mark.asyncio
async def test_belgesiz_mesaj_orkestratore_belge_none_gonderir(sahte_repo, monkeypatch):
    """Ek YOKSA `belge=None` gitmeli - eski davranis (belgesiz sohbet) BOZULMAMALI."""
    sahte = _SahteOrchestrator(pdf_bytes=None)
    monkeypatch.setattr(chat_service, "get_orchestrator", lambda: sahte)

    session = await sahte_repo.create_session(user_id=1, title="Test")
    async for _ in chat_service.stream_chat_response(
        user_id=1, message="merhaba", session=session, request_id="req-4"
    ):
        pass

    assert sahte.son_cagri_kwargs["belge"] is None


# ---------------------------------------------------------------------------
# Rapor indirme ucu - sahiplik kontrolu (route katmani)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_indirme_ucu_baska_kullanicinin_raporunu_reddeder(sahte_repo):
    """`message_owner_id` baska kullaniciya aitse indirme ucu 404 URETMELI.

    Route fonksiyonunu (`app.api.routes.chat.chat_report`) DOGRUDAN cagirir -
    TestClient uzerinden gitmek `CurrentUser` icin gercek JWT + gercek DB
    baglama akisini de tetikler; burada yalnizca sahiplik mantigi test edilir.
    """
    from app.api.routes.chat import chat_report

    session = await sahte_repo.create_session(user_id=1, title="Test")
    mesaj = await sahte_repo.add_message(
        session_id=session["id"], sender_role="assistant", content="x"
    )
    report_cache.kaydet(str(mesaj["id"]), b"%PDF-gizli", "gizli.pdf")

    with pytest.raises(NotFoundError):
        await chat_report(user={"id": 999}, message_id=mesaj["id"])


@pytest.mark.asyncio
async def test_indirme_ucu_sahibine_pdf_doner(sahte_repo):
    from app.api.routes.chat import chat_report

    session = await sahte_repo.create_session(user_id=5, title="Test")
    mesaj = await sahte_repo.add_message(
        session_id=session["id"], sender_role="assistant", content="x"
    )
    report_cache.kaydet(str(mesaj["id"]), b"%PDF-gercek-sahip", "rapor.pdf")

    yanit = await chat_report(user={"id": 5}, message_id=mesaj["id"])

    assert yanit.body == b"%PDF-gercek-sahip"
    assert yanit.media_type == "application/pdf"
    assert "rapor.pdf" in yanit.headers["content-disposition"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "turkce_dosya_adi",
    [
        "Dijital Hesap Cüzdanı_analiz_raporu.pdf",  # canlida BIREBIR yasandi
        "alışsatış_analiz_raporu.pdf",  # canlida BIREBIR yasandi
        "Şirket Bilançosu Özeti.pdf",
        "İşlem Geçmişi.pdf",
    ],
)
async def test_indirme_ucu_turkce_dosya_adiyla_cokmez(sahte_repo, turkce_dosya_adi):
    """REGRESYON KORUMASI - canli hata.

    `dosya_adi` icin HTTP basligi kurulurken `Response.init_headers`
    degeri Latin-1'e kodluyor. Noktasiz Turkce 'ı' (U+0131) Latin-1
    araliginin (0-255) DISINDA - duz `filename="{ad}"` yazmak
    `UnicodeEncodeError` firlatiyordu ve bu istisna Response NESNESI
    olusurken (ilk bayt istemciye gitmeden) patladigi icin tarayici
    bunu duzgun bir HTTP hatasi degil, ham "Failed to fetch" ag hatasi
    olarak goruyordu. Eski testler yalnizca ASCII-guvenli "rapor.pdf"
    kullaniyordu, bu yuzden bu sinif hic yakalanmamisti.
    """
    from app.api.routes.chat import chat_report

    session = await sahte_repo.create_session(user_id=1, title="Test")
    mesaj = await sahte_repo.add_message(
        session_id=session["id"], sender_role="assistant", content="x"
    )
    report_cache.kaydet(str(mesaj["id"]), b"%PDF-turkce", turkce_dosya_adi)

    yanit = await chat_report(user={"id": 1}, message_id=mesaj["id"])

    # Asil kanit: baslik GERCEKTEN Latin-1'e kodlanabiliyor mu? Starlette
    # tam olarak bunu yapiyor; burada patlarsa test de coker.
    for anahtar, deger in yanit.raw_headers:
        anahtar.decode("latin-1")
        deger.decode("latin-1")

    baslik = yanit.headers["content-disposition"]
    assert baslik.startswith("attachment;")
    # `filename*=UTF-8''...` GERCEK adi yuzde-kodlu tasimali - modern
    # tarayicilarin gosterecegi/indirecegi isim budur.
    assert "filename*=UTF-8''" in baslik
    from urllib.parse import unquote

    yuzde_kismi = baslik.split("filename*=UTF-8''", 1)[1]
    assert unquote(yuzde_kismi) == turkce_dosya_adi


def test_content_disposition_ascii_yedek_tirnak_icermez():
    """ASCII yedek alaninda kacmamis bir `"` HTTP basligini bozardi."""
    from app.api.routes.chat import _content_disposition

    baslik = _content_disposition('kötü"ad.pdf')

    # `filename="..."` degerini SARAN tirnaklar HARIC, iceride kacmamis
    # bir `"` kalmamali - kalsaydi baslik erken kapanir, geri kalani
    # (orn. `; filename*=...`) deger olarak sizardi.
    ascii_deger = baslik.split(";")[1].split("=", 1)[1].strip()
    assert ascii_deger.startswith('"') and ascii_deger.endswith('"')
    assert '"' not in ascii_deger[1:-1]
