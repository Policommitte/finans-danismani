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
        }

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
from typing import Any

from app.agents.base import BaseAgent
from app.mcp.servers.market import MARKET_SERVER_NAME
from app.mcp.servers.rag import RAG_SERVER_NAME
from app.orchestration.models import AgentError, AgentState, Source

logger = logging.getLogger(__name__)

AGENT_NAME = "market_research"

_LIVE_KEYWORDS = ("fiyat", "kac para", "guncel", "canli", "kap bildir", "kac tl", "kac lira")
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

#: Sembol gibi gorunen ama hisse kodu OLMAYAN kisaltmalar.
_SYMBOL_STOPWORDS = frozenset({"BIST", "TCMB", "SPKK", "TUIK", "OECD", "USDTR"})

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
            sembol = self._extract_symbol(task["query"])
            if sembol:
                task["symbol"] = sembol

        return task

    @staticmethod
    def _extract_symbol(query: str) -> str | None:
        """Sorgudan hisse kodunu cikarir ("THYAO bugun neden yukseldi" -> THYAO).

        Buyuk harf duyarli calisir: hisse kodlari her zaman buyuk yazilir, bu
        sayede sirada gecen normal Turkce kelimeler sembol sanilmaz.
        """
        for aday in _SYMBOL_PATTERN.findall(query):
            if aday not in _SYMBOL_STOPWORDS:
                return aday
        return None

    def _resolve_mode(self, task: dict[str, Any], query: str) -> str:
        """Hangi veri kaynaklarina gidilecegine karar verir: rag / live / both.

        Canli fiyat yolu ancak bir sembol bilindiginde anlamlidir; sembol yoksa
        sorgu ne olursa olsun RAG'e dusulur.
        """
        mode = task.get("mode")
        if mode in ("rag", "live", "both"):
            return mode

        normalized = _normalize(query)
        canli_isteniyor = bool(task.get("symbol")) and any(k in normalized for k in _LIVE_KEYWORDS)
        baglam_isteniyor = any(k in normalized for k in _CONTEXT_KEYWORDS)

        if canli_isteniyor and baglam_isteniyor:
            return "both"
        if canli_isteniyor:
            return "live"
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

        quote = await self.call_tool(
            server=MARKET_SERVER_NAME,
            tool="market_get_quote",
            arguments={"symbol": sembol},
        )

        if not quote.get("found", False):
            return f"{sembol} icin canli fiyat verisi bulunamadi.", None

        canli_veri = {
            "symbol": quote["symbol"],
            "price": quote["price"],
            "timestamp": quote["timestamp"],
        }
        ozet = (
            f"{canli_veri['symbol']} guncel fiyat: {canli_veri['price']} "
            f"{quote.get('currency', '')} ({quote.get('change_percent', 0):+.2f}%)."
        ).strip()

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
