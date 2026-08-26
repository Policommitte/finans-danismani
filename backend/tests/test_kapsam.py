"""Kapsam siniflandirici testleri (app/engine/kapsam.py).

Bu dosyanin cogu vakasi GERCEK KULLANIM sirasinda ortaya cikmis hatalardan
turetilmistir; parametre listelerini kisaltmadan once ilgili yorumu okuyun.

Iki yonlu risk vardir ve ikisi de sinaniyor:

  YANLIS POZITIF  Gercek bir finans sorusu sohbet sanilir -> kullanici
                  cevapsiz kalir. En pahalisi budur.
  YANLIS NEGATIF  Hakaret ya da konu disi soru finans sanilir -> sistem
                  portfoy dokumu uretir. Bu modul zaten bunu onlemek icin var.
"""

import pytest

from app.engine.kapsam import (
    KAPSAM_BASKA_KISI,
    KAPSAM_BELIRSIZ,
    KAPSAM_DISI,
    KAPSAM_FINANS,
    KAPSAM_KUFUR,
    KAPSAM_SELAMLAMA,
    KAPSAM_TESEKKUR,
    KAPSAM_VEDA,
    KISA_YANIT_KAPSAMLARI,
    kapsam_belirle,
    kisa_yanit,
)

# ---------------------------------------------------------------------------
# Finans sorulari - HICBIRI kisa yanita dusmemeli
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu",
    [
        "Portföyüm nasıl gidiyor?",
        "Riskim ne durumda?",
        "Portföyümün dağılımı nedir?",
        "X şirketinin son çeyrek bilançosu nasıl?",
        # Canli sistemde hataya yol acmis iki gercek soru:
        "bana thyaonun son 1 yıldaki karlılık oranıyla ilgili bilgi verir misin",
        "THYAO hissesinin son 1 yıldaki karlılığı",
        "SASA neden düştü?",
        "dolar kuru ne olur",
        "altın almalı mıyım",
        "bitcoin yükselir mi",
        "BIST 100 endeksi bugün ne durumda",
        "emeklilik için nasıl birikim yapmalıyım",
        "kredi kartı borcumu nasıl kapatırım",
        "enflasyon karşısında param nasıl korunur",
        "hangi fona yatırım yapmalıyım",
    ],
)
def test_finans_sorulari_ajanlara_gider(sorgu):
    assert kapsam_belirle(sorgu) == KAPSAM_FINANS


def test_buyuk_harfli_sembol_finans_sayilir():
    """'THYAO ne kadar?' hicbir finans kokune dusmez ama sembol tasir."""
    assert kapsam_belirle("THYAO ne kadar?") == KAPSAM_FINANS


# ---------------------------------------------------------------------------
# Kufur
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu",
    [
        # Kullanicinin sisteme gonderdigi gercek mesaj:
        "ananı sikiyom senı foflofoş etsinler",
        "siktir git",
        "sen bir gerizekalısın",
        "aptal bot",
        "amk",
        "bu ne saçmalık ya",
    ],
)
def test_hakaret_kisa_yanita_duser(sorgu):
    assert kapsam_belirle(sorgu) == KAPSAM_KUFUR


@pytest.mark.parametrize(
    "sorgu",
    [
        "amk portföyüm neden düştü",
        "aq bu enflasyon ne zaman düşecek",
    ],
)
def test_dolgu_kufru_gercek_soruyu_iptal_etmez(sorgu):
    """Sinirli ama gercek soru soran kullaniciya cevap verilmeli."""
    assert kapsam_belirle(sorgu) == KAPSAM_FINANS


@pytest.mark.parametrize(
    "sorgu",
    [
        # "sikinti" normalize edilince "sik" kokunu icerir - desen bunu
        # hakaret saymamali, yoksa nakit akisi sorulari engellenir.
        "nakit sıkıntısı yaşıyorum ne yapmalıyım",
        "piyasa sıkışık görünüyor",
    ],
)
def test_sikinti_kelimesi_hakaret_sayilmaz(sorgu):
    assert kapsam_belirle(sorgu) == KAPSAM_FINANS


# ---------------------------------------------------------------------------
# Sohbet kaliplari
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu, beklenen",
    [
        ("Merhaba", KAPSAM_SELAMLAMA),
        ("selam", KAPSAM_SELAMLAMA),
        ("günaydın", KAPSAM_SELAMLAMA),
        ("nasılsın?", KAPSAM_SELAMLAMA),
        ("teşekkürler", KAPSAM_TESEKKUR),
        ("sağ ol", KAPSAM_TESEKKUR),
        ("eyvallah", KAPSAM_TESEKKUR),
        ("görüşürüz", KAPSAM_VEDA),
        ("hoşça kal", KAPSAM_VEDA),
    ],
)
def test_sohbet_kaliplari(sorgu, beklenen):
    assert kapsam_belirle(sorgu) == beklenen


def test_buyuk_harfli_selam_sembol_sanilmaz():
    """'SELAM' bes harfli buyuk bir kelimedir - sembol sezgisi yutmamali."""
    assert kapsam_belirle("SELAM") == KAPSAM_SELAMLAMA


@pytest.mark.parametrize(
    "sorgu",
    [
        "Merhaba, portföyüm nasıl?",
        "selam risk durumum ne alemde",
        "teşekkürler, peki dolar ne olur",
    ],
)
def test_selamlama_ile_baslayan_gercek_soru_finanstir(sorgu):
    """Nezaket kelimesi sorunun kendisini gizlememeli."""
    assert kapsam_belirle(sorgu) == KAPSAM_FINANS


# ---------------------------------------------------------------------------
# Kapsam disi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu",
    [
        "sen kimsin",
        "hangi modelsin",
        "hava durumu nasıl",
        "bana bir şiir yaz",
        "maç skoru kaç",
        "yemek tarifi ver",
        "bana bir şaka yap",
        "python kod yaz",
    ],
)
def test_baska_alanlar_kapsam_disi(sorgu):
    assert kapsam_belirle(sorgu) == KAPSAM_DISI


def test_fenerbahce_hissesi_finans_maci_kapsam_disi():
    """FENER gercekten BIST'te islem goruyor - kelime tek basina yetmez."""
    assert kapsam_belirle("Fenerbahçe hissesi nasıl gidiyor") == KAPSAM_FINANS
    assert kapsam_belirle("Fenerbahçe maç skoru neydi") == KAPSAM_DISI


# ---------------------------------------------------------------------------
# Belirsiz + devam turu
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sorgu", ["peki şimdi?", "bunu bir daha anlat", "", "   "])
def test_sinyalsiz_ilk_tur_netlestirme_ister(sorgu):
    assert kapsam_belirle(sorgu) == KAPSAM_BELIRSIZ


@pytest.mark.parametrize("sorgu", ["peki şimdi?", "bunu bir daha anlat", "neden?"])
def test_devam_turunda_sinyalsiz_soru_ajanlara_gider(sorgu):
    """Baglam onceki turda; cok turlu sohbet kirilmamali (FR-CHAT-03)."""
    assert kapsam_belirle(sorgu, devam_turu=True) == KAPSAM_FINANS


def test_devam_turu_hakareti_gecirmez():
    """Devam turu, kapsam kararini tamamen devre disi BIRAKMAZ."""
    assert kapsam_belirle("ananı sikiyom", devam_turu=True) == KAPSAM_KUFUR
    assert kapsam_belirle("merhaba", devam_turu=True) == KAPSAM_SELAMLAMA


# ---------------------------------------------------------------------------
# Yanit tablosu
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("kapsam", sorted(KISA_YANIT_KAPSAMLARI))
def test_her_kapsamin_bir_yaniti_var(kapsam):
    metin = kisa_yanit(kapsam)
    assert metin and metin.strip()


def test_bilinmeyen_kapsam_netlestirme_yanitina_duser():
    assert kisa_yanit("boyle_bir_kapsam_yok") == kisa_yanit(KAPSAM_BELIRSIZ)


def test_kisa_yanitlar_yatirim_tavsiyesi_ibaresi_tasimaz():
    """Ibare finansal BILGI iceren ciktilar icindir; burada bilgi yoktur."""
    for kapsam in KISA_YANIT_KAPSAMLARI:
        assert "yatırım tavsiyesi değildir" not in kisa_yanit(kapsam)


def test_kufur_yaniti_hakarete_karsilik_vermez():
    """Yanit sinir cizer; tartismaya girmez, kufru tekrarlamaz."""
    metin = kisa_yanit(KAPSAM_KUFUR).lower()
    assert "küfür" not in metin and "hakaret" not in metin
    assert len(metin) < 200


# ---------------------------------------------------------------------------
# Baska kisinin verisi
# ---------------------------------------------------------------------------
#
# Sizinti riski YOKTUR (kimlik contextvar'dan gelir, tool semasinda degil).
# Buradaki dert YANLIS ATIF: sistem eskiden bu soruya giris yapmis
# kullanicinin rakamlarini dondurup "Ayse'nin portfoyu ..." diyordu.
#
# ⚠️ TESPIT KUCUK/BUYUK HARFE DUYARSIZDIR. Once buyuk harfe dayanan bir
# ayrim denendi (kisi adi = Baslik Bicimi, hisse kodu = TAMAMEN BUYUK) ama
# canlida kirildi: kullanicilar sohbette neredeyse hep kucuk harf yazar
# ("ayşenin portföy bilgilerini getirir misin?" hicbir ozel ad buyuk
# yazilmadan geldi ve sistem soruyu normal finans sorusu sanip Mehmet'in
# verisini "Ayse'nin" diye sundu). Asagidaki testlerin tamami hem buyuk hem
# kucuk yazimla kapsanir.


@pytest.mark.parametrize(
    "sorgu",
    [
        # Buyuk harfle (Baslik Bicimi)
        "Ayşe'nin portföyünü göster",
        "Mehmet'in bakiyesi ne kadar",
        "Zeynep'in risk durumu nedir",
        "Can'ın toplam portföy değeri",
        "Elifin yatırımlarını listele",
        "Büşra'nın hesabını aç",
        "Ahmet'in kazancı ne oldu",
        # Kucuk harfle - GERCEK sohbette en sik gorulen yazim
        "ayşenin portföy bilgilerini getirir misin?",
        "mehmetin bakiyesi ne kadar",
        "zeynepin risk durumu nedir",
        "canın toplam portföy değeri",
        "elifin yatırımlarını listele",
        "büşranın hesabını aç",
    ],
)
def test_baska_kisinin_verisi_reddedilir(sorgu):
    assert kapsam_belirle(sorgu) == KAPSAM_BASKA_KISI


@pytest.mark.parametrize(
    "sorgu",
    [
        # Kendi verisi - normal akisa gitmeli.
        "Portföyüm nasıl gidiyor?",
        "Benim portföyümün riski ne",
        "kendi portföyümü göster",
        "Riskim ne durumda?",
        # ⚠️ CUMLE BASINDA BUYUK HARF + IYELIK+TAMLAMA EKI UST USTE.
        # "Portfoy-um-un" hem "benim portfoyumun" hem de yuzeysel olarak
        # "Ozel ad + tamlayan eki" gibi gorunur. `_govde_dislaniyor_mu` bu
        # cift-ek durumunu (iyelik CIKARILDIKTAN sonra KOK listesiyle
        # eslesme) ele almazsa bu sorular BASKA KISI saniliyordu (olculdu).
        "Portfoyumun riski nedir?",
        "Portföyümün dağılımı nedir?",
        "Hesabımın bakiyesi ne",
        "hesabımın bakiyesi ne",
        "Yatırımımın getirisi ne kadar",
        "riskimin ne olduğunu söyle",
        # ⚠️ HISSE/VARLIK KODLARI KISI SANILMAMALI - hem buyuk hem kucuk yazim.
        "SASA'nın zararı ne durumda",
        "sasanın zararı ne durumda",
        "ASELS'in kazancı nedir",
        "THYAO'nun fiyatı ne kadar",
        "BTC'nin portföydeki payı",
        "Bitcoin'in değeri ne",
        "bitcoinin degeri ne",
        "altının değeri ne",
        "dolarin kuru ne",
        # ⚠️ KURUM/PIYASA - insan degil, yanlis-atif riski tasimaz (MCP
        # tool'lari zaten yalnizca giris yapmis kullaniciyi getirir).
        "şirketin portföyü ne durumda",
        "TCMB'nin kararı ne oldu",
        "bankanın faiz oranı nedir",
    ],
)
def test_kendi_verisi_ve_hisse_kodlari_etkilenmez(sorgu):
    assert kapsam_belirle(sorgu) != KAPSAM_BASKA_KISI


def test_baska_kisi_kisa_yanit_kapsamlarinda():
    """Ajan fan-out'u ATLANMALI: soru hicbir ajana gitmemeli."""
    assert KAPSAM_BASKA_KISI in KISA_YANIT_KAPSAMLARI


def test_baska_kisi_yaniti_ne_yapabildigini_soyler():
    metin = kisa_yanit(KAPSAM_BASKA_KISI)
    assert "getiremem" in metin
    assert "kendi" in metin.lower() or "giriş yapmış" in metin.lower()
