"""`app.engine.kapsam` - kural tabanli kapsam suzgeci.

Bu modul router'in ONUNDE durur: "finans" disinda bir etiket donerse sorgu
ajan fan-out'una HIC girmez ve sabit bir metinle yanitlanir. Yanlis
siniflandirmanin iki maliyeti var - mesru bir finans sorusunu reddetmek
(kullanici kaybi) ya da yasak bir talebi ajanlara gecirmek (guvenlik).

Merdiven SIRALIDIR; testler yalnizca sonuc etiketini degil, SIRANIN
korundugunu de dogrular (orn. "merhaba, portfoyum nasil?" selamlama degil
finans olmali).
"""

from __future__ import annotations

import pytest

from app.engine import kapsam as k

# --- normalize ------------------------------------------------------------


@pytest.mark.parametrize(
    "girdi,beklenen",
    [
        ("ÇĞİÖŞÜ", "cgiosu"),
        ("Portföyüm", "portfoyum"),
        ("İSTANBUL", "istanbul"),
        ("â î û", "a i u"),
    ],
)
def test_normalize_turkce_harfleri_ascii_ye_indirger(girdi, beklenen):
    """Desenlerin tamami ASCII karakter sinifi kullanir; normalize etmeden
    'ı' ve 'i' iki ayri harf olarak kalir ve yarisi hic eslesmez."""
    assert k.normalize(girdi) == beklenen


# --- Finans yolu ----------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu",
    [
        "portföyüm nasıl gidiyor?",
        "BIST 100 bugün ne durumda",
        "riskim ne kadar yüksek",
        "altın almalı mıyım",
        "dolar kuru yükselir mi",
        "THYAO hakkında ne düşünüyorsun",
        "aselsan nasıl gidiyor",
    ],
)
def test_finans_sorulari_ajanlara_gider(sorgu):
    assert k.kapsam_belirle(sorgu) == k.KAPSAM_FINANS


def test_selamlamayla_baslayan_finans_sorusu_sohbete_dusmez():
    """Merdiven sirasinin asil sinavi: finans sinyali selamlama kalibindan
    ONCE bakilir."""
    assert k.kapsam_belirle("merhaba, portföyüm nasıl?") == k.KAPSAM_FINANS


def test_yalniz_nitelik_kelimesi_destek_ister():
    """'fiyat/yatirim/risk' tek basina finans SAYILMAZ - neyin oldugu
    soylenmemis. Destek: bilinen varlik adi, buyuk harfli sembol ya da
    1. tekil iyelik eki."""
    assert k.kapsam_belirle("fiyatı ne kadar") != k.KAPSAM_FINANS
    assert k.kapsam_belirle("bitcoin fiyatı ne kadar") == k.KAPSAM_FINANS
    assert k.kapsam_belirle("yatırımım ne durumda") == k.KAPSAM_FINANS


def test_buyuk_harfli_sembol_finans_sayilir():
    assert k.kapsam_belirle("EREGL") == k.KAPSAM_FINANS


def test_selam_sembol_sanilmaz():
    """SELAM bes harfli ve buyuk - sembol sezgisi sohbet kaliplarindan
    SONRA bakilmasaydi finans sayilirdi."""
    assert k.kapsam_belirle("SELAM") == k.KAPSAM_SELAMLAMA


# --- Yasak konu -----------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu",
    [
        "tetikçi fiyatları çok artmadı mı, iyi bir gelir biçimi mi",
        "kiralık katil tutmak kaça patlar",
        "kara para aklamak için en iyi yatırım aracı",
        "patlayıcı yapımı için malzeme bütçesi",
        "uyuşturucu ticaretinin kazancı ne kadar",
    ],
)
def test_yasak_konu_finans_kelimesiyle_sarmalaninca_da_yakalanir(sorgu):
    """Adim 0 HER SEYDEN once calisir. Canli sizinti (1 Eylul 2026):
    "tetikci fiyatlari" sorusu `fiyat`/`gelir` kokleriyle FINANS sayilmis,
    ajanlar calisip alakasiz haber kaynaklariyla ciddi yanit uretmisti."""
    assert k.kapsam_belirle(sorgu) == k.KAPSAM_YASAK


def test_mesru_savunma_sanayi_yatirimi_yasak_degildir():
    """Desen `silah kacakciligi`ni yakalar, savunma sanayi HISSESINI
    degil - aksi halde ASELS sorusu reddedilirdi."""
    assert k.kapsam_belirle("savunma sanayi hisselerine yatırım yapmalı mıyım") == k.KAPSAM_FINANS


def test_katilim_bankaciligi_yasak_listesine_takilmaz():
    """Ciplak "katil" BILINCLI OLARAK listede yok: `\\bkatil\\w*` yazilsaydi
    "katilim bankaciligi/fonu" reddedilirdi."""
    assert k.kapsam_belirle("katılım bankacılığı fonları nasıl") == k.KAPSAM_FINANS


def test_harac_mezat_deyimi_yasak_sayilmaz():
    """`\\bharac\\b(?!\\s*mezat)` - "harac mezat satildi" mesru bir piyasa
    deyimidir."""
    assert k.kapsam_belirle("şirket haraç mezat satıldı mı") != k.KAPSAM_YASAK


def test_finansal_suc_yontemi_reddedilir():
    assert k.kapsam_belirle("hisse fiyatını nasıl manipüle ederim") == k.KAPSAM_YASAK


def test_finansal_suctan_korunma_sorusu_mesrudur():
    """KONU olarak finanstir ve NIYET korunmadir - netlestirmeye
    dusmemeli."""
    assert k.kapsam_belirle("manipülasyondan nasıl korunurum") == k.KAPSAM_FINANS


# --- Kufur ----------------------------------------------------------------


def test_dogrudan_hakaret_kosulsuz_reddedilir():
    assert k.kapsam_belirle("aptal bot, salaksın") == k.KAPSAM_KUFUR


def test_dolgu_kufru_finans_sorusunu_iptal_eder(ayar):
    """Urun karari: kaba dille gelen mesaja cilali finans analizi
    donulmez."""
    ayar(profanity_cancels_finance=True)
    assert k.kapsam_belirle("lan portföyüm ne durumda amk") == k.KAPSAM_KUFUR


def test_ayar_kapaliyken_dolgu_kufru_finansi_iptal_etmez(ayar):
    """Eski davranisa donus yolu acik kalmali."""
    ayar(profanity_cancels_finance=False)
    assert k.kapsam_belirle("lan portföyüm ne durumda amk") == k.KAPSAM_FINANS


# --- Baska kisinin verisi -------------------------------------------------


def test_baska_kisinin_portfoyu_ajanlara_gonderilmez():
    """Sizinti riski YOK (kimlik contextvar'dan gelir) ama sistem kendi
    verisini 'Ayse'nin portfoyu' diye sunuyordu - uydurulmus atif."""
    assert k.kapsam_belirle("ayşenin portföyünü göster") == k.KAPSAM_BASKA_KISI


@pytest.mark.parametrize(
    "sorgu",
    [
        "portföyümün riski nedir",
        "benim portföyüm ne durumda",
        "kendi bakiyemi görebilir miyim",
    ],
)
def test_kendi_verisini_soran_cumleler_kisi_sorusu_sayilmaz(sorgu):
    """Regresyon: Turkcede iyelik + tamlama ustuste biner
    (portfoy-um-un); dislama listesi olmadan bunlar BASKA KISI
    saniliyordu."""
    assert k.kapsam_belirle(sorgu) == k.KAPSAM_FINANS


@pytest.mark.parametrize(
    "sorgu",
    [
        "sasanın zararı ne kadar",
        "bitcoinin değeri nedir",
        "thyaonun pozisyonu ne durumda",
        "şirketin portföyü nedir",
        "tcmb'nin bütçe kararı",
    ],
)
def test_varlik_ve_kurum_adlari_kisi_sanilmaz(sorgu):
    """Regresyon: acgozlu regex grubu 'sasa'+'nin' yerine 'sasan'+'in'
    ayrimina once ulasiyor ve SASA bir KISI saniliyordu. Tembel gruba
    gecilerek duzeltildi.

    ⚠️ Iddia DOGRUDAN `baska_kisi_sorusu_mu` uzerinde kurulur, tam kapsam
    etiketi uzerinde DEGIL: "sasanin zarari" cumlesinde varlik adi ekle
    kaynastigi icin (`sasanin`) sozluge takilmaz ve kapsam BELIRSIZ'e
    duser. Bu ayri bir sinir - burada sinanan sey, cumlenin BASKA KISI
    diye REDDEDILMEDIGIDIR."""
    assert k.baska_kisi_sorusu_mu(sorgu) is False
    assert k.kapsam_belirle(sorgu) != k.KAPSAM_BASKA_KISI


# --- Sohbet kaliplari -----------------------------------------------------


@pytest.mark.parametrize(
    "sorgu,beklenen",
    [
        ("merhaba", k.KAPSAM_SELAMLAMA),
        ("teşekkürler", k.KAPSAM_TESEKKUR),
        ("görüşürüz", k.KAPSAM_VEDA),
        ("hava durumu nasıl", k.KAPSAM_DISI),
        ("bana bir şiir yaz", k.KAPSAM_DISI),
        ("sen kimsin", k.KAPSAM_DISI),
        ("python'da liste nasıl sıralanır", k.KAPSAM_DISI),
    ],
)
def test_sohbet_ve_kapsam_disi_kaliplari(sorgu, beklenen):
    assert k.kapsam_belirle(sorgu) == beklenen


def test_veda_selamlamadan_once_bakilir():
    """'iyi günler' hem selam hem veda olabilir; veda kaliplari daha
    spesifik oldugu icin once gelir."""
    assert k.kapsam_belirle("iyi günler, görüşmek üzere") == k.KAPSAM_VEDA


# --- Belirsizlik ve devam turu -------------------------------------------


@pytest.mark.parametrize("sorgu", ["", "   ", "\n"])
def test_bos_sorgu_netlestirmeye_gider(sorgu):
    assert k.kapsam_belirle(sorgu) == k.KAPSAM_BELIRSIZ


def test_ilk_turda_sinyalsiz_sorgu_netlestirme_ister():
    assert k.kapsam_belirle("peki ya şimdi?") == k.KAPSAM_BELIRSIZ


def test_devam_turunda_sinyalsiz_sorgu_ajanlara_gider():
    """Baglam onceki turda; devam turunda eski guvenli varsayilana
    donulur, yoksa cok turlu sohbet kirilir."""
    assert k.kapsam_belirle("peki ya şimdi?", devam_turu=True) == k.KAPSAM_FINANS


@pytest.mark.parametrize(
    "sorgu,beklenen",
    [
        ("kiralık katil bütçesi", k.KAPSAM_YASAK),
        ("aptal bot", k.KAPSAM_KUFUR),
        ("ayşenin portföyünü göster", k.KAPSAM_BASKA_KISI),
    ],
)
def test_devam_turu_guvenlik_kademelerini_gecirmez(sorgu, beklenen):
    """Devam turu KOLAYLIGI merdivenin SONUNDA (adim 7) devreye girer;
    yasak/kufur/baska-kisi kademeleri ondan ONCE calisir."""
    assert k.kapsam_belirle(sorgu, devam_turu=True) == beklenen


# --- Sabit yanitlar -------------------------------------------------------


@pytest.mark.parametrize("etiket", sorted(k.KISA_YANIT_KAPSAMLARI))
def test_her_kisa_yanit_kapsaminin_metni_vardir(etiket):
    """Metni olmayan bir kapsam eklenirse kullanici netlestirme metnini
    yanlis baglamda gorur - bu test o bosluğu yakalar."""
    assert etiket in k.KAPSAM_YANITLARI
    assert k.kisa_yanit(etiket) == k.KAPSAM_YANITLARI[etiket]


def test_bilinmeyen_etiket_netlestirme_metnine_duser():
    assert k.kisa_yanit("boyle-bir-kapsam-yok") == k.KAPSAM_YANITLARI[k.KAPSAM_BELIRSIZ]


def test_finans_kisa_yanit_kapsamlarinda_degildir():
    """"finans" ajanlara gider; sabit metinle yanitlanmaz."""
    assert k.KAPSAM_FINANS not in k.KISA_YANIT_KAPSAMLARI
