# RAG Agent ve MCP Katmani — Backend & DB Ekipleri Icin Ozet

Bu rapor, `RAG-Agent` dalinda su ana kadar eklenen iskeleti anlatir:
`MarketResearchAgent`, paylasilan `MCPClient`/`MCPServer` yapisi, mock MCP
sunuculari ve LLM istemci katmani. Amac; backend'in geri kalanini yazacak
ekibin (Orchestrator, PortfolioAgent, RiskStrategyAgent, API katmani) ve
veri/DB ekibinin (LlamaIndex indeksi, Postgres portfoy DB, KAP/Borsa
entegrasyonu) neyin **sozlesme** olarak kaldigini, neyin **placeholder**
oldugunu net gorebilmesidir.

---

## 1. Klasor Haritasi

```
backend/app/
  agents/
    base.py              # BaseAgent + AgentResult (sozlesme)
    market_research.py   # MarketResearchAgent (RAG + canli veri)
  core/
    llm.py               # LLMClient protokolu + GeminiLLMClient
  mcp/
    client.py            # MCPClient, MCPServer, hata hiyerarsisi (sozlesme)
    mock.py              # build_mock_mcp_client() — dev/test wiring
    servers/
      rag.py             # MCP Server 1 (LlamaIndex) icin mock
      market.py          # MCP Server 3 (Borsa & KAP) icin mock
  tests/
    test_mcp_client.py
    test_market_research_agent.py
```

Eksik olan (bilerek, baska ekipler yazacak):
- Orchestrator / router
- `PortfolioAgent`, `RiskStrategyAgent`
- MCP Server 2 (Portfoy DB / PostgreSQL) — **PortfolioAgent'in sorumlulugunda**
- Gercek MCP transport (JSON-RPC / stdio / SSE)
- API katmani (`app/api/routes/`)

---

## 2. MCP Katmani

### 2.1 Neden "MCP" ama gercek MCP degil

`client.py` docstring'inde de belirtildigi gibi, su an hicbir MCP sunucusu
ayri bir surecte calismiyor. LlamaIndex indeksi, Postgres, Borsa/KAP
entegrasyonlari henuz yok. Bu yuzden `MCPClient`, gercek MCP protokolunun
(JSON-RPC / stdio / SSE) transport'unu **implemente etmez**; agent'larin
bagimli olacagi **cagri sozlesmesini** saglayan **in-process bir
yonlendirme/registry katmanidir**:

```python
await mcp_client.call_tool(server="rag", tool="rag_search", arguments={...})
```

Ileride gercek bir MCP sunucusuna baglanmak gerektiginde, o sunucu icin
`MCPServer.call`'i JSON-RPC uzerinden proxy'leyen yeni bir `MCPServer` alt
sinifi / adaptoru yazilir ve `register_server` ile eklenir. **`BaseAgent`
ve `MarketResearchAgent`'in kullandigi arayuz degismez.**

### 2.2 Kalici siniflar (`app/mcp/client.py`)

| Sinif | Rol |
|---|---|
| `MCPClient` | Agent'lara `constructor` uzerinden enjekte edilen paylasilan istemci. `call_tool(server, tool, arguments)` API'si. |
| `MCPServer` | Tek bir mantiksal sunucu (`rag`, `market`, `portfolio`, ...) icin tool kayit defteri. `register_tool`, `has_tool`, `call`. |
| `MCPClientError` | Tum MCP kaynakli hatalarin ata sinifi. |
| `MCPServerNotFoundError` | Bilinmeyen sunucu adi. |
| `MCPToolNotFoundError` | Sunucuda olmayan tool. |
| `MCPToolExecutionError` | Tool handler'in kendi hatasini sarar (`cause` alanindan orijinal exception erisilebilir). |

Bu siniflarin **API'si** kalicidir. Orchestrator ve tum agent'lar bu
arayuze karsi yazilmalidir.

### 2.3 Sunucu adlari ve tool sozlesmeleri (kalici)

```
server = "rag"       tool = "rag_search"
server = "market"    tool = "market_get_quote"
server = "market"    tool = "market_get_kap_disclosures"
server = "portfolio" tool = ...   # PortfolioAgent ekibi tanimlayacak
```

`RAG_SERVER_NAME` ve `MARKET_SERVER_NAME` sabitleri sunucu adlarini
merkezilestirir; agent'lar bunlari import eder.

### 2.4 Tool imzalari

**`rag.rag_search`** — `app/mcp/servers/rag.py`

```python
async def rag_search(
    query: str,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    # filters destekli anahtarlar: symbol, date_from (YYYY-MM-DD), date_to
    return {"query": query, "chunks": [...]}
```

Beklenen `chunks` elemani:
```python
{
    "chunk_id": str,
    "text": str,
    "source": str,          # orn. "Dunya Gazetesi", "KAP"
    "date": "YYYY-MM-DD",
    "metadata": {"symbol": "THYAO", "topic": "earnings"},
    "score": float,         # 0..1 arasi benzerlik skoru
}
```

**`market.market_get_quote`** — `app/mcp/servers/market.py`

```python
async def market_get_quote(symbol: str) -> dict[str, Any]:
    # Bulunamazsa: {"symbol": ..., "found": False}
    return {
        "symbol": "THYAO",
        "found": True,
        "timestamp": "ISO-8601",
        "price": 312.50,
        "currency": "TRY",
        "change_percent": 1.85,
    }
```

**`market.market_get_kap_disclosures`**

```python
async def market_get_kap_disclosures(
    symbol: str, since: str | None = None
) -> dict[str, Any]:
    return {
        "symbol": "THYAO",
        "disclosures": [
            {
                "disclosure_id": str,
                "title": str,
                "summary": str,
                "date": "YYYY-MM-DD",  # en yeniden eskiye sirali
            }
        ],
    }
```

**Onemli:** Tool **adlari, argument adlari ve donus sozlukleri** kalici
sozlesmedir. Gercek entegrasyon (LlamaIndex, KAP API) hazir oldugunda
sadece **govde** degisir, imza degismez.

### 2.5 Placeholder olanlar

| Yer | Placeholder mi? | Yerine ne gelecek |
|---|---|---|
| `servers/rag.py::_MOCK_CHUNKS` | Evet | LlamaIndex indeksi + embedding pipeline |
| `servers/rag.py::rag_search` govdesi | Evet (score'a gore siralayan filtre) | Gercek semantik arama |
| `servers/market.py::_MOCK_QUOTES` | Evet | Borsa API baglantisi |
| `servers/market.py::_MOCK_DISCLOSURES` | Evet | KAP API baglantisi |
| `mock.py::build_mock_mcp_client()` | Kismen | Dev/test icin kalir; production'da Orchestrator kendi wiring'ini yapacak |

---

## 3. Agent Katmani

### 3.1 `BaseAgent` ve `AgentResult` — kalici sozlesme

`app/agents/base.py`:

```python
class AgentResult(BaseModel):
    agent_name: str
    data: dict[str, Any]
    success: bool = True
    error: str | None = None

class BaseAgent(ABC):
    def __init__(self, name: str, mcp_client: MCPClient) -> None: ...

    @abstractmethod
    async def run(self, task: dict[str, Any]) -> AgentResult: ...
```

Prensipler:
- **Dependency Injection:** Her agent kendi `MCPClient`'ini olusturmaz;
  Orchestrator tek bir `MCPClient` olusturur ve tum agent'lara enjekte eder.
- **Bagimsizlik:** Her agent, ayni istekte calisan diger agent'larin
  durumunu/ciktisini varsaymaz. Router bu agent'i cagirmayabilir ya da tek
  basina cagirabilir.
- **`security_gate` icin:** `success`/`error` alanlari, senteze gecmeden
  onceki guvenlik/uygunluk kapisinin sonucu isleme alip almayacagina karar
  vermesi icindir.

### 3.2 `MarketResearchAgent` — mimarideki yeri

`app/agents/market_research.py`:

- **MCP Server 1 (RAG)** ve **MCP Server 3 (Borsa & KAP)** ile **birlikte**
  calisan **tek agent**tir.
- **MCP Server 2 (Portfoy DB)'ye asla erismez** — o sunucu
  `PortfolioAgent`'in sorumlulugundadir.

### 3.3 Task sozlesmesi (provisional)

Router/Orchestrator henuz repoda olmadigi icin sabitlenmis bir sema yok.
Agent, router'in su sekilde bir sozluk gondermesini varsayar:

```python
task = {
    "query": str,                        # zorunlu
    "mode": "rag" | "live" | "both",     # opsiyonel; yoksa sorgudan cikarilir
    "symbol": str | None,                # orn. "THYAO"
    "date_from": str | None,             # "YYYY-MM-DD", RAG filtresi
    "date_to": str | None,               # "YYYY-MM-DD", RAG filtresi
    "top_k": int | None,                 # RAG icin chunk sayisi
    "include_disclosures": bool | None,  # live modda KAP bildirimi de ekle
    "since": str | None,                 # KAP filtresi (YYYY-MM-DD)
}
```

Router farkli bir alan adi/sekli kullanirsa `market_research.py`
guncellenmelidir.

### 3.4 `run(task)` akisi

1. **Dogrulama** — `task["query"]` bos ise `AgentResult(success=False)` doner.
2. **Mode cozumu** — `_resolve_mode`: explicit `mode` verilmisse kullanir;
   aksi halde Turkce anahtar kelime sezgisiyle karar verir
   (`_LIVE_KEYWORDS` = "fiyat", "kac para", "guncel", "canli", "kap bildir";
   `_CONTEXT_KEYWORDS` = "neden", "sebep", "nicin", "haber", "rapor",
   "analiz"). `symbol` varsa canli veri gerekebilir.
3. **RAG kolu (`_run_rag`)** —
   - `filters` sozlugunu (`symbol`, `date_from`, `date_to`) kurar.
   - `mcp.call_tool("rag", "rag_search", ...)` cagirir.
   - Chunk yoksa `NO_RETRIEVAL_MESSAGE` (indekslenmis icerik yok) doner,
     `confidence = 0`.
   - Chunk varsa `_build_rag_prompt` ile **groundedness prompt**'u kurar
     (LLM'e "sadece bu kaynaklardaki bilgiyi kullan, uydurma" der) ve
     `LLMClient.generate` cagrir. `confidence`, chunk skorlarinin
     ortalamasi olarak dondurulur.
4. **Live kolu (`_run_live`)** —
   - `symbol` zorunlu; yoksa uyari mesajiyla erken doner.
   - `market.market_get_quote` cagrir.
   - `include_disclosures = True` ise `market.market_get_kap_disclosures`
     de cagrilir ve en yeni bildirim ozete eklenir.
5. **Sonuc zarfi:**

```python
AgentResult(
    agent_name="market_research",
    data={
        "summary": str,               # Turkce, kisa yanit
        "sources": [                  # RAG kaynaklari
            {"source": str, "excerpt": str, "date": str}
        ],
        "live_data": {                # varsa
            "symbol": str, "price": float, "timestamp": str
        } | None,
        "confidence": float | None,   # RAG icin ortalama score
    },
    success=True,
)
```

- Herhangi bir `MCPClientError` yakalanirsa `success=False`, `error=str(exc)`
  ile donulur; agent icinde traceback sizmaz.

### 3.5 Placeholder vs. kalici — `MarketResearchAgent`

| Parca | Durum |
|---|---|
| Sinif adi ve konumu | Kalici |
| `run(task) -> AgentResult` sozlesmesi | Kalici |
| `data` sozlugunun anahtarlari (`summary`, `sources`, `live_data`, `confidence`) | Kalici |
| MCP tool cagrilari (isim ve argumanlar) | Kalici |
| `_resolve_mode` anahtar kelime sezgisi | **Placeholder** — router explicit `mode` gonderdiginde gereksizlesir |
| `task` sema dokumantasyonu | **Provisional** — router sozlesmesi netlesince guncellenir |
| `_build_rag_prompt` metni | Ayarlanabilir; sozlesme degil |

---

## 4. LLM Katmani (`app/core/llm.py`)

```python
class LLMClient(Protocol):
    async def generate(self, prompt: str, *, model: str | None = None) -> str: ...

class GeminiLLMClient:
    # google-genai SDK uzerinden Gemini'ye baglanan ince sarmalayici
    ...

def get_llm_client(agent: str) -> LLMClient:
    # settings.model_for(agent) ile agent'a ozel model adi secilir
    ...
```

- Agent'lar dogrudan `GeminiLLMClient`'a **bagli degildir**; `LLMClient`
  protokoluyle konusur. Bu sayede testlerde gercek API cagrisi yapilmadan
  sahte bir `generate()` enjekte edilebilir (bkz. `test_market_research_agent.py`).
- Saglayici olarak Google Gemini (`gemini-2.5-flash` varsayilan) secildi.
  `.env` icinde `LLM_API_KEY` gerekir.
- **`LLMClient` protokolu kalici**; saglayici degistirilebilir (baska bir
  `LLMClient` implementasyonu yazilir, `get_llm_client` guncellenir).

---

## 5. Backend Ekibi Icin Entegrasyon Noktalari

Orchestrator / router yazilirken:

1. Uygulama basladiginda **tek bir `MCPClient`** olustur.
2. Gercek `MCPServer`'lari (rag, market, portfolio) `register_server`
   ile bagla. Mock kullaniliyorsa `build_mock_mcp_client()` cagrilabilir.
3. Her istek icin router, hangi agent'larin kosacagina karar verir ve her
   birine kendi `task` sozlugunu gonderir. Ayni `MCPClient` instance'i tum
   agent'lara enjekte edilir.
4. Agent'lardan gelen `AgentResult`'lar `security_gate` -> sentez adimina
   verilir. `success=False` olanlar sentez asamasi tarafindan filtrelenir.
5. `MarketResearchAgent` icin task uretirken §3.3'teki sema kullanilmali;
   farkli bir sema secilirse agent guncellenmelidir.

---

## 6. DB / Veri Ekibi Icin Entegrasyon Noktalari

### 6.1 MCP Server 1 — LlamaIndex RAG

Yerine gececek dosya: `app/mcp/servers/rag.py`.

Yapilacak: `rag_search` **govdesini** gercek LlamaIndex indeksine baglamak.

Uymasi gereken sozlesme:
- Argumanlar: `query: str`, `top_k: int = 5`, `filters: dict | None`.
- `filters` desteklenen anahtarlar: `symbol` (buyuk harfe cevrilir),
  `date_from`, `date_to` (`YYYY-MM-DD`).
- Donus: `{"query": query, "chunks": [ ... ]}` (§2.4'teki chunk sekliyle).
- `score` alani 0..1 arasi olmali; agent bunun ortalamasindan `confidence`
  uretir.

### 6.2 MCP Server 3 — Borsa & KAP

Yerine gececek dosya: `app/mcp/servers/market.py`.

Yapilacak: `market_get_quote` ve `market_get_kap_disclosures` govdelerini
gercek Borsa/KAP kaynaklarina baglamak.

Uymasi gereken sozlesme:
- `market_get_quote`: sembol bulunmazsa `{"symbol": ..., "found": False}`;
  bulunursa §2.4'teki tam sozluk. `timestamp` ISO-8601 UTC.
- `market_get_kap_disclosures`: `since` verilmisse `date >= since` filtresi.
  `disclosures` **en yeniden eskiye** sirali olmali (agent `[0]`'i "son
  bildirim" olarak kullanir).

### 6.3 MCP Server 2 — Portfoy DB (bu klasorde yer almaz)

Postgres semasi ve tool sozlesmesi `PortfolioAgent` ekibiyle birlikte
tanimlanacaktir. Adlandirma icin oneri: `server="portfolio"`; tool adlari
`portfolio_get_positions`, `portfolio_get_transactions`, vb. Kesin sozlesme
`PortfolioAgent` PR'inda netlesecek.

---

## 7. Testler

- `backend/tests/test_mcp_client.py` — `MCPClient`/`MCPServer` kayit,
  cagri ve hata yollari.
- `backend/tests/test_market_research_agent.py` — `MarketResearchAgent`'in
  RAG / live / both modlari, sahte bir `LLMClient` enjekte edilerek.

Gercek entegrasyon PR'lari **bu testleri kirmadan** gecirilmelidir; kirilirsa
sozlesme degismis demektir ve agent tarafi da guncellenmelidir.

---

## 8. Ozet Tablo: Placeholder vs. Kalici

| Bilesen | Durum |
|---|---|
| `MCPClient`, `MCPServer`, hata siniflari | **Kalici (API)** |
| Sunucu adlari (`rag`, `market`, `portfolio`) | **Kalici** |
| Tool adlari ve imzalari (`rag_search`, `market_get_quote`, `market_get_kap_disclosures`) | **Kalici** |
| Chunk / quote / disclosure sozluklerinin sekli | **Kalici** |
| `BaseAgent`, `AgentResult` | **Kalici** |
| `MarketResearchAgent.run` ve `data` sekli | **Kalici** |
| `LLMClient` Protocol | **Kalici** |
| `GeminiLLMClient` | Kalici (saglayici degisebilir) |
| `_MOCK_CHUNKS`, `_MOCK_QUOTES`, `_MOCK_DISCLOSURES` | **Placeholder** |
| `rag_search` / `market_*` **govdeleri** | **Placeholder** |
| `_resolve_mode` anahtar kelime sezgisi | **Placeholder** (router explicit `mode` verecek) |
| `task` sema dokumantasyonu | **Provisional** |
| `build_mock_mcp_client()` | Dev/test icin kalir, prod wiring'i degildir |
