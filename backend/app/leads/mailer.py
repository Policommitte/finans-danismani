"""Gmail SMTP uzerinden lead mail gonderimi.

Sadece STDLIB kullanir (`smtplib`, `email`) - yeni bagimlilik gerekmez.

`GMAIL_SENDER_EMAIL` / `GMAIL_APP_PASSWORD` bos oldugu surece hicbir mail
GONDERILMEZ ve istisna FIRLATILMAZ - `SKIPPED` doner, uygulama calismaya
devam eder. Ayni felsefe: `LLM_API_KEY` / `EMBEDDING_MODEL`.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger(__name__)

#: Konu satiri - icerik henuz onemli degil, urun sahibi sonra netlestirecek.
KONU = "[TASLAK] Yatırım danışmanlığı görüşmesi"


def is_configured() -> bool:
    """Gmail gonderimi icin gerekli iki alan da dolu mu?"""
    return bool(settings.gmail_sender_email.strip() and settings.gmail_app_password.strip())


async def send_lead_email(to_email: str, first_name: str) -> dict:
    """Bir lead'e mail gonderir; sonucu asla istisna olarak FIRLATMAZ.

    Returns:
        {"status": "SENT"|"SKIPPED"|"FAILED", "to_email": str,
         "subject": str, "error": str|None}
    """
    if not is_configured():
        logger.warning("Gmail ayarlari bos; mail gonderilmedi (SKIPPED)", extra={"to": to_email})
        return {"status": "SKIPPED", "to_email": to_email, "subject": KONU, "error": None}

    # Seed kullanicilarinin adresleri @example.com (teslim edilemez, ayrilmis
    # alan adi) - redirect ayarliysa gercek RCPT bu adres olur.
    gercek_alici = settings.lead_email_redirect_to.strip() or to_email
    mesaj = _mesaj_olustur(gercek_alici, first_name, orijinal_alici=to_email)

    try:
        # smtplib BLOKLAYICI - event loop'u kilitlememesi icin ayri thread'de.
        await asyncio.to_thread(_gonder_sync, mesaj)
    except Exception as exc:  # noqa: BLE001 - gonderim hatasi akisi durdurmamali
        logger.exception("Lead maili gonderilemedi", extra={"to": gercek_alici})
        return {
            "status": "FAILED",
            "to_email": gercek_alici,
            "subject": KONU,
            "error": f"{type(exc).__name__}: {exc}",
        }

    return {"status": "SENT", "to_email": gercek_alici, "subject": KONU, "error": None}


def _mesaj_olustur(to_email: str, first_name: str, orijinal_alici: str) -> EmailMessage:
    mesaj = EmailMessage()
    mesaj["From"] = settings.gmail_sender_email
    mesaj["To"] = to_email
    mesaj["Subject"] = KONU

    govde = (
        f"Merhaba {first_name},\n\n"
        "Portföyünüzü değerlendirdik ve sizin için uygun olabilecek bir "
        "yatırım danışmanlığı fırsatımız var. Detaylar için bizimle "
        "iletişime geçebilirsiniz.\n\n"
        "Bu bir taslak mesajdır, içerik ürün ekibi tarafından "
        "netleştirilecektir.\n"
    )
    if orijinal_alici != to_email:
        govde += f"\n(asıl alıcı: {orijinal_alici})\n"

    mesaj.set_content(govde)
    return mesaj


def _gonder_sync(mesaj: EmailMessage) -> None:
    baglam = ssl.create_default_context()
    with smtplib.SMTP_SSL(
        settings.gmail_smtp_host,
        settings.gmail_smtp_port,
        context=baglam,
        timeout=settings.gmail_timeout_seconds,
    ) as sunucu:
        sunucu.login(settings.gmail_sender_email, settings.gmail_app_password)
        sunucu.send_message(mesaj)