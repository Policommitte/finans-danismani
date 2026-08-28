"""Outbox'i bosaltan tur.

Fiyat gorevinin her tick'inde calisir (bkz. `app/market/scheduler.py`).
Ayri bir zamanlayici KURULMAZ: emir gerceklesmeleri zaten fiyat tick'inde
uretilir, bildirimi ayni turda gondermek en kisa gecikmeyi verir.

HICBIR KOSULDA ISTISNA FIRLATMAZ: bildirim gonderimi fiyat akisini ve emir
motorunu durdurmamalidir.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.notifications import templates
from app.notifications.base import NotificationMessage
from app.notifications.deps import get_notifier
from app.repositories.deps import get_notification_repository

logger = logging.getLogger(__name__)

#: Bu kadar denemeden sonra satir kalici olarak FAILED yazilir.
#: Surekli hata veren tek bir adres kuyrugu sonsuza kadar mesgul etmemeli.
MAX_ATTEMPTS = 5


async def bildirimleri_gonder(limit: int | None = None) -> dict[str, int]:
    """Bekleyen bildirimleri isler; {sent, skipped, failed} sayaclarini doner."""
    repository = get_notification_repository()
    notifier = get_notifier()
    batch = limit or settings.notification_batch_size

    rows = await repository.claim_pending(batch, MAX_ATTEMPTS)
    sayac = {"sent": 0, "skipped": 0, "failed": 0}

    for row in rows:
        outbox_id = int(row["id"])

        if _cok_eski(row.get("created_at")):
            # Kanal uzun sure kapali kalip sonra acilirsa birikmis gecmis
            # bildirimler tek seferde gitmesin: eski olay bilgi degil gurultudur.
            await repository.mark(outbox_id, "SKIPPED", "olay cok eski")
            sayac["skipped"] += 1
            continue

        payload = _payload(row.get("payload"))
        konu, govde = templates.build(row["event_type"], payload)
        mesaj = NotificationMessage(
            recipient=row.get("recipient") or "",
            subject=konu,
            body=govde,
            event_type=row["event_type"],
            order_id=row.get("order_id"),
        )

        try:
            sonuc = await notifier.send(mesaj)
        except Exception as exc:  # noqa: BLE001 - kanal sozlesmeyi bozmus olabilir
            logger.exception("bildirim kanali beklenmedik hata verdi")
            await _basarisiz(repository, row, f"{type(exc).__name__}: {exc}", sayac)
            continue

        if sonuc.sent:
            await repository.mark(outbox_id, "SENT", sonuc.detail)
            sayac["sent"] += 1
        elif sonuc.skipped:
            await repository.mark(outbox_id, "SKIPPED", sonuc.detail)
            sayac["skipped"] += 1
        else:
            await _basarisiz(repository, row, sonuc.detail or "bilinmeyen hata", sayac)

    if sayac["sent"] or sayac["failed"]:
        logger.info("bildirim turu tamamlandi", extra=sayac)
    return sayac


async def _basarisiz(repository, row: dict, hata: str, sayac: dict) -> None:
    """Basarisiz gonderimi kapatir ya da tekrar denenmek uzere birakir.

    Deneme hakki dolmadiysa satir PENDING kalir - `claim_pending` sayaci
    zaten artirmistir, yani sonsuz dongu olusmaz.
    """
    if int(row.get("attempts") or 0) >= MAX_ATTEMPTS:
        await repository.mark(int(row["id"]), "FAILED", hata)
        sayac["failed"] += 1
    else:
        logger.warning(
            "bildirim gonderilemedi, tekrar denenecek",
            extra={"outbox_id": row["id"], "attempts": row.get("attempts"), "hata": hata},
        )


def _cok_eski(created_at) -> bool:
    an = _datetime(created_at)
    if an is None:
        return False
    sinir = datetime.now(timezone.utc) - timedelta(minutes=settings.notification_max_age_minutes)
    return an < sinir


def _datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        an = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return an if an.tzinfo else an.replace(tzinfo=timezone.utc)


def _payload(value) -> dict:
    """JSONB surucuye gore dict ya da str gelebilir; ikisini de kabul et."""
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}
