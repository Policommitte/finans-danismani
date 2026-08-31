"""Kanal secimi TEK yerde.

    NOTIFICATIONS_ENABLED=true VE SMTP_HOST dolu  -> SmtpNotifier
    aksi halde                                    -> NoopNotifier

Cagiran kod (dispatcher, servisler, testler) hangisinin secildigini BILMEZ;
hepsi `base.Notifier` protokolune konusur. Mail baglandiginda degisen tek sey
`.env` dosyasidir.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import settings
from app.notifications.base import Notifier
from app.notifications.noop import NoopNotifier

logger = logging.getLogger(__name__)


@lru_cache
def get_notifier() -> Notifier:
    if settings.email_enabled:
        from app.notifications.smtp import SmtpNotifier

        logger.info("bildirim kanali: smtp", extra={"host": settings.smtp_host})
        return SmtpNotifier()

    logger.info("bildirim kanali bagli degil; olaylar outbox'a yazilip SKIPPED kapatilacak")
    return NoopNotifier()


def reset_notifier() -> None:
    """Testler ortam degiskenini degistirdikten sonra cagirir."""
    get_notifier.cache_clear()


def describe_channel() -> str:
    """`/health` ve log icin: hangi kanal bagli?"""
    return "smtp" if settings.email_enabled else "disabled"
