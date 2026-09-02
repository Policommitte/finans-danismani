"""Tahmin katmaninin ortak sozlesmesi.

Grafik tarafinin ihtiyaci basit: her gelecek gun icin bir NOKTA ve bir
BANT (alt/ust). Model detayi (TimesFM kuantilleri, shrinkage agirligi,
drift terimi) bu sinirin GERISINDE kalir - frontend hangi modelin
calistigini bilmez, model degistirilse arayuz degismez.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class TahminNoktasi(BaseModel):
    """Gelecekteki TEK bir gun.

    `alt`/`ust` %80 tahmin araligidir: olculen gercek kapsam %79,1
    (hedef %80). Yani "bu bandin disina cikma ihtimali ~%20"dir ve bu
    rakam UYDURMA DEGIL, 378 kesitlik backtest'te dogrulanmistir.
    """

    tarih: str = Field(description="ISO gun (YYYY-AA-GG)")
    deger: float = Field(description="Nokta tahmini")
    alt: float = Field(description="%80 araliginin alt siniri")
    ust: float = Field(description="%80 araliginin ust siniri")


class Tahmin(BaseModel):
    """Bir varligin (ya da portfoyun) ileriye donuk tahmini."""

    sembol: str
    #: Tahminin dayandigi SON GERCEK fiyat. Grafikte kesikli cizgi bu
    #: noktadan baslar - aksi halde gercek seriyle tahmin arasinda gorsel
    #: bir kopukluk olusur.
    son_fiyat: float
    #: Son gercek gozlemin tarihi. Kesikli cizginin baslangic noktasi.
    son_tarih: str
    noktalar: list[TahminNoktasi] = Field(default_factory=list)
    #: Uretimde kullanilan model/yapilandirma etiketi (izlenebilirlik).
    model: str = ""
    #: Kullaniciya gosterilecek dogruluk uyarisi. ZORUNLU alan degil ama
    #: arayuzde gosterilmesi URUN KARARIDIR: olculen dogruluk naive'e cok
    #: yakin, yanlis guven verilmemeli.
    uyari: str = ""

    def bos_mu(self) -> bool:
        return not self.noktalar
