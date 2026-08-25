"""MarketResearchAgent - piyasa haberleri/raporlari (RAG) ve canli fiyat/KAP verisi.

Iki MCP sunucusuna birden erisen tek ajandir:
  * `rag`    (MCP Server 1) -> LlamaIndex tabanli haber/rapor arama
  * `market` (MCP Server 3) -> canli fiyat ve KAP bildirimleri

Portfoy veritabanina (MCP Server 2) HICBIR sekilde erismez; orasi
PortfolioAgent'in sorumlulugundadir.

ORCHESTRATOR ILE SOZLESME
    Ajan graph'a `market_research` node'u olarak baglanir ve `BaseAgent`
    sozlesmesine uyar: `_execute(state) -> dict`, yalnizca DEGISEN alanlari
    dondurur:

        {"market_data": {...}, "sources": [Source, ...]}

    `market_data` yalnizca bu ajan tarafindan yazilir (catisma yok); `sources`
    ise reducer'li (`operator.add`) bir alandir, diger ajanlarin kaynaklarinin
    uzerine yazmaz.

PARAMETRELERIN KAYNAGI
    Router yapilandirilmis parametre uretebiliyorsa `state.agent_tasks`
    icinden okunur; uretmiyorsa parametreler `state.user_query` uzerinden
    cikarilir. Desteklenen alanlar:

        {
            "query": str,                        # yoksa state.user_query
            "mode": "rag" | "live" | "both",     # yoksa sorgudan cikarilir
            "symbol": str | None,                # orn. "THYAO"
            "date_from": str | None,             # "YYYY-MM-DD", RAG filtresi
            "date_to": str | None,               # "YYYY-MM-DD", RAG filtresi
            "top_k": int | None,                 # RAG chunk sayisi
            "include_disclosures": bool | None,  # live modda KAP bildirimi ekle
            "since": str | None,                 # KAP bildirim filtresi
            "history_days": int | None,          # "son 1 yil" -> 365
            "seasonality": dict | None,          # {"start_month", "end_month",
                                                 #  "label", "years"}
        }

    `symbol` OZEL DURUM: `build_task` regex ile bir tahmin uretir ama
    `_sembolu_katalogdan_coz` bu tahmini `market_list_symbols` ciktisiyla
    DOGRULAR; katalogda yoksa siler. Yani ajanin sonunda kullandigi sembol her
    zaman veritabaninda gercekten var olan bir koddur.

GUVENLIK NOTU
    RAG'den donen metin DIS KAYNAKLIDIR (haber/rapor icerigi) ve guvenilmez
    kabul edilir. Bu yuzden kaynak alintilari `market_data["sources"]` icinde
    de tasinir: `security_gate` node'u sentezden once ham `market_data`'yi
    tarar, boylece indekslenmis bir dokumana gomulmus prompt injection denemesi
    LLM'e ulasmadan yakalanir.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from app.agents.base import BaseAgent
from app.mcp.client import MCPClientError, MCPToolExecutionError
from app.mcp.server import MARKET_SERVER_NAME, RAG_SERVER_NAME
from app.orchestration.models import AgentError, AgentState, Source

logger = logging.getLogger(__name__)

AGENT_NAME = "market_research"

_LIVE_KEYWORDS = ("fiyat", "kac para", "guncel", "canli", "kap bildir", "kac tl", "kac lira")

#: Bir DONEMIN performansini soran ifadeler. Bunlar `market_get_history`
#: yolunu acar.
#:
#: NEDEN GEREKLI: "THYAO hissesinin son 1 yildaki karliligi" sorusu hicbir
#: `_LIVE_KEYWORDS` ile eslesmiyordu, bu yuzden mod "rag" oluyor ve ajan
#: haber indeksinde THYAO ariyordu. Fiyat serisi `price_history` tablosunda
#: duruyor ve `market_get_history` tool'u tam bu ozeti (change_pct,
#: first/last price, oynaklik) donduruyor - ama HICBIR AJAN onu cagirmiyordu.
_PERFORMANS_KEYWORDS = (
    "karlilik",
    "performans",
    "getiri",
    "ne kadar kazandir",
    "ne kadar kaybettir",
    "degisim",
    "yukseldi",
    "dustu",
    "artti",
    "azaldi",
)

#: "son 1 yil", "son alti ay", "3 aylik", "gecen yil", "yillik" ...
_PERIYOT_RE = re.compile(
    r"son\s+(\d+)?\s*(yil|ay|hafta|ceyrek|gun)"
    r"|(\d+)\s*(yillik|aylik|haftalik|gunluk|ceyreklik)"
    r"|gecen\s+(yil|ay|hafta)"
    r"|\b(yillik|aylik|haftalik|ceyreklik)\b"
)

_BIRIM_GUN = {
    "yil": 365,
    "yillik": 365,
    "ceyrek": 90,
    "ceyreklik": 90,
    "ay": 30,
    "aylik": 30,
    "hafta": 7,
    "haftalik": 7,
    "gun": 1,
    "gunluk": 1,
}

#: Performans sorusu var ama donem belirtilmemisse kullanilan varsayilan.
#: `market_get_history`'nin kendi varsayilaniyla ayni tutuldu.
_VARSAYILAN_GECMIS_GUN = 30


def _periyot_gun(query: str) -> int | None:
    """Sorgudan gecmis penceresini gun cinsinden cikarir; yoksa `None`.

    Donem ifadesi varsa onu kullanir ("son 1 yil" -> 365). Donem yok ama
    performans sorusu varsa varsayilana duser. Ikisi de yoksa `None` doner
    ve gecmis yolu hic acilmaz.
    """
    normalized = _normalize(query)

    eslesme = _PERIYOT_RE.search(normalized)
    if eslesme:
        sayi_str = eslesme.group(1) or eslesme.group(3)
        birim = eslesme.group(2) or eslesme.group(4) or eslesme.group(5) or eslesme.group(6)
        gun = _BIRIM_GUN.get(birim or "", _VARSAYILAN_GECMIS_GUN)
        try:
            carpan = int(sayi_str) if sayi_str else 1
        except ValueError:
            carpan = 1
        # Tool 1-365 arasina kirpiyor; burada da makul bir tavan koyuyoruz.
        return max(1, min(gun * carpan, 365))

    if any(k in normalized for k in _PERFORMANS_KEYWORDS):
        return _VARSAYILAN_GECMIS_GUN
    return None


_CONTEXT_KEYWORDS = ("neden", "sebep", "nicin", "haber", "rapor", "analiz", "bilanco", "yorum")

NO_RETRIEVAL_MESSAGE = (
    "Bu konuda indekslenmis haber/rapor bulunamadi; halihazirda erisilebilir "
    "kaynaklarda ilgili bir icerik yok."
)

#: Varsayilan RAG chunk sayisi.
DEFAULT_TOP_K = 5

#: RAG chunk metadata'sindaki `topic` -> `Source.tip` eslemesi.
#: Bilinmeyen konular "haber" kabul edilir.
_TOPIC_TO_TIP = {
    "earnings": "bilanco",
    "disclosure": "haber",
    "analyst": "analist_raporu",
    "news": "haber",
}

#: Sorgudan hisse kodu cikarmak icin: 4-5 harfli BUYUK harfli tokenlar.
#: Kullanici "THYAO bugun neden yukseldi" yazdiginda sembolu buradan alir.
_SYMBOL_PATTERN = re.compile(r"\b[A-Z]{4,5}\b")

#: Kucuk harfle ve Turkce ekle yazilmis sembol: "thyaonun", "thyao'da",
#: "aselsin". Buyuk harf deseni bunlari KACIRIYORDU - "bana thyaonun son 1
#: yildaki karliligi" sorusunda sembol bulunamadigi icin mod "rag" oluyor ve
#: ajan fiyat gecmisi yerine haber indeksinde arama yapiyordu.
#:
#: Yanlis pozitif riski var ("bilginin" -> "BILGI"). Bunu iki sey dengeliyor:
#: (1) yalnizca EK ILE geldiginde eslesiyor, ciplak kelime degil;
#: (2) buyuk harf deseni once denendigi icin dogru yazilmis kod her zaman
#: kazaniyor; (3) sembol yanlissa `market_get_quote` bos doner ve mod "both"
#: oldugu icin RAG yolu yine calisir - yani en kotu ihtimalde bir bos cagri.
_SYMBOL_SUFFIXED_PATTERN = re.compile(
    r"\b([a-zA-Z]{4,5})['\u2019\u02bc]?"
    r"(?:nun|nin|nun|nun|nan|nen|dan|den|tan|ten|da|de|ta|te|yi|yu|yu|ya|ye|si|su|nu|ni)\b",
    re.IGNORECASE,
)

#: Sembol gibi gorunen ama hisse kodu OLMAYAN kisaltmalar.
_SYMBOL_STOPWORDS = frozenset({"BIST", "TCMB", "SPKK", "TUIK", "OECD", "USDTR"})

#: Bir kelimenin sonundan atilabilecek Turkce ekler.
#:
#: Sembol eslesmesinde kullanilir: "thyaonun" -> THYAO + "nun". Bos string
#: TAM eslesmeyi ("thyao") temsil eder. Liste kapali tutuluyor - "kok +
#: herhangi bir sey" kurali "altinda" kelimesini ALTIN sembolune baglardi.
_TR_EKLER = frozenset(
    {
        "",
        "i",
        "u",
        "a",
        "e",
        "n",
        "in",
        "un",
        "nin",
        "nun",
        "na",
        "ne",
        "ya",
        "ye",
        "yi",
        "yu",
        "si",
        "su",
        "ni",
        "nu",
        "da",
        "de",
        "ta",
        "te",
        "dan",
        "den",
        "tan",
        "ten",
        "nda",
        "nde",
        "ndan",
        "nden",
        "la",
        "le",
        "yla",
        "yle",
        "ler",
        "lar",
        "leri",
        "lari",
        "lerin",
        "larin",
        "lerde",
        "larda",
        "lerden",
        "lardan",
        "li",
        "lu",
        "lik",
        "luk",
        "dir",
        "dur",
        "tir",
        "tur",
        "nun",
        "nin",
        "cu",
        "ci",
    }
)

#: Katalogda sembol olarak kabul edilecek en kisa kod. Iki harfli kodlar
#: gunluk Turkce kelimelerle cakisir ve gurultu uretir.
_ASGARI_SEMBOL_UZUNLUGU = 3

#: Katalog onbellek suresi (saniye). Varliklar sik degismez; her sorguda
#: tool cagirmak gereksiz gidis-gelis demektir.
_KATALOG_TTL_SN = 600.0


def _ekli_eslesme(token: str, kok: str) -> bool:
    """`token`, `kok` + taninan bir Turkce ek mi?

    Ikisi de NORMALIZE edilmis (ASCII + kucuk harf) beklenir.
    """
    if not token.startswith(kok):
        return False
    return token[len(kok) :] in _TR_EKLER


def sembol_coz(query: str, katalog: list[dict[str, Any]]) -> str | None:
    """Sorgudaki hisse kodunu KATALOGDAN cozer; tahmin etmez.

    Eski yontem sorguyu regex'e bakip "4-5 harfli kelime + Turkce ek" gorunce
    sembol sayiyordu. Olculen sonuc:

        "thyao hissesi almayi dusunuyorum"  -> HISSE
        "enflasyon verisi ne zaman"         -> VERI
        "sasa neden dustu"                  -> None
        "aselsan hisselerinde son durum"    -> None

    Yanlis sembol iki yolu birden kapatiyordu: RAG aramasi olmayan bir sirkete
    filtreleniyor, fiyat sorgusu bos donuyordu. Bu fonksiyon aday uretmez -
    yalnizca VERITABANINDA GERCEKTEN VAR OLAN kodlarla eslestirir, dolayisiyla
    "HISSE" gibi bir sonuc uretmesi yapisal olarak mumkun degildir.

    Args:
        katalog: `market_list_symbols` ciktisi - `{"symbol", "ad"}` sozlukleri.

    Returns:
        Bulunan sembol (buyuk harf) ya da `None`.
    """
    metin = _normalize(query)
    tokenler = re.findall(r"[a-z0-9]+", metin)
    if not tokenler:
        return None

    # (puan, -konum, sembol): once puan, esitlikte sorguda ONCE gecen kazanir.
    en_iyi: tuple[int, int, str] | None = None

    def aday_ekle(puan: int, konum: int, sembol: str) -> None:
        nonlocal en_iyi
        aday = (puan, -konum, sembol.upper())
        if en_iyi is None or aday > en_iyi:
            en_iyi = aday

    for kayit in katalog:
        sembol = str(kayit.get("symbol") or "").strip()
        if len(sembol) < _ASGARI_SEMBOL_UZUNLUGU:
            continue
        kok = _normalize(sembol)

        for konum, token in enumerate(tokenler):
            if _ekli_eslesme(token, kok):
                # Tam eslesme ekli eslesmeden guclu: "btc" > "btcden".
                aday_ekle(3 if token == kok else 2, konum, sembol)
                break

        # Sirket ADI ile eslesme: "aselsan" -> ASELS, "turk hava yollari" -> THYAO.
        # Kullanici kodu degil adi yaziyorsa da bulabilmeliyiz.
        ad = _normalize(str(kayit.get("ad") or ""))
        if not ad:
            continue
        if ad and ad in metin:
            aday_ekle(3, metin.index(ad), sembol)
            continue
        ilk_kelime = ad.split()[0] if ad.split() else ""
        if len(ilk_kelime) >= 5:
            for konum, token in enumerate(tokenler):
                if _ekli_eslesme(token, ilk_kelime):
                    aday_ekle(2, konum, sembol)
                    break

    return en_iyi[2] if en_iyi else None


# ---------------------------------------------------------------------------
# Mevsimsellik: "gecmis yillarin yaz aylarinda nasil hareket etti?"
# ---------------------------------------------------------------------------

#: (anahtar kelime deseni, baslangic ayi, bitis ayi, etiket)
#:
#: Desenler `\b` ile sinirlanmis ve ekler ACIKCA yazilmistir. "yaz" ozellikle
#: tehlikeli: `\byaz\w*` deseni "yazilim", "yazar", "yazdi" kelimelerini de
#: yakalardi. Bu yuzden yalnizca gercek cekimler listeleniyor.
_MEVSIM_DESENLERI: tuple[tuple[re.Pattern[str], int, int, str], ...] = (
    (re.compile(r"\bilkbahar\w*|\bbahar(da|in|lari)?\b"), 3, 5, "ilkbahar (Mart-Mayis)"),
    (re.compile(r"\bsonbahar\w*|\bguz(un|de|leri)?\b"), 9, 11, "sonbahar (Eylul-Kasim)"),
    (re.compile(r"\byaz(in|lari|larda|larinda|dan|da)?\b"), 6, 8, "yaz (Haziran-Agustos)"),
    (re.compile(r"\bkis(in|lari|larda|larinda|dan|da)?\b"), 12, 2, "kis (Aralik-Subat)"),
)

_AY_ADLARI: dict[str, int] = {
    "ocak": 1,
    "subat": 2,
    "mart": 3,
    "nisan": 4,
    "mayis": 5,
    "haziran": 6,
    "temmuz": 7,
    "agustos": 8,
    "eylul": 9,
    "ekim": 10,
    "kasim": 11,
    "aralik": 12,
}
_AY_DESENI = re.compile(r"\b(" + "|".join(_AY_ADLARI) + r")\w*\b")

#: Mevsim/ay adi TEK BASINA yetmez - "yaz" ayrica "yazmak" fiilidir, "aralik"
#: ayrica "bosluk" demektir. Bu isaretlerden biri de gecmeliidir ki soru
#: gercekten "yillar boyunca su donemde ne oldu" sorusu olsun.
_MEVSIMSEL_ISARETLER = (
    "son yil",
    "yillard",
    "yillarin",
    "yillarda",
    "gecmis yil",
    "gecen yillar",
    "her yil",
    "yillar boyunca",
    "genelde",
    "genellikle",
    "mevsim",
    "sezon",
    "donem",
    "aylarinda",
    "aylari",
    "ayinda",
)

#: Kac yil geriye bakilacagi - sorguda belirtilmemisse.
_VARSAYILAN_MEVSIM_YILI = 5

#: Bu sayidan az yil bulunursa yanit metnine ACIK bir yetersizlik uyarisi
#: eklenir. Iki gozlemle "mevsimsel oruntu" demek veri degil temennidir.
_MEVSIMSEL_ASGARI_YIL = 3

_MEVSIM_YIL_RE = re.compile(r"son\s+(\d{1,2})\s*yil")


def _mevsim_araligi(query: str) -> dict[str, Any] | None:
    """Sorgudan mevsimsel karsilastirma penceresini cikarir; yoksa `None`.

    Returns:
        `{"start_month", "end_month", "label", "years"}` ya da `None`.
    """
    metin = _normalize(query)

    if not any(isaret in metin for isaret in _MEVSIMSEL_ISARETLER):
        return None

    bulunan: tuple[int, int, str] | None = None
    for desen, bas, bit, etiket in _MEVSIM_DESENLERI:
        if desen.search(metin):
            bulunan = (bas, bit, etiket)
            break

    if bulunan is None:
        ay_eslesmesi = _AY_DESENI.search(metin)
        if ay_eslesmesi is None:
            return None
        ay = _AY_ADLARI[ay_eslesmesi.group(1)]
        bulunan = (ay, ay, f"{ay_eslesmesi.group(1)} ayi")

    yil_eslesmesi = _MEVSIM_YIL_RE.search(metin)
    try:
        yil = int(yil_eslesmesi.group(1)) if yil_eslesmesi else _VARSAYILAN_MEVSIM_YILI
    except ValueError:
        yil = _VARSAYILAN_MEVSIM_YILI

    return {
        "start_month": bulunan[0],
        "end_month": bulunan[1],
        "label": bulunan[2],
        "years": max(1, min(yil, 10)),
    }


#: Turkce karakterleri ASCII karsiliklarina cevirir; anahtar kelime listesi tek
#: yazimla ("guncel") hem "güncel" hem "guncel" girdisini yakalar.
#:
#: NOT: `app.engine.orchestrator` icinde de ayni tablo vardir. Ajan katmaninin
#: motor katmanina bagimli olmamasi icin (agents -> engine dairesel import)
#: burada bilincli olarak yerel bir kopya tutuluyor.
_TR_TRANSLATION = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def _normalize(text: str) -> str:
    return text.translate(_TR_TRANSLATION).lower()


class MarketResearchAgent(BaseAgent):
    """RAG + canli piyasa verisini birlestiren arastirma ajani."""

    name = AGENT_NAME

    def __init__(self, mcp_client, llm=None, timeout_seconds: int = 20) -> None:
        """
        Args:
            mcp_client: Paylasilan MCP client ('rag' ve 'market' sunuculari
                kayitli olmalidir).
            llm: RAG sonuclarini kaynaga dayali ozetlemek icin kullanilan model.
                `None` ise ajan LLM'siz calisir ve kaynak alintilarindan
                deterministik bir ozet uretir (bilgi UYDURMAZ) - boylece API
                anahtari olmadan da uctan uca test edilebilir.
            timeout_seconds: `BaseAgent.run()` tarafindan uygulanan ust sinir.
        """
        super().__init__(mcp_client=mcp_client, llm=llm, timeout_seconds=timeout_seconds)
        #: `market_list_symbols` onbellegi - bkz. `_sembol_katalogu`.
        self._katalog: list[dict[str, Any]] | None = None
        self._katalog_zamani: float = 0.0

    # ------------------------------------------------------------------
    # Graph node mantigi
    # ------------------------------------------------------------------

    async def _execute(self, state: AgentState) -> dict:
        """Piyasa arastirmasini yapar ve DEGISEN state alanlarini doner.

        `run()` (BaseAgent) timeout ve hata yonetimini ustlendigi icin burada
        yalnizca is mantigi vardir. Tek istisna: LLM cagrisi coktugunde RAG
        verisi bosa gitmesin diye hata YEREL olarak yakalanir, veri korunur ve
        `agent_errors` alanina bir kayit eklenir (kismi basari).
        """
        # Router bu ajani istemediyse ucuz no-op: tool/LLM cagrisi yapilmaz.
        if not self.is_requested(state):
            logger.debug("piyasa arastirma ajani atlandi", extra={"agent": self.name})
            return {}

        task = self.build_task(state)
        # Regex tahminini KATALOGLA degistir: bu adim olmadan "thyao hissesi"
        # sorgusundan sembol HISSE cikiyor ve hem RAG filtresi hem fiyat
        # sorgusu bosa gidiyor.
        await self._sembolu_katalogdan_coz(task)
        query = (task.get("query") or "").strip()

        if not query:
            return {
                "agent_errors": [
                    AgentError(
                        agent_name=self.name,
                        error_type="unknown",
                        message="Piyasa arastirmasi icin bos olmayan bir sorgu gerekiyor.",
                    )
                ]
            }

        mode = self._resolve_mode(task, query)
        ozet_parcalari: list[str] = []
        kaynaklar: list[Source] = []
        ham_kaynaklar: list[dict[str, Any]] = []
        canli_veri: dict[str, Any] | None = None
        guven: float | None = None
        hatalar: list[AgentError] = []

        if mode in ("rag", "both"):
            rag_ozet, kaynaklar, ham_kaynaklar, guven, rag_hatasi = await self._run_rag(task, query)
            if rag_ozet:
                ozet_parcalari.append(rag_ozet)
            if rag_hatasi is not None:
                hatalar.append(rag_hatasi)

        if mode in ("live", "both"):
            canli_ozet, canli_veri = await self._run_live(task)
            if canli_ozet:
                ozet_parcalari.append(canli_ozet)

        ozet = "\n\n".join(ozet_parcalari) if ozet_parcalari else NO_RETRIEVAL_MESSAGE

        guncelleme: dict = {
            "market_data": {
                "summary": ozet,
                "sources": ham_kaynaklar,
                "live_data": canli_veri,
                "confidence": guven,
                "mode": mode,
            },
            # Reducer'li alan: yalnizca bu turda bulunan kaynaklar eklenir.
            "sources": kaynaklar,
        }
        if hatalar:
            guncelleme["agent_errors"] = hatalar

        return guncelleme

    # ------------------------------------------------------------------
    # Parametre cikarimi
    # ------------------------------------------------------------------

    def build_task(self, state: AgentState) -> dict[str, Any]:
        """Ajanin calisma parametrelerini state'ten uretir.

        Oncelik router'in yazdigi `state.agent_tasks[self.name]` sozlugundedir;
        eksik alanlar `user_query` uzerinden tamamlanir. Router henuz
        yapilandirilmis parametre uretmedigi icin pratikte cikarim yolu
        calisir - ancak sozlesme hazir oldugundan router gelistiginde bu ajanda
        degisiklik gerekmez.
        """
        task: dict[str, Any] = dict(state.agent_tasks.get(self.name) or {})
        task.setdefault("query", state.user_query)

        if not task.get("symbol"):
            sembol, kesin = self._sembol_ve_kesinlik(task["query"])
            if sembol:
                task["symbol"] = sembol
                # Router acikca sembol verdiyse (ileride) kesin sayilir;
                # tahmin edildiyse `_run_live` teyit eder.
                task.setdefault("symbol_kesin", kesin)

        if "seasonality" not in task:
            mevsim = _mevsim_araligi(task["query"])
            if mevsim is not None:
                task["seasonality"] = mevsim

        if "history_days" not in task:
            gun = _periyot_gun(task["query"])
            if gun is not None:
                task["history_days"] = gun

        return task

    async def _sembol_katalogu(self) -> list[dict[str, Any]] | None:
        """`market_list_symbols` ciktisi - kisa sureli onbellekli.

        `None` DONMESI "katalog okunamadi" demektir (MCP client yok ya da tool
        hata verdi) ve cagiran taraf o durumda eski regex tahminine geri
        duser - yani yeni tool baglanmadan da ajan calismaya devam eder.
        """
        simdi = time.monotonic()
        if self._katalog is not None and simdi - self._katalog_zamani < _KATALOG_TTL_SN:
            return self._katalog

        try:
            sonuc = await self.call_tool(
                server=MARKET_SERVER_NAME, tool="market_list_symbols", arguments={}
            )
        except MCPClientError:
            # MCPToolExecutionError bunun alt sinifi; tool henuz kayitli
            # degilse de burasi calisir.
            logger.warning("sembol katalogu okunamadi, regex tahminine dusuluyor", exc_info=True)
            return None

        self._katalog = sonuc.get("symbols") or []
        self._katalog_zamani = simdi
        return self._katalog

    async def _sembolu_katalogdan_coz(self, task: dict[str, Any]) -> None:
        """`task["symbol"]` degerini katalogla dogrular ya da SILER.

        Silme kismi kritik: katalog okunabildigi halde sorguda hicbir gercek
        sembol yoksa, `build_task`'in regex tahmini ("HISSE", "VERI") task'ta
        kalmamalidir. Kalirsa `_run_rag` aramayi olmayan bir sirkete
        filtreler ve sonuc her zaman bos doner.

        Router sembolu ACIKCA verdiyse (`symbol_kesin=True`) dokunulmaz.
        """
        if task.get("symbol") and task.get("symbol_kesin") is True:
            return

        katalog = await self._sembol_katalogu()
        if katalog is None:
            return  # katalog yok - eski davranis korunur

        sembol = sembol_coz(task.get("query") or "", katalog)
        if sembol:
            task["symbol"] = sembol
            task["symbol_kesin"] = True
            return

        if task.pop("symbol", None) is not None:
            logger.debug(
                "regex tahmini sembol katalogda yok, dusuruldu",
                extra={"agent": self.name},
            )
        task["symbol_kesin"] = False

    @staticmethod
    def _extract_symbol(query: str) -> str | None:
        """Sorgudan hisse kodunu cikarir ("THYAO bugun neden yukseldi" -> THYAO).

        Buyuk harf duyarli calisir: hisse kodlari her zaman buyuk yazilir, bu
        sayede sirada gecen normal Turkce kelimeler sembol sanilmaz.
        """
        sembol, _ = MarketResearchAgent._sembol_ve_kesinlik(query)
        return sembol

    @staticmethod
    def _sembol_ve_kesinlik(query: str) -> tuple[str | None, bool]:
        """(sembol, kesin_mi) doner.

        `kesin=True`  buyuk harfle, eksiz yazilmis kod - guvenilir.
        `kesin=False` kucuk harf + Turkce ekten TAHMIN edildi. Bu desen
                      "borsanin" -> BORSA, "bilginin" -> BILGI gibi yanlis
                      pozitifler uretiyor (12 masum cumlede 4 tane olculdu),
                      bu yuzden cagiran taraf DOGRULAMADAN kullanmamali:
                      `_run_live` once fiyat sorgusuyla teyit eder, tutmazsa
                      sembolu sessizce duser ve yanit RAG'den gelir.
        """
        for aday in _SYMBOL_PATTERN.findall(query):
            if aday not in _SYMBOL_STOPWORDS:
                return aday, True

        for aday in _SYMBOL_SUFFIXED_PATTERN.findall(query):
            buyuk = aday.upper()
            if buyuk not in _SYMBOL_STOPWORDS:
                return buyuk, False
        return None, False

    def _resolve_mode(self, task: dict[str, Any], query: str) -> str:
        """Hangi veri kaynaklarina gidilecegine karar verir: rag / live / both.

        Canli fiyat yolu ancak bir sembol bilindiginde anlamlidir; sembol yoksa
        sorgu ne olursa olsun RAG'e dusulur.
        """
        mode = task.get("mode")
        if mode in ("rag", "live", "both"):
            return mode

        normalized = _normalize(query)
        # Gecmis sorusu da piyasa yolunu acar: veri `price_history`'de,
        # haber indeksinde degil.
        canli_isteniyor = bool(task.get("symbol")) and (
            any(k in normalized for k in _LIVE_KEYWORDS)
            or task.get("history_days") is not None
            # Mevsimsellik de bir fiyat gecmisi sorusudur; verisi
            # `price_history` tablosunda, haber indeksinde degil.
            or task.get("seasonality") is not None
        )
        baglam_isteniyor = any(k in normalized for k in _CONTEXT_KEYWORDS)

        if canli_isteniyor and baglam_isteniyor:
            return "both"
        if canli_isteniyor:
            # Donem/mevsim sorusunda RAG'i de acik tutuyoruz: piyasa yolu bos
            # donerse kullanici hicbir sey alamazdi. "both" ile en kotu
            # ihtimalde haber ozeti geliyor.
            gecmis_sorusu = (
                task.get("history_days") is not None or task.get("seasonality") is not None
            )
            return "both" if gecmis_sorusu else "live"
        return "rag"

    # ------------------------------------------------------------------
    # RAG yolu (MCP Server 1)
    # ------------------------------------------------------------------

    async def _run_rag(
        self, task: dict[str, Any], query: str
    ) -> tuple[str | None, list[Source], list[dict[str, Any]], float | None, AgentError | None]:
        """Haber/rapor indeksinde arama yapar ve kaynaga dayali ozet uretir.

        Returns:
            (ozet, Source listesi, ham kaynak sozlukleri, guven skoru, hata)
        """
        filters: dict[str, Any] = {}
        if sembol := task.get("symbol"):
            filters["symbol"] = sembol
        if date_from := task.get("date_from"):
            filters["date_from"] = date_from
        if date_to := task.get("date_to"):
            filters["date_to"] = date_to

        sonuc = await self.call_tool(
            server=RAG_SERVER_NAME,
            tool="rag_search",
            arguments={
                "query": query,
                "top_k": task.get("top_k") or DEFAULT_TOP_K,
                "filters": filters,
            },
        )
        chunks: list[dict[str, Any]] = sonuc.get("chunks", [])

        if not chunks:
            # Kaynak yoksa LLM'e HIC gidilmez: modelin bosluktan icerik
            # uretmesi (halusinasyon) bu yolla tamamen engellenir.
            return NO_RETRIEVAL_MESSAGE, [], [], 0.0, None

        kaynaklar = [self._to_source(chunk) for chunk in chunks]
        ham_kaynaklar = [
            {
                "source": chunk.get("source", "bilinmiyor"),
                "excerpt": (chunk.get("text") or "")[:400],
                "date": chunk.get("date"),
            }
            for chunk in chunks
        ]
        guven = round(sum(c.get("score", 0.0) for c in chunks) / len(chunks), 3)

        ozet, hata = await self._summarize(query, chunks)
        return ozet, kaynaklar, ham_kaynaklar, guven, hata

    async def _summarize(
        self, query: str, chunks: list[dict[str, Any]]
    ) -> tuple[str, AgentError | None]:
        """Chunk'lari kaynaga dayali tek bir ozete cevirir.

        LLM bagli degilse ya da cagri coktuyse deterministik alintiya duser:
        veri kaybolmaz, kullanici yine kaynaklari gorur. LLM bagliyken olusan
        hata `llm_error` olarak raporlanir; hic bagli olmamasi ise bir hata
        DEGILDIR (LLM'siz calisma bilincli olarak desteklenir).
        """
        if self.llm is None:
            return self._fallback_summary(chunks), None

        try:
            return await self.generate(_build_rag_prompt(query, chunks)), None
        except Exception as exc:  # noqa: BLE001 - LLM cokse de RAG verisi korunmali
            logger.exception("piyasa ozeti uretilemedi", extra={"agent": self.name})
            return self._fallback_summary(chunks), AgentError(
                agent_name=self.name,
                error_type="llm_error",
                message=f"Piyasa ozeti model tarafindan uretilemedi: {exc}",
            )

    @staticmethod
    def _fallback_summary(chunks: list[dict[str, Any]]) -> str:
        """LLM'siz ozet: kaynak metinlerinden ALINTI yapar, yorum katmaz."""
        satirlar = ["Bulunan kaynaklardan alintilar:"]
        for chunk in chunks:
            kaynak = chunk.get("source", "bilinmiyor")
            tarih = chunk.get("date") or "tarih yok"
            metin = (chunk.get("text") or "").strip()
            satirlar.append(f"- [{kaynak}, {tarih}] {metin}")
        return "\n".join(satirlar)

    @staticmethod
    def _to_source(chunk: dict[str, Any]) -> Source:
        """RAG chunk'ini izlenebilirlik modeline cevirir (FR-RAG-04).

        Chunk'ta ayri bir baslik alani yoktur; bu yuzden baslik kaynak adi ve
        tarihten uretilir - kullanici "bu bilgi nereden geldi?" sorusunun
        cevabini yanit altindaki kaynak listesinde gorur.
        """
        metadata = chunk.get("metadata") or {}
        kaynak_adi = chunk.get("source", "bilinmiyor")
        tarih = chunk.get("date")

        return Source(
            # `doc_id` DOKUMAN kimligidir (rag.documents.external_id), chunk
            # kimligi degil: kullanici kaynagi acmak istediginde chunk numarasi
            # ise yaramaz. Tool dokuman kimligini vermiyorsa chunk'a duselir.
            doc_id=str(chunk.get("doc_id") or chunk.get("chunk_id") or ""),
            baslik=chunk.get("title") or f"{kaynak_adi} ({tarih or 'tarih yok'})",
            sirket=metadata.get("symbol"),
            tarih=tarih,
            # Tool dokuman tipini zaten sozlesmedeki degerle donuyorsa (haber |
            # bilanco | analist_raporu | duyuru) oldugu gibi kullanilir; eski
            # `topic` alanini donen sunucular icin esleme tablosuna duselir.
            # Eslemeye korukorune guvenilseydi bir bilanco dokumani "haber"
            # olarak etiketlenirdi.
            tip=chunk.get("tip") or _TOPIC_TO_TIP.get(metadata.get("topic"), "haber"),
            score=chunk.get("score"),
        )

    # ------------------------------------------------------------------
    # Canli veri yolu (MCP Server 3)
    # ------------------------------------------------------------------

    async def _run_live(self, task: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
        """Canli fiyat ve (istenirse) son KAP bildirimini getirir.

        Bu yol bir RAG islemi degildir; yapisal veri dondurur ve LLM CAGIRMAZ.
        """
        sembol = task.get("symbol")
        if not sembol:
            return "Canli veri icin bir hisse kodu tespit edilemedi.", None

        # Sembol bulunamazsa tool ortak zarfta `ok=False` doner, istemci de bunu
        # istisnaya cevirir. Kullanici acisindan "boyle bir sembol yok" bir
        # sistem hatasi degildir; akis kesilmeden bilgilendirici mesaj doner.
        try:
            quote = await self.call_tool(
                server=MARKET_SERVER_NAME,
                tool="market_get_quote",
                arguments={"symbol": sembol},
            )
        except MCPToolExecutionError:
            logger.warning("canli fiyat alinamadi", extra={"symbol": sembol}, exc_info=True)
            return self._sembol_bulunamadi(task, sembol), None

        if quote.get("price") is None:
            return self._sembol_bulunamadi(task, sembol), None

        # Alan adlari `app/mcp/server.py::market_get_quote` sozlesmesidir.
        canli_veri = {
            "symbol": quote.get("symbol") or sembol,
            "price": quote["price"],
            "timestamp": quote.get("ts"),
        }
        degisim = quote.get("daily_change_pct") or 0
        ozet = (
            f"{canli_veri['symbol']} guncel fiyat: {canli_veri['price']} "
            f"{quote.get('currency') or ''} ({degisim:+.2f}%)."
        ).strip()

        # --- Donem performansi -------------------------------------------
        # `history_days` yalnizca sorguda bir donem/performans ifadesi
        # gectiginde dolu olur (bkz. `_periyot_gun`). Veri `price_history`
        # tablosundan gelir - haber indeksinden DEGIL; "son 1 yildaki
        # karlilik" gibi sorulari cevaplayan tek yol budur.
        gun = task.get("history_days")
        if gun:
            gecmis_ozet, gecmis = await self._gecmis_getir(sembol, int(gun))
            if gecmis is not None:
                canli_veri["history"] = gecmis
            if gecmis_ozet:
                ozet += " " + gecmis_ozet

        # --- Mevsimsellik ------------------------------------------------
        # "Gecmis yillarin yaz aylarinda nasil hareket etti?" sorusu
        # `history_days` ile CEVAPLANAMAZ: o pencere her zaman bugune
        # yapisiktir. Takvimin ayni dilimini yillar boyunca karsilastirmak
        # icin ayri bir tool var.
        mevsim = task.get("seasonality")
        if mevsim:
            mevsim_ozet, mevsim_veri = await self._mevsimsellik_getir(sembol, mevsim)
            if mevsim_veri is not None:
                canli_veri["seasonality"] = mevsim_veri
            if mevsim_ozet:
                ozet += " " + mevsim_ozet

        if task.get("include_disclosures"):
            sonuc = await self.call_tool(
                server=MARKET_SERVER_NAME,
                tool="market_get_kap_disclosures",
                arguments={"symbol": sembol, "since": task.get("since")},
            )
            bildirimler = sonuc.get("disclosures", [])
            if bildirimler:
                son = bildirimler[0]
                ozet += f" Son KAP bildirimi ({son['date']}): {son['title']}."

        return ozet, canli_veri

    @staticmethod
    def _sembol_bulunamadi(task: dict[str, Any], sembol: str) -> str:
        """Fiyat bulunamadiginda kullaniciya ne yazilacagi.

        Sembol KESIN ise ("THYAO" diye yazilmis) bu gercek bir bilgi:
        soylenir. TAHMIN ise ("borsanin" -> BORSA) sessiz kalinir - yoksa
        kullanici sormadigi bir sembol icin "bulunamadi" mesaji gorur ve
        yanit kirlenir. Mod donem sorularinda "both" oldugu icin RAG yolu
        zaten devrede.
        """
        if task.get("symbol_kesin", True):
            return f"{sembol} icin canli fiyat verisi bulunamadi."
        return ""

    async def _mevsimsellik_getir(
        self, sembol: str, mevsim: dict[str, Any]
    ) -> tuple[str, dict[str, Any] | None]:
        """`market_get_seasonality` ozetini metin + yapisal veri olarak doner.

        URETILEN METIN GOZLEM SAYISINI HER ZAMAN SOYLER. Sebep: veritabaninda
        iki yillik gecmis varsa "yaz mevsiminde ortalama +%8" cumlesi teknik
        olarak dogru ama karar icin yanilticidir - iki gozlem bir oruntu
        degildir. Esigin altinda kalindiginda cumleye acik bir yetersizlik
        uyarisi ekleniyor; sayiyi gizlemek yerine baglamini veriyoruz.
        """
        etiket = mevsim.get("label") or "secili donem"
        try:
            sonuc = await self.call_tool(
                server=MARKET_SERVER_NAME,
                tool="market_get_seasonality",
                arguments={
                    "symbol": sembol,
                    "start_month": mevsim["start_month"],
                    "end_month": mevsim["end_month"],
                    "years": mevsim.get("years") or _VARSAYILAN_MEVSIM_YILI,
                },
            )
        except MCPToolExecutionError:
            logger.warning(
                "mevsimsellik verisi alinamadi",
                extra={"symbol": sembol, "mevsim": etiket},
                exc_info=True,
            )
            return f"{sembol} icin {etiket} donemine ait fiyat gecmisi bulunamadi.", None

        donemler = [d for d in (sonuc.get("periods") or []) if d.get("change_pct") is not None]
        if not donemler:
            return (
                f"{sembol} icin {etiket} doneminde tamamlanmis bir yil verisi yok; "
                f"mevsimsel bir karsilastirma yapilamiyor."
            ), sonuc

        # Suren donem ("bu yaz", henuz bitmemis) listeye girer ama ORTALAMAYA
        # girmez; kullanicinin bunu ayirt edebilmesi icin acikca etiketlenir.
        satirlar = ", ".join(
            f"{d['year']}: {d['change_pct']:+.2f}%"
            + (f" (devam ediyor, {d['end']} itibariyla)" if d.get("partial") else "")
            for d in donemler
        )
        yil_sayisi = sonuc.get("year_count") or 0
        ortalama = sonuc.get("average_change_pct")
        pozitif = sonuc.get("positive_years", 0)

        metin = f"{sembol} {etiket} donemi getirileri - {satirlar}."
        if ortalama is not None and yil_sayisi:
            metin += (
                f" Tamamlanmis yillarin ortalamasi {ortalama:+.2f}% "
                f"({yil_sayisi} yilin {pozitif} tanesi pozitif)."
            )

        if yil_sayisi < _MEVSIMSEL_ASGARI_YIL:
            metin += (
                f" DIKKAT: elde yalnizca {yil_sayisi} tamamlanmis yil var; "
                f"bu sayi mevsimsel bir oruntuden soz etmek icin yeterli DEGILDIR."
            )

        # Veri neden az? Kullanicinin "ama 2 yillik verim var" demesini
        # onlemek icin ELENEN donemleri de soyluyoruz.
        elenen: list[str] = []
        if sonuc.get("insufficient_periods"):
            elenen.append(f"{sonuc['insufficient_periods']} yil veri donemi bastan sona kapsamiyor")
        if sonuc.get("incomplete_periods"):
            elenen.append(f"{sonuc['incomplete_periods']} yil donemi henuz baslamamis/erken")
        if elenen:
            metin += f" (Hesaba katilamayan: {'; '.join(elenen)}.)"

        return metin, sonuc

    async def _gecmis_getir(self, sembol: str, gun: int) -> tuple[str, dict[str, Any] | None]:
        """`market_get_history` ozetini metin + yapisal veri olarak doner.

        Tool ham seriyi DEGIL ozet istatistikleri doner (change_pct,
        first/last/min/max, oynaklik) - LLM baglamini sismeden doldurmak icin
        (mimari v4 bolum 6.4). Hata durumunda akis kesilmez: bos metin doner,
        canli fiyat yine de kullaniciya ulasir.
        """
        try:
            sonuc = await self.call_tool(
                server=MARKET_SERVER_NAME,
                tool="market_get_history",
                arguments={"symbol": sembol, "days": gun},
            )
        except MCPToolExecutionError:
            logger.warning(
                "fiyat gecmisi alinamadi", extra={"symbol": sembol, "days": gun}, exc_info=True
            )
            return f"{sembol} icin {gun} gunluk fiyat gecmisi bulunamadi.", None

        degisim = sonuc.get("change_pct")
        if degisim is None:
            return f"{sembol} icin {gun} gunluk fiyat gecmisi bulunamadi.", None

        gecmis = {
            "days": sonuc.get("days", gun),
            "first_price": sonuc.get("first_price"),
            "last_price": sonuc.get("last_price"),
            "min_price": sonuc.get("min_price"),
            "max_price": sonuc.get("max_price"),
            "change_pct": degisim,
            "volatility_pct": sonuc.get("volatility_pct"),
            "point_count": sonuc.get("point_count"),
        }
        ozet = (
            f"Son {gecmis['days']} gunde {sembol} fiyati "
            f"{gecmis['first_price']} -> {gecmis['last_price']} "
            f"({degisim:+.2f}%); en dusuk {gecmis['min_price']}, "
            f"en yuksek {gecmis['max_price']}, oynaklik "
            f"%{gecmis['volatility_pct']}. "
            f"({gecmis['point_count']} veri noktasi, kaynak: fiyat gecmisi tablosu.)"
        )
        return ozet, gecmis

    # ------------------------------------------------------------------
    # Tool kesfi
    # ------------------------------------------------------------------

    async def get_tools(self) -> list:
        """Bu ajanin erisebilecegi tool'lar: yalnizca 'rag' ve 'market'.

        Taban siniftaki ad onegi filtresi ("market_research_") burada ise
        yaramaz; ajan tool'lari iki ayri sunucudan alir. Portfoy sunucusu
        bilincli olarak DISARIDA birakilmistir (NFR-04 yetki ayrimi).
        """
        if self.mcp_client is None:
            return []

        tools: list = []
        for sunucu in (RAG_SERVER_NAME, MARKET_SERVER_NAME):
            tools.extend(await self.mcp_client.get_tools(server=sunucu))
        return tools


def _build_rag_prompt(query: str, chunks: list[dict[str, Any]]) -> str:
    """Kaynaga dayali (grounded) ozet prompt'u.

    Modelden ACIKCA yalnizca verilen kaynaklara dayanmasi istenir; boylece
    yanit izlenebilir kalir ve kaynakta olmayan bilgi uretilmesi engellenir.
    """
    lines = [
        f"Kullanici sorusu: {query}",
        "",
        "Asagidaki kaynaklara dayanarak Turkce, kisa ve net bir yanit yaz. "
        "Sadece bu kaynaklarda yer alan bilgileri kullan, kaynaklarda olmayan "
        "hicbir bilgi uydurma.",
        "",
    ]
    for i, chunk in enumerate(chunks, start=1):
        kaynak = chunk.get("source", "bilinmiyor")
        tarih = chunk.get("date") or "tarih yok"
        lines.append(f"[{i}] Kaynak: {kaynak} ({tarih})")
        lines.append(chunk.get("text", ""))
        lines.append("")
    lines.append("Yanit:")
    return "\n".join(lines)
