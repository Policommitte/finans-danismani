"""Belge boru hattinin ORTAK SOZLESMESI.

Boru hatti uc bagimsiz parcadan gecer ve her biri farkli bir teknolojiyle
calisir:

    ayristirma (pdfplumber/openpyxl/vision)  ->  AyristirilmisBelge
    analiz     (LLM)                          ->  AnalizSonucu
    derleme    (ReportLab + matplotlib)       ->  PDF baytlari

Aradaki modeller BURADA tanimlanir ki parcalar birbirinin ic detayini
bilmesin: PDF derleyici `pdfplumber` diye bir sey oldugunu, ayristirici da
rapor duzenini bilmez.

⚠️ `AnalizSonucu` ayni zamanda LLM'DEN BEKLENEN JSON'un semasidir. Modelden
duz metin degil yapilandirilmis cikti istenmesinin sebebi: tablo ve grafik
DETERMINISTIK cizilmelidir. Serbest metinden sayi ayiklamaya calismak
("%18 buyume" ifadesini regex'le yakalamak) sessiz hatalar uretir - model
"18" yerine "onsekiz" yazdiginda grafik bos cikar ve kimse fark etmez.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

#: Desteklenen belge turleri. Kullanici bunlarin disinda bir sey yuklerse
#: istek daha ayristirmaya GIRMEDEN reddedilir (bkz. `parser.belge_turu`).
BelgeTuru = str  # "pdf" | "excel" | "gorsel"


class Tablo(BaseModel):
    """Belgeden cikarilan tek bir tablo.

    `basliklar` BOS OLABILIR: her tabloda basligi olan bir ilk satir yoktur
    (ozellikle PDF'lerde). Bos birakilirsa rapor tabloyu bassiz cizer -
    uydurma baslik URETILMEZ.
    """

    basliklar: list[str] = Field(default_factory=list)
    satirlar: list[list[str]] = Field(default_factory=list)
    kaynak: str = ""  # "sayfa 3" / "Sayfa1 (Excel)" gibi insan okur etiket


class AyristirilmisBelge(BaseModel):
    """Ham dosyanin makine tarafindan okunabilir hale gelmis hali."""

    tur: BelgeTuru
    dosya_adi: str
    metin: str = ""
    tablolar: list[Tablo] = Field(default_factory=list)
    sayfa_sayisi: int = 0
    #: Ayristirma sirasinda olusan ama isi DURDURMAYAN sorunlar. Kullaniciya
    #: raporun dipnotunda gosterilir; sessizce yutulmaz.
    #: Ornek: "12 sayfanin 3'u taranmis goruntu, metin cikarilamadi".
    uyarilar: list[str] = Field(default_factory=list)

    def ozet_girdi(self, azami_karakter: int) -> str:
        """LLM'e gonderilecek girdiyi uretir ve BUTCEYE SIGDIRIR.

        Neden kirpiliyor: bir yillik faaliyet raporu 300 sayfa olabilir;
        tamamini gondermek baglam penceresini asar ve istek 400 ile doner.
        Kirpma BASTAN yapilir - finansal belgelerde ozet, bilanco ve yonetim
        degerlendirmesi genellikle bas taraftadir.
        """
        parcalar: list[str] = []
        if self.metin.strip():
            parcalar.append(self.metin.strip())

        for tablo in self.tablolar:
            satir_metni = ["\t".join(tablo.basliklar)] if tablo.basliklar else []
            satir_metni += ["\t".join(hucre for hucre in satir) for satir in tablo.satirlar]
            if satir_metni:
                parcalar.append(f"[TABLO - {tablo.kaynak}]\n" + "\n".join(satir_metni))

        tam = "\n\n".join(parcalar)
        if len(tam) <= azami_karakter:
            return tam

        # Kirpma notu BUTCEYE DAHILDIR. Sonuna eklenip toplam asilsaydi
        # fonksiyon adiyla celisirdi ve cagiran taraf baglam penceresini
        # tasirdi - "azami" derken gercekten azami olmali.
        not_metni = "\n\n[... belge uzun oldugu icin kirpildi ...]"
        kalan = max(azami_karakter - len(not_metni), 0)
        return tam[:kalan] + not_metni


class Gosterge(BaseModel):
    """Ozet tablosunda gosterilecek TEK bir satir.

    `deger` metindir (birimiyle birlikte, "1,2 milyon TL"): kullaniciya
    gosterilecek olan budur. `sayisal` ise grafik icin opsiyonel ham degerdir;
    model veremezse grafik o gostergeyi atlar, tablo yine dogru gorunur.
    """

    ad: str
    deger: str
    sayisal: float | None = None


class Grafik(BaseModel):
    """Modelin onerdigi TEK grafik.

    Grafik ZORUNLU DEGILDIR: her belgede cizmeye deger sayisal seri
    bulunmaz. Model `None` dondururse rapor grafiksiz uretilir - anlamsiz
    bir grafik cizmektense hic cizmemek yeglenir.
    """

    tur: str = "bar"  # bar | line | pie
    baslik: str = ""
    etiketler: list[str] = Field(default_factory=list)
    degerler: list[float] = Field(default_factory=list)
    eksen_adi: str = ""

    def gecerli_mi(self) -> bool:
        """Cizilebilir mi? Bozuk/eksik veri sessizce grafik URETMEMELI."""
        return (
            len(self.etiketler) == len(self.degerler)
            and len(self.degerler) >= 2
            and self.tur in {"bar", "line", "pie"}
            and all(isinstance(d, (int, float)) for d in self.degerler)
        )


class AnalizSonucu(BaseModel):
    """LLM'in urettigi yapilandirilmis analiz - raporun icerigi.

    Tum alanlar VARSAYILANLI: model bir alani atlarsa rapor o bolumu
    cizmeden devam eder. Kismi rapor, hic rapor olmamasindan iyidir.
    """

    baslik: str = "Belge Analiz Raporu"
    ozet: str = ""
    bulgular: list[str] = Field(default_factory=list)
    gostergeler: list[Gosterge] = Field(default_factory=list)
    grafik: Grafik | None = None
    riskler: list[str] = Field(default_factory=list)
    #: Kullanicinin finansal terim bilmeden anlayabilecegi kapanis paragrafi.
    #: Urun geregi ZORUNLU hedef: rapor "sade dille" bitmeli.
    sade_aciklama: str = ""

    def bos_mu(self) -> bool:
        """Gosterilecek hicbir sey uretilememis mi?"""
        return not any(
            [self.ozet, self.bulgular, self.gostergeler, self.riskler, self.sade_aciklama]
        )
