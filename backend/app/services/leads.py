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

    `LEAD_ENGINE_ENABLED=false` iken tarama HICBIR SEKILDE calismaz - ne
    otomatik acilis gorevi ne elle `POST /api/leads/scan` (force=true
    dahil). `force`, yalnizca asgari aralik kontrolunu atlar; motor
    kapaliyken bir anlami yoktur.
    """
    repository = get_lead_repository()

    if not settings.lead_engine_enabled:
        son = await repository.latest_scan()
        return _ozet(
            son, skipped=True, skip_reason="lead motoru devre disi (LEAD_ENGINE_ENABLED=false)"
        )

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

    #: Kota SONUCU degil DENEMEYI sayar: yalnizca `emailed_count`'a
    #: bakilsaydi SMTP surekli hata verdiginde sayac hic artmaz ve tarama
    #: otonom kuyruktaki HER kullanici icin (her biri timeout suresi kadar)
    #: SMTP denerdi - kota bir ust sinir olmaktan cikardi.
    deneme_sayisi = 0
    ardisik_hata = 0

    #: Gmail hic yapilandirilmamissa tek tek denemenin anlami yok: her
    #: kullanici icin bos yere claim + SKIPPED yazmak yerine bastan bir kez
    #: kontrol edilir. Kuyruklar yine dolar, yalnizca mail denenmez.
    mail_gonderilebilir = mailer.is_configured()
    if not mail_gonderilebilir:
        logger.warning("Gmail ayarlari bos; bu taramada hic mail denenmeyecek")

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
                        "likit_para": signal.get("likit_para") or 0,
                        "days_since_activity": signal.get("days_since_activity"),
                    },
                )
                continue

            skor_sonucu = rules.potansiyel_skoru_hesapla(signal)
            kuyruk = rules.kuyruk_sec(signal)

            if kuyruk == "BSD":
                # BSD kuyruguna dusmek bir TEMAS DEGIL, bir ONERIDIR: gercek
                # temas ancak danisman kisiyi aradiginda olur ve bunu takip
                # etmiyoruz (kapsam disi). Bu yuzden `lead_contacts`'a kayit
                # ACILMAZ - aksi halde kisi sogutma penceresine girer ve bir
                # sonraki taramada kuyruktan sessizce kaybolurdu.
                sayaclar["bsd_count"] += 1
            else:
                sayaclar["autonomous_count"] += 1
                if (
                    mail_gonderilebilir
                    and deneme_sayisi < rules.MAX_EMAILS_PER_SCAN
                    and ardisik_hata < rules.MAX_ARDISIK_MAIL_HATASI
                ):
                    contact_id = await repository.claim_email_contact(
                        signal["user_id"], scan_id, signal["email"], mailer.KONU
                    )
                    if contact_id is not None:
                        deneme_sayisi += 1
                        sonuc = await mailer.send_lead_email(signal["email"], signal["first_name"])
                        if sonuc["status"] == "SENT":
                            sayaclar["emailed_count"] += 1
                            ardisik_hata = 0
                        elif sonuc["status"] == "FAILED":
                            ardisik_hata += 1
                            await repository.mark_contact_failed(
                                contact_id, sonuc["error"] or "bilinmeyen hata"
                            )
                            if ardisik_hata >= rules.MAX_ARDISIK_MAIL_HATASI:
                                # SMTP tamamen cokmus olabilir: her denemenin
                                # timeout suresi kadar surdugu bir donguyu
                                # sonuna kadar isletmek taramayi dakikalarca
                                # asili birakir. Kuyruk yazimi devam eder.
                                logger.error(
                                    "ust uste %s mail hatasi - bu taramada gonderim durduruldu",
                                    ardisik_hata,
                                )
                        elif sonuc["status"] == "SKIPPED":
                            # Bu dala normalde ULASILMAZ: `mail_gonderilebilir`
                            # kontrolu zaten yukarida yapiliyor. Emniyet supabi
                            # olarak duruyor - `send_lead_email` ileride baska
                            # bir nedenle SKIPPED donerse claim `SENT` olarak
                            # kalmasin (kullanici 180 gun bosuna kilitlenirdi).
                            await repository.mark_contact_skipped(contact_id)

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
                    "likit_para": signal.get("likit_para") or 0,
                    "days_since_activity": signal.get("days_since_activity"),
                },
            )
    # `Exception` DEGIL `BaseException`: `asyncio.CancelledError` Python
    # 3.8'den beri BaseException'dan turer. Acilis taramasi ~10 saniye surer
    # ve `uvicorn --reload` bu sirada yeniden baslarsa gorevi IPTAL eder;
    # `except Exception` bunu yakalamadigi icin `hata` None kalir, ama
    # `finally` yine de taramayi "bitmis ve hatasiz" olarak kapatirdi.
    # Sonuc: yarim kalmis bir tarama (orn. 13 kisiden 4'u) veritabaninda
    # basarili gorunur ve danisman ekrani onu "en son tarama" diye gosterip
    # aniden bosalirdi.
    except BaseException as exc:  # noqa: BLE001 - hata kaydedilir, sonra YENIDEN FIRLATILIR
        hata = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        await repository.finish_scan(scan_id, sayaclar, error=hata)

    son = await repository.latest_scan()
    return _ozet(son, skipped=False, skip_reason=None)


async def bsd_kuyrugu_getir(limit: int = 100) -> dict:
    return await _kuyruk_getir("BSD", limit)


async def otonom_kuyruk_getir(limit: int = 100) -> dict:
    """Otonom kuyruk - IKI kaynagin birlesimi.

    1. `lead_contacts`: son `COOLDOWN_DAYS` gun icinde GERCEKTEN mail
       gonderilenler. Mail gonderilen kisi sogutmaya girdigi icin sonraki
       taramalarda `EXCLUDED` olur ve son taramanin AUTONOMOUS listesinden
       duserdi - oysa danisman "kime mail gitti"yi gormeye devam etmeli.
    2. Son taramanin `AUTONOMOUS` kararlari: kota dolduysa, ardisik hata
       freni devreye girdiyse ya da Gmail hic yapilandirilmamissa kisi
       otonom kuyruga girer ama mail GITMEZ - yalnizca (1)'e bakilsaydi bu
       kisiler hicbir listede gorunmez, ekranda sessiz bir bosluk olurdu.

    Kullanici basina TEK satir doner; `mail_gonderildi` alani hangi durumda
    oldugunu soyler.
    """
    repository = get_lead_repository()
    mail_gidenler = await repository.list_emailed(rules.COOLDOWN_DAYS, limit=limit)
    son_karar = await repository.list_queue("AUTONOMOUS", limit=limit)

    # Ayni kullanici iki kaynakta da olabilir; GERCEK temas kaydi kazanir.
    birlesik: dict[int, dict] = {
        item["user_id"]: {**item, "mail_gonderildi": False} for item in son_karar
    }
    birlesik.update({item["user_id"]: {**item, "mail_gonderildi": True} for item in mail_gidenler})

    items = sorted(birlesik.values(), key=lambda i: i.get("score") or 0, reverse=True)[:limit]
    son = await repository.latest_scan()
    return {
        "items": items,
        "count": len(items),
        "scan": _ozet(son, skipped=False, skip_reason=None),
    }


async def dislananlar_getir(limit: int = 100) -> dict:
    return await _kuyruk_getir("EXCLUDED", limit)


async def gorusme_sonucu_kaydet(
    user_id: int, advisor_id: int | None, outcome: str, note: str | None = None
) -> None:
    """Danismanin telefon gorusmesi sonucunu kaydeder.

    Tarama motoruna DOLAYLI olarak baglidir: `KABUL`/`ISTEMIYOR`
    isaretlenenler bir sonraki taramada `advisor_closed` ile dislanir
    (bkz. `lead_rules.uygunluk_degerlendir`). Burada tarama tetiklenmez -
    ekran zaten `call_outcome` alanini dogrudan gosterir, kullaniciyi
    beklemeye sokmanin anlami yok.
    """
    repository = get_lead_repository()
    await repository.record_call_outcome(user_id, advisor_id, outcome, note)


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
