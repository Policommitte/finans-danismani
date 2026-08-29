"""Veritabani sembolu <-> Yahoo Finance ticker eslemesi.

Bu dosya bir SOZLESME tablosudur: `assets.symbol` sutunundaki her deger icin
Yahoo'da hangi ticker'in cekilecegini soyler. Yeni bir varlik eklemek icin
asagidaki listeye bir satir eklemek yeterlidir; toplama kodu degismez.

NEDEN AYRI DOSYA?
    Sembol eslemesi projedeki en kirilgan yerdir - Yahoo ticker'lari zaman
    zaman degisir (`GC=F` -> baska bir kontrat gibi). Tek dosyada toplandiginda
    duzeltme tek yerden yapilir.

TURETILMIS VARLIKLAR
    Yahoo'da "TRY cinsinden gram altin" diye bir sembol YOKTUR. Bu yuzden
    GRAM_ALTIN ve GUMUS dogrudan cekilmez, su formulle turetilir:

        gram_TRY = (ons_USD / 31.1034768) * USDTRY

    Bu piyasa standardi "saf altin" hesabidir; kuyumcu makasi ve iscilik
    payi ICERMEZ. Kullanicinin kuyumcuda gordugu fiyattan bir miktar dusuk
    olmasi normaldir.
"""

from __future__ import annotations

from dataclasses import dataclass

#: 1 troy ons = 31.1034768 gram (uluslararasi kiymetli maden standardi).
TROY_ONS_GRAM = 31.1034768

#: Turetme yontemi: ons/USD fiyatini gram/TRY'ye cevir.
TURETME_ONS_USD_GRAM_TRY = "ONS_USD_GRAM_TRY"

#: Altin/gumus turetmesi ve USD varliklarin TRY karsiligi icin gereken kur.
USDTRY_TICKER = "USDTRY=X"


@dataclass(frozen=True)
class VarlikEslesme:
    """Bir `assets` satiri ile Yahoo ticker'i arasindaki bag.

    Attributes:
        db_symbol: `assets.symbol` sutunundaki DEGISMEZ deger. Toplama kodu
            veritabanini bu alana gore gunceller.
        kategori: `asset_categories.code` degeri. Yalnizca filtreleme ve
            raporlama icin kullanilir; DB'deki kategori DEGISTIRILMEZ.
        yahoo_ticker: Yahoo Finance sembolu.
        turetme: `None` ise fiyat dogrudan Yahoo'dan alinir. Doluysa
            `yahoo_ticker` ara girdidir ve fiyat hesaplanarak uretilir.
        aciklama: Insan icin not - hangi enstruman cekiliyor.
    """

    db_symbol: str
    kategori: str
    yahoo_ticker: str
    turetme: str | None = None
    aciklama: str = ""

    @property
    def turetilmis(self) -> bool:
        return self.turetme is not None


#: Veritabanindaki varliklardan Yahoo'da karsiligi OLANLAR.
#:
#: KARAR (16 Agustos 2026): TR10Y (tahvil) veritabanindan TAMAMEN SILINDI.
#: Yahoo'da Turkiye 10 yillik tahvil getirisi icin guvenilir, surekli veri
#: donen bir sembol yoktu; dummy/mock veri olarak kalmasi yerine kaldirilmasi
#: tercih edildi. Bagli portfoy/islem/alarm/izleme kaydi olmadigi dogrulanarak
#: silindi. Tahvil verisi ileride ayri bir kaynaktan ele alinabilir.
ESLESMELER: tuple[VarlikEslesme, ...] = (
    # --- Endeksler ---------------------------------------------------------
    VarlikEslesme("BIST100", "INDEX", "^XU100", aciklama="BIST 100 Endeksi"),
    # --- BIST hisseleri: Yahoo'da ".IS" eki ile ---------------------------
    VarlikEslesme("AKCNS", "STOCK", "AKCNS.IS", aciklama="Akcansa"),
    VarlikEslesme("BIMAS", "STOCK", "BIMAS.IS", aciklama="BIM Birlesik Magazalar"),
    VarlikEslesme("KCHOL", "STOCK", "KCHOL.IS", aciklama="Koc Holding"),
    VarlikEslesme("KONTR", "STOCK", "KONTR.IS", aciklama="Kontrolmatik"),
    VarlikEslesme("SISE", "STOCK", "SISE.IS", aciklama="Sisecam"),
    VarlikEslesme("THYAO", "STOCK", "THYAO.IS", aciklama="Turk Hava Yollari"),
    VarlikEslesme("GARAN", "STOCK", "GARAN.IS", aciklama="Garanti BBVA"),
    VarlikEslesme("TCELL", "STOCK", "TCELL.IS", aciklama="Turkcell"),
    VarlikEslesme("SASA", "STOCK", "SASA.IS", aciklama="Sasa Polyester"),
    VarlikEslesme("ASELS", "STOCK", "ASELS.IS", aciklama="Aselsan"),
    VarlikEslesme("EREGL", "STOCK", "EREGL.IS", aciklama="Erdemir"),
    VarlikEslesme("TOASO", "STOCK", "TOASO.IS", aciklama="Tofas"),
    VarlikEslesme("TUPRS", "STOCK", "TUPRS.IS", aciklama="Tupras"),
    # --- Doviz: Yahoo'da "=X" eki ile -------------------------------------
    VarlikEslesme("USD/TRY", "FOREX", USDTRY_TICKER, aciklama="Amerikan Dolari"),
    VarlikEslesme("EUR/TRY", "FOREX", "EURTRY=X", aciklama="Euro"),
    # --- Kiymetli maden: TURETILMIS (bkz. modul docstring'i) --------------
    VarlikEslesme(
        "GRAM_ALTIN",
        "GOLD",
        "GC=F",
        turetme=TURETME_ONS_USD_GRAM_TRY,
        aciklama="COMEX altin vadeli (ons/USD) -> gram/TRY",
    ),
    VarlikEslesme(
        "GUMUS",
        "GOLD",
        "SI=F",
        turetme=TURETME_ONS_USD_GRAM_TRY,
        aciklama="COMEX gumus vadeli (ons/USD) -> gram/TRY",
    ),
    # --- ABD hisseleri: dogrudan --------------------------------------------
    VarlikEslesme("AAPL", "USA_STOCK", "AAPL", aciklama="Apple Inc."),
    VarlikEslesme("AMZN", "USA_STOCK", "AMZN", aciklama="Amazon Inc"),
    VarlikEslesme("BRK-B", "USA_STOCK", "BRK-B", aciklama="Berkshire Hathaway Inc."),
    VarlikEslesme("GOOG", "USA_STOCK", "GOOG", aciklama="Alphabet Inc"),
    VarlikEslesme("INTC", "USA_STOCK", "INTC", aciklama="Intel"),
    VarlikEslesme("JPM", "USA_STOCK", "JPM", aciklama="JPMorgan Chase & Co."),
    VarlikEslesme("KO", "USA_STOCK", "KO", aciklama="Coca-Cola Company"),
    VarlikEslesme("LLY", "USA_STOCK", "LLY", aciklama="Eli Lilly and Company"),
    VarlikEslesme("META", "USA_STOCK", "META", aciklama="Meta Platforms Inc"),
    VarlikEslesme("MSFT", "USA_STOCK", "MSFT", aciklama="Microsoft Corporation"),
    VarlikEslesme("TSLA", "USA_STOCK", "TSLA", aciklama="Tesla Inc."),
    VarlikEslesme("NVDA", "USA_STOCK", "NVDA", aciklama="Nvidia"),
    VarlikEslesme("T", "USA_STOCK", "T", aciklama="AT&T Inc."),
    VarlikEslesme("WMT", "USA_STOCK", "WMT", aciklama="Walmart Inc."),
    # --- ETF ---------------------------------------------------------------
    VarlikEslesme("QQQ", "ETF", "QQQ", aciklama="Invesco QQQ Trust"),
    VarlikEslesme("SPY", "ETF", "SPY", aciklama="SPDR S&P 500 ETF Trust"),
    VarlikEslesme("VTI", "ETF", "VTI", aciklama="Vanguard Total Stock Market ETF"),
    # --- Emtia -------------------------------------------------------------
    VarlikEslesme("BAKIR", "COMMODITY", "HG=F", aciklama="Bakir vadeli"),
    VarlikEslesme("BRENT", "COMMODITY", "BZ=F", aciklama="Brent petrol vadeli"),
    VarlikEslesme("MISIR", "COMMODITY", "ZC=F", aciklama="Misir vadeli"),
    # --- Tahvil getirisi ---------------------------------------------------
    VarlikEslesme("US10Y", "BOND", "^TNX", aciklama="ABD 10 yil tahvil getirisi"),
    # --- Kripto: varsayilan calistirmada KAPALI ----------------------------
    # Gorevin kapsaminda degil; `--kategori CRYPTO` ile acikca istenirse
    # calisir. Fiyatlar USD cinsindendir (assets.currency = 'USD').
    VarlikEslesme("BTC", "CRYPTO", "BTC-USD", aciklama="Bitcoin"),
    VarlikEslesme("ETH", "CRYPTO", "ETH-USD", aciklama="Ethereum"),
    VarlikEslesme("SOL", "CRYPTO", "SOL-USD", aciklama="Solana"),
    VarlikEslesme("USDT", "CRYPTO", "USDT-USD", aciklama="Tether"),
)

#: `--kategori` verilmediginde toplanan gruplar. Kripto disarida: gorevde
#: istenen kume hisse + altin + doviz + ABD hissesidir.
#:
#: COMMODITY, ETF ve BOND 26 Agustos 2026'da eklendi - bu varliklar da
#: varsayilan calistirmada guncellensin diye. CRYPTO hala DISARIDA: onceki
#: karar korunuyor, `--kategori CRYPTO` ile acikca istenmesi gerekir.
VARSAYILAN_KATEGORILER: tuple[str, ...] = (
    "INDEX",
    "STOCK",
    "FOREX",
    "GOLD",
    "USA_STOCK",
    "COMMODITY",
    "ETF",
    "BOND",
)

#: Yahoo'da guvenilir karsiligi olmadigi icin hic eslenmemis DB sembolleri.
#: Raporda "atlandi" olarak gosterilir ki eksik veri sessizce kaybolmasin.
#:
#: 26 Agustos 2026: asagidaki bes varlik istendi ama Yahoo'da veri DONMEDI
#: (canli test edildi, hepsi bos/404). Veritabanina HIC eklenmediler -
#: sahte fiyatla yer tutucu satir acmak yerine acik boslugu kayda gecirmek
#: tercih edildi (TR10Y icin verilen kararla ayni yaklasim):
#:
#:   TI1, TTA, AFA  -> TEFAS yatirim fonu kodlari olabilir; Yahoo Finance
#:                     Turkiye yatirim fonlarini indekslemiyor.
#:   TR 2 Yil       -> Turkiye tahvil getirisi. TR10Y ile ayni sorun; denenen
#:                     TR2YT=RR / ^TR2Y / TURKEY2Y sembollerinin hicbiri veri
#:                     dondurmedi.
#:   Eurobond       -> Tek bir enstruman degil, bir varlik SINIFI. Once hangi
#:                     ihrac (vade/kupon) izlenecegine karar verilmeli.
#:
#: GBP kullanici karariyla ATLANDI (Yahoo'da GBPTRY=X mevcut ve calisiyor -
#: teknik bir engel yok, istenmedi).
ESLENMEYEN_SEMBOLLER: tuple[str, ...] = (
    "TI1",
    "TTA",
    "AFA",
    "TR2Y",
    "EUROBOND",
)


def eslesmeleri_getir(kategoriler: list[str] | None = None) -> list[VarlikEslesme]:
    """Istenen kategorilerdeki eslesmeleri doner.

    Args:
        kategoriler: `asset_categories.code` listesi. `None` ise
            `VARSAYILAN_KATEGORILER` kullanilir.
    """
    secili = tuple(kategoriler) if kategoriler else VARSAYILAN_KATEGORILER
    buyuk = {k.upper() for k in secili}
    return [e for e in ESLESMELER if e.kategori in buyuk]


def ons_usd_to_gram_try(ons_usd: float, usdtry: float) -> float:
    """Ons/USD fiyatini gram/TRY'ye cevirir.

    Ornek: 4458.10 USD/ons ve 47.8960 USD/TRY ->
        4458.10 / 31.1034768 = 143.33 USD/gram
        143.33 * 47.8960     = 6864.63 TRY/gram
    """
    if ons_usd <= 0 or usdtry <= 0:
        raise ValueError("Ons fiyati ve USD/TRY kuru pozitif olmalidir.")
    return (ons_usd / TROY_ONS_GRAM) * usdtry
