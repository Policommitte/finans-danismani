"""SMTP kanali - mail sistemi baglandiginda devreye giren uygulama.

YENI BAGIMLILIK YOK: standart kutuphanedeki `smtplib` bloklayici oldugu icin
`asyncio.to_thread` ile ayri bir is parcaciginda calistirilir. Bildirim
gonderimi ucu ucuna birkac saniye surebilir; olay dongusunu bloklamasi
fiyat gorevini ve istekleri geciktirirdi.

Bu sinif KENDILIGINDEN SECILMEZ: `deps.get_notifier()` yalnizca
`settings.email_enabled` dogruyken (NOTIFICATIONS_ENABLED=true ve SMTP_HOST
dolu) buna gecer.
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings
from app.notifications.base import NotificationMessage, NotificationResult

logger = logging.getLogger(__name__)


class SmtpNotifier:
    name = "smtp"

    async def send(self, message: NotificationMessage) -> NotificationResult:
        if not message.recipient:
            return NotificationResult.skip("alici adresi yok")
        try:
            await asyncio.to_thread(self._send_sync, message)
        except Exception as exc:  # noqa: BLE001 - gonderim hatasi akisi durdurmamali
            logger.warning(
                "bildirim gonderilemedi",
                extra={"order_id": message.order_id, "hata": f"{type(exc).__name__}: {exc}"},
            )
            return NotificationResult.fail(f"{type(exc).__name__}: {exc}")
        return NotificationResult.ok()

    def _send_sync(self, message: NotificationMessage) -> None:
        mail = EmailMessage()
        mail["From"] = settings.smtp_from
        mail["To"] = message.recipient
        mail["Subject"] = message.subject
        mail.set_content(message.body)

        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=settings.smtp_timeout_seconds,
        ) as server:
            if settings.smtp_starttls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(mail)
