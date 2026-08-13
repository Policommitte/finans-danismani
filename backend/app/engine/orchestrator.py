"""Orkestrasyon motoru - LangGraph StateGraph kurulumu ve streaming yurutme.

Bu modul sistemin kalbidir: kullanici sorgusunu alir, guvenlik denetiminden
gecirir, ilgili ajanlari (kimi paralel kimi sirali) calistirir ve sonuclari tek
bir Turkce yanitta birlestirerek token token akitir.

AKIS
----
    START
      -> security_in       (girdi denetimi; guvensizse -> reject)
      -> router            (niyet analizi, ajan secimi)
      -> market_research + portfolio     (PARALEL fan-out)
      -> risk_strategy     (SIRALI; ikisinin verisini bekler)
      -> security_gate     (ham ajan verisi denetimi; sorunluysa -> safe_response)
      -> synthesizer       (sentez + STREAMING)
      -> END

PARALEL MI, SIRALI MI?
    LangGraph'ta sirali calisma varsayilandir, paralellik istisnadir. Kural:
    bir ajan baska bir ajanin ciktisina ihtiyac duyuyorsa SIRALI, duymuyorsa
    PARALEL konumlanir.

      - MarketResearchAgent -> bagimliligi yok        -> paralel
      - PortfolioAgent      -> bagimliligi yok        -> paralel
      - RiskStrategyAgent   -> portfolio_data + market_data gerekir -> SIRALI

    Risk ajani paralel calistirilirsa bu alanlar henuz `None` oldugu icin ajan
    bos veriyle calisir. Bu, hata FIRLATMAYAN ama yanlis sonuc ureten turden
    sessiz bir hatadir; topoloji bu yuzden bilincli olarak boyle kurulmustur.

AJANLARIN BAGLANMASI
    Orchestrator hicbir ajani kendisi olusturmaz; hepsi constructor uzerinden
    ENJEKTE edilir. Gercek ajan implementasyonlari (piyasa arastirma, portfoy,
    risk) ayri bir calisma dalinda gelistirilmektedir. Kayitli olmayan ajan
    icin graph kenari uretilmez - yani orchestrator eksik ajanla da calisir.
"""

import asyncio
import logging
import time
import uuid
from collections.abc import AsyncGenerator, Sequence

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.base import BaseAgent
from app.orchestration.models import RESET, AgentError, AgentState, Source

logger = logging.getLogger(__name__)

# --- Graph node adlari (string tekrarini onlemek icin sabitlendi) ---
NODE_SECURITY_IN = "security_in"
NODE_ROUTER = "router"
NODE_SECURITY_GATE = "security_gate"
NODE_SYNTHESIZER = "synthesizer"
NODE_REJECT = "reject"
NODE_SAFE_RESPONSE = "safe_response"

# --- Ajan node adlari ---
AGENT_MARKET_RESEARCH = "market_research"
AGENT_PORTFOLIO = "portfolio"
AGENT_RISK_STRATEGY = "risk_strategy"

#: Birbirinden bagimsiz ajanlar - router'dan sonra PARALEL calisir.
PARALLEL_AGENTS: tuple[str, ...] = (AGENT_MARKET_RESEARCH, AGENT_PORTFOLIO)

#: Baska ajanlarin ciktisina ihtiyac duyan ajanlar - paralel fazdan SONRA,
#: tanimlandiklari sirayla zincirlenerek calisir.
SEQUENTIAL_AGENTS: tuple[str, ...] = (AGENT_RISK_STRATEGY,)

#: Kullaniciya SSE ile gonderilecek ilerleme mesajlari.
#:
#: NOT: LangGraph `updates` olayini node CALISTIKTAN SONRA yayinlar. Bu yuzden
#: mesajlar "su an yapiliyor" degil, "tamamlandi / sirada ne var" dilinde
#: yazilmistir; aksi halde kullaniciya yanlis bir ilerleme bilgisi giderdi.
NODE_STATUS_MESSAGES: dict[str, str] = {
    NODE_SECURITY_IN: "Sorgu guvenlik denetiminden gecti.",
    NODE_ROUTER: "Ilgili uzmanlar belirlendi.",
    AGENT_MARKET_RESEARCH: "Piyasa arastirmasi tamamlandi.",
    AGENT_PORTFOLIO: "Portfoy analizi tamamlandi.",
    AGENT_RISK_STRATEGY: "Risk degerlendirmesi tamamlandi.",
    NODE_SECURITY_GATE: "Sonuclar birlestiriliyor...",
}

#: Node adi -> SSE `status` olayinin `stage` alani (mimari v4 bolum 10.1).
#:
#: Frontend node adlarina DEGIL bu sabit kumeye baglanir: node adi bir
#: uygulama detayidir, `stage` ise sozlesmenin parcasidir. Yeni bir ajan node'u
#: eklendiginde frontend'in durum gostergesi degismek zorunda kalmaz.
NODE_STAGES: dict[str, str] = {
    NODE_SECURITY_IN: "security",
    NODE_ROUTER: "routing",
    AGENT_MARKET_RESEARCH: "agents",
    AGENT_PORTFOLIO: "agents",
    AGENT_RISK_STRATEGY: "risk",
    NODE_SECURITY_GATE: "synth",
}

#: Niyet analizi icin anahtar kelimeler (ASCII'ye normalize edilmis halde).
#: Sorguda bir ajanin kelimelerinden herhangi biri geciyorsa o ajan istenir.
INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    AGENT_PORTFOLIO: (
        "portfoy",
        "varlik",
        "hisse",
        "dagilim",
        "bakiye",
        "pozisyon",
        "yatirimim",
        "hesabim",
        "islem gecmisi",
    ),
    AGENT_MARKET_RESEARCH: (
        "piyasa",
        "haber",
        "bilanco",
        "sirket",
        "kar",
        "ceyrek",
        "rapor",
        "analist",
        "borsa",
        "endeks",
        "faiz",
        "enflasyon",
    ),
    AGENT_RISK_STRATEGY: (
        "risk",
        "dengele",
        "strateji",
        "oneri",
        "tavsiye",
        "cesitlendir",
        "guvenli",
        "getiri",
    ),
}

#: Turkce karakterleri ASCII karsiliklarina cevirir. Boylece anahtar kelime
#: listesi tek bir yazimla ("portfoy") hem "portföy" hem "portfoy" girdisini
#: yakalar. Duzeltme isaretli harfler de dahildir: finans metinlerinde "kâr"
#: yazimi yaygin ve "kar" anahtar kelimesiyle eslesmesi gerekir.
_TR_TRANSLATION = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")

#: Girdi guvenlik denetimi basarisiz oldugunda donen sabit mesaj.
REJECT_MESSAGE = "Bu isteği işleyemiyorum. Lütfen finansal danışmanlık kapsamında bir soru sorun."

#: Cikti guvenlik denetimi basarisiz oldugunda donen sabit mesaj.
SAFE_RESPONSE_MESSAGE = (
    "Şu anda güvenli bir yanıt üretemiyorum. Lütfen sorunuzu farklı bir "
    "şekilde ifade ederek tekrar deneyin."
)

#: Synthesizer sistem prompt'u - uyum kurallarini tasir.
SYNTHESIZER_SYSTEM_PROMPT = """Sen bir kişisel finans danışmanı asistanısın.
Aşağıdaki uzman analizlerini tek ve akıcı bir Türkçe yanıtta birleştir.

Uymak zorunda olduğun kurallar:
1. Yanıtının sonuna mutlaka "Bu bilgiler yatırım tavsiyesi değildir." ibaresini ekle.
2. Kişisel veri (TCKN, hesap/IBAN numarası, telefon, e-posta) yazma; geçse bile maskele.
3. Kullandığın bilgiyi hangi kaynağa dayandırdığını belirt.
4. Bir uzmandan veri gelmediyse bunu dürüstçe söyle, veri uydurma.
5. Sade ve anlaşılır bir dil kullan; gereksiz teknik jargon kullanma."""


def _normalize(text: str) -> str:
    """Metni anahtar kelime eslesmesi icin normalize eder.

    Turkce karakterleri ASCII'ye cevirip kucuk harfe dusurur. Ozellikle "İ"
    harfi Python'un varsayilan `lower()` davranisinda sorun cikardigi icin
    ceviri once yapilir.
    """
    return text.translate(_TR_TRANSLATION).lower()


class Orchestrator:
    """LangGraph StateGraph'ini kurar ve streaming olarak calistirir.

    Kullanim:
        orchestrator = Orchestrator(
            agents={"portfolio": portfolio_agent, ...},
            security_agent=security_agent,
            synthesizer_llm=llm,
        )
        async for event in orchestrator.stream_request(soru, user_id, thread_id):
            ...
    """

    def __init__(
        self,
        agents: dict[str, BaseAgent],
        security_agent,
        synthesizer_llm=None,
        checkpointer=None,
        synthesizer_timeout_seconds: int = 40,
    ) -> None:
        """
        Args:
            agents: Node adi -> ajan ornegi eslemesi. Beklenen anahtarlar
                `PARALLEL_AGENTS` ve `SEQUENTIAL_AGENTS` icinde tanimlidir.
                Eksik ajan sorun degildir; graph yalnizca kayitli ajanlar icin
                node ve kenar uretir. Tanimsiz bir ad verilirse ilgili ajan
                paralel faza eklenir.
            security_agent: `check_input_node` ve `security_gate_node`
                metodlarina sahip guvenlik ajani.
            synthesizer_llm: Sentez icin kullanilacak guclu model. `None` ise
                LLM'siz deterministik bir ozet uretilir - boylece orchestrator
                LLM entegrasyonu tamamlanmadan da uctan uca calisir.
            checkpointer: Konusma gecmisini saklayan LangGraph checkpointer.
                Verilmezse bellek ici `MemorySaver` kullanilir (demo icin
                yeterli; kalicilik gerekirse PostgreSQL checkpointer'a gecilir).
            synthesizer_timeout_seconds: Sentez adiminin ust sinir suresi.
        """
        self.agents = agents
        self.security_agent = security_agent
        self.synthesizer_llm = synthesizer_llm
        self.synthesizer_timeout_seconds = synthesizer_timeout_seconds
        self.checkpointer = checkpointer if checkpointer is not None else MemorySaver()
        self.graph = self.build_graph().compile(checkpointer=self.checkpointer)

    # ------------------------------------------------------------------
    # Graph kurulumu
    # ------------------------------------------------------------------

    def build_graph(self) -> StateGraph:
        """Node'lari ve kenarlari tanimlanmis (henuz derlenmemis) graph'i uretir.

        Ajanlar tek bir node icinde `asyncio.gather` ile DEGIL, LangGraph
        fan-out kenarlariyla paralel calisir. Boylece node bazli ilerleme
        olayi, checkpoint ve hata izolasyonu korunur.
        """
        builder = StateGraph(AgentState)

        # --- Node'lar ---
        builder.add_node(NODE_SECURITY_IN, self.security_agent.check_input_node)
        builder.add_node(NODE_ROUTER, self.route_node)
        for name, agent in self.agents.items():
            builder.add_node(name, agent.run)
        builder.add_node(NODE_SECURITY_GATE, self.security_agent.security_gate_node)
        builder.add_node(NODE_SYNTHESIZER, self.synthesize)
        builder.add_node(NODE_REJECT, self.reject_response)
        builder.add_node(NODE_SAFE_RESPONSE, self.safe_response)

        # --- Giris: once GUVENLIK, sonra routing ---
        # Kotu niyetli bir sorgu routing'e hic girmemelidir.
        builder.add_edge(START, NODE_SECURITY_IN)
        builder.add_conditional_edges(
            NODE_SECURITY_IN,
            self._input_safety_branch,
            {NODE_ROUTER: NODE_ROUTER, NODE_REJECT: NODE_REJECT},
        )

        # --- Ajan topolojisi (paralel fan-out + sirali fan-in) ---
        self._add_agent_edges(builder)

        # --- Cikti denetimi: SENTEZDEN ONCE ---
        builder.add_conditional_edges(
            NODE_SECURITY_GATE,
            self._output_safety_branch,
            {NODE_SYNTHESIZER: NODE_SYNTHESIZER, NODE_SAFE_RESPONSE: NODE_SAFE_RESPONSE},
        )

        # --- Cikislar ---
        builder.add_edge(NODE_SYNTHESIZER, END)
        builder.add_edge(NODE_REJECT, END)
        builder.add_edge(NODE_SAFE_RESPONSE, END)

        return builder

    def _add_agent_edges(self, builder: StateGraph) -> None:
        """Router ile guvenlik kapisi arasindaki ajan kenarlarini kurar.

        Topoloji `PARALLEL_AGENTS` / `SEQUENTIAL_AGENTS` sabitlerinden turetilir
        ve YALNIZCA kayitli ajanlar icin kenar uretilir. Bu sayede:
          - Henuz yazilmamis bir ajan graph'i bozmaz.
          - Yeni ajan eklemek icin sabit listeye bir satir eklemek yeterlidir.
        """
        parallel = [name for name in PARALLEL_AGENTS if name in self.agents]
        sequential = [name for name in SEQUENTIAL_AGENTS if name in self.agents]

        # Sabit listelerde tanimsiz ama enjekte edilmis ajanlar (ornegin test
        # sahte ajanlari) bagimsiz kabul edilip paralel faza alinir.
        known = set(PARALLEL_AGENTS) | set(SEQUENTIAL_AGENTS)
        parallel.extend(name for name in self.agents if name not in known)

        # FAN-OUT: bagimsiz ajanlarin hepsi router'dan ayni anda tetiklenir.
        if parallel:
            for name in parallel:
                builder.add_edge(NODE_ROUTER, name)
            upstream: list[str] = parallel
        else:
            upstream = [NODE_ROUTER]

        # FAN-IN: sirali ajanlar bir onceki katmanin TAMAMINI bekler.
        # LangGraph, bir node'a gelen tum kenarlar tamamlanmadan o node'u
        # calistirmaz; bekleme mantigi otomatik yonetilir.
        for name in sequential:
            for parent in upstream:
                builder.add_edge(parent, name)
            upstream = [name]

        # Son katman -> cikti guvenlik denetimi
        for parent in upstream:
            builder.add_edge(parent, NODE_SECURITY_GATE)

    # ------------------------------------------------------------------
    # Dallanma kararlari (conditional edges)
    # ------------------------------------------------------------------

    @staticmethod
    def _input_safety_branch(state: AgentState) -> str:
        """Girdi guvenliyse routing'e, degilse ret yoluna dallanir."""
        return NODE_ROUTER if state.is_input_safe else NODE_REJECT

    @staticmethod
    def _output_safety_branch(state: AgentState) -> str:
        """Ham ajan verisi temizse sentezle, degilse guvenli yanit dondur."""
        return NODE_SYNTHESIZER if state.is_output_safe else NODE_SAFE_RESPONSE

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route_node(self, state: AgentState) -> dict:
        """Niyete gore hangi ajanlarin anlamli oldugunu isaretler.

        NOT: Graph kenarlari STATIKTIR; bu node ajanlari devre disi birakmaz,
        yalnizca `requested_agents` listesini doldurur. Ajanlar bu listeye
        bakarak kendilerini erken sonlandirabilir (ucuz no-op) - bkz.
        `BaseAgent.is_requested`. Risk ajani sirali konumda oldugu icin
        atlansa bile graph akisi bozulmaz.
        """
        requested = self.route_intent(state)
        return {"requested_agents": requested, "intent": self._intent_adi(requested)}

    @staticmethod
    def _intent_adi(requested: list[str]) -> str:
        """Istenen ajan kumesini tek bir niyet etiketine cevirir.

        Etiket `chat_messages.meta` icine yazilir ve loglarda kullanilir;
        yonlendirme karari zaten `requested_agents` ile verilmistir.
        """
        kume = set(requested)
        if not kume:
            return "sohbet"
        if len(kume) > 1:
            return "karma"
        return {
            AGENT_PORTFOLIO: "portfoy",
            AGENT_MARKET_RESEARCH: "piyasa",
            AGENT_RISK_STRATEGY: "risk",
        }.get(next(iter(kume)), "belirsiz")

    def route_intent(self, state: AgentState) -> list[str]:
        """Basit sorularda tum ajanlari tetiklememek icin niyet analizi.

        Kural tabanli calisir (LLM'siz): ucretsiz API kotasini korumak icin
        bilincli bir tercihtir. Sorguda hicbir anahtar kelime eslesmezse
        guvenli varsayilan olarak TUM kayitli ajanlar istenir - eksik yanit
        vermektense biraz fazla calismak yeglenir.

        TODO(Sprint 3): Basit sohbet sorularinda ("merhaba") fan-out'u tamamen
        atlayan kisa yol eklenecek.
        """
        normalized = _normalize(state.user_query)

        requested = [
            name
            for name in self.agents
            if any(keyword in normalized for keyword in INTENT_KEYWORDS.get(name, ()))
        ]

        if not requested:
            return list(self.agents)

        # Risk ajani portfoy/piyasa verisine dayanir; sorguda dogrudan gecmese
        # bile bu ajanlardan biri istendiyse risk analizi de anlamlidir.
        if AGENT_RISK_STRATEGY in self.agents and AGENT_RISK_STRATEGY not in requested:
            if any(name in requested for name in PARALLEL_AGENTS):
                requested.append(AGENT_RISK_STRATEGY)

        return requested

    # ------------------------------------------------------------------
    # Sentez ve sabit yanitlar
    # ------------------------------------------------------------------

    async def synthesize(self, state: AgentState, config: RunnableConfig | None = None) -> dict:
        """Ajan sonuclarini tek Turkce yanitta birlestirir ve TOKEN TOKEN akitir.

        Sistem prompt'u uyum kurallarini tasir (bkz. SYNTHESIZER_SYSTEM_PROMPT):
        yatirim tavsiyesi ibaresi, PII maskeleme, kaynak gosterimi ve eksik ajan
        varsa bunu durustce belirtme.

        `synthesizer_llm` verilmemisse LLM'siz deterministik bir ozet uretilir;
        bu sayede orchestrator, model entegrasyonu tamamlanmadan da uctan uca
        test edilebilir.

        Args:
            config: LangGraph'in node'a gecirdigi calisma konfigurasyonu.
                LLM cagrisina MUTLAKA aktarilmalidir - aksi halde token'lar
                `messages` stream moduna dusmez ve gercek streaming calismaz
                (bkz. `_stream_llm`).
        """
        if self.synthesizer_llm is None:
            text = self._fallback_response(state)
            return {"final_response": text, "messages": [AIMessage(content=text)]}

        messages = self._build_synthesis_messages(state)

        try:
            text = await asyncio.wait_for(
                self._stream_llm(messages, config),
                timeout=self.synthesizer_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("synthesizer zaman asimina ugradi")
            text = self._fallback_response(state)
        except Exception:  # noqa: BLE001 - sentez cokerse kullanici bos ekran gormesin
            logger.exception("synthesizer beklenmeyen hata verdi")
            text = self._fallback_response(state)

        return {"final_response": text, "messages": [AIMessage(content=text)]}

    async def _stream_llm(self, messages: list, config: RunnableConfig | None = None) -> str:
        """LLM'i token token calistirir ve tam metni doner.

        `config` LLM cagrisina ACIKCA gecirilir. Bunun sebebi: LangGraph
        token'lari callback zinciri uzerinden yakalar; callback'ler ise
        `asyncio.wait_for` gibi yeni bir task acan cagrilarda ve Python 3.10'da
        otomatik olarak tasinmaz. Config elden gecirilmezse kod hata vermez ama
        streaming SESSIZCE calismaz - yanit ancak tamamlandiktan sonra tek
        parca gider.
        """
        parts: list[str] = []
        async for chunk in self.synthesizer_llm.astream(messages, config=config):
            content = getattr(chunk, "content", chunk)
            if content:
                parts.append(str(content))
        return "".join(parts)

    def _build_synthesis_messages(self, state: AgentState) -> list:
        """Synthesizer'a gonderilecek mesaj listesini hazirlar.

        Onceki turlarin mesajlari da eklenir; boylece cok turlu baglam
        (FR-CHAT-03) korunur.
        """
        messages: list = [SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT)]

        # Onceki konusma gecmisi (son mesaj mevcut sorgunun kendisidir).
        messages.extend(state.messages)

        messages.append(HumanMessage(content=self._build_context(state)))
        return messages

    def _build_context(self, state: AgentState) -> str:
        """Ajan ciktilarini LLM'e verilecek tek bir baglam metnine cevirir."""
        bolumler = [f"Kullanicinin sorusu: {state.user_query}"]

        veri_alanlari = (
            ("Portfoy analizi", state.portfolio_data),
            ("Piyasa arastirmasi", state.market_data),
            ("Risk degerlendirmesi", state.risk_data),
        )
        for baslik, veri in veri_alanlari:
            if veri is not None:
                bolumler.append(f"\n{baslik}:\n{_ajan_metni(veri)}")

        if state.sources:
            kaynaklar = "\n".join(f"- [{s.doc_id}] {s.baslik}" for s in state.sources)
            bolumler.append(f"\nKaynaklar:\n{kaynaklar}")

        if state.agent_errors:
            hatalar = "\n".join(f"- {e.agent_name}: {e.message}" for e in state.agent_errors)
            bolumler.append("\nUlasilamayan veriler (kullaniciya durustce belirt):\n" + hatalar)

        return "\n".join(bolumler)

    def _fallback_response(self, state: AgentState) -> str:
        """LLM olmadan uretilen deterministik yanit.

        Iki durumda kullanilir:
          1. `synthesizer_llm` henuz baglanmadi (iskelet/test asamasi).
          2. LLM cagrisi zaman asimina ugradi veya hata verdi.

        Uretilen metin de uyum kurallarina uyar: eksik veriyi durustce belirtir
        ve yatirim tavsiyesi ibaresini icerir.
        """
        satirlar: list[str] = []

        veri_alanlari = (
            ("Portföy analizi", state.portfolio_data),
            ("Piyasa araştırması", state.market_data),
            ("Risk değerlendirmesi", state.risk_data),
        )
        for baslik, veri in veri_alanlari:
            if veri is not None:
                satirlar.append(f"{baslik}: {_ajan_metni(veri)}")

        if not satirlar:
            satirlar.append("Şu anda görüntülenebilecek bir analiz sonucu bulunmuyor.")

        # Kismi basarisizlik: hangi uzmandan veri gelmedigini durustce soyle.
        if state.agent_errors:
            eksikler = ", ".join(sorted({e.agent_name for e in state.agent_errors}))
            satirlar.append(f"Not: Şu analizlere şu anda ulaşılamadı: {eksikler}.")

        if state.sources:
            kaynaklar = ", ".join(s.baslik for s in state.sources)
            satirlar.append(f"Kaynaklar: {kaynaklar}")

        satirlar.append("Bu bilgiler yatırım tavsiyesi değildir.")
        return "\n".join(satirlar)

    def reject_response(self, state: AgentState) -> dict:
        """Girdi guvensizse: guvenli ret mesaji.

        Bu node'a gelindiginde hicbir ajan calismamistir; kotu niyetli sorgu
        sisteme hic girmemis olur.
        """
        logger.info("istek girdi denetiminde reddedildi", extra={"flags": state.security_flags})
        return {"final_response": REJECT_MESSAGE, "messages": [AIMessage(content=REJECT_MESSAGE)]}

    def safe_response(self, state: AgentState) -> dict:
        """Ham veri denetimi basarisizsa: guvenli genel yanit.

        Ajanlar calismistir ancak urettikleri veri denetimden gecmemistir;
        bu yuzden veri kullaniciya HIC gosterilmez.
        """
        logger.warning("cikti denetimi basarisiz", extra={"flags": state.security_flags})
        return {
            "final_response": SAFE_RESPONSE_MESSAGE,
            "messages": [AIMessage(content=SAFE_RESPONSE_MESSAGE)],
        }

    # ------------------------------------------------------------------
    # Streaming giris noktasi
    # ------------------------------------------------------------------

    async def stream_request(
        self,
        query: str,
        user_id: int,
        thread_id: int,
        request_id: str = "",
        portfolio_id: int | None = None,
    ) -> AsyncGenerator[dict, None]:
        """FastAPI endpoint'inin cagirdigi TEK giris noktasi.

        Bir string yerine `AsyncGenerator` dondurur; cunku string token akitamaz.
        Uretilen olaylar SSE'ye birebir cevrilir (mimari v4 bolum 10.1):

            {"type": "meta",        "request_id": ..., "conversation_id": ...}
            {"type": "status",      "stage": ..., "message": ...}
            {"type": "sources",     "items": [...]}
            {"type": "token",       "content": ...}
            {"type": "agent_error", "agent": ..., "error_type": ...}
            {"type": "error",       "code": ..., "message": ...}
            {"type": "done",        "latency_ms": ...}

        SIRA GARANTISI: `meta` ilk, `sources` ilk `token`'dan once, `done` en
        son. Frontend kaynak kartlarini yanit akmaya baslamadan yerlestirir;
        aksi halde metin akarken kartlar sonradan belirir ve arayuz ziplar,
        akis yarida kesilirse kaynaklar hic gorunmez.

        `done` olayina `message_id` alanini API katmani ekler (mesaj kalici
        hale getirildikten sonra); orchestrator DB'ye dokunmaz.

        Token olaylari YALNIZCA synthesizer node'undan gelir; ajanlarin kendi
        ic LLM cagrilari kullaniciya sizmaz.
        """
        request_id = request_id or str(uuid.uuid4())
        baslangic = time.perf_counter()

        initial_state = {
            "user_query": query,
            "user_id": user_id,
            "thread_id": thread_id,
            "request_id": request_id,
            "portfolio_id": portfolio_id,
            # Mesaj gecmisine kullanici mesajini ekle (cok turlu baglam).
            "messages": [HumanMessage(content=query)],
            # Onceki turdan kalan ajan ciktilarini temizle: checkpointer ayni
            # thread icin state'i sakladigindan, sifirlanmazsa bir onceki
            # turun portfoy/piyasa verisi bu turda guncelmis gibi gorunur.
            "portfolio_data": None,
            "market_data": None,
            "risk_data": None,
            # Reducer'li alanlar: `[]` yazmak SIFIRLAMAZ (reducer "hicbir sey
            # ekleme" olarak uygular). Sentinel gonderilmezse kaynaklar ve ajan
            # hatalari her turda birikir; ikinci turda kaynaklar ikiye katlanir
            # ve bir turda hata veren ajan duzelse bile "ulasilamadi" uyarisi
            # kalir. Bkz. `app.orchestration.models.add_or_reset`.
            "sources": [RESET],
            "agent_errors": [RESET],
            "security_flags": [RESET],
            "final_response": None,
            "is_input_safe": True,
            "is_output_safe": True,
        }
        # LangGraph checkpointer'i thread_id'yi string bekler; DB'deki
        # `chat_sessions.id` ise int. Donusum sinirda TEK yerde yapilir.
        config = {"configurable": {"thread_id": str(thread_id)}}

        token_yayinlandi = False
        kaynaklar_yayinlandi = False
        toplanan_kaynaklar: list[Source] = []
        son_yanit: str | None = None

        def _kaynak_olayi() -> dict:
            return {"type": "sources", "items": self._serialize_sources(toplanan_kaynaklar)}

        yield {"type": "meta", "request_id": request_id, "conversation_id": thread_id}

        try:
            async for mode, chunk in self.graph.astream(
                initial_state, config=config, stream_mode=["updates", "messages"]
            ):
                if mode == "messages":
                    token = self._extract_token(chunk)
                    if token:
                        # Emniyet kemeri: security_gate guncellemesi bir sekilde
                        # gelmediyse kaynaklar yine de ilk token'dan once gider.
                        if toplanan_kaynaklar and not kaynaklar_yayinlandi:
                            kaynaklar_yayinlandi = True
                            yield _kaynak_olayi()
                        token_yayinlandi = True
                        yield {"type": "token", "content": token}
                    continue

                # mode == "updates": node tamamlandiginda gelir
                for node_name, update in chunk.items():
                    durum = self._status_message(node_name, update)
                    if durum:
                        yield {
                            "type": "status",
                            "stage": NODE_STAGES.get(node_name, "agents"),
                            "message": durum,
                        }

                    if isinstance(update, dict):
                        toplanan_kaynaklar.extend(update.get("sources") or [])

                        # Kismi basarisizlik: tek ajan coktu, sohbet DEVAM
                        # ediyor. Frontend bunu uyari olarak gosterir, akisi
                        # hata sayip kapatmaz.
                        for hata in update.get("agent_errors") or []:
                            yield self._agent_error_olayi(hata)

                        yanit = update.get("final_response")
                        if yanit:
                            son_yanit = yanit

                    # security_gate son ajan adimindan SONRA, synthesizer'dan
                    # ONCE calisir: kaynaklarin tamami bu noktada hazirdir.
                    if (
                        node_name == NODE_SECURITY_GATE
                        and toplanan_kaynaklar
                        and not kaynaklar_yayinlandi
                    ):
                        kaynaklar_yayinlandi = True
                        yield _kaynak_olayi()

        except Exception:  # noqa: BLE001 - istemciye bos akis donmemeli
            # Hata ayrintisi YALNIZCA loga gider. Istisna metni ic ayrinti
            # (dosya yolu, baglanti dizesi, tool argumani) tasiyabilir; projenin
            # hata sozlesmesi bunlari istemciye acmaz. Makine-okunur `code`
            # istemciye gider, insan-okunur ayrinti gitmez.
            logger.exception("orchestrator akisi basarisiz", extra={"request_id": request_id})
            yield {
                "type": "error",
                "code": "ORCHESTRATOR_FAILED",
                "message": "İstek işlenirken beklenmeyen bir hata oluştu.",
            }
            return

        # Streaming YAPILMAYAN yollar (reject / safe_response / LLM'siz sentez)
        # yaniti tek parca uretir. Frontend'in tek bir render yolu olsun diye
        # bu metni de token olayi olarak gonderiyoruz (v2.3'teki ayri `final`
        # olayi bu yuzden kaldirildi).
        if son_yanit and not token_yayinlandi:
            if toplanan_kaynaklar and not kaynaklar_yayinlandi:
                kaynaklar_yayinlandi = True
                yield _kaynak_olayi()
            yield {"type": "token", "content": son_yanit}

        if toplanan_kaynaklar and not kaynaklar_yayinlandi:
            yield _kaynak_olayi()

        # `message_id` alanini API katmani ekler: mesaj once kalici hale
        # getirilir, sonra `done` istemciye yazilir. Yanit metni bu olayda
        # TEKRAR gonderilmez - API katmani token'lari zaten biriktiriyor.
        yield {
            "type": "done",
            "latency_ms": round((time.perf_counter() - baslangic) * 1000, 2),
        }

    @staticmethod
    def _agent_error_olayi(hata) -> dict:
        """`AgentError`'i SSE olayina cevirir.

        Hata MESAJI istemciye gonderilmez: ic ayrinti (tool adi, baglanti
        dizesi, istisna metni) tasiyabilir. Frontend'e ajan adi ve hata TURU
        yeter - "piyasa verisine ulasilamadi" cumlesini bu ikisinden kurar.
        """
        if isinstance(hata, AgentError):
            return {"type": "agent_error", "agent": hata.agent_name, "error_type": hata.error_type}
        if isinstance(hata, dict):
            return {
                "type": "agent_error",
                "agent": hata.get("agent_name", "bilinmiyor"),
                "error_type": hata.get("error_type", "unknown"),
            }
        return {"type": "agent_error", "agent": "bilinmiyor", "error_type": "unknown"}

    @staticmethod
    def _status_message(node_name: str, update) -> str | None:
        """Bir node tamamlandiginda kullaniciya gonderilecek ilerleme mesajini secer.

        Guvenlik node'lari icin mesaj KOSULLUDUR: denetim basarisiz olduysa
        "denetimden gecti" demek kullaniciyi yaniltir. Bu durumda ilerleme
        mesaji hic gonderilmez; hemen ardindan gelen ret/guvenli yanit metni
        durumu zaten aciklar.
        """
        if isinstance(update, dict):
            if node_name == NODE_SECURITY_IN and update.get("is_input_safe") is False:
                return None
            if node_name == NODE_SECURITY_GATE and update.get("is_output_safe") is False:
                return None

        return NODE_STATUS_MESSAGES.get(node_name)

    @staticmethod
    def _extract_token(chunk) -> str:
        """`messages` stream olayindan synthesizer token'ini cikarir.

        LangGraph bu modda `(mesaj_parcasi, metadata)` ikilisi yayinlar.
        Iki filtre uygulanir:

          1. Node adi: yalnizca synthesizer'dan gelenler kullaniciya gider;
             ajanlarin kendi ic LLM cagrilari kullaniciya sizmaz.

          2. Mesaj tipi: yalnizca `AIMessageChunk` yani GERCEK token parcalari
             gecer. LangGraph, node'un state'e yazdigi tamamlanmis `AIMessage`
             nesnesini de bu modda yayinlar; tip kontrolu olmazsa ayni metin
             hem token token hem de sonunda tek parca olarak iki kez gonderilir.
        """
        if not isinstance(chunk, tuple) or len(chunk) != 2:
            return ""

        message_chunk, metadata = chunk

        if not isinstance(message_chunk, AIMessageChunk):
            return ""

        if not isinstance(metadata, dict) or metadata.get("langgraph_node") != NODE_SYNTHESIZER:
            return ""

        content = getattr(message_chunk, "content", "")
        return str(content) if content else ""

    @staticmethod
    def _serialize_sources(sources: Sequence) -> list[dict]:
        """Kaynak listesini JSON'a cevrilebilir sozluklere donusturur.

        Ajanlar `Source` nesnesi yerine duz sozluk de dondurebildigi icin her
        iki durum da desteklenir.
        """
        serialized: list[dict] = []
        for source in sources:
            if isinstance(source, dict):
                serialized.append(source)
            elif hasattr(source, "model_dump"):
                serialized.append(source.model_dump())
        return serialized


def _ajan_metni(veri) -> str:
    """Ajan ciktisini okunabilir metne cevirir.

    Ajanlar yapisal veri (`dict`) dondurur; bu veriyi `str(dict)` olarak
    yazmak hem LLM baglamini gereksiz doldurur hem de LLM'siz calisirken
    kullaniciya ham Python sozlugu gosterir. Ajanlar kendi ozetlerini
    `summary_text` / `summary` alaninda tasidigi icin once o kullanilir.

    Yapisal veri KAYBOLMAZ: dashboard ayni sayilari REST uclarindan okur,
    burada yalnizca metne cevrilir.
    """
    if isinstance(veri, dict):
        for alan in ("summary_text", "summary"):
            deger = veri.get(alan)
            if isinstance(deger, str) and deger.strip():
                return deger
    return str(veri)
