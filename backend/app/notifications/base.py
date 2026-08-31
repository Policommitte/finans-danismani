"""Bildirim kanali sozlesmesi (Protocol) ve tasinan veri tipleri."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class NotificationMessage:
    """Kanaldan cikacak tek bir bildirim."""

    recipient: str
    subject: str
    body: str
    event_type: str
    order_id: int | None = None


@dataclass(frozen=True)
class NotificationResult:
    """Gonderim sonucu.

    UC durum bilincli olarak ayrilir; outbox'ta uc farkli statuye yazilirlar:

        sent=True                -> SENT     (kanaldan cikti)
        skipped=True             -> SKIPPED  (bilincli gonderilmedi; HATA DEGIL)
        ikisi de False           -> FAILED   (kanal acikti, gonderim patladi)

    "Kanal kapali" ile "gonderim basarisiz" ayrimi onemli: ilkinde tekrar
    denemek anlamsizdir, ikincisinde anlamlidir.
    """

    sent: bool
    skipped: bool = False
    detail: str | None = None

    @classmethod
    def ok(cls, detail: str | None = None) -> NotificationResult:
        return cls(sent=True, skipped=False, detail=detail)

    @classmethod
    def skip(cls, reason: str) -> NotificationResult:
        return cls(sent=False, skipped=True, detail=reason)

    @classmethod
    def fail(cls, reason: str) -> NotificationResult:
        return cls(sent=False, skipped=False, detail=reason)


class Notifier(Protocol):
    """Bir bildirim kanali.

    Uygulamalar ISTISNA FIRLATMAZ; hatayi `NotificationResult.fail()` olarak
    dondururler. Bildirim gonderimi hicbir kosulda emir akisini durdurmamalidir.
    """

    name: str

    async def send(self, message: NotificationMessage) -> NotificationResult: ...
