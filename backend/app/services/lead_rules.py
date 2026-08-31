"""Lead uygunluk kurallari ve potansiyel skoru - sayinin TEK kaynagi.

Hem tek seferlik tarama gorevi (`app/leads/scheduler.py`) hem ileride
yazilacak herhangi bir REST/MCP yolu bu modulu cagirir.

Kurallar DETERMINISTIKTIR: LLM kullanmaz, ayni girdi her zaman ayni
sonucu verir.

HEDEF KITLE: zaten yatirim yapmis (portfoyu olan) musteriler DEGIL -
bankada atil bakiyesi (`likit_para`) 120K-1M TL arasinda duran ama HIC
yatirim yapmamis musteriler. Bu yuzden esik kontrolleri `total_value_try`
(yatirim portfoyu) DEGIL `likit_para` (atil banka bakiyesi) uzerinden
yapilir; `total_value_try > 0` ise kullanici zaten yatirimci sayilir ve
dislanir (already_invested).

SEG-01 (yas araligi 25-45) UYGULANMIYOR: `users` tablosunda dogum
tarihi/yas verisi yok, eklemek kayit formunu da degistirmeyi gerektirir
(kapsam disi) ve sahte veri riski yaratir (bkz. proje gecmisindeki sahte
price_history olayi).

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

#: SEG-03 - atil bakiye alt esigi. Bu TL'nin altindaki atil bakiye
#: dislanir (balance_below_threshold).
MIN_ATIL_BAKIYE_TRY = 120_000.0

#: SEG-07 - BSD kuyrugu esigi. Bu atil bakiye VE UZERI insan danismana (BSD) gider.
BSD_ESIK_TRY = 500_000.0

#: SEG-04 - kampanya disi birakma ustsiniri. Bu atil bakiye VE UZERI zaten ozel
#: bankacilik musterisi sayilir, bu kampanyaya hic dahil edilmez.
UST_SINIR_TRY = 1_000_000.0

#: SEG-05 - hareketsizlik esigi (gun). Bu kadar gundur islem/sohbet
#: YOKSA kullanici "hareketsiz" sayilir (kampanyanin hedefi). Hic
#: aktivite kaydi olmayan (days_since_activity=None) kullanicilar bu
#: kontrolden otomatik GECER - "uzun suredir yatirim yapmamis ama atil
#: bakiyesi olan" musteri tam da budur.
MIN_INACTIVITY_DAYS = 90

#: SEG-10 - sogutma penceresi (gun), basitlestirilmis (bkz. modul
#: docstring'i): yanit bagimsiz, salt zaman bazli.
COOLDOWN_DAYS = 180

#: Bir tarama basina AZAMI mail DENEMESI - kota korumasi (patlama
#: yaricapi). Basarili gonderim degil DENEME sayilir; aksi halde SMTP
#: surekli hata verdiginde sinir hic devreye girmezdi.
MAX_EMAILS_PER_SCAN = 20

#: Ust uste bu kadar gonderim basarisiz olursa o taramada mail gonderimi
#: BIRAKILIR (kuyruk yazimi devam eder). SMTP tamamen cokmusse her deneme
#: timeout suresi kadar surer; 20 denemeyi sonuna kadar isletmek taramayi
#: dakikalarca asili birakir.
MAX_ARDISIK_MAIL_HATASI = 3


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
            `marketing_consent`, `email`, `monthly_income`, `likit_para`,
            `total_value_try`, `days_since_activity` alanlarini tasir.
        last_contact_at: Bu kullaniciya en son ne zaman temas edildigi
            (`lead_contacts.created_at`); hic temas yoksa None.
        cooldown_days: Soğutma penceresi (gun) - test/override icin.

    Returns:
        Uygunsa None. Degilse: "consent_missing" | "email_missing" |
        "income_below_threshold" | "already_invested" |
        "balance_below_threshold" | "above_upper_limit" |
        "recently_active" | "cooldown_active".
    """
    if not signal.get("marketing_consent"):
        return "consent_missing"

    if not signal.get("email"):
        return "email_missing"

    if not (float(signal.get("monthly_income") or 0) > 0):
        return "income_below_threshold"

    if float(signal.get("total_value_try") or 0) > 0:
        return "already_invested"

    atil_bakiye = float(signal.get("likit_para") or 0)
    if atil_bakiye < MIN_ATIL_BAKIYE_TRY:
        return "balance_below_threshold"

    if atil_bakiye >= UST_SINIR_TRY:
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

    SEG-07/SEG-08: atil bakiye BSD_ESIK_TRY (500K) VE UZERINDE ise BSD
    (insan danisman) kuyruguna, altindaysa otonom (mail) kuyruguna gider.
    """
    atil_bakiye = float(signal.get("likit_para") or 0)
    return "BSD" if atil_bakiye >= BSD_ESIK_TRY else "AUTONOMOUS"


def potansiyel_skoru_hesapla(signal: dict) -> dict:
    """0-90 arasi potansiyel skoru + bilesenleri + Turkce gerekceler.

    Skor SIRALAMA icindir (BSD ekraninda kimi once aramali) - uygunluk
    kararini ETKILEMEZ, o `uygunluk_degerlendir`/`kuyruk_sec` icinde ayri
    kurallarla veriliyor.

    BILESENLER (0-90)
        atil_bakiye     (0-45)  Bankadaki atil bakiye, BSD esigine oranla
        gelir           (0-30)  Aylik gelir, 500K'lik bir ust sinira oranla
        hareketsizlik   (0-15)  Ne kadar uzun suredir hareketsiz (180 gunde tavan)

    "Urun boslugu" bileseni (eski surumde vardi) KALDIRILDI: hedef kitle
    zaten "hic yatirim yapmamis" (total_value_try=0) oldugu icin
    holding_count her zaman 0 - bu bilesen her lead icin sabit/anlamsiz
    hale gelirdi.

    Bu agirliklar bir sektor standardi degil, savunulabilir basit bir
    modeldir; degistirilirse tek yer burasidir (bkz. `risk.py` ile ayni
    felsefe).
    """
    atil_bakiye = float(signal.get("likit_para") or 0)
    monthly_income = float(signal.get("monthly_income") or 0)
    days_since_activity = signal.get("days_since_activity")

    varlik = _kirp(atil_bakiye / BSD_ESIK_TRY * 45, 0, 45)
    gelir = _kirp(monthly_income / 500_000 * 30, 0, 30)
    # `or 180` DEGIL `is None` kontrolu: bugun aktif olan bir kullanicinin
    # `days_since_activity` degeri 0'dir ve Python'da 0 falsy'dir - `or 180`
    # yazimi onu "hic aktivite yok" sayip TAVAN hareketsizlik puani verirdi.
    # Bugun bu yola `recently_active` kurali yuzunden hic ulasilmiyor, ama
    # kural sirasi/esikleri degisirse sessizce yanlis skor uretirdi.
    gun = 180 if days_since_activity is None else days_since_activity
    hareketsizlik = _kirp(gun / 180 * 15, 0, 15)

    skor = round(varlik + gelir + hareketsizlik)

    return {
        "score": skor,
        "components": {
            "atil_bakiye": round(varlik, 1),
            "gelir": round(gelir, 1),
            "hareketsizlik": round(hareketsizlik, 1),
        },
        "reasons": _gerekceler(atil_bakiye, days_since_activity),
    }


def _gerekceler(atil_bakiye: float, days_since_activity: int | None) -> list[str]:
    gerekceler: list[str] = []
    if atil_bakiye >= BSD_ESIK_TRY:
        gerekceler.append(f"Atıl bakiyesi {atil_bakiye:,.0f} TL - BSD eşiğinin üzerinde.")
    if days_since_activity is not None:
        gerekceler.append(f"{days_since_activity} gündür hesapta işlem/sohbet yok.")
    else:
        gerekceler.append("Hiç işlem/sohbet aktivitesi kaydı yok.")
    gerekceler.append("Hiç yatırım yapmamış - portföyünde varlık yok.")
    return gerekceler


def _kirp(value: float, alt: float, ust: float) -> float:
    return max(alt, min(value, ust))
