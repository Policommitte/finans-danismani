"""Orkestrasyon katmaninin ortak veri modelleri.

Bu modul, LangGraph graph'i boyunca tasinan durumu (`AgentState`) ve ajanlarin
uretttigi yardimci yapilari (`Source`, `AgentError`, `ToolResult`) tanimlar.
Tum ajanlar ve orchestrator ayni modelleri kullanir; boylece bir ajanin yazdigi
alani baska bir ajan dogrudan okuyabilir.

DIKKAT: Bu dosyadaki reducer kurallari graph'in dogru calismasi icin kritiktir.
Degistirmeden once bolum "AgentState" docstring'ini okuyun.

NOT (paket adi): Bu paket onceden `app/schema/` adiyla duruyordu ve REST
modellerini tutan `app/schemas/` ile yan yanaydi; tek harf farki kalici
karisiklik uretiyordu (mimari v4 bolum 12). Orkestrasyon modelleri artik
`app/orchestration/`, REST modelleri `app/schemas/` altindadir.
"""

from typing import Annotated, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

#: Reducer'li bir alani TUR BASINDA sifirlamak icin kullanilan sentinel.
#:
#: Neden gerekli: `operator.add` gibi birikimli reducer'lar, giris state'ine
#: `[]` yazilarak sifirlanamaz - LangGraph giris degerini checkpoint'teki
#: degere reducer ile UYGULAR, `[] + mevcut` ise "hicbir sey ekleme" demektir,
#: sifirlama degil. Ayni `thread_id` ile ikinci tura girildiginde `sources` ve
#: `agent_errors` onceki turun degerlerinin uzerine eklenir; synthesizer ayni
#: kaynaklari tekrar tekrar listeler ve bir turda hata veren ajan duzelse bile
#: "ulasilamadi" uyarisi kalir.
#:
#: Sentinel duz bir string'dir; checkpointer'in serilestirebilmesi icin
#: (msgpack) ozel bir sinif KULLANILMAZ.
RESET = "__RESET__"


def add_or_reset(current: list | None, update) -> list:
    """Birikimli reducer + tur basi sifirlama destegi.

    Davranis:
        add_or_reset([a], [b])          -> [a, b]      (normal birikim)
        add_or_reset([a], [RESET])      -> []          (turu sifirla)
        add_or_reset([a], [RESET, b])   -> [b]         (sifirla + yaz)

    LangGraph'in `messages` alanindaki `RemoveMessage` deseninin muadilidir:
    kanali temizlemenin tek yolu, reducer'in anladigi ozel bir deger gondermek.
    """
    if update is None:
        return list(current or [])

    if not isinstance(update, (list, tuple)):
        update = [update]

    if update and update[0] == RESET:
        return list(update[1:])

    return list(current or []) + list(update)


class Source(BaseModel):
    """RAG yanitinin dayandigi kaynak dokuman.

    Kullanicinin "bu bilgi nereden geldi?" sorusuna cevap verebilmek icin
    (FR-RAG-04 izlenebilirlik) her RAG sonucu bu modele donusturulup
    `AgentState.sources` listesine eklenir.
    """

    doc_id: str
    baslik: str
    sirket: str | None = None
    tarih: str | None = None
    tip: str | None = None  # haber | bilanco | analist_raporu | duyuru
    score: float | None = None


class AgentError(BaseModel):
    """Bir ajanin basarisizligi.

    ONEMLI: Bu hata akisi DURDURMAZ. Ajan cokse bile graph devam eder ve
    synthesizer eksik veriyle durust bir yanit uretir ("piyasa verisine su anda
    ulasilamadi"). Boylece tek bir ajanin cokmesi tum istegi dusurmez.
    """

    agent_name: str
    error_type: Literal["timeout", "tool_error", "llm_error", "unknown"]
    message: str


class ToolResult(BaseModel):
    """Bir MCP tool cagrisinin sonucu.

    `latency_ms` alani izlenebilirlik icin tutulur (NFR-05): hangi tool'un ne
    kadar surdugu loglanabilsin diye.
    """

    tool_name: str
    output: dict
    latency_ms: float
    success: bool = True
    error: str | None = None


class RouterDecision(BaseModel):
    """Router node'unun karari (mimari v4 bolum 10.4).

    Router KURAL TABANLIDIR (LLM'siz); model bu karari yalnizca yapilandirilmis
    halde tasimak icin vardir - loglanabilir ve test edilebilir olur.
    """

    intent: Literal["portfoy", "piyasa", "risk", "karma", "sohbet", "belirsiz"]
    agents: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarifying_question: str | None = None
    reasoning: str = ""


class AgentState(BaseModel):
    """Graph boyunca tasinan ortak durum.

    LangGraph node'lari bu modelin bir ornegini alir ve YALNIZCA degisen
    alanlari iceren bir sozluk dondurur. Tum state'i dondurmek paralel
    calismada uzerine yazma (overwrite) hatasina yol acar.

    ONEMLI - Reducer kurali:
        Paralel calisan node'lar AYNI alana yazarsa LangGraph catisma hatasi
        verir. Bu yuzden:
          - Her ajan KENDI alanina yazar (portfolio_data / market_data /
            risk_data) -> catisma yok, reducer gerekmez.
          - Birden fazla node'un yazdigi alanlar (sources, agent_errors,
            security_flags) `Annotated[..., add_or_reset]` ile reducer tasimak
            ZORUNDA. Reducer olmadan ikinci yazan birincinin verisini siler.

    ONEMLI - Tur basi sifirlama:
        Reducer'li alanlar checkpointer'da BIRIKIR. `stream_request` her turun
        basinda bu alanlara `[RESET]` yazar (bkz. `add_or_reset`); aksi halde
        ikinci turda kaynaklar ikiye katlanir.
    """

    # --- Girdi ---
    user_query: str

    # user_id / thread_id INT'tir: DB'de `users.id` ve `chat_sessions.id`
    # SERIAL, MCP yetkilendirmesi de (mimari v4 bolum 6.1) bu degerin
    # contextvar ile KARSILASTIRILMASINA dayanir. Tip donusumu sinirda
    # (auth katmani / API) bir kez yapilir; graph icinde hep int'tir.
    user_id: int
    thread_id: int  # == chat_sessions.id (FR-CHAT-03)

    #: Istegin uctan uca izlenebilirlik kimligi. HTTP katmanindaki
    #: `X-Request-ID` ile AYNI degerdir; `tool_calls` ve `security_events`
    #: kayitlari bu id ile eslesir (NFR-05).
    request_id: str = ""

    #: Islem yapilan portfoy. Verilmezse MCP tool'lari kullanicinin varsayilan
    #: portfoyunu (`portfolios.is_default`) kullanir.
    portfolio_id: int | None = None

    # --- Konusma gecmisi (cok turlu baglam) ---
    # `add_messages` reducer'i yeni mesajlari listeye ekler, uzerine yazmaz.
    # Checkpointer ile birlikte ayni thread_id'deki onceki turlar korunur.
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # --- Routing ---
    # Router node'unun "bu sorgu icin hangi ajanlar anlamli" karari.
    # Kenarlar statik oldugu icin ajanlar bu listeye bakip kendilerini erken
    # sonlandirabilir (ucuz no-op).
    requested_agents: list[str] = Field(default_factory=list)

    #: Router'in tespit ettigi niyet (portfoy | piyasa | risk | karma | ...).
    #: Yalnizca router yazar; loglama ve `chat_messages.meta` icin tutulur.
    intent: str | None = None

    # Ajan bazli OPSIYONEL parametreler: {ajan_adi: {...}}
    #
    # Router bir ajan icin yapilandirilmis parametre uretebildiginde (orn.
    # market_research icin {"symbol": "THYAO", "mode": "live", "top_k": 3})
    # bunu buraya yazar. Bos birakilirsa ajanlar parametreleri `user_query`
    # uzerinden kendileri cikarir - yani bu alan hicbir zaman ZORUNLU degildir.
    # Yalnizca router yazdigi icin paralel yazma catismasi olusmaz.
    agent_tasks: dict[str, dict] = Field(default_factory=dict)

    # --- Ajan ciktilari (her ajan KENDI alanina yazar, catisma yok) ---
    portfolio_data: dict | None = None
    market_data: dict | None = None
    risk_data: dict | None = None

    # --- Paralel yazilan alanlar: reducer ZORUNLU ---
    sources: Annotated[list[Source], add_or_reset] = Field(default_factory=list)
    agent_errors: Annotated[list[AgentError], add_or_reset] = Field(default_factory=list)
    security_flags: Annotated[list[str], add_or_reset] = Field(default_factory=list)

    # --- Guvenlik bayraklari ---
    # security_in node'u girdi icin, security_gate node'u ham ajan ciktisi icin
    # bu alanlari doldurur; conditional edge'ler bu degerlere bakarak dallanir.
    is_input_safe: bool = True
    is_output_safe: bool = True

    # --- Cikti ---
    final_response: str | None = None
