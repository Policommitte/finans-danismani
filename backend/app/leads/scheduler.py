"""Lead taramasini tetikleyen TEK SEFERLIK gorev.

`app/market/scheduler.py`'nin aksine SONSUZ DONGU degildir: uygulama
acilisinda bir kez calisir ve doner. Tekrar calistirmak icin (`reload=True`
ile her dosya kaydinda `lifespan()` yeniden tetiklenir - bkz. `run.py`)
gercek "tekrar tetikleme" kararini `services.leads.tarama_calistir` icindeki
DAKIKA BAZLI ASGARI ARALIK kontrolu verir, burasi degil.

Gorev HICBIR ZAMAN uygulamayi dusurmez: hata olursa loglanir, `lifespan`
akisi devam eder.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)


async def run_lead_scan_once(trigger: str = "manual", force: bool = False) -> dict:
    """Tek bir tarama calistirir; sonucu (`LeadScanSummary` benzeri dict) doner.

    Hata olursa istisna YUKARI FIRLATILIR - `POST /api/leads/scan` bunu
    yakalayip 500'e cevirir. `schedule_startup_lead_scan` ise kendi
    try/except'i icinde bu fonksiyonu cagirir, acilis sirasinda hicbir
    istisna uygulamayi dusurmez.
    """
    from app.services import leads as service

    return await service.tarama_calistir(trigger=trigger, force=force)


async def schedule_startup_lead_scan() -> None:
    """Acilista bir kez calisir: kisa bir gecikme bekler, taramayi calistirir, doner.

    `market/scheduler.py::run_price_scheduler`'in aksine SONSUZ DONGU
    YOKTUR - bu bilincli bir tasarim: lead taramasi "surekli akan" bir
    seyler degil, "kayitli kullanicilar arasinda bir kerelik tarama"dir.
    """
    await asyncio.sleep(settings.lead_scan_startup_delay_seconds)

    try:
        sonuc = await run_lead_scan_once(trigger="startup", force=False)
        if sonuc.get("skipped"):
            logger.info("lead taramasi atlandi: %s", sonuc.get("skip_reason"))
        else:
            logger.info(
                "lead taramasi bitti: tarandi=%s bsd=%s otonom=%s dislanan=%s mail=%s",
                sonuc.get("scanned_count"), sonuc.get("bsd_count"),
                sonuc.get("autonomous_count"), sonuc.get("excluded_count"),
                sonuc.get("emailed_count"),
            )
    except asyncio.CancelledError:
        logger.info("lead taramasi durduruldu")
        raise
    except Exception:  # noqa: BLE001 - acilis taramasi uygulamayi dusurmemeli
        logger.exception("lead taramasi basarisiz")