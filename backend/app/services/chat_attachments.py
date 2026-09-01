"""Sohbet ekleri (goersel/dosya) - kod cozme, boyut/format dogrulama ve
yapay zeka analizi.

MIMARI KARAR: ek'li mesajlar CIT-AGENLI ORKESTRATORU (app/engine) ATLAR.
Chatbot'un arkasindaki LangGraph orkestrasyonu portfoy/piyasa arac
cagirabilen karmasik bir sistemdir; ona multimodal girdi ogretmek ciddi bir
mimari degisiklik ve regresyon riski olurdu. Bu yuzden ek'li mesajlar
DOGRUDAN Gemini'ye (metin+gorsel ya da metin+cikarilmis-dosya-metni) gider -
portfoy verisiyle capraz analiz YAPMAZ, sadece yuklenen icerigi yorumlar.

STIL: pexels.py'deki savunmaci yaklasimla tutarli - beklenmedik hatalar
sessizce yutulmaz ama kullaniciya ASLA cig Python istisnasi/500 sizdirilmaz;
her hata AppError alt sinifina (net Turkce mesajla) cevrilir, cagiran taraf
(chat.py) bunu SSE `error` olayina donusturur.
"""

from __future__ import annotations

import base64
import binascii
import logging

from app.config import settings
from app.core.errors import BusinessRuleError, ServiceUnavailableError
from app.core.llm import get_llm_client, saglayici_belirle

logger = logging.getLogger(__name__)

#: Ekler icin ust sinir - hem frontend hem backend tarafinda ayni deger
#: kullanilir (frontend/src/components/chat/AttachmentMenu.tsx).
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024

#: Desteklenen goersel MIME turleri (Gemini'nin dogrudan kabul ettigi
#: bicimler - HEIC/HEIF gibi mobil-ozel bicimler kapsamin disi).
SUPPORTED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

#: Desteklenen "dosya" turleri: PDF (metin cikarimi) + duz metin bicimleri.
#: Word/.docx gibi ikili belge bicimleri KAPSAM DISI (yeni bagimlilik
#: gerektirir, kullanici istekte ozellikle belirtmedi).
SUPPORTED_PLAIN_TEXT_MIME_TYPES = {
    "text/plain",
    "text/csv",
    "text/markdown",
    "application/json",
}
SUPPORTED_PDF_MIME_TYPE = "application/pdf"


def decode_attachment(data_base64: str, mime_type: str, kind: str) -> bytes:
    """Base64 govdeyi cozer; boyut ve format sinirlarini dogrular.

    Basarisizlikta HER ZAMAN `BusinessRuleError` (422, net Turkce mesaj) -
    cagiran taraf akis baslamadan once bunu yakalayip normal HTTP hata
    sozlesmesine cevirir (bkz. routes/chat.py).
    """
    try:
        data = base64.b64decode(data_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BusinessRuleError("Ek dosya okunamadi, lutfen tekrar deneyin.") from exc

    if len(data) == 0:
        raise BusinessRuleError("Ek dosya bos gorunuyor.")

    if len(data) > MAX_ATTACHMENT_BYTES:
        limit_mb = MAX_ATTACHMENT_BYTES // (1024 * 1024)
        raise BusinessRuleError(
            f"Dosya {limit_mb}MB sinirini asiyor, lutfen daha kucuk bir dosya deneyin."
        )

    if kind == "image":
        if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
            raise BusinessRuleError(
                "Desteklenmeyen gorsel formati. JPG, PNG, WEBP veya GIF kullanin."
            )
    elif kind == "file":
        is_pdf = mime_type == SUPPORTED_PDF_MIME_TYPE
        is_plain_text = mime_type in SUPPORTED_PLAIN_TEXT_MIME_TYPES
        if not is_pdf and not is_plain_text:
            raise BusinessRuleError(
                "Desteklenmeyen dosya formati. PDF veya duz metin (txt/csv/md/json) kullanin."
            )
    else:
        raise BusinessRuleError("Gecersiz ek turu.")

    return data


def extract_pdf_text(data: bytes) -> str:
    """PDF'ten metni cikarir; okunamazsa net Turkce hatayla `BusinessRuleError`."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - kurulum eksikse acikca soyle
        raise ServiceUnavailableError("PDF okuma bilesenleri yuklu degil.") from exc

    try:
        import io

        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise BusinessRuleError("Sifreli PDF dosyalari desteklenmiyor.")
        sayfalar = [sayfa.extract_text() or "" for sayfa in reader.pages]
    except BusinessRuleError:
        raise
    except (
        Exception
    ) as exc:  # noqa: BLE001 - pypdf cesitli hatalar firlatabilir (PdfReadError dahil)
        logger.warning("pdf metni cikarilamadi", extra={"hata": f"{type(exc).__name__}: {exc}"})
        raise BusinessRuleError(
            "PDF dosyasi okunamadi, dosyanin bozuk olmadigindan emin olun."
        ) from exc

    metin = "\n".join(sayfa.strip() for sayfa in sayfalar if sayfa.strip())
    if not metin:
        raise BusinessRuleError(
            "PDF icinde okunabilir metin bulunamadi (taranmis goersel olabilir)."
        )
    return metin


#: Prompt'a eklenecek metnin ust siniri - cok uzun belgeler LLM baglam
#: penceresini tasirmasin diye kirpilir; kullaniciya bu ACIKCA belirtilir.
MAX_DOCUMENT_CHARS = 20_000


async def analyze_image(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    """Goersel + soru -> Gemini yaniti.

    Yalnizca Gemini saglayicisinda calisir: coğu NIM (NVIDIA NIM) modeli
    goersel destegi garanti etmiyor, bu yuzden nazikce reddedilir (sessizce
    yanlis/uydurma bir yanit URETMEK yerine).
    """
    model = settings.model_for("synthesizer")
    if not model:
        raise ServiceUnavailableError(
            "Yapay zeka modeli yapilandirilmamis, gorsel analizi su an kullanilamiyor."
        )

    if saglayici_belirle(model) != "gemini":
        raise BusinessRuleError(
            "Gorsel analizi su an yalnizca Gemini modeliyle calisiyor; "
            "yapilandirilmis model gorsel desteklemiyor."
        )

    client = get_llm_client("synthesizer")
    if client is None or not hasattr(client, "generate_with_image"):
        raise ServiceUnavailableError(
            "Yapay zeka modeli yapilandirilmamis, gorsel analizi su an kullanilamiyor."
        )

    try:
        return await client.generate_with_image(prompt, image_bytes, mime_type)
    except Exception as exc:  # noqa: BLE001 - saglayici SDK'sina bagli cesitli hatalar
        logger.warning("gorsel analizi basarisiz", extra={"hata": f"{type(exc).__name__}: {exc}"})
        raise ServiceUnavailableError(
            "Gorsel analiz edilirken bir sorun olustu, lutfen tekrar deneyin."
        ) from exc


async def analyze_document(prompt: str, extracted_text: str) -> str:
    """Belgeden cikarilan metin + soru -> LLM yaniti (herhangi bir saglayicida calisir)."""
    model = settings.model_for("synthesizer")
    if not model:
        raise ServiceUnavailableError(
            "Yapay zeka modeli yapilandirilmamis, dosya analizi su an kullanilamiyor."
        )

    client = get_llm_client("synthesizer")
    if client is None:
        raise ServiceUnavailableError(
            "Yapay zeka modeli yapilandirilmamis, dosya analizi su an kullanilamiyor."
        )

    kirpildi = len(extracted_text) > MAX_DOCUMENT_CHARS
    metin = extracted_text[:MAX_DOCUMENT_CHARS]
    not_ek = "\n\n[Not: belge uzun oldugu icin sadece ilk bolumu okundu.]" if kirpildi else ""

    tam_prompt = (
        f"Kullanicinin yukledigi belgenin icerigi:\n---\n{metin}\n---{not_ek}\n\n"
        f"Kullanicinin sorusu: {prompt}"
    )

    try:
        return await client.generate(tam_prompt)
    except Exception as exc:  # noqa: BLE001 - saglayici SDK'sina bagli cesitli hatalar
        logger.warning("dosya analizi basarisiz", extra={"hata": f"{type(exc).__name__}: {exc}"})
        raise ServiceUnavailableError(
            "Dosya analiz edilirken bir sorun olustu, lutfen tekrar deneyin."
        ) from exc
