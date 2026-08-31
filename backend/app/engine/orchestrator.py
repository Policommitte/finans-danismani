"""Orkestrasyon motoru - LangGraph StateGraph kurulumu ve streaming yurutme.

Bu modul sistemin kalbidir: kullanici sorgusunu alir, guvenlik denetiminden
gecirir, ilgili ajanlari (kimi paralel kimi sirali) calistirir ve sonuclari tek
bir Turkce yanitta birlestirerek token token akitir.

AKIS
----
    START
      -> security_in       (girdi denetimi; guvensizse -> reject)
      -> router            (KAPSAM + niyet analizi)
           |-- finans disi --> small_talk   (tek cumlelik sabit yanit -> END)
           |
      -> market_research + portfolio     (PARALEL fan-out)
      -> risk_strategy     (SIRALI; ikisinin verisini bekler)
      -> security_gate     (ham ajan verisi denetimi; sorunluysa -> safe_response)
      -> synthesizer       (sentez + STREAMING)
      -> END

IKI FARKLI "HAYIR" YOLU VAR - KARISTIRMAYIN
    reject      GUVENLIK karari: prompt injection, komut calistirma, sir
                sizdirma girisimi. `security_agent` verir, ajanlar hic calismaz.
    small_talk  KAPSAM karari: selamlama, tesekkur, kufur, baska bir alana ait
                soru. Tehlike yoktur, sadece bu sistemin isi degildir.

    Kufur eden bir kullanici SALDIRGAN degildir; `security_agent` onu bilincli
    olarak gecirir (desenleri dar tutulmustur, bkz. o modulun docstring'i).
    Kapsam karari bu yuzden ayri bir katmandir.

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
import re
import time
import uuid
from collections.abc import AsyncGenerator, Callable, Sequence

from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.base import BaseAgent
from app.agents.security_agent import PII_FLAG
from app.config import settings
from app.engine.kapsam import (
    KAPSAM_BELIRSIZ,
    KISA_YANIT_KAPSAMLARI,
    SEMBOL_DESENI,
    kapsam_belirle,
    kisa_yanit,
)
from app.orchestration.models import RESET, AgentError, AgentState, Source

logger = logging.getLogger(__name__)

# --- Graph node adlari (string tekrarini onlemek icin sabitlendi) ---
NODE_SECURITY_IN = "security_in"
NODE_ROUTER = "router"
NODE_SECURITY_GATE = "security_gate"
NODE_SYNTHESIZER = "synthesizer"
NODE_REJECT = "reject"
NODE_SAFE_RESPONSE = "safe_response"
NODE_SMALL_TALK = "small_talk"

# --- Ajan node adlari ---
AGENT_MARKET_RESEARCH = "market_research"
AGENT_PORTFOLIO = "portfolio"
AGENT_RISK_STRATEGY = "risk_strategy"

#: Birbirinden bagimsiz ajanlar - router'dan sonra PARALEL calisir.
PARALLEL_AGENTS: tuple[str, ...] = (AGENT_MARKET_RESEARCH, AGENT_PORTFOLIO)

#: Baska ajanlarin ciktisina ihtiyac duyan ajanlar - paralel fazdan SONRA,
#: tanimlandiklari sirayla zincirlenerek calisir.
SEQUENTIAL_AGENTS: tuple[str, ...] = (AGENT_RISK_STRATEGY,)

#: Ajan -> deterministik yanittaki bolum basligi. Sozlugun SIRASI ayni zamanda
#: yedek siradir (router bir sey soylemediginde kullanilir).
_BOLUM_BASLIKLARI: dict[str, str] = {
    AGENT_MARKET_RESEARCH: "Piyasa araştırması",
    AGENT_PORTFOLIO: "Portföy analizi",
    AGENT_RISK_STRATEGY: "Risk değerlendirmesi",
}

#: Ajan -> o ajanin state'teki veri alanini okuyan islev.
_AJAN_VERISI: dict[str, Callable[[AgentState], dict | None]] = {
    AGENT_MARKET_RESEARCH: lambda s: s.market_data,
    AGENT_PORTFOLIO: lambda s: s.portfolio_data,
    AGENT_RISK_STRATEGY: lambda s: s.risk_data,
}

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
#:
#: ESLESME KELIME BASINA SABITLIDIR (bkz. `_KELIME_DESENLERI`): kelime ortada
#: degil, BASTA aranir. Duz `in` kontrolu kullanildiginda "bakarak" icindeki
#: "kar" piyasa ajanini tetikliyordu - "bana bakarak tavsiye eder misin"
#: sorusu piyasa arastirmasi baslatiyordu. Son ek serbesttir, yani "portfoy"
#: hala "portfoyumdeki" ile eslesir.
INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    AGENT_PORTFOLIO: (
        "portfoy",
        "varlik",
        # "hisse" BILINCLI OLARAK YOK: herhangi bir hisse hakkindaki soru
        # ("THYAO hissesinin son 1 yildaki karliligi") portfoy analizini de
        # tetikliyordu - kullanicinin istemedigi bir bolum yaniti sisiriyor.
        # Portfoyu kasteden kullanim iyelik ekiyle gelir, onu yakaliyoruz.
        "hissem",
        "hisselerim",
        "elimdeki",
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
        # Performans/donem sorulari: bunlar olmadan "SASA hissesi neden
        # dustu?" hicbir anahtar kelimeyle eslesmiyor ve guvenli varsayilan
        # devreye girip TUM ajanlari kosturuyordu.
        "performans",
        "karlilik",
        "yukseldi",
        "dustu",
        # Enstruman ve fiyat sorulari. Bunlarin YOKLUGU olculdu: "yaz
        # baslamadan THYAO almayi dusunuyorum, tavsiye eder misin?" sorusu
        # yalnizca "tavsiye" ile eslesip risk+portfoy ajanlarina gidiyor,
        # piyasa ajani HIC calismiyordu - oysa sorunun cevabi (fiyat gecmisi,
        # mevsimsellik) tam olarak o ajanda.
        #
        # "hisse" burada BILINCLI olarak var ama AGENT_PORTFOLIO'da yok: bir
        # hisse hakkindaki soru piyasa sorusudur, portfoy sorusu degil.
        "hisse",
        "senet",
        "fiyat",
        "dolar",
        "euro",
        "altin",
        "doviz",
        "kripto",
        "bitcoin",
        "emtia",
        "petrol",
        "temettu",
        # Bir varligin getirisi PIYASA sorusudur. Eskiden yalnizca risk
        # ajaninin kelimesiydi ve "THYAO'nun getirisi ne?" sorusu portfoy+risk
        # ajanlarini calistiriyordu.
        "getiri",
        # Mevsimsellik: "gecmis yillarin yaz aylarinda ne oldu?"
        "mevsim",
        "sezon",
    ),
    AGENT_RISK_STRATEGY: (
        "risk",
        "dengele",
        "strateji",
        "cesitlendir",
        # ⚠️ Asagidakiler TEK BASLARINA risk ajanini tetiklemeye YETMEZ -
        # bkz. `_GENEL_TAVSIYE_KELIMELERI` ve `route_intent`.
        "oneri",
        "tavsiye",
        "guvenli",
    ),
}

#: Risk ajanini tek baslarina tetiklememesi gereken GENEL tavsiye kelimeleri.
#:
#: Sorun: "THYAO almami tavsiye eder misin?" cumlesindeki "tavsiye" risk
#: ajanini aciyor, risk ajani portfoy verisine bagimli oldugu icin portfoy de
#: otomatik ekleniyordu. Sonuc: tek bir hisse sorusu portfoy dokumu + risk
#: raporu uretiyordu. Kullanici bunu ust uste uc kez bildirdi.
#:
#: Kural: bu kelimeler piyasa sorusuyla BIRLIKTE geciyorsa tavsiye edilen sey
#: kullanicinin portfoyu degil, sorulan enstrumandir - risk/portfoy eklenmez.
#: Yalniz baslarina gecerlerse ("bana ne onerirsin?") kullanicinin kendi
#: durumu kastediliyordur, eski davranis korunur.
#:
#: "getiri" bu listede DEGIL, AGENT_MARKET_RESEARCH'e tasindi: bir varligin
#: getirisi bir piyasa sorusudur, risk sorusu degil.
_GENEL_TAVSIYE_KELIMELERI: frozenset[str] = frozenset({"oneri", "tavsiye", "guvenli"})

#: Turkce karakterleri ASCII karsiliklarina cevirir. Boylece anahtar kelime
#: listesi tek bir yazimla ("portfoy") hem "portföy" hem "portfoy" girdisini
#: yakalar. Duzeltme isaretli harfler de dahildir: finans metinlerinde "kâr"
#: yazimi yaygin ve "kar" anahtar kelimesiyle eslesmesi gerekir.
_TR_TRANSLATION = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")

#: Girdi guvenlik denetimi basarisiz oldugunda donen sabit mesaj.
REJECT_MESSAGE = "Bu isteği işleyemiyorum. Lütfen finansal danışmanlık kapsamında bir soru sorun."

#: Girdide kisisel veri (TCKN) bulundugunda donen mesaj.
#:
#: Genel `REJECT_MESSAGE`'tan AYRI: "finansal danismanlik kapsaminda soru
#: sorun" demek burada yaniltici olurdu - kullanicinin sorusu zaten finansaldi,
#: sorun sorunun KONUSU degil ICINDEKI VERI. Kullanici neyi duzeltmesi
#: gerektigini bilmezse ayni numarayi tekrar yazar.
PII_REJECT_MESSAGE = (
    "Güvenliğiniz için kimlik numarası gibi kişisel verileri işleyemiyorum. "
    "Lütfen sorunuzu bu bilgi olmadan tekrar yazın — portföyünüze zaten "
    "hesabınız üzerinden erişebiliyorum."
)


class _SentezDurdu(Exception):
    """Sentez akisi IC sinira takildi: model iki token arasinda cok bekledi.

    `asyncio.TimeoutError`'dan AYRI bir tur olmasi bilincli - `synthesize`
    icindeki dis zaman asimi yakalayicisiyla karismasin diye. Ikisi farkli
    seyi olcer: dis sinir TOPLAM sureyi, bu ise iki token ARASINI.
    """

    def __init__(self, limit_saniye: int) -> None:
        super().__init__(f"Token akisi {limit_saniye} saniye durdu.")
        self.limit_saniye = limit_saniye


#: Yarim kalan sentezin KULLANILABILIR sayilmasi icin gereken en az karakter.
#:
#: Altinda kalirsa metin bir ise yaramaz ("Portfoyunuz gen..." gibi) ve
#: deterministik ozet daha iyidir. Ustundeyse kullanicinin okudugu gercek
#: analizi atmak zarar verir - o metin zaten EKRANA GITTI, geri alinamaz.
KISMI_YANIT_ASGARI_KARAKTER = 120

#: Yarim kalan sentezin sonuna eklenen aciklama.
KISMI_YANIT_NOTU = "(Yanıtın devamı teknik bir nedenle üretilemedi.)"

#: Uyum ibaresi - `SYNTHESIZER_SYSTEM_PROMPT` 13. madde ile AYNI metin.
YATIRIM_TAVSIYESI_IBARESI = "Bu bilgiler yatırım tavsiyesi değildir."

#: Cikti guvenlik denetimi basarisiz oldugunda donen sabit mesaj.
SAFE_RESPONSE_MESSAGE = (
    "Şu anda güvenli bir yanıt üretemiyorum. Lütfen sorunuzu farklı bir "
    "şekilde ifade ederek tekrar deneyin."
)

#: Synthesizer sistem prompt'u - uyum kurallarini tasir.
SYNTHESIZER_SYSTEM_PROMPT = """Sen bir kişisel finans danışmanı asistanısın.
Elindeki uzman analizlerini, KULLANICININ SORDUĞU SORUYA cevap veren tek bir
Türkçe yanıta dönüştür.

ÖNCE SORUYU CEVAPLA
1. İlk cümle sorunun doğrudan cevabı olsun. Girişe, başlığa, "analizlerinize
   göre" gibi hazırlık cümlelerine yer verme.
2. Uzman analizleri senin HAM MALZEMEN; rapor değil. Hepsini sırayla anlatma.
   Yalnızca soruyu cevaplamaya yarayan kısmı kullan, gerisini bırak.
3. Kullanıcı portföyünü sormadıysa yanıta portföy dökümüyle BAŞLAMA. Portföy
   bilgisi ancak cevabı değiştiriyorsa ve tek cümleyle girer.

KISA TUT
4. En fazla 150 kelime. Cevap net olduğunda 2-3 cümlede bitir.
5. Madde listesi yalnızca gerçekten liste olan şeyler için (örn. birkaç yıllık
   getiri). Üç maddeyi geçme.
6. Aynı sayıyı iki kez yazma; tekrar eden cümle kurma.

DÜRÜSTLÜK
7. Sayıları uzmanlardan geldiği gibi kullan. YENİ SAYI ÜRETME, yuvarlayıp
   değiştirme, veriden çıkarım yapıp rakam uydurma.
8. Veri az ya da yetersizse bunu tek cümleyle açıkça söyle; uzmanın "yeterli
   değildir" uyarısını YUTMA.
9. Bir uzmandan veri gelmediyse dürüstçe belirt.
10. Kişisel veri (TCKN, hesap/IBAN numarası, telefon, e-posta) yazma; geçse
    bile maskele.
11. Kullandığın bilgi bir kaynağa dayanıyorsa kaynağı kısaca belirt.
12. Sade dil kullan; gereksiz teknik jargondan kaçın.
13. Yanıtın sonuna mutlaka "Bu bilgiler yatırım tavsiyesi değildir." ibaresini
    ekle."""


#: Ajan adi -> "bu ajanin kelimelerinden biri kelime BASINDA geciyor mu"
#: sorusunu tek geciste yanitlayan derlenmis desen.
_KELIME_DESENLERI: dict[str, re.Pattern[str]] = {
    ajan: re.compile("|".join(rf"\b{re.escape(kelime)}" for kelime in kelimeler))
    for ajan, kelimeler in INTENT_KEYWORDS.items()
    if kelimeler
}


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
        synthesizer_stall_seconds: int = 20,
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
            synthesizer_timeout_seconds: DIS sinir - sentezin TOPLAM suresi.
                Emniyet subabidir.
            synthesizer_stall_seconds: IC sinir - iki token ARASINDA en fazla
                bekleme. Model ortada takilirsa dis siniri beklemeden durur ve
                o ana kadar uretilen metin KORUNUR (bkz. `synthesize`).
        """
        self.agents = agents
        self.security_agent = security_agent
        self.synthesizer_llm = synthesizer_llm
        self.synthesizer_timeout_seconds = synthesizer_timeout_seconds
        # Ic sinir her zaman dis sinirdan kucuk kalmali; aksi halde dis iptal
        # once devreye girer ve iki kademeli yapinin anlami kaybolur.
        self.synthesizer_stall_seconds = max(
            1, min(synthesizer_stall_seconds, synthesizer_timeout_seconds - 1)
        )
        self.checkpointer = checkpointer if checkpointer is not None else MemorySaver()
        #: Router'in KOSULLU olarak tetikledigi ilk katman. `_add_agent_edges`
        #: doldurur, `_kapsam_dallanmasi` calisma aninda okur.
        self._router_hedefleri: tuple[str, ...] = ()
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
        builder.add_node(NODE_SMALL_TALK, self.small_talk_response)

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
        # Kapsam disi yanit ajanlari da SENTEZLEYICIYI de atlar: metin sabittir,
        # LLM cagrisi yapilmaz. "Merhaba" demek bir model cagrisina mal olmaz.
        builder.add_edge(NODE_SMALL_TALK, END)

        return builder

    def _add_agent_edges(self, builder: StateGraph) -> None:
        """Router ile guvenlik kapisi arasindaki ajan kenarlarini kurar.

        Topoloji `PARALLEL_AGENTS` / `SEQUENTIAL_AGENTS` sabitlerinden turetilir
        ve YALNIZCA kayitli ajanlar icin kenar uretilir. Bu sayede:
          - Henuz yazilmamis bir ajan graph'i bozmaz.
          - Yeni ajan eklemek icin sabit listeye bir satir eklemek yeterlidir.

        Router'dan cikan kenar KOSULLUDUR: sorgu finans kapsaminin disindaysa
        (`small_talk`) ajan katmanlarina hic girilmez. Geri kalan katmanlar
        arasi kenarlar statiktir - bir kez ajan faznina girildikten sonra
        topoloji her zaman ayni sekilde akar.
        """
        parallel = [name for name in PARALLEL_AGENTS if name in self.agents]
        sequential = [name for name in SEQUENTIAL_AGENTS if name in self.agents]

        # Sabit listelerde tanimsiz ama enjekte edilmis ajanlar (ornegin test
        # sahte ajanlari) bagimsiz kabul edilip paralel faza alinir.
        known = set(PARALLEL_AGENTS) | set(SEQUENTIAL_AGENTS)
        parallel.extend(name for name in self.agents if name not in known)

        # Katman listesi: [paralel ajanlar] -> [sirali ajan] -> ... -> [gate]
        # Hic ajan kayitli degilse tek katman kalir ve router dogrudan guvenlik
        # kapisina baglanir - graph yine gecerlidir.
        katmanlar: list[list[str]] = []
        if parallel:
            katmanlar.append(parallel)
        katmanlar.extend([ad] for ad in sequential)
        katmanlar.append([NODE_SECURITY_GATE])

        # FAN-IN: her katman bir oncekinin TAMAMINI bekler. LangGraph, bir
        # node'a gelen tum kenarlar tamamlanmadan o node'u calistirmaz;
        # bekleme mantigi otomatik yonetilir.
        onceki = katmanlar[0]
        for katman in katmanlar[1:]:
            for hedef in katman:
                for ust in onceki:
                    builder.add_edge(ust, hedef)
            onceki = katman

        # FAN-OUT: ilk katmanin tamami router'dan AYNI ANDA tetiklenir.
        # Kosullu kenar fonksiyonu liste dondurdugunde LangGraph bunu paralel
        # fan-out olarak uygular - statik kenarla ayni topoloji, tek farki
        # kapsam disi sorgularda hic tetiklenmemesi.
        self._router_hedefleri = tuple(katmanlar[0])
        builder.add_conditional_edges(
            NODE_ROUTER,
            self._kapsam_dallanmasi,
            {NODE_SMALL_TALK: NODE_SMALL_TALK, **{ad: ad for ad in self._router_hedefleri}},
        )

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

    def _kapsam_dallanmasi(self, state: AgentState) -> str | list[str]:
        """Kapsam disi sorguyu kisa yanita, finans sorusunu ajanlara yollar.

        Liste dondurmek LangGraph'ta PARALEL FAN-OUT demektir; finans yolunda
        donen liste, kosullu kenar eklenmeden onceki statik kenarlarin birebir
        karsiligidir.
        """
        if state.scope in KISA_YANIT_KAPSAMLARI:
            return NODE_SMALL_TALK
        return list(self._router_hedefleri)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route_node(self, state: AgentState) -> dict:
        """Once KAPSAM, sonra niyet karari verir.

        Iki asamalidir ve sira onemlidir:

          1. KAPSAM - "bu soru bize mi?" Finans disiysa `requested_agents` bos
             kalir ve `_kapsam_dallanmasi` akisi `small_talk`'a cevirir; hicbir
             ajan, hicbir LLM calismaz.
          2. NIYET - "hangi uzman?" Yalnizca finans sorularinda calisir.

        NOT: Ajan katmanlari arasindaki kenarlar STATIKTIR; bu node ajanlari
        tek tek devre disi birakmaz, yalnizca `requested_agents` listesini
        doldurur. Ajanlar bu listeye bakarak kendilerini erken sonlandirabilir
        (ucuz no-op) - bkz. `BaseAgent.is_requested`.
        """
        kapsam = kapsam_belirle(state.user_query, devam_turu=self._devam_turu(state))

        if kapsam in KISA_YANIT_KAPSAMLARI:
            logger.info(
                "sorgu finans kapsami disinda, ajanlar atlaniyor",
                extra={"scope": kapsam, "request_id": state.request_id},
            )
            return {"requested_agents": [], "intent": "sohbet", "scope": kapsam}

        requested = self.route_intent(state)
        return {
            "requested_agents": requested,
            "intent": self._intent_adi(requested),
            "scope": kapsam,
        }

    @staticmethod
    def _devam_turu(state: AgentState) -> bool:
        """Bu sohbette daha once en az bir tur yasandi mi?

        `stream_request` her turun basinda kullanicinin mesajini listeye ekler;
        onceki turlar checkpointer'dan geri gelir. Yani listede mevcut sorudan
        BASKA bir sey varsa bu bir devam turudur.

        Neden onemli: "Peki ya simdi?" ya da "Neden?" gibi devam sorulari tek
        baslarina hicbir finans sinyali tasimaz. Kapsam siniflandirici bunlari
        ilk turda netlestirme sorusuna yollar, devam turunda ise ajanlara
        birakir - aksi halde cok turlu sohbet (FR-CHAT-03) kirilir.
        """
        return len(state.messages) > 1

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

    @staticmethod
    def _piyasa_sinyali_var(ham_sorgu: str, requested: list[str]) -> bool:
        """Sorgu belirli bir ENSTRUMANDAN mi soz ediyor?

        Iki isaret: piyasa ajaninin kendi anahtar kelimeleri, ya da ham metinde
        buyuk harfli bir BIST sembolu ("THYAO almami tavsiye eder misin" -
        burada hicbir piyasa kelimesi yok ama soru acikca bir hisse hakkinda).

        Kucuk harfle yazilan ciplak sembol yakalanmaz; onu cozmek sembol
        listesini okumayi gerektirir ve router bilincli olarak LLM'siz ve
        senkron tutuluyor (bkz. `kapsam.SEMBOL_DESENI`).
        """
        return AGENT_MARKET_RESEARCH in requested or bool(SEMBOL_DESENI.search(ham_sorgu))

    @staticmethod
    def _yalnizca_genel_tavsiye(normalized: str) -> bool:
        """Risk ajani SADECE genel bir tavsiye kelimesiyle mi eslesti?

        `True` ise sorguda "risk", "dengele", "cesitlendir", "strateji" gibi
        gercek bir risk/portfoy stratejisi kelimesi YOKTUR - yalnizca "tavsiye"
        ya da "oneri" gecmistir.
        """
        desen = _KELIME_DESENLERI.get(AGENT_RISK_STRATEGY)
        if desen is None:
            return False
        eslesmeler = {e.group().strip() for e in desen.finditer(normalized)}
        return bool(eslesmeler) and eslesmeler <= _GENEL_TAVSIYE_KELIMELERI

    def route_intent(self, state: AgentState) -> list[str]:
        """Bir FINANS sorusunda hangi uzmanlarin anlamli oldugunu secer.

        Kural tabanli calisir (LLM'siz): ucretsiz API kotasini korumak icin
        bilincli bir tercihtir.

        Kapsam karari bu metottan ONCE verilmistir (bkz. `route_node`); burasi
        artik yalnizca finans sorularini gorur. Hicbir anahtar kelime
        eslesmediginde ne yapilacagi buna gore degisir - asagidaki iki dala
        bakin.
        """
        normalized = _normalize(state.user_query)

        requested = [
            name
            for name in self.agents
            if name in _KELIME_DESENLERI and _KELIME_DESENLERI[name].search(normalized)
        ]

        if not requested:
            # Devam turu: baglam onceki turda, hangi uzmanin gerektigi buradan
            # anlasilamaz ("Peki ya simdi?"). Eski guvenli varsayilan korunur -
            # eksik yanit vermektense biraz fazla calis.
            if self._devam_turu(state):
                return list(self.agents)

            # Ilk tur: finans sinyali VAR ama hangi uzman oldugu belirsiz
            # ("THYAO ne kadar?"). Varsayilan PIYASA ARASTIRMASIDIR.
            #
            # ESKI DAVRANIS: burada da TUM ajanlar donuyordu. Sonuc, kullanici
            # tek bir hisse sordugunda yanitin portfoy dokumuyle baslamasiydi -
            # istenmeyen bir bolum, ustelik risk ajanini da tetikleyip
            # `tool_error` uretiyordu. Piyasa ajaninin RAG geri donusu genel
            # finans sorularini da karsiladigi icin dogru varsayilan odur.
            if AGENT_MARKET_RESEARCH in self.agents:
                return [AGENT_MARKET_RESEARCH]
            return list(self.agents)

        # Genel tavsiye kelimesi + piyasa sorusu = enstruman tavsiyesi.
        # "THYAO almami tavsiye eder misin?" sorusunda tavsiye edilen sey
        # kullanicinin portfoyu degil, sordugu hisse. Risk ajanini burada
        # tutmak portfoy ajanini da zincirle getiriyor ve yanit istenmeyen bir
        # portfoy dokumuyle sisiyordu.
        if (
            AGENT_RISK_STRATEGY in requested
            and self._yalnizca_genel_tavsiye(normalized)
            and self._piyasa_sinyali_var(state.user_query, requested)
        ):
            requested.remove(AGENT_RISK_STRATEGY)
            if AGENT_MARKET_RESEARCH in self.agents and AGENT_MARKET_RESEARCH not in requested:
                requested.append(AGENT_MARKET_RESEARCH)

        # Risk ajani PORTFOY VERISINE bagimlidir: `risk_strategy.py::_execute`
        # `state.portfolio_data is None` ise hesaplamayi reddedip
        # `tool_error` uretir. Bu yuzden yalnizca portfoy ajani da
        # istendiginde otomatik ekleniyor.
        #
        # ESKI DAVRANIS: "herhangi bir PARALLEL ajan istendiyse" ekleniyordu.
        # Piyasa sorusu (portfoysuz) risk ajanini tetikliyor, o da portfoy
        # verisi olmadigi icin patlayip kullaniciya "risk_strategy ajani
        # gecici olarak tamamlanamadi" yaziyordu - hem gereksiz hem yaniltici.
        if (
            AGENT_RISK_STRATEGY in self.agents
            and AGENT_RISK_STRATEGY not in requested
            and AGENT_PORTFOLIO in requested
        ):
            requested.append(AGENT_RISK_STRATEGY)

        # Ters yon: risk DOGRUDAN istendiyse ("riskim ne durumda?") portfoy
        # ajani da sart - risk skoru `state.portfolio_data` uzerinden
        # hesaplaniyor. Eklemezsek risk ajani portfoy verisi bulamayip
        # `tool_error` uretir.
        if (
            AGENT_RISK_STRATEGY in requested
            and AGENT_PORTFOLIO in self.agents
            and AGENT_PORTFOLIO not in requested
        ):
            requested.append(AGENT_PORTFOLIO)

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
        # Sentez coktugunde kullanici deterministik ozete duser. Bu iyi bir
        # kademeli bozulma AMA SESSIZDI: hata yalnizca loga yaziliyordu ve
        # disaridan bakan "yanit neden boyle genel?" sorusunun cevabini
        # bulamiyordu. Artik hata `agent_errors`'a da yaziliyor, yani SSE
        # `agent_error` olayi olarak arayuze ulasiyor.
        hatalar: list[AgentError] = []

        # AKIS BIRIKTIRICISI cagiran tarafta durur - `_stream_llm` iptal
        # edilse bile icindeki metin BURADA kalir. Zaman asiminda o ana kadar
        # uretilmis analizi kurtarabilmemizin tek yolu budur; liste
        # `_stream_llm`'in icinde olsaydi iptalle birlikte erisilemez olurdu.
        parcalar: list[str] = []

        try:
            text = await asyncio.wait_for(
                self._stream_llm(messages, config, parcalar),
                timeout=self.synthesizer_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "synthesizer dis zaman asimina ugradi",
                extra={"limit_sn": self.synthesizer_timeout_seconds},
            )
            text = self._kismi_yanit_veya_ozet(state, parcalar)
            hatalar.append(
                AgentError(
                    agent_name=NODE_SYNTHESIZER,
                    error_type="timeout",
                    message=f"{self.synthesizer_timeout_seconds}s icinde tamamlanmadi",
                )
            )
        except _SentezDurdu as durus:
            # IC sinir: akis ortada takildi. Dis siniri beklemeye gerek yok.
            logger.warning(
                "synthesizer token akisi durdu",
                extra={"limit_sn": self.synthesizer_stall_seconds},
            )
            text = self._kismi_yanit_veya_ozet(state, parcalar)
            hatalar.append(
                AgentError(
                    agent_name=NODE_SYNTHESIZER,
                    error_type="timeout",
                    message=(
                        f"Model {durus.limit_saniye} saniye boyunca yeni token uretmedi; "
                        "uretilen kisim korundu."
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001 - sentez cokerse kullanici bos ekran gormesin
            logger.exception("synthesizer beklenmeyen hata verdi")
            text = self._kismi_yanit_veya_ozet(state, parcalar)
            hatalar.append(
                AgentError(agent_name=NODE_SYNTHESIZER, error_type="llm_error", message=str(exc))
            )

        guncelleme: dict = {"final_response": text, "messages": [AIMessage(content=text)]}
        if hatalar:
            guncelleme["agent_errors"] = hatalar
        return guncelleme

    def _kismi_yanit_veya_ozet(self, state: AgentState, parcalar: list[str]) -> str:
        """Yarim kalan sentezi kurtarir; kurtarilamiyorsa deterministik ozete duser.

        ⚠️ NEDEN ATMIYORUZ: `stream_request` uretilen token'lari ANINDA
        kullaniciya yolluyor ve bir kez yayinlandiktan sonra geri alinamiyor
        (`token_yayinlandi`). Zaman asiminda metni atip deterministik ozete
        donmek, kullanicinin ekraninda yarim cumle BIRAKIYORDU - canli testte
        goruldu: "... Risk skoru 78/100 ile" diye kesilip kaldi ve uyum
        ibaresi bile eklenemedi.

        Bu yuzden yeterince uzun bir kisim uretildiyse o metin TAMAMLANIR:
        yarim cumle atilir, durum notu ve uyum ibaresi eklenir.
        """
        kismi = "".join(parcalar).strip()
        if len(kismi) < KISMI_YANIT_ASGARI_KARAKTER:
            # Elde anlamli bir metin yok; deterministik ozet daha iyi.
            return self._fallback_response(state)

        # Cumle ortasinda kesildiyse son yarim cumleyi at - "Risk skoru 78/100
        # ile" gibi asili bir ifade birakmaktansa tam cumlede bitirmek yeglenir.
        son_sinir = max(kismi.rfind("."), kismi.rfind("!"), kismi.rfind("?"), kismi.rfind("\n"))
        if son_sinir >= KISMI_YANIT_ASGARI_KARAKTER:
            kismi = kismi[: son_sinir + 1].rstrip()

        satirlar = [kismi, "", KISMI_YANIT_NOTU]
        # Uyum ibaresi zorunlu (bkz. SYNTHESIZER_SYSTEM_PROMPT 13. madde);
        # sentez yarim kaldigi icin model onu yazmaya firsat bulamamis olabilir.
        if YATIRIM_TAVSIYESI_IBARESI not in kismi:
            satirlar.append(YATIRIM_TAVSIYESI_IBARESI)
        return "\n".join(satirlar)

    async def _stream_llm(
        self,
        messages: list,
        config: RunnableConfig | None = None,
        parcalar: list[str] | None = None,
    ) -> str:
        """LLM'i token token calistirir ve tam metni doner.

        `config` LLM cagrisina ACIKCA gecirilir. Bunun sebebi: LangGraph
        token'lari callback zinciri uzerinden yakalar; callback'ler ise
        `asyncio.wait_for` gibi yeni bir task acan cagrilarda ve Python 3.10'da
        otomatik olarak tasinmaz. Config elden gecirilmezse kod hata vermez ama
        streaming SESSIZCE calismaz - yanit ancak tamamlandiktan sonra tek
        parca gider.
        """
        # Tek seferlik istemciye (app.core.llm.GeminiLLMClient /
        # NvidiaLLMClient) dusuldugunde `astream` YOKTUR. Sentez o durumda da
        # LLM ile yapilmali - yalnizca akis olmaz. `stream_request` token
        # uretilmeyen yollarda nihai metni tek token olayi olarak gonderdigi
        # icin frontend sozlesmesi degismez.
        if not hasattr(self.synthesizer_llm, "astream"):
            return await self.synthesizer_llm.generate(_mesajlari_metne_cevir(messages))

        # Biriktirici CAGIRAN TARAFTAN gelir; boylece bu coroutine iptal
        # edilse bile uretilen metin kaybolmaz (bkz. `synthesize`).
        parts: list[str] = parcalar if parcalar is not None else []

        akis = self.synthesizer_llm.astream(messages, config=config)
        while True:
            try:
                # IC SINIR: iki token ARASI bekleme. Dis sinir toplam sureyi
                # olcer ve saglikli ama uzun bir yaniti da keser; asil belirti
                # modelin ORTADA TAKILMASI - bunu burada erken yakaliyoruz.
                chunk = await asyncio.wait_for(
                    akis.__anext__(), timeout=self.synthesizer_stall_seconds
                )
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError as exc:
                # `aclose` cagrilmazsa altta acik kalan HTTP baglantisi
                # tick tick birikir (ajan tarafinda ayni ders alinmisti).
                await akis.aclose()
                raise _SentezDurdu(self.synthesizer_stall_seconds) from exc

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

        eksikler = self._verisi_eksik_ajanlar(state)
        if eksikler:
            hatalar = "\n".join(f"- {ad}" for ad in eksikler)
            bolumler.append("\nUlasilamayan veriler (kullaniciya durustce belirt):\n" + hatalar)

        return "\n".join(bolumler)

    @staticmethod
    def _verisi_eksik_ajanlar(state: AgentState) -> list[str]:
        """Hata veren ajanlardan GERCEKTEN veri uretemeyenler.

        `agent_errors` listesinde olmak "veri yok" demek DEGILDIR. Ajanlar
        kismi basari uretebiliyor: portfoy ajani rakamlari hesapladiktan sonra
        LLM yorumu alamazsa deterministik ozetini korur ve yanina `llm_error`
        ekler - veri tamdir, yalnizca cumleyi model kurmamistir.

        Ayrimi yapmadan "su analizlere ulasilamadi" yazmak kullaniciyi
        YANILTIR. Canlida birebir goruldu: yanit portfoy toplamini, risk
        skorunu ve gerekcelerini eksiksiz yazdiktan sonra altina "Not: Su
        analizlere su anda ulasilamadi: portfolio, risk_strategy" ekliyordu.
        """
        veri_alani = {
            AGENT_PORTFOLIO: state.portfolio_data,
            AGENT_MARKET_RESEARCH: state.market_data,
            AGENT_RISK_STRATEGY: state.risk_data,
        }
        eksikler: list[str] = []
        for hata in state.agent_errors:
            ad = getattr(hata, "agent_name", None) or (
                hata.get("agent_name") if isinstance(hata, dict) else None
            )
            # Sentezleyici bir VERI ajani degil; kendi hatasini "su analize
            # ulasilamadi" diye kullaniciya yazmak anlamsiz olurdu.
            if ad == NODE_SYNTHESIZER:
                continue
            if not ad or ad in eksikler:
                continue
            # Tanimadigimiz bir ajan icin guvenli varsayilan: eksik say.
            if veri_alani.get(ad, None) is None:
                eksikler.append(ad)
        return sorted(eksikler)

    @staticmethod
    def _bolum_sirasi(state: AgentState) -> list[str]:
        """Yanit bolumlerinin sirasi: once router'in istedikleri, sonra geri kalan.

        Router `requested_agents`'i niyet sirasinda dolduruyor: "THYAO alayim
        mi?" sorusunda piyasa arastirmasi basa, portfoy sona geliyor. Geri
        kalan ajanlar (router istemedigi halde veri uretmisse) sabit sirayla
        eklenir, boylece hicbir veri kaybolmaz.
        """
        sira = [ad for ad in state.requested_agents if ad in _BOLUM_BASLIKLARI]
        sira += [ad for ad in _BOLUM_BASLIKLARI if ad not in sira]
        return sira

    def _fallback_response(self, state: AgentState) -> str:
        """LLM olmadan uretilen deterministik yanit.

        Iki durumda kullanilir:
          1. `synthesizer_llm` henuz baglanmadi (iskelet/test asamasi).
          2. LLM cagrisi zaman asimina ugradi veya hata verdi.

        Uretilen metin de uyum kurallarina uyar: eksik veriyi durustce belirtir
        ve yatirim tavsiyesi ibaresini icerir.

        BOLUM SIRASI ROUTER'IN SIRASIDIR. Sabit sira (once portfoy) kullanici
        tek bir hisse sordugunda bile yaniti portfoy dokumuyle baslatiyordu -
        sorunun cevabi en altta kaliyordu. `requested_agents` zaten niyet
        sirasinda geliyor (bkz. `route_intent`), onu kullaniyoruz.
        """
        satirlar: list[str] = []

        for ajan in self._bolum_sirasi(state):
            baslik, veri = _BOLUM_BASLIKLARI[ajan], _AJAN_VERISI[ajan](state)
            if veri is not None:
                satirlar.append(f"{baslik}: {_ajan_metni(veri)}")

        if not satirlar:
            satirlar.append("Şu anda görüntülenebilecek bir analiz sonucu bulunmuyor.")

        # Kismi basarisizlik: hangi uzmandan VERI GELMEDIGINI durustce soyle.
        # Hata veren ama verisini yine de ureten ajan (orn. LLM yorumu
        # alinamayan portfoy ajani) buraya GIRMEZ - bkz. `_verisi_eksik_ajanlar`.
        eksik_ajanlar = self._verisi_eksik_ajanlar(state)
        if eksik_ajanlar:
            satirlar.append(f"Not: Şu analizlere şu anda ulaşılamadı: {', '.join(eksik_ajanlar)}.")

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
        mesaj = PII_REJECT_MESSAGE if PII_FLAG in (state.security_flags or []) else REJECT_MESSAGE
        return {"final_response": mesaj, "messages": [AIMessage(content=mesaj)]}

    def small_talk_response(self, state: AgentState) -> dict:
        """Finans kapsami disindaki sorguya tek cumlelik sabit yanit.

        Bu node'a gelindiginde hicbir ajan ve hicbir LLM calismamistir. Metin
        `app.engine.kapsam` icindeki sabit tablodan gelir - yani "merhaba"
        demek ne token ne de kota harcar.

        `reject_response`'tan farki: orada bir GUVENLIK karari vardir, burada
        yalnizca konu disi bir sorgu. Kullaniciya donen dil de buna gore
        farklidir (bkz. modul docstring'i, "IKI FARKLI HAYIR YOLU").
        """
        metin = kisa_yanit(state.scope or KAPSAM_BELIRSIZ)
        logger.info(
            "kapsam disi sorgu kisa yanitla sonlandirildi",
            extra={"scope": state.scope, "request_id": state.request_id},
        )
        return {"final_response": metin, "messages": [AIMessage(content=metin)]}

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
            # Router her turda yeniden yazar; yine de onceki turun kapsam
            # etiketi bir an bile gorunmesin diye acikca sifirlaniyor.
            "scope": None,
        }
        # LangGraph checkpointer'i thread_id'yi string bekler; DB'deki
        # `chat_sessions.id` ise int. Donusum sinirda TEK yerde yapilir.
        config = {"configurable": {"thread_id": str(thread_id)}}

        token_yayinlandi = False
        kaynaklar_yayinlandi = False
        toplanan_kaynaklar: list[Source] = []
        son_yanit: str | None = None
        #: Kullaniciya GERCEKTEN gonderilmis token'lar. Nihai metin bundan
        #: uzunsa aradaki fark sonda ek token olarak yollanir (bkz. asagisi).
        yayinlanan: list[str] = []

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
                        yayinlanan.append(token)
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
        elif son_yanit and token_yayinlandi:
            # AKIS YARIM KALDIYSA KUYRUGU GONDER.
            #
            # Sentez zaman asimina ugradiginda `_kismi_yanit_veya_ozet` metni
            # tamamliyor (yarim cumleyi atiyor, durum notu ve uyum ibaresi
            # ekliyor) - ama bu ek metin kullaniciya HIC ULASMIYORDU: token
            # yayinlandigi icin yukaridaki dal atlaniyor, nihai metin de
            # yalnizca veritabanina yaziliyordu. Kullanici ekranda yarim
            # cumleyle kaliyordu (canli testte olculdu: "... Risk skoru 78/100
            # ile" diye kesildi, uyum ibaresi hic gorunmedi).
            akan = "".join(yayinlanan)
            if son_yanit.startswith(akan) and len(son_yanit) > len(akan):
                yield {"type": "token", "content": son_yanit[len(akan) :]}

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
    def _hata_ayrintisi_gonderilsin() -> bool:
        """Ajan hatasinin METNI istemciye gitsin mi?

        URETIMDE HAYIR: istisna metni ic ayrinti (tool adi, baglanti dizesi,
        dosya yolu) tasiyabilir.

        GELISTIRMEDE EVET. Sebep aci deneyimden geliyor: canlida her LLM
        cagrisi patliyordu ve kullaniciya giden tek bilgi "llm_error"di. Bu
        kelime hicbir sey soylemiyor - 400 mu, 404 mu, anahtar mi, kota mi
        belli degil. Ayrinti loglara yaziliyordu ama hatayi arayan kisi
        arayuze bakiyordu. Gelistirirken hatayi GORUNDUGU yerde gostermek,
        sunucu loglarina inmekten cok daha hizli.
        """
        return (settings.app_env or "").strip().lower() not in ("production", "prod")

    @classmethod
    def _agent_error_olayi(cls, hata) -> dict:
        """`AgentError`'i SSE olayina cevirir.

        Frontend'e ajan adi ve hata TURU yeter - "piyasa verisine ulasilamadi"
        cumlesini bu ikisinden kurar. Hata METNI yalnizca uretim disinda
        eklenir (bkz. `_hata_ayrintisi_gonderilsin`).
        """
        if isinstance(hata, AgentError):
            olay = {"type": "agent_error", "agent": hata.agent_name, "error_type": hata.error_type}
            mesaj = hata.message
        elif isinstance(hata, dict):
            olay = {
                "type": "agent_error",
                "agent": hata.get("agent_name", "bilinmiyor"),
                "error_type": hata.get("error_type", "unknown"),
            }
            mesaj = hata.get("message", "")
        else:
            olay = {"type": "agent_error", "agent": "bilinmiyor", "error_type": "unknown"}
            mesaj = ""

        if mesaj and cls._hata_ayrintisi_gonderilsin():
            olay["message"] = str(mesaj)[:500]
        return olay

    @staticmethod
    def _status_message(node_name: str, update) -> str | None:
        """Bir node tamamlandiginda kullaniciya gonderilecek ilerleme mesajini secer.

        Guvenlik node'lari icin mesaj KOSULLUDUR: denetim basarisiz olduysa
        "denetimden gecti" demek kullaniciyi yaniltir. Bu durumda ilerleme
        mesaji hic gonderilmez; hemen ardindan gelen ret/guvenli yanit metni
        durumu zaten aciklar.

        Ayni gerekce router icin de gecerli: kapsam disi bir sorguda "Ilgili
        uzmanlar belirlendi." demek yanlistir - hicbir uzman calismayacak.
        """
        if isinstance(update, dict):
            if node_name == NODE_SECURITY_IN and update.get("is_input_safe") is False:
                return None
            if node_name == NODE_SECURITY_GATE and update.get("is_output_safe") is False:
                return None
            if node_name == NODE_ROUTER and update.get("scope") in KISA_YANIT_KAPSAMLARI:
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


def _mesajlari_metne_cevir(messages: Sequence) -> str:
    """LangChain mesaj listesini duz metne cevirir.

    Yalnizca `generate(prompt: str)` sunan tek seferlik istemciler icin
    gerekli. Rol etiketleri korunur; aksi halde sistem prompt'undaki uyum
    kurallari kullanici metniyle birbirine karisir.
    """
    _ROL = {"system": "SISTEM", "human": "KULLANICI", "ai": "ASISTAN"}
    satirlar: list[str] = []
    for mesaj in messages:
        icerik = getattr(mesaj, "content", None)
        if not icerik:
            continue
        rol = _ROL.get(getattr(mesaj, "type", ""), "KULLANICI")
        satirlar.append(f"[{rol}]\n{icerik}")
    return "\n\n".join(satirlar)


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
