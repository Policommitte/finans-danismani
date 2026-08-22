"""Lead motoru orkestrasyonu - tarama calistirir, kuyruklari okur.

Katman kurali: bu dosya `app/services/lead_rules.py` (kurallar) ve
`app/leads/mailer.py` (I/O) arasindaki koprudur; ne kural degerlendirmesi
ne SMTP detayi burada YAZILMAZ.

`app/leads/scheduler.py::run_lead_scan_once` bu modulun `tarama_calistir`
fonksiyonunu cagirir.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.leads import mailer
from app.repositories.deps import get_lead_repository
from app.services import lead_rules as rules

logger = logging.getLogger(__name__)


async def tarama_calistir(trigger: str = "manual", force: bool = False) -> dict:
    """Bir lead taramasi calistirir; `LeadScanSummary` bicimli dict doner.

    `force=False` iken son taramadan bu yana yeterli sure gecmediyse
    tarama ATLANIR (hata degil, `skipped=True` ile normal bir sonuc).
    """
    repository = get_lead_repository()

    if not force:
        gecen_dakika = await repository.minutes_since_last_scan()
        if gecen_dakika is not None and gecen_dakika < settings.lead_scan_min_interval_minutes:
            son = await repository.latest_scan()
            return _ozet(
                son,
                skipped=True,
                skip_reason=f"son tarama {gecen_dakika:.0f} dk once, tarama atlandi",
            )

    scan_id = await repository.start_scan(trigger)
    sayaclar = {
        "scanned_count": 0,
        "bsd_count": 0,
        "autonomous_count": 0,
        "excluded_count": 0,
        "emailed_count": 0,
    }
    hata: str | None = None

    try:
        sinyaller = await repository.list_lead_signals()
        temas_haritasi = await repository.last_contacted_map(rules.COOLDOWN_DAYS)

        for signal in sinyaller:
            sayaclar["scanned_count"] += 1
            son_temas = temas_haritasi.get(signal["user_id"])

            neden = rules.uygunluk_degerlendir(signal, son_temas)
            if neden is not None:
                sayaclar["excluded_count"] += 1
                await repository.record_decision(
                    scan_id,
                    {
                        "user_id": signal["user_id"],
                        "decision": "EXCLUDED",
                        "exclusion_reason": neden,
                        "score": 0,
                        "score_components": {},
                        "reasons": [],
                        "total_value_try": signal.get("total_value_try", 0),
                        "monthly_income": signal.get("monthly_income", 0),
                        "days_since_activity": signal.get("days_since_activity"),
                    },
                )
                continue

            skor_sonucu = rules.potansiyel_skoru_hesapla(signal)
            kuyruk = rules.kuyruk_sec(signal)

            if kuyruk == "BSD":
                sayaclar["bsd_count"] += 1
                await repository.record_bsd_handover(signal["user_id"], scan_id)
            else:
                sayaclar["autonomous_count"] += 1
                if sayaclar["emailed_count"] < rules.MAX_EMAILS_PER_SCAN:
                    contact_id = await repository.claim_email_contact(
                        signal["user_id"], scan_id, signal["email"], mailer.KONU
                    )
                    if contact_id is not None:
                        sonuc = await mailer.send_lead_email(signal["email"], signal["first_name"])
                        if sonuc["status"] == "SENT":
                            sayaclar["emailed_count"] += 1
                        elif sonuc["status"] == "FAILED":
                            await repository.mark_contact_failed(
                                contact_id, sonuc["error"] or "bilinmeyen hata"
                            )
                else:
                    logger.warning(
                        "lead_max_emails_per_scan asildi, mail atlandi",
                        extra={"user_id": signal["user_id"], "limit": rules.MAX_EMAILS_PER_SCAN},
                    )

            await repository.record_decision(
                scan_id,
                {
                    "user_id": signal["user_id"],
                    "decision": kuyruk,
                    "exclusion_reason": None,
                    "score": skor_sonucu["score"],
                    "score_components": skor_sonucu["components"],
                    "reasons": skor_sonucu["reasons"],
                    "total_value_try": signal.get("total_value_try", 0),
                    "monthly_income": signal.get("monthly_income", 0),
                    "days_since_activity": signal.get("days_since_activity"),
                },
            )
    except Exception as exc:  # noqa: BLE001 - hata kaydedilir, sonra YENIDEN FIRLATILIR
        hata = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        await repository.finish_scan(scan_id, sayaclar, error=hata)

    son = await repository.latest_scan()
    return _ozet(son, skipped=False, skip_reason=None)


async def bsd_kuyrugu_getir(limit: int = 100) -> dict:
    return await _kuyruk_getir("BSD", limit)


async def otonom_kuyruk_getir(limit: int = 100) -> dict:
    return await _kuyruk_getir("AUTONOMOUS", limit)


async def dislananlar_getir(limit: int = 100) -> dict:
    return await _kuyruk_getir("EXCLUDED", limit)


async def son_tarama_getir() -> dict | None:
    repository = get_lead_repository()
    son = await repository.latest_scan()
    return _ozet(son, skipped=False, skip_reason=None) if son else None


async def _kuyruk_getir(decision: str, limit: int) -> dict:
    repository = get_lead_repository()
    items = await repository.list_queue(decision, limit=limit)
    son = await repository.latest_scan()
    return {
        "items": items,
        "count": len(items),
        "scan": _ozet(son, skipped=False, skip_reason=None),
    }

def _ozet(scan: dict | None, skipped: bool, skip_reason: str | None) -> dict:
    if scan is None:
        return {
            "scan_id": None,
            "trigger": None,
            "started_at": None,
            "finished_at": None,
            "scanned_count": 0,
            "bsd_count": 0,
            "autonomous_count": 0,
            "excluded_count": 0,
            "emailed_count": 0,
            "skipped": skipped,
            "skip_reason": skip_reason,
        }
    return {
        "scan_id": scan["id"],
        "trigger": scan["trigger"],
        "started_at": scan["started_at"],
        "finished_at": scan["finished_at"],
        "scanned_count": scan["scanned_count"],
        "bsd_count": scan["bsd_count"],
        "autonomous_count": scan["autonomous_count"],
        "excluded_count": scan["excluded_count"],
        "emailed_count": scan["emailed_count"],
        "skipped": skipped,
        "skip_reason": skip_reason,
    }