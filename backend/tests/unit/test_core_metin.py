"""`app.core.metin.icerikten_baslik` - bos baslik telafisi.

`rag.documents.baslik` dokumanlarin ~%35'inde bostu; ayni siteden ayni gun
gelen iki farkli haber kaynak kartinda BIREBIR AYNI gorunuyordu. Bu
fonksiyon iki yerden cagrilir (goruntu ani + kalici temizlik script'i) ve
IKISININ DE ayni metni uretmesi sart.
"""

from __future__ import annotations

import pytest

from app.core.metin import icerikten_baslik


@pytest.mark.parametrize("girdi", ["", "   ", "\n\t  \n", None])
def test_bos_icerik_bos_baslik_uretir(girdi):
    assert icerikten_baslik(girdi) == ""


def test_ilk_cumle_noktalama_ile_kesilir():
    metin = "Merkez Bankasi faizi sabit tuttu. Karar piyasada beklentiye uygun karsilandi."
    assert icerikten_baslik(metin) == "Merkez Bankasi faizi sabit tuttu."


@pytest.mark.parametrize("isaret", [".", "!", "?"])
def test_uc_cumle_sonu_isareti_de_taninir(isaret):
    assert icerikten_baslik(f"Kisa cumle{isaret} Devami burada.") == f"Kisa cumle{isaret}"


def test_sinirdan_uzun_ilk_cumle_kelime_sinirinda_kirpilir():
    """Cumle sinirindan sonra geliyorsa (konum > en_fazla) kesme kullanilmaz;
    kelime sinirindan kirpilir ve elips eklenir."""
    metin = "kelime " * 30 + "son. Ikinci cumle."
    baslik = icerikten_baslik(metin, en_fazla=40)
    assert len(baslik) <= 41  # 40 + elips
    assert baslik.endswith("…")
    assert not baslik.endswith(" …")


def test_sinirin_altindaki_tek_cumle_oldugu_gibi_doner():
    assert icerikten_baslik("Kisa bir haber metni") == "Kisa bir haber metni"


def test_bosluklar_tek_bosluga_indirgenir():
    """Kaynak HTML'den geldigi icin satir sonu ve cift bosluk yaygin."""
    assert icerikten_baslik("Faiz\n\n  karari   aciklandi") == "Faiz karari aciklandi"


def test_farkli_icerikler_farkli_baslik_uretir():
    """Asil regresyon: ayni gun/ayni siteden iki haber ayirt edilebilmeli."""
    a = icerikten_baslik("Dolar kuru geriledi. Detaylar...")
    b = icerikten_baslik("Altin rekor tazeledi. Detaylar...")
    assert a != b


def test_deterministiktir():
    """Iki cagiran (goruntu ani + temizlik script'i) ayni sonucu almali."""
    metin = "Borsa gunu yukselisle kapatti. BIST 100 endeksi %1,2 arti."
    assert icerikten_baslik(metin) == icerikten_baslik(metin)
