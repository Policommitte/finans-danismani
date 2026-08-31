"""Bildirim koprusu.

Bu paket bir MAIL ISTEMCISI DEGIL, bir KOPRUDUR: emir olaylari
`notification_outbox` tablosuna yazilir, buradaki `Notifier` uygulamasi da
onlari bir kanaldan cikarir. Kanal su an baglanmamistir (`NoopNotifier`);
SMTP tanimlandiginda `deps.get_notifier()` otomatik olarak `SmtpNotifier`e
gecer ve cagiran hicbir kod degismez.
"""

from app.notifications.base import NotificationMessage, NotificationResult, Notifier

__all__ = ["NotificationMessage", "NotificationResult", "Notifier"]
