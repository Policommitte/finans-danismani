"""Orkestrasyon katmaninin ortak veri modelleri.

Bu modul, LangGraph graph'i boyunca tasinan durumu (`AgentState`) ve ajanlarin
uretttigi yardimci yapilari (`Source`, `AgentError`, `ToolResult`) tanimlar.
Tum ajanlar ve orchestrator ayni modelleri kullanir; boylece bir ajanin yazdigi
alani baska bir ajan dogrudan okuyabilir.

DIKKAT: Bu dosyadaki reducer kurallari graph'in dogru calismasi icin kritiktir.
Degistirmeden once bolum "AgentState" docstring'ini okuyun.
"""

import operator
from typing import Annotated, Literal

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


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
    tip: str | None = None  # haber | bilanco | analist_raporu
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
            security_flags) `Annotated[..., operator.add]` ile reducer tasimak
            ZORUNDA. Reducer olmadan ikinci yazan birincinin verisini siler.
    """

    # --- Girdi ---
    user_query: str
    user_id: str
    thread_id: str  # oturum kimligi (FR-CHAT-03)

    # --- Konusma gecmisi (cok turlu baglam) ---
    # `add_messages` reducer'i yeni mesajlari listeye ekler, uzerine yazmaz.
    # Checkpointer ile birlikte ayni thread_id'deki onceki turlar korunur.
    messages: Annotated[list, add_messages] = Field(default_factory=list)

    # --- Routing ---
    # Router node'unun "bu sorgu icin hangi ajanlar anlamli" karari.
    # Kenarlar statik oldugu icin ajanlar bu listeye bakip kendilerini erken
    # sonlandirabilir (ucuz no-op).
    requested_agents: list[str] = Field(default_factory=list)

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
    sources: Annotated[list[Source], operator.add] = Field(default_factory=list)
    agent_errors: Annotated[list[AgentError], operator.add] = Field(default_factory=list)
    security_flags: Annotated[list[str], operator.add] = Field(default_factory=list)

    # --- Guvenlik bayraklari ---
    # security_in node'u girdi icin, security_gate node'u ham ajan ciktisi icin
    # bu alanlari doldurur; conditional edge'ler bu degerlere bakarak dallanir.
    is_input_safe: bool = True
    is_output_safe: bool = True

    # --- Cikti ---
    final_response: str | None = None
