"""Lead uygunluk kurallari ve potansiyel skoru - sayinin TEK kaynagi.

Hem tek seferlik tarama gorevi (`app/leads/scheduler.py`) hem ileride
yazilacak herhangi bir REST/MCP yolu bu modulu cagirir.

Kurallar DETERMINISTIKTIR: LLM kullanmaz, ayni girdi her zaman ayni
sonucu verir.

SEG-01 (yas araligi 25-45) UYGULANMIYOR: `users` tablosunda dogum
tarihi/yas verisi yok, eklemek kayit formunu da degistirmeyi gerektirir
(kapsam disi) ve sahte veri riski yaratir (bkz. proje gecmisindeki sahte
price_history olayi). Diger kurallar (varlik, gelir, hareketsizlik,
riza) gercek veriyle calisir.

SEG-06 (maas duzeni) BASITLESTIRILDI: spesifikasyon "son 3 ayda duzenli
maas/gelir girisi" istiyor - bu gercek islem gecmisi analizi gerektirir
(bankada gercek para yatisi kaydi yok). Yerine `monthly_income > 0`
(beyan edilmis bir geliri var mi) kontrolu kullanilir.

SEG-10 (sogutma) BASITLESTIRILDI: spesifikasyon "ilgilenmiyorum yaniti
sonrasi" diyor - bu bir red/opt-out akisi gerektirir (ayri endpoint,
yeni tablo). Yerine, yanit bagimsiz, salt zaman pencereli bir sogutma
kullanilir: `lead_contacts` tablosundaki en son temastan bu yana
`COOLDOWN_DAYS` gecmediyse kullanici atlanir.

Esik degerleri Tablo 3.1 (SEG-01..SEG-10) ile hizalidir; sayilar
`app/config.py` uzerinden .env ile override edilebilir.
"""

from __future__ import annotations

from datetime import datetime, timezone

#: SEG-03 - atil bakiye alt esigi. Bu TL'nin altindaki portfoy degeri
#: dislanir (balance_below_threshold).
MIN_PORTFOLIO_VALUE_TRY = 120_000.0

#: SEG-07 - BSD kuyrugu esigi. Bu TL VE UZERI insan danismana (BSD) gider.
BSD_ESIK_TRY = 500_000.0

#: SEG-04 - kampanya disi birakma ustsiniri. Bu TL VE UZERI zaten ozel
#: bankacilik musterisi sayilir, bu kampanyaya hic dahil edilmez.
UST_SINIR_TRY = 1_000_000.0

#: SEG-05 - hareketsizlik esigi (gun). Bu kadar gundur islem/sohbet
#: YOKSA kullanici "hareketsiz" sayilir (kampanyanin hedefi).
MIN_INACTIVITY_DAYS = 90

#: SEG-10 - sogutma penceresi (gun), basitlestirilmis (bkz. modul
#: docstring'i): yanit bagimsiz, salt zaman bazli.
COOLDOWN_DAYS = 180

#: Bir tarama basina gonderilebilecek AZAMI otonom mail sayisi - kota
#: korumasi (patlama yaricapi).
MAX_EMAILS_PER_SCAN = 20


def uygunluk_degerlendir(
    signal: dict,
    last_contact_at: datetime | None,
    cooldown_days: int = COOLDOWN_DAYS,
) -> str | None:
    """Kullanici uygun mu? Degilse dislama nedenini doner, uygunsa None.

    Kurallar SIRAYLA kontrol edilir, ilk basarisiz olan kazanir (akis
    semasindaki gibi yukaridan asagiya).

    Args:
        signal: `v_lead_user_signals` satiri (ya da bellek ici karsiligi) -
            `marketing_consent`, `email`, `monthly_income`,
            `total_value_try`, `days_since_activity` alanlarini tasir.
        last_contact_at: Bu kullaniciya en son ne zaman temas edildigi
            (`lead_contacts.created_at`); hic temas yoksa None.
        cooldown_days: Soğutma penceresi (gun) - test/override icin.

    Returns:
        Uygunsa None. Degilse: "consent_missing" | "email_missing" |
        "income_below_threshold" | "balance_below_threshold" |
        "above_upper_limit" | "recently_active" | "cooldown_active".
    """
    if not signal.get("marketing_consent"):
        return "consent_missing"

    if not signal.get("email"):
        return "email_missing"

    if not (float(signal.get("monthly_income") or 0) > 0):
        return "income_below_threshold"

    total_value = float(signal.get("total_value_try") or 0)
    if total_value < MIN_PORTFOLIO_VALUE_TRY:
        return "balance_below_threshold"

    if total_value >= UST_SINIR_TRY:
        return "above_upper_limit"

    days_since_activity = signal.get("days_since_activity")
    if days_since_activity is not None and days_since_activity < MIN_INACTIVITY_DAYS:
        return "recently_active"

    if last_contact_at is not None:
        gun_farki = (datetime.now(timezone.utc) - last_contact_at).days
        if gun_farki < cooldown_days:
            return "cooldown_active"

    return None


def kuyruk_sec(signal: dict) -> str:
    """Uygun bir kullaniciyi BSD ya da otonom kuyruga yonlendirir.

    SEG-07/SEG-08: varlik BSD_ESIK_TRY (500K) VE UZERINDE ise BSD (insan
    danisman) kuyruguna, altindaysa otonom (mail) kuyruguna gider. Skora
    gore DEGIL, dogrudan varlik esigine gore - akis semasindaki
    "varlik ust segment esiginde mi" kuralina sadik kalinir.
    """
    total_value = float(signal.get("total_value_try") or 0)
    return "BSD" if total_value >= BSD_ESIK_TRY else "AUTONOMOUS"


def potansiyel_skoru_hesapla(signal: dict) -> dict:
    """0-100 arasi potansiyel skoru + bilesenleri + Turkce gerekceler.

    Skor SIRALAMA icindir (BSD ekraninda kimi once aramali) - uygunluk
    kararini ETKILEMEZ, o `uygunluk_degerlendir`/`kuyruk_sec` icinde ayri
    kurallarla veriliyor.

    BILESENLER (0-100)
        varlik          (0-45)  Portfoy degeri, BSD esigine oranla
        gelir           (0-30)  Aylik gelir, 500K'lik bir ust sinira oranla
        hareketsizlik   (0-15)  Ne kadar uzun suredir hareketsiz (180 gunde tavan)
        urun_boslugu    (0-10)  Az sayida varlik = capraz satis firsati

    Bu agirliklar bir sektor standardi degil, savunulabilir basit bir
    modeldir; degistirilirse tek yer burasidir (bkz. `risk.py` ile ayni
    felsefe).
    """
    total_value = float(signal.get("total_value_try") or 0)
    monthly_income = float(signal.get("monthly_income") or 0)
    days_since_activity = signal.get("days_since_activity")
    holding_count = int(signal.get("holding_count") or 0)

    varlik = _kirp(total_value / BSD_ESIK_TRY * 45, 0, 45)
    gelir = _kirp(monthly_income / 500_000 * 30, 0, 30)
    hareketsizlik = _kirp((days_since_activity or 180) / 180 * 15, 0, 15)
    urun_boslugu = _kirp((1 - min(holding_count, 5) / 5) * 10, 0, 10)

    skor = round(varlik + gelir + hareketsizlik + urun_boslugu)

    return {
        "score": skor,
        "components": {
            "varlik": round(varlik, 1),
            "gelir": round(gelir, 1),
            "hareketsizlik": round(hareketsizlik, 1),
            "urun_boslugu": round(urun_boslugu, 1),
        },
        "reasons": _gerekceler(total_value, days_since_activity, holding_count),
    }


def _gerekceler(
    total_value: float, days_since_activity: int | None, holding_count: int
) -> list[str]:
    gerekceler: list[str] = []
    if total_value >= BSD_ESIK_TRY:
        gerekceler.append(f"Portföy değeri {total_value:,.0f} TL - BSD eşiğinin üzerinde.")
    if days_since_activity is not None:
        gerekceler.append(f"{days_since_activity} gündür hesapta işlem/sohbet yok.")
    else:
        gerekceler.append("Hiç işlem/sohbet aktivitesi kaydı yok.")
    if holding_count <= 2:
        gerekceler.append(f"Portföyde yalnızca {holding_count} varlık var - çapraz satış fırsatı.")
    return gerekceler


def _kirp(value: float, alt: float, ust: float) -> float:
    return max(alt, min(value, ust))
