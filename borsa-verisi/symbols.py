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
    # --- BIST hisseleri: Yahoo'da ".IS" eki ile ---------------------------
    VarlikEslesme("THYAO", "STOCK", "THYAO.IS", aciklama="Turk Hava Yollari"),
    VarlikEslesme("GARAN", "STOCK", "GARAN.IS", aciklama="Garanti BBVA"),
    VarlikEslesme("TCELL", "STOCK", "TCELL.IS", aciklama="Turkcell"),
    VarlikEslesme("SASA", "STOCK", "SASA.IS", aciklama="Sasa Polyester"),
    VarlikEslesme("ASELS", "STOCK", "ASELS.IS", aciklama="Aselsan"),
    VarlikEslesme("EREGL", "STOCK", "EREGL.IS", aciklama="Erdemir"),
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
    VarlikEslesme("TSLA", "USA_STOCK", "TSLA", aciklama="Tesla Inc."),
    VarlikEslesme("NVDA", "USA_STOCK", "NVDA", aciklama="Nvidia"),
    # --- Kripto: varsayilan calistirmada KAPALI ----------------------------
    # Gorevin kapsaminda degil; `--kategori CRYPTO` ile acikca istenirse
    # calisir. Fiyatlar USD cinsindendir (assets.currency = 'USD').
    VarlikEslesme("BTC", "CRYPTO", "BTC-USD", aciklama="Bitcoin"),
    VarlikEslesme("ETH", "CRYPTO", "ETH-USD", aciklama="Ethereum"),
    VarlikEslesme("SOL", "CRYPTO", "SOL-USD", aciklama="Solana"),
    # ======================================================================
    # 26 Agustos 2026'da eklenen varliklar
    # ======================================================================
    # --- BIST hisseleri ---------------------------------------------------
    VarlikEslesme("BIMAS", "STOCK", "BIMAS.IS", aciklama="BIM Birlesik Magazalar"),
    VarlikEslesme("TUPRS", "STOCK", "TUPRS.IS", aciklama="Tupras"),
    VarlikEslesme("KCHOL", "STOCK", "KCHOL.IS", aciklama="Koc Holding"),
    VarlikEslesme("SISE", "STOCK", "SISE.IS", aciklama="Sisecam"),
    VarlikEslesme("AKCNS", "STOCK", "AKCNS.IS", aciklama="Akcansa"),
    VarlikEslesme("TOASO", "STOCK", "TOASO.IS", aciklama="Tofas"),
    VarlikEslesme("KONTR", "STOCK", "KONTR.IS", aciklama="Kontrolmatik"),
    # --- ABD hisseleri ----------------------------------------------------
    #
    # HISSE SINIFI: birden fazla sinifi olan sirketlerde EN DUSUK FIYATLI
    # sinif secildi (kullanici karari, 26 Agustos 2026):
    #   Alphabet  -> GOOG  (Class C, 339.10)   ; GOOGL Class A 342.00 idi
    #   Berkshire -> BRK-B (504.91)            ; BRK-A 756.928 idi
    VarlikEslesme("MSFT", "USA_STOCK", "MSFT", aciklama="Microsoft Corporation"),
    VarlikEslesme("AMZN", "USA_STOCK", "AMZN", aciklama="Amazon Inc"),
    VarlikEslesme("GOOG", "USA_STOCK", "GOOG", aciklama="Alphabet Inc (Class C)"),
    VarlikEslesme("META", "USA_STOCK", "META", aciklama="Meta Platforms Inc"),
    VarlikEslesme("BRK-B", "USA_STOCK", "BRK-B", aciklama="Berkshire Hathaway (Class B)"),
    VarlikEslesme("JPM", "USA_STOCK", "JPM", aciklama="JPMorgan Chase & Co."),
    VarlikEslesme("LLY", "USA_STOCK", "LLY", aciklama="Eli Lilly and Company"),
    VarlikEslesme("INTC", "USA_STOCK", "INTC", aciklama="Intel"),
    VarlikEslesme("WMT", "USA_STOCK", "WMT", aciklama="Walmart Inc."),
    VarlikEslesme("KO", "USA_STOCK", "KO", aciklama="Coca-Cola Company"),
    VarlikEslesme("T", "USA_STOCK", "T", aciklama="AT&T Inc."),
    # --- Kripto (varsayilanda KAPALI, yukaridaki notla ayni) --------------
    VarlikEslesme("USDT", "CRYPTO", "USDT-USD", aciklama="Tether"),
    # --- Emtia: Yahoo'da "=F" ekiyle vadeli kontrat -----------------------
    # Fiyatlar USD cinsindendir ve KONTRAT birimine baglidir (orn. bakir
    # libre/pound, misir bushel basina sent). TRY'ye cevrilmez.
    VarlikEslesme("BRENT", "COMMODITY", "BZ=F", aciklama="Brent ham petrol vadeli"),
    VarlikEslesme("BAKIR", "COMMODITY", "HG=F", aciklama="COMEX bakir vadeli"),
    VarlikEslesme("MISIR", "COMMODITY", "ZC=F", aciklama="CBOT misir vadeli"),
    # --- ETF --------------------------------------------------------------
    VarlikEslesme("SPY", "ETF", "SPY", aciklama="SPDR S&P 500 ETF"),
    VarlikEslesme("QQQ", "ETF", "QQQ", aciklama="Invesco QQQ (Nasdaq 100)"),
    VarlikEslesme("VTI", "ETF", "VTI", aciklama="Vanguard Total Stock Market ETF"),
    # --- Tahvil -----------------------------------------------------------
    # ⚠️ ^TNX bir FIYAT DEGIL, GETIRI ORANIDIR (yuzde). `assets.currency`
    # bu yuzden 'PCT' - 'USD' yazmak "4.66 dolar" gibi okunur ve yaniltici
    # olur. Diger varliklarla ayni sutunda durur ama BIRIMI FARKLIDIR;
    # yorumlayan taraf (ajan/frontend) bunu currency alanindan ayirt eder.
    VarlikEslesme("US10Y", "BOND", "^TNX", aciklama="ABD 10 yillik tahvil getirisi (%)"),
)

#: `--kategori` verilmediginde toplanan gruplar. Kripto disarida: gorevde
#: istenen kume hisse + altin + doviz + ABD hissesidir.
#:
#: COMMODITY, ETF ve BOND 26 Agustos 2026'da eklendi - bu varliklar da
#: varsayilan calistirmada guncellensin diye. CRYPTO hala DISARIDA: onceki
#: karar korunuyor, `--kategori CRYPTO` ile acikca istenmesi gerekir.
VARSAYILAN_KATEGORILER: tuple[str, ...] = (
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
