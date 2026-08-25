"""Kapsam siniflandirici - fan-out'a girmeden once "bu soru bize mi?" karari.

NEDEN VAR
---------
Router kural tabanlidir ve eskiden hicbir anahtar kelime eslesmezse GUVENLI
VARSAYILAN olarak TUM ajanlari calistiriyordu ("eksik yanit vermektense biraz
fazla calis"). Bu varsayilan finans sorularinda dogru, finans DISI girdilerde
yanlisti: kullanici kufur ettiginde ya da "hava nasil" diye sordugunda sistem
portfoy dokumu + risk degerlendirmesi uretiyordu. Gercek bir ornek - hakaret
iceren bir mesaja verilen yanit portfoy toplamiyla basliyor, risk bolumu
hakarete cevap yaziyordu.

Bu modul o bosluğu kapatir: sorgu ajan fan-out'una girmeden once alti sinifa
ayrilir ve finans DISI olanlar tek cumlelik sabit bir yanitla, LLM cagrisi
YAPILMADAN sonlandirilir (bkz. `orchestrator.NODE_SMALL_TALK`).

SIRA ONEMLIDIR
--------------
`kapsam_belirle` icindeki kontrol sirasi bilinclidir; degistirmeden once
asagidaki ornekleri okuyun:

    "Merhaba, portfoyum nasil?"   -> FINANS   (selamlama ONCE bakilsa sohbet
                                               sanilir ve soru cevapsiz kalirdi)
    "SELAM"                       -> SELAMLAMA (sembol sezgisi ONCE bakilsa
                                               5 harfli buyuk kelime BIST
                                               sembolu sanilirdi)
    "Fenerbahce hissesi nasil?"   -> FINANS   (FENER gercekten BIST'te islem
                                               goruyor; "hisse" kelimesi
                                               kapsam disi listesinden ONCE
                                               degerlendirilir)
    "Fenerbahce mac skoru"        -> KAPSAM_DISI
    "amk portfoyum neden dustu"   -> FINANS   (dolgu kufru gercek soruyu
                                               iptal etmemeli)
    "anani sikiyom"               -> KUFUR

KUFURDE IKI KADEME
------------------
Kademe ayrimi kabalik derecesine gore DEGIL, DESENIN KESINLIGINE goredir:

  A) Dogrudan hakaretler ("anani sik-", "orospu", "siktir", "gerizekali")
     gercek bir finans sorusunda pratikte hic gecmez -> finans sinyalinden
     ONCE bakilir, her durumda kisa yanita duser.

  B) Dolgu kufurleri ("amk", "aq", "bok", "lanet") gercek soruların icinde
     sikca gecer -> YALNIZCA finans sinyali yoksa kisa yanita duser.

YATIRIM TAVSIYESI IBARESI
-------------------------
Bu modulun urettigi yanitlar bilincli olarak "Bu bilgiler yatirim tavsiyesi
degildir." ibaresini TASIMAZ: ibare finansal BILGI iceren ciktilar icin
zorunludur (bkz. `SYNTHESIZER_SYSTEM_PROMPT`), buradaki metinlerde ise
hicbir finansal bilgi yoktur. "Rica ederim." cumlesinin altina uyari
yapistirmak sozlesmeyi degil yalnizca okunabilirligi bozar.
"""

from __future__ import annotations

import re

# --- Kapsam etiketleri ----------------------------------------------------

#: Finans sorusu - normal ajan akisina gider.
KAPSAM_FINANS = "finans"

KAPSAM_SELAMLAMA = "selamlama"
KAPSAM_TESEKKUR = "tesekkur"
KAPSAM_VEDA = "veda"
KAPSAM_KUFUR = "kufur"
KAPSAM_DISI = "kapsam_disi"
#: Ne finans sinyali ne de taninan bir kalip var - netlestirme istenir.
KAPSAM_BELIRSIZ = "belirsiz"

#: Ajan fan-out'unu ATLAYAN kapsamlar. `KAPSAM_FINANS` disinda kalan her sey.
KISA_YANIT_KAPSAMLARI: frozenset[str] = frozenset(
    {
        KAPSAM_SELAMLAMA,
        KAPSAM_TESEKKUR,
        KAPSAM_VEDA,
        KAPSAM_KUFUR,
        KAPSAM_DISI,
        KAPSAM_BELIRSIZ,
    }
)

#: Turkce karakterleri ASCII'ye cevirir - desenler ASCII yazilir.
#: `security_agent.normalize` ile AYNI tablo; "İ".lower() iki kod noktasi
#: urettigi icin ceviri once, kucuk harf sonra yapilir.
_TR_TRANSLATION = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")


def normalize(text: str) -> str:
    """Metni desen eslesmesi icin ASCII + kucuk harfe indirger."""
    return text.translate(_TR_TRANSLATION).lower()


# --- Finans sinyali -------------------------------------------------------

#: Sorguda bunlardan biri geciyorsa soru FINANSAL sayilir ve ajanlara gider.
#:
#: `\w*` son eki Turkce cekim eklerini tolere eder: `\bportfoy\w*` hem
#: "portfoy" hem "portfoyumdeki" ile eslesir. Kelime BASI `\b` ile sabitlenir;
#: aksi halde "psikoloji" icindeki "sik" gibi tesadufi ic eslesmeler olur.
#:
#: ⚠️ BURAYA KISA VE COK ANLAMLI KOK EKLEMEYIN. Ornegin ciplak "kar" `\w*` ile
#: "karar", "karsi", "kart", "kardes" kelimelerini de yakalar ve finans DISI
#: her cumleyi finans sanir - modulun tum amacini bosa cikarir. Bu yuzden
#: "kar" yerine "karli/karlilik/kar payi" yazilmistir.
_FINANS_KOKLERI: tuple[str, ...] = (
    # Portfoy / hesap
    r"portfoy",
    r"portfolyo",
    r"varlik",
    r"hisse",
    r"senet",
    r"bakiye",
    r"pozisyon",
    r"dagilim",
    r"yatirim",
    r"birikim",
    r"tasarruf",
    r"butce",
    r"nakit",
    r"sermaye",
    r"mevduat",
    # Piyasa
    r"piyasa",
    r"borsa",
    r"bist",
    r"endeks",
    r"bilanco",
    r"ceyrek",
    r"analist",
    r"temettu",
    r"halka\s*arz",
    r"volatilite",
    r"likidite",
    r"emtia",
    r"kripto",
    r"bitcoin",
    r"ethereum",
    # Enstruman / kur
    r"doviz",
    r"dolar",
    r"euro",
    r"sterlin",
    # NOT: "altin" koku "altinda" (altında) kelimesini de yakalar. Yanlis
    # pozitifin bedeli dusuk (soru ajanlara gider, kapsam disi yaniti degil),
    # "altin fiyati" sorusunu kacirmanin bedeli yuksek oldugu icin kaldi.
    r"altin",
    r"gumus",
    r"petrol",
    r"tahvil",
    r"bono",
    r"parite",
    # Getiri / risk
    r"getiri",
    r"kazanc",
    r"karli",
    r"karlilik",
    r"kar\s+(payi|marji|orani)",
    r"zarar",
    r"risk",
    r"strateji",
    r"cesitlendir",
    r"tavsiye",
    r"oneri",
    r"performans",
    r"enflasyon",
    r"faiz",
    r"tufe",
    r"ufe",
    r"merkez\s*bankasi",
    r"tcmb",
    # Islem / muhasebe
    r"komisyon",
    r"kaldirac",
    r"stopaj",
    r"vergi",
    r"kredi",
    r"taksit",
    r"borc",
    r"maas",
    r"harcama",
    r"fiyat",
    r"maliyet",
    r"deger\s*kayb",
    r"deger\s*kazan",
    # Kisa kodlar
    r"btc",
    r"eth",
    r"usd",
)

#: Ek TAKISIZ eslesecek kelimeler. `_FINANS_KOKLERI` sonuna `\w*` ekledigi
#: icin bazi kokler kendi disinda kelimeleri de yutar - onlar buraya alinir:
#:
#:    "kur"  + \w*  -> kural, kurum, kurulus, kurtar   (finansla ilgisiz)
#:    "fon"  + \w*  -> fonksiyon
#:    "tl"   + \w*  -> (zararsiz ama tutarlilik icin burada)
#:
#: Doviz KURU sorusu zaten "doviz/dolar/euro" kokleriyle yakalandigi icin
#: ciplak "kur" koke listesinden cikarilmistir.
_FINANS_KELIMELERI: tuple[str, ...] = (
    r"kur",
    r"kuru",
    r"kurlar",
    r"kurlari",
    r"fon",
    r"fonu",
    r"fonum",
    r"fonlar",
    r"fonlari",
    r"fonlarim",
    r"tl",
    r"try",
    r"eur",
)

_FINANS_DESENI = re.compile(
    "|".join(
        [rf"\b(?:{kok})\w*" for kok in _FINANS_KOKLERI]
        + [rf"\b(?:{kelime})\b" for kelime in _FINANS_KELIMELERI]
    )
)

#: BIST sembolu sezgisi - HAM metin uzerinde calisir (buyuk harf bilgisi
#: normalizasyonda kaybolur). "THYAO ne kadar?" hicbir finans kokune
#: dusmez ama acikca bir finans sorusudur.
#:
#: Bu sezgi bilincli olarak EN SONDA degerlendirilir: "SELAM" da bes harfli
#: buyuk bir kelimedir ve once sohbet kaliplarina bakilmazsa sembol sanilir.
#:
#: BILINEN SINIR: kucuk harfle yazilan ciplak sembol ("thyao ne kadar")
#: yakalanmaz ve ilk turda netlestirme yanitina duser. Kullanici sorusunu
#: tekrar yazdiginda tur DEVAM turu olur ve ajanlara gider - yani hata
#: kendini duzeltir. Bunu tam cozmek icin sembol listesini DB'den okumak
#: gerekir; router'i LLM'siz ve senkron tutma karari (kota) buna izin vermiyor.
#:
#: Router da kullaniyor (`orchestrator._piyasa_sinyali_var`), bu yuzden ACIK
#: adla disari veriliyor.
SEMBOL_DESENI = re.compile(r"\b[A-ZÇĞİÖŞÜ]{4,6}\b")

_SEMBOL_DESENI = SEMBOL_DESENI


# --- Kufur: A kademesi (kesin) -------------------------------------------

#: Dogrudan hakaretler. Finans sinyalinden ONCE bakilir.
#:
#: ⚠️ "sik" kokunu `\w*` ile YAZMAYIN: normalize edilmis metinde "sikinti"
#: (sıkıntı) ve "sikisik" (sıkışık) kelimeleri bu koke duser ve "nakit
#: sikintisi yasiyorum" cumlesi hakaret sayilir. Bu yuzden yalnizca gercek
#: cekimler tek tek yazilmistir.
_KUFUR_A = re.compile(
    r"\banani?\s*sik"
    r"|\bavradini\b"
    r"|\bsik(tir|erim|eyim|iyim|iyom|iyorum|im|ler)\b"
    r"|\bhassiktir\b"
    r"|\bamina\s*(koy|kod)|\baminakoy"
    r"|\bamcik\w*"
    r"|\byarra\w*|\byarak\b"
    r"|\borospu\w*|\bkahpe\b|\bpezevenk\b|\bgavat\b|\bsurtuk\b"
    r"|\bpic\b|\bpicler\b|\bibne\w*|\bpust\b|\bserefsiz\w*"
    r"|\bgerizekali\w*|\bgeri\s*zekali\w*|\bsalak\w*|\baptal\w*"
    r"|\bdangalak\w*|\bembesil\w*|\bmal\s*misin\b|\bbeyinsiz\w*"
    r"|\bfuck\w*|\bbitch\w*|\bidiot\w*|\bmoron\w*|\basshole\w*|\bstupid\b"
)

# --- Kufur: B kademesi (dolgu) -------------------------------------------

#: Gercek sorularin icinde de gecen dolgu kufurleri. YALNIZCA finans sinyali
#: yoksa kisa yanita duser - "amk portfoyum neden dustu" cevapsiz kalmamali.
_KUFUR_B = re.compile(
    r"\bamk\b|\baq\b|\bmk\b|\bbok\w*|\blanet\w*|\bkahretsin\b|\bsacmali\w*|\bsacmala\w*"
)


# --- Sohbet kaliplari -----------------------------------------------------

_VEDA = re.compile(
    r"\bgorusuruz\b|\bgorusmek\s*uzere\b|\bhosca\s*kal\w*|\bbay\s*bay\b"
    r"|\bkendine\s*iyi\s*bak\b|\biyi\s*calismalar\b|\bbye\b|\bgood\s*bye\b"
)

_TESEKKUR = re.compile(
    r"\btesekkur\w*|\bteskkur\w*|\bsag\s*ol\w*|\bsagol\w*|\beyvallah\b"
    r"|\beline\s*saglik\b|\bcok\s*iyisin\b|\bharikasin\b|\bmukemmelsin\b"
    r"|\bthanks?\b|\bthank\s*you\b"
)

_SELAMLAMA = re.compile(
    r"\bmerhaba\b|\bselam\w*|\baleykum\b|\bgunaydin\b"
    r"|\biyi\s*(sabahlar|gunler|aksamlar|geceler)\b"
    r"|\bnasilsin\w*|\bnaber\b|\bne\s*haber\b|\bnabiyon\b"
    r"|\bhello\b|\bhey\b|\bhi\b"
)

#: Acikca baska bir alana ait sorular. Liste TAM DEGILDIR ve olmasi da
#: gerekmez: buraya dusmeyen finans disi sorular `KAPSAM_BELIRSIZ` olarak
#: netlestirme yanitina gider - o da fan-out'tan iyidir.
_KAPSAM_DISI = re.compile(
    # Asistanin kendisi hakkinda
    r"\bsen\s*kimsin\b|\bkimsin\s*sen\b|\badin\s*ne\b|\bismin\s*ne\b"
    r"|\bkac\s*yasindasin\b|\bhangi\s*model\w*|\byapay\s*zeka\s*mi\w*"
    r"|\brobot\s*mu\w*|\bchatgpt\b|\bgpt\b|\bgemini\b|\bclaude\b"
    r"|\bseni\s*kim\s*(yapti|yazdi|gelistirdi)\b"
    # Hava / gunluk
    r"|\bhava\s*(durumu|nasil|sicak|soguk)\b|\byagmur\s*yag\w*"
    # Yemek
    r"|\byemek\s*tarif\w*|\btarif\s*ver\w*|\bne\s*pisir\w*|\brestoran\w*"
    r"|\bkahvalti\b|\bpasta\s*yap\w*"
    # Spor
    r"|\bmac\s*(skor\w*|kacta|sonucu|ozeti)\b|\bfutbol\b|\bsampiyonluk\b"
    r"|\bkim\s*kazandi\b|\bgol\s*at\w*"
    # Eglence / kultur
    r"|\bfilm\s*(oner\w*|izle\w*)|\bdizi\s*oner\w*|\bsarki\s*(soyle|oner)\w*"
    r"|\bsaka\s*yap\w*|\bespri\s*yap\w*|\bfikra\s*anlat\w*|\bkomik\s*bir\s*sey\b"
    r"|\boyun\s*oyna\w*"
    # Saglik
    r"|\bhastayim\b|\bdoktora?\s*git\w*|\bilac\s*(oner\w*|kullan\w*)|\bagriyor\b"
    # Odev / kod / yaratici yazim
    r"|\bkod\s*yaz\w*|\bpython\b|\bjavascript\b|\bodev\w*\s*yap\w*"
    r"|\bsiir\s*yaz\w*|\bhikaye\s*yaz\w*|\bmakale\s*yaz\w*|\bceviri\s*yap\w*"
    r"|\bsinav\w*\s*(gir\w*|calis\w*)"
    # Seyahat
    r"|\botel\s*(oner\w*|bul\w*)|\bucak\s*bileti\b|\btatil\s*(yeri|oner\w*)"
)


# --- Sabit yanitlar -------------------------------------------------------

#: Kapsam -> kullaniciya donen tek parca metin.
#:
#: Hepsi KISA tutulmustur: bu yollarda LLM calismaz, dolayisiyla metin
#: birebir kullaniciya gider. Uzun bir sablon burada "robot" gibi okunur.
KAPSAM_YANITLARI: dict[str, str] = {
    KAPSAM_SELAMLAMA: (
        "Merhaba! Kişisel finans asistanınızım. Portföyünüz, piyasa gelişmeleri "
        "veya risk durumunuz hakkında soru sorabilirsiniz."
    ),
    KAPSAM_TESEKKUR: "Rica ederim. Başka bir konuda yardımcı olabilir miyim?",
    KAPSAM_VEDA: "Görüşmek üzere! Finansal konularda yine yanınızdayım.",
    KAPSAM_KUFUR: (
        "Bu şekilde bir konuşmaya devam edemem. Finansal konularda bir sorunuz "
        "olursa yardımcı olmaktan memnuniyet duyarım."
    ),
    KAPSAM_DISI: (
        "Bu konuda yardımcı olamıyorum. Yalnızca kişisel finans alanında "
        "(portföy, piyasa, risk ve yatırım) destek verebiliyorum."
    ),
    KAPSAM_BELIRSIZ: (
        "Sorunuzu tam olarak anlayamadım. Portföyünüz, piyasa gelişmeleri veya "
        "risk durumunuz hakkında ne öğrenmek istersiniz?"
    ),
}


def kapsam_belirle(sorgu: str, *, devam_turu: bool = False) -> str:
    """Sorguyu kapsam sinifina ayirir.

    Args:
        sorgu: Kullanicinin ham metni.
        devam_turu: Bu sohbette daha once en az bir tur yasandiysa `True`.
            Devam turlarinda "peki ya simdi?" gibi TEK BASINA anlamsiz ama
            baglamda gecerli sorular gelir; bunlarda eski guvenli varsayilana
            (ajanlari calistir) donulur, aksi halde cok turlu sohbet kirilir.

    Returns:
        `KAPSAM_FINANS` ya da `KISA_YANIT_KAPSAMLARI` icinden bir etiket.
    """
    if not sorgu or not sorgu.strip():
        return KAPSAM_BELIRSIZ

    n = normalize(sorgu)

    # 1) Dogrudan hakaret: finans sinyalinden ONCE, kosulsuz.
    if _KUFUR_A.search(n):
        return KAPSAM_KUFUR

    # 2) Finans sinyali: bundan sonrasi yalnizca finans DISI metinleri gorur.
    #    Selamlama/kapsam-disi kaliplari bu adimdan SONRA gelir; "merhaba,
    #    portfoyum nasil?" sorusunun sohbete dusmemesi buna bagli.
    if _FINANS_DESENI.search(n):
        return KAPSAM_FINANS

    # 3) Dolgu kufru: finans sinyali yoksa artik hakaret sayilir.
    if _KUFUR_B.search(n):
        return KAPSAM_KUFUR

    # 4) Sohbet kaliplari. Veda once: "iyi gunler" hem selam hem veda olabilir,
    #    veda kaliplari daha spesifiktir.
    if _VEDA.search(n):
        return KAPSAM_VEDA
    if _TESEKKUR.search(n):
        return KAPSAM_TESEKKUR
    if _SELAMLAMA.search(n):
        return KAPSAM_SELAMLAMA

    # 5) Bilinen baska alanlar.
    if _KAPSAM_DISI.search(n):
        return KAPSAM_DISI

    # 6) Sembol sezgisi - HAM metin. Sohbet kaliplarindan SONRA bakilir,
    #    yoksa "SELAM" bes harfli bir sembol sanilir.
    if _SEMBOL_DESENI.search(sorgu):
        return KAPSAM_FINANS

    # 7) Devam turu: baglam onceki turda; tek basina anlamsiz gorunse de
    #    ajanlara gitmeli.
    if devam_turu:
        return KAPSAM_FINANS

    # 8) Ilk turda, hicbir sinyal yok -> netlestirme iste.
    return KAPSAM_BELIRSIZ


def kisa_yanit(kapsam: str) -> str:
    """Kapsam etiketine karsilik gelen sabit yaniti doner."""
    return KAPSAM_YANITLARI.get(kapsam, KAPSAM_YANITLARI[KAPSAM_BELIRSIZ])
