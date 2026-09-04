"""Bildirim outbox'i ve mail koprusu testleri.

Mail kanali BAGLI DEGIL; bu testler koprunun dogru davrandigini sabitler:
olaylar yaziliyor mu, kanal kapaliyken satirlar birikmeden kapaniyor mu,
kanal acilinca gercekten gonderiliyor mu.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.notifications import templates
from app.notifications.base import NotificationMessage, NotificationResult
from app.notifications.dispatcher import MAX_ATTEMPTS, dispatch_notifications
from app.repositories import in_memory
from app.repositories.in_memory import (
    InMemoryNotificationRepository,
    InMemoryTradingRepository,
    reset_data,
)


@pytest.fixture
def repository():
    reset_data()
    return InMemoryTradingRepository()


@pytest.fixture
def outbox():
    return InMemoryNotificationRepository()


class _KaydedenNotifier:
    """Gonderim yapiyormus gibi davranir ve mesajlari saklar."""

    name = "kaydeden"

    def __init__(self, sonuc: NotificationResult | None = None):
        self.gonderilenler: list[NotificationMessage] = []
        self._sonuc = sonuc or NotificationResult.ok()

    async def send(self, message: NotificationMessage) -> NotificationResult:
        self.gonderilenler.append(message)
        return self._sonuc


@pytest.fixture
def notifier_patch(monkeypatch):
    """`get_notifier()` yerine test notifier'i koyar."""

    def apply(notifier):
        monkeypatch.setattr("app.notifications.dispatcher.get_notifier", lambda: notifier)
        return notifier

    return apply


async def _filled_order(repository) -> None:
    await repository.create_market_order(
        user_id=1,
        symbol="THYAO",
        side="BUY",
        quantity=5,
        idempotency_key="bildirim-testi",
        commission_rate=0.0015,
    )
    await repository.process_pending_orders(
        [{"asset_id": 1, "price": 300.0}], commission_rate=0.0015
    )


@pytest.mark.asyncio
async def test_filled_order_written_to_outbox(repository, outbox):
    await _filled_order(repository)

    rows = await outbox.list_for_user(1)
    assert len(rows) == 1
    kayit = rows[0]
    assert kayit["event_type"] == "ORDER_FILLED"
    assert kayit["status"] == "PENDING"
    assert kayit["payload"]["symbol"] == "THYAO"
    assert kayit["payload"]["side"] == "BUY"
    assert kayit["payload"]["price"] == 300.0


@pytest.mark.asyncio
async def test_rejected_order_written_to_outbox(repository, outbox):
    """Satilabilir adet yoksa emir reddedilir ve bu da bildirilir."""
    await repository.create_market_order(
        user_id=1,
        symbol="THYAO",
        side="SELL",
        quantity=5,
        idempotency_key="ret-testi",
        commission_rate=0.0015,
    )
    # Pozisyonu emir bekliyorken sifirla: gerceklesme aninda adet yetersiz kalir.
    in_memory._PORTFOLIO_ASSETS[:] = [h for h in in_memory._PORTFOLIO_ASSETS if h["asset_id"] != 1]
    await repository.process_pending_orders(
        [{"asset_id": 1, "price": 300.0}], commission_rate=0.0015
    )

    rows = await outbox.list_for_user(1)
    assert [r["event_type"] for r in rows] == ["ORDER_REJECTED"]
    assert "yetersiz" in rows[0]["payload"]["rejection_reason"]


@pytest.mark.asyncio
async def test_row_closed_as_skipped_when_channel_not_connected(repository, outbox):
    """Varsayilan kanal NoopNotifier: satir PENDING birikmemeli."""
    await _filled_order(repository)

    sayac = await dispatch_notifications()

    assert sayac == {"sent": 0, "skipped": 1, "failed": 0}
    kayit = (await outbox.list_for_user(1))[0]
    assert kayit["status"] == "SKIPPED"


@pytest.mark.asyncio
async def test_sent_when_channel_enabled(repository, outbox, notifier_patch):
    notifier = notifier_patch(_KaydedenNotifier())
    await _filled_order(repository)

    sayac = await dispatch_notifications()

    assert sayac["sent"] == 1
    assert (await outbox.list_for_user(1))[0]["status"] == "SENT"
    mesaj = notifier.gonderilenler[0]
    assert "THYAO" in mesaj.subject
    assert mesaj.recipient  # kullanicinin e-postasi fotograflanmis olmali
    assert templates.SIMULASYON_UYARISI in mesaj.body
    assert templates.TAVSIYE_UYARISI in mesaj.body


@pytest.mark.asyncio
async def test_too_old_event_not_sent(repository, outbox, notifier_patch):
    """Kanal aylar sonra acilirsa birikmis gecmis bildirimler gitmemeli."""
    notifier = notifier_patch(_KaydedenNotifier())
    await _filled_order(repository)
    eski = datetime.now(timezone.utc) - timedelta(days=3)
    in_memory._NOTIFICATION_OUTBOX[0]["created_at"] = eski.isoformat()

    sayac = await dispatch_notifications()

    assert sayac == {"sent": 0, "skipped": 1, "failed": 0}
    assert notifier.gonderilenler == []
    kayit = (await outbox.list_for_user(1))[0]
    assert kayit["status"] == "SKIPPED"
    assert kayit["last_error"] == "olay cok eski"


@pytest.mark.asyncio
async def test_send_error_retried_then_marked_failed(repository, outbox, notifier_patch):
    notifier_patch(_KaydedenNotifier(NotificationResult.fail("smtp kapali")))
    await _filled_order(repository)

    # Ilk denemelerde satir PENDING kalir ki gecici hata bildirimi yakmasin.
    sayac = await dispatch_notifications()
    assert sayac == {"sent": 0, "skipped": 0, "failed": 0}
    assert (await outbox.list_for_user(1))[0]["status"] == "PENDING"

    for _ in range(MAX_ATTEMPTS - 1):
        sayac = await dispatch_notifications()

    kayit = (await outbox.list_for_user(1))[0]
    assert sayac["failed"] == 1
    assert kayit["status"] == "FAILED"
    assert kayit["last_error"] == "smtp kapali"


@pytest.mark.asyncio
async def test_closed_row_not_sent_twice(repository, outbox, notifier_patch):
    notifier = notifier_patch(_KaydedenNotifier())
    await _filled_order(repository)

    await dispatch_notifications()
    await dispatch_notifications()

    assert len(notifier.gonderilenler) == 1


@pytest.mark.asyncio
async def test_row_out_of_attempts_no_longer_claimed(outbox):
    reset_data()
    in_memory._NOTIFICATION_OUTBOX.append(
        {
            "id": 1,
            "user_id": 1,
            "order_id": None,
            "event_type": "ORDER_FILLED",
            "channel": "EMAIL",
            "recipient": "a@b.c",
            "payload": {},
            "status": "PENDING",
            "attempts": MAX_ATTEMPTS,
            "last_error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "processed_at": None,
        }
    )

    assert await outbox.claim_pending(10, MAX_ATTEMPTS) == []
