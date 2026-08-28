"""Baglanmamis kanal - varsayilan.

Mail sistemi henuz bagli degil. Bu uygulama bildirimi URETIR ve LOGLAR ama
hicbir yere gondermez; outbox satiri SKIPPED olarak kapanir.

NEDEN PENDING BIRAKILMIYOR: kanal haftalar sonra acildiginda birikmis tum
gecmis bildirimler tek seferde kullaniciya giderdi. Satiri kapatmak, olay
kaydini korurken bu riski ortadan kaldirir.
"""

from __future__ import annotations

import logging

from app.notifications.base import NotificationMessage, NotificationResult

logger = logging.getLogger(__name__)


class NoopNotifier:
    name = "noop"

    async def send(self, message: NotificationMessage) -> NotificationResult:
        logger.info(
            "bildirim uretildi ama kanal bagli degil",
            extra={
                "event_type": message.event_type,
                "order_id": message.order_id,
                "subject": message.subject,
            },
        )
        return NotificationResult.skip("bildirim kanali bagli degil")
