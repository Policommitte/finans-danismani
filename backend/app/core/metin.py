"""Metin yardimcilari - saf fonksiyonlar, uygulama bagimliligi YOK.

`app/core/quantity.py` ile ayni desen: yalnizca standart kutuphane import
edilir. Bu ONEMLI - buradaki fonksiyonlar hem calisma zamaninda (ajanlar) hem
de bakim script'lerinde kullaniliyor; script'in LLM/orkestrasyon yiginini
yuklemek zorunda kalmamasi icin modul hafif kalmali.
"""

from __future__ import annotations


def icerikten_baslik(icerik: str, en_fazla: int = 80) -> str:
    """Metnin ilk cumlesinden okunabilir bir baslik uretir.

    NEDEN GEREKLI: `rag.documents.baslik` dokumanlarin %35'inde BOS
    (82/234 - olculdu). Baslik bos olunca kaynak satiri yalnizca tarih ve
    site adiyla kaliyordu: "(2026-08-13) · BigPara Borsa". Ayni siteden ayni
    gunlerde gelen iki FARKLI haber kullaniciya BIREBIR AYNI gorunuyordu.

    IKI YERDEN CAGRILIR ve ayni sonucu uretmeleri sart:
      - `market_research._to_source` - goruntu aninda, veri bozuksa telafi.
      - `scripts/temizle_dokuman_basliklari.py` - veriyi KALICI olarak duzeltir.
    Iki ayri kopya olsaydi ayni dokuman arayuzde baska, veritabaninda baska
    bir baslik tasirdi; bu yuzden fonksiyon burada, ortak ve hafif bir modulde
    duruyor.
    """
    metin = " ".join((icerik or "").split())
    if not metin:
        return ""

    # Ilk cumle sinirinda kes; yoksa kelime sinirinda kirp.
    for isaret in (". ", "! ", "? "):
        konum = metin.find(isaret)
        if 0 < konum <= en_fazla:
            return metin[: konum + 1].strip()

    if len(metin) <= en_fazla:
        return metin
    kirpik = metin[:en_fazla].rsplit(" ", 1)[0]
    return f"{kirpik}…"
