# RAG Agent ve MCP Katmani — Backend & DB Ekipleri Icin Ozet

> **2026-08-20 guncellemesi:** Bu dosya ilk yazildiginda (RAG-Agent dalinin
> iskelet asamasinda) `mcp/mock.py` ve `mcp/servers/{rag,market}.py` gibi
> **mock** dosyalar tarif ediyordu. Bu dosyalar artik REPODA YOK - gercek
> `mcp/server.py` (tek modul, TOOL_GROUPS kayit defteri) onlarin yerini aldi.
> Asagidaki icerik GUNCEL koda gore yeniden yazildi; "kalici sozlesme" olarak
> isaretlenen kisimlar hala gecerli, "placeholder" olanlar ise artik farkli
> sekilde placeholder (bkz. §8).

Bu rapor, backend'in RAG/MCP katmaninin **bugunku** halini anlatir:
`MarketResearchAgent`, paylasilan `MCPClient`/`MCPServer` yapisi, gercek
`mcp/server.py` tool kayit defteri, `SqlRagRepository`/`InMemoryRagRepository`
ve LLM istemci katmani.

---

## 1. Klasor Haritasi (guncel)

```
backend/app/
  agents/
    base.py              # BaseAgent + AgentError (sozlesme)
    market_research.py   # MarketResearchAgent (RAG + canli veri)
    portfolio.py          # PortfolioAgent
    risk_strategy.py      # RiskStrategyAgent
    security_agent.py     # Guvenlik ajani (Kapi 1 + Kapi 2)
  core/
    llm.py               # LLMClient protokolu + GeminiLLMClient
  ingestion/
    chunking.py           # semantic_split -> chunk_document
    embeddings.py          # Embedder protokolu + CohereEmbedder + get_embedder()
    backfill.py            # rag.documents -> rag.chunks (+embedding) toplu isleme
  mcp/
    client.py             # MCPClient, MCPServer, hata hiyerarsisi (sozlesme)
    context.py             # user_id contextvar (require_user_id)
    server.py               # TEK gercek MCP sunucusu - TUM tool'lar burada kayitli
    servers/                # BOS (yalnizca __pycache__) - eski mock modul artiklari,
                             # silinmesi guvenli, hicbir yerden import edilmiyor
  repositories/
    base.py                 # Protocol'ler (UserRepository, ..., RagRepository, ...)
    sql.py                   # PostgreSQL implementasyonlari - BIRINCIL
    in_memory.py              # Bellek ici implementasyonlar - YEDEK
    deps.py                    # Hangi implementasyon secilecek (TEK yer)
  engine/
    orchestrator.py            # LangGraph StateGraph, router, sentez, SSE
  tests/
    test_mcp_client.py
    test_mcp_server.py
    test_market_research_agent.py
    test_market_research_orchestration.py
    test_hybrid_search.py       # SqlRagRepository.hybrid_search() (2026-08-20)
    test_sql_repositories.py
```

`Orchestrator`, `PortfolioAgent`, `RiskStrategyAgent`, gercek DB baglantisi,
gercek embedding pipeline'i - bu raporun ilk halinde "baska ekipler yazacak"
diye not edilen her sey artik yazildi. Hala eksik/acik olanlar §8 ve
`docs/gelecek-isler.md`'de listelidir.

---

## 2. MCP Katmani

### 2.1 Gercek MCP protokolu mu?

Hayir - `client.py` docstring'inde belirtildigi gibi hicbir MCP sunucusu ayri
bir surecte calismiyor. `MCPClient`/`MCPServer` gercek MCP protokolunun
(JSON-RPC / stdio / SSE) transport'unu **implemente etmez**; agent'larin
bagimli oldugu **cagri sozlesmesini** saglayan **in-process bir
yonlendirme/registry katmanidir**:

```python
await mcp_client.call_tool(server="rag", tool="rag_search", arguments={...})
```

Bu tasarim kararinda degisiklik yok; ilk yazildigindan beri ayni.

### 2.2 Kalici siniflar (`app/mcp/client.py`)

| Sinif | Rol |
|---|---|
| `MCPClient` | Agent'lara constructor uzerinden enjekte edilen paylasilan istemci. `call_tool(server, tool, arguments)` API'si. |
| `MCPServer` | Tek bir mantiksal sunucu (`core`, `rag`, `market`) icin tool kayit defteri. `register_tool`, `has_tool`, `call`. |
| `MCPClientError` | Tum MCP kaynakli hatalarin ata sinifi. |
| `MCPServerNotFoundError` | Bilinmeyen sunucu adi. |
| `MCPToolNotFoundError` | Sunucuda olmayan tool. |
| `MCPToolExecutionError` | Tool handler'in kendi hatasini sarar (`cause` alanindan orijinal exception erisilebilir). Onemli: handler icinde SQL/embedding gibi bir cagri patlarsa da bu hataya sarilir - bkz. §4.3. |

### 2.3 Sunucu adlari ve tool sozlesmeleri (kalici) — `app/mcp/server.py`

```
server = "core"      tool = "user_get_profile"
server = "core"      tool = "portfolio_get_summary" | "portfolio_get_holdings"
                              | "portfolio_get_allocation" | "portfolio_get_transactions"
server = "market"    tool = "market_get_quote" | "market_get_history"
                              | "market_get_kap_disclosures"
server = "rag"       tool = "rag_search"
```

`CORE_SERVER_NAME`, `RAG_SERVER_NAME`, `MARKET_SERVER_NAME` sabitleri sunucu
adlarini merkezilestirir; ajanlar bunlari import eder. Tum tool'lar `TOOL_GROUPS`
sozlugunde tek yerde kayitlidir; `build_servers()` bunu `MCPServer` nesnelerine
cevirir. Yeni tool eklemek icin `TOOL_GROUPS`'a bir satir eklemek yeterlidir.

### 2.4 `rag_search` tool imzasi (guncel)

```python
async def rag_search(
    query: str,
    top_k: int = 5,
    sirket: str | None = None,
    tip: str | None = None,
    date_from: str | None = None,   # "YYYY-MM-DD" - 2026-08-20'de eklendi
    date_to: str | None = None,     # "YYYY-MM-DD" - 2026-08-20'de eklendi
    filters: dict[str, Any] | None = None,  # geriye donuk uyum
) -> dict[str, Any]:
    ...
    return {"query": query, "chunks": [...]}
```

`filters` sozlugu `{"sirket"|"symbol", "tip", "date_from", "date_to"}`
kabul eder - `MarketResearchAgent._run_rag` bu yolu kullanir. **Onemli
gecmis bug (2026-08-20'de bulunup duzeltildi):** `date_from`/`date_to`
onceden hem dogrudan parametre hem `filters` icinde SESSIZCE DUSUYORDU;
artik ikisi de `SqlRagRepository`'ye kadar dogru tasinir.

Donen `chunks` elemani (degismedi):
```python
{
    "chunk_id": str, "doc_id": str, "baslik": str, "sirket": str | None,
    "symbol": str | None, "tarih": str, "tip": str, "content": str,
    "score": float,
    # eski adlar (MarketResearchAgent geriye donuk uyum icin):
    "title": str, "text": str, "source": str, "date": str, "metadata": dict,
}
```

**`market.market_get_quote`** ve **`market.market_get_kap_disclosures`** —
imzalar degismedi; govdeleri artik `SqlMarketRepository`/`SqlRagRepository`'ye
baglaniyor (bkz. §2.5). `market_get_kap_disclosures` hala `rag.search()`'u
(BM25) cagiriyor, `.hybrid_search()`'u DEGIL - bilincli, dokunulmadi (KAP
bildirimleri tarihe gore siralanir, alaka skoruna gore degil).

### 2.5 Govdeler artik GERCEK, placeholder DEGIL

| Yer | Eski durum (ilk yazim) | Bugunku durum |
|---|---|---|
| RAG arama govdesi | `_MOCK_CHUNKS` (mock.py) | `SqlRagRepository.search()`/`.hybrid_search()` - gercek Postgres BM25 + (varsa) Cohere embedding + `rag.hybrid_search()` SQL fonksiyonu (RRF) |
| Borsa fiyati govdesi | `_MOCK_QUOTES` | `SqlMarketRepository.get_quote()` - Yahoo Finance (`ApiMarketProvider`) + simulator hibrit (mimari v4 §8) |
| KAP bildirimi govdesi | `_MOCK_DISCLOSURES` | `rag.documents` icindeki `tip='duyuru'` satirlari (ayri bir KAP entegrasyonu YOK, bilincli tasarim) |
| DB baglantisi yoksa | (yoktu) | `InMemoryRagRepository`/`InMemoryMarketRepository` - `repositories/deps.py::_veritabani_calisiyor()` baglanti kurulamazsa otomatik devreye girer, `/health` `data_source: in-memory` doner |

---

## 3. RAG Arama — iki yol, tek sozlesme

`SqlRagRepository` (`app/repositories/sql.py`) iki metot sunar; `rag_search`
MCP tool'u **`hybrid_search()`** cagirir, `search()` degil:

```python
async def search(query, top_k=5, sirket=None, tip=None,
                  date_from=None, date_to=None) -> list[dict]:
    """Yalnizca BM25 (content_tsv full-text). Embedding GEREKTIRMEZ."""

async def hybrid_search(query, top_k=5, sirket=None, tip=None,
                         date_from=None, date_to=None) -> list[dict]:
    """Dense (Cohere embed-v4) + BM25 -> RRF (rag.hybrid_search SQL fonksiyonu).
    `search()`'un YERINE GECMEZ, UZERINE KURULUR:
      - embedder enjekte edilmediyse (EMBEDDING_API_KEY/EMBEDDING_MODEL yok)
        -> DOGRUDAN search()'e duser.
      - sorgu-zamani embedding cagrisi basarisiz/zaman asimina ugrarsa
        (RAG_QUERY_EMBEDDING_TIMEOUT_SECONDS, varsayilan 3sn)
        -> search()'e duser, istek COKMEZ.
      - embedding basariliysa rag.hybrid_search() SQL fonksiyonu cagrilir.
    Donus sekli search() ile BIREBIR ayni - cagiran taraf (mcp/server.py::
    _chunk_payload) ikisini ayirt etmez.
    """
```

`repositories/deps.py::get_rag_repository()` DB bagliysa `SqlRagRepository`'yi
`app.ingestion.embeddings.get_embedder()` ile kurar (embedder `None` donerse
sorun degil - yukaridaki ilk fallback devreye girer).

**Kritik istisna:** yukaridaki fallback zinciri yalnizca EMBEDDING adimini
kapsar. `rag.hybrid_search()` SQL fonksiyon cagrisinin kendisi patlarsa
(orn. Supabase'de fonksiyon henuz guncellenmediyse - bkz. `gelecek-isler.md`
madde 3) bu hata YAKALANMAZ, `MCPToolExecutionError` olarak yukari cikar ve
`BaseAgent.run()` bunu `AgentError(error_type="tool_error")`'a cevirir -
yani o turde `market_research` ajaninin RAG bacagi tamamen basarisiz olur
(kismi basarisizlik, sohbet cokmez, ama veri de gelmez).

---

## 4. Agent Katmani

### 4.1 `BaseAgent` — kalici sozlesme (degismedi)

`app/agents/base.py`:

```python
class BaseAgent(ABC):
    name: str
    def __init__(self, mcp_client, llm, timeout_seconds: int) -> None: ...
    @abstractmethod
    async def _execute(self, state: AgentState) -> dict: ...
    async def run(self, state: AgentState) -> dict:
        """Timeout/hata yonetimi MERKEZI - alt siniflar yalnizca _execute yazar."""
    async def call_tool(self, server: str, tool: str, arguments: dict) -> dict: ...
    def is_requested(self, state: AgentState) -> bool: ...
```

İlk yazımdaki `AgentResult` modeli artık kullanılmıyor; ajanlar
`AgentState`'in DEĞİŞEN alanlarını doğrudan dict olarak döner (bkz.
`orchestration/models.py`, mimari v4 §5.3-5.4). Prensipler aynı: dependency
injection, ajan bağımsızlığı, `run()`'ın timeout/hata yakalamayı merkezileştirmesi.

### 4.2 `MarketResearchAgent` — degismeyen kisimlar

- MCP Server "rag" ve "market" ile birlikte calisan tek ajandir.
- Portfoy sunucusuna ("core") ASLA erismez (NFR-04).
- `_resolve_mode` (rag/live/both), `_extract_symbol`, RAG/canli veri
  ayristirmasi - hepsi ilk yazimdaki gibi calisiyor, degismedi.
- `task` semasi (`query`, `mode`, `symbol`, `date_from`, `date_to`, `top_k`,
  `include_disclosures`, `since`) hala PROVISIONAL - router hala yapilandirilmis
  parametre uretmiyor (bkz. `docs/gelecek-isler.md` madde 1).

### 4.3 Guvenlik notu (degismedi)

RAG'den donen metin dis kaynaklidir; `security_gate` node'u sentezden once
ham `market_data`'yi tarar (bkz. mimari v4 §11).

---

## 5. LLM Katmani (`app/core/llm.py`) — degismedi

```python
class LLMClient(Protocol):
    async def generate(self, prompt: str, *, model: str | None = None) -> str: ...

class GeminiLLMClient: ...
def get_llm_client(agent: str) -> LLMClient: ...
```

LLM modeli hala secilmedi (`docs/backend-kararlar.md` §11) - ajanlar
LLM'siz de calisir, deterministik alinti/ozet uretirler.

---

## 6. Backend Ekibi Icin Entegrasyon Noktalari — GUNCEL DURUM

Ilk yazimda "Orchestrator/router yazilirken yapilacaklar" listesiydi; hepsi
artik yazildi:

1. ✅ Tek `MCPClient`, uygulama basinda kuruluyor (`app/engine/factory.py`).
2. ✅ Gercek `MCPServer`'lar (`build_servers()`) `register_server` ile baglaniyor.
3. ✅ Router (`Orchestrator.route_intent`) her istekte hangi ajanlarin
   calisacagina karar veriyor - kural tabanli (LLM'siz), Turkce anahtar
   kelime eslesmesiyle.
4. ✅ `AgentError`'lar `security_gate` -> sentez adimina isleniyor.
5. `MarketResearchAgent` icin task uretimi hala §4.2'deki gibi provisional -
   router yapilandirilmis parametre urettiginde ajan guncellenecek.

---

## 7. DB / Veri Ekibi Icin Entegrasyon Noktalari — GUNCEL DURUM

### 7.1 RAG ingestion pipeline'i — YAZILDI (`app/ingestion/`)

`chunking.py` + `embeddings.py` (Cohere `embed-v4.0`) + `backfill.py` gercek
bir pipeline'dir, mock degil. Supabase'de 234 doküman/917 chunk, yerel
Docker DB'de 8 seed doküman/14 chunk gercek embedding tasiyor (bkz. embedding
pipeline oturum notlari, 2026-08-19/20).

Uymasi gereken sozlesme (degismedi):
- `rag_search` argumanlari: `query`, `top_k`, `sirket`/`filters.symbol`,
  `tip`, `date_from`, `date_to`.
- `filtered` CTE'de `sirket` eslesmesi asla `rag.documents.sirket`'e bakmaz
  (o kolon haberin KAYNAGI - "AA Ekonomi" gibi - haberin KONUSU degil);
  yalnizca `assets.symbol`/`assets.name` join'i ve `baslik ILIKE` fallback'i
  kullanilir. Bu kural hem `search()`'te hem `rag.hybrid_search()`'te aynidir.

### 7.2 Borsa & KAP — YAZILDI

`market_get_quote`/`market_get_history` gercek Yahoo Finance verisine
baglandi (`ApiMarketProvider` + simulator hibrit, mimari v4 §8). KAP icin
ayri bir entegrasyon yok, bilincli tasarim: `rag.documents.tip='duyuru'`
satirlari kullaniliyor.

### 7.3 Portfoy DB — YAZILDI

`SqlPortfolioRepository` (`app/repositories/sql.py`), `PortfolioAgent`
tarafindan kullaniliyor. Tool adlari: `portfolio_get_summary`,
`portfolio_get_holdings`, `portfolio_get_allocation`, `portfolio_get_transactions`.

---

## 8. Testler

- `test_mcp_client.py` — `MCPClient`/`MCPServer` kayit, cagri, hata yollari.
- `test_mcp_server.py` — tum tool kataloğu, ortak zarf, `rag_search`'un
  `date_from`/`date_to` dahil parametre kabulu (`@pytest.mark.db`).
- `test_market_research_agent.py`, `test_market_research_orchestration.py` —
  RAG/live/both modlari, sahte `LLMClient` (`@pytest.mark.db`).
- `test_hybrid_search.py` (2026-08-20) — `SqlRagRepository.hybrid_search()`:
  embeddersiz/hata/timeout durumunda BM25'e dusme, dense ayagin GERCEKTEN
  calistigi (sahte ama gercek bir chunk'in embedding'iyle esleme), sirket/tip/
  tarih filtreleri (`@pytest.mark.db`).
- `test_sql_repositories.py` — SQL repository'lerin bellek ici ile AYNI
  sozlesmeyi urettigini sinar.

`@pytest.mark.db` testleri gercek bir Postgres ister (`TEST_DATABASE_URL`).
`tests/conftest.py`'deki `_veritabani` fixture'i bu testler icin
`embedding_api_key`'i BILEREK bosaltir - aksi halde `rag_search`'u dolayli
cagiran her `db` testi gercek bir Cohere API cagrisi yapardi. Dense yolu
kasitli sinayan tek yer `test_hybrid_search.py`'dir (sahte embedder enjekte
eder, `get_embedder()`'i hic cagirmaz).

---

## 9. Ozet Tablo: Placeholder vs. Kalici (2026-08-20 itibarıyla)

| Bilesen | Durum |
|---|---|
| `MCPClient`, `MCPServer`, hata siniflari | **Kalici (API)** — degismedi |
| Sunucu adlari (`core`, `rag`, `market`) | **Kalici** — `portfolio` yerine `core` kullanildi (PortfolioAgent §7.3'te) |
| Tool adlari ve imzalari | **Kalici** — `rag_search`'e `date_from`/`date_to` eklendi (uyumlu genisleme) |
| `BaseAgent`, `AgentError` (`AgentResult` degil) | **Kalici** — model adı degisti, sozlesme prensibi ayni |
| `MarketResearchAgent.run`/`_execute` ve `market_data` sekli | **Kalici** |
| `LLMClient` Protocol, `GeminiLLMClient` | **Kalici** |
| RAG/Borsa/KAP govdeleri | ✅ **ARTIK GERCEK** — mock degil (bkz. §2.5) |
| `mcp/mock.py`, `mcp/servers/*.py` | **REPODA YOK** — bu dosya artik onlari tarif etmiyor |
| `SqlRagRepository.search()` (BM25) | **Kalici, bagimsiz sozlesme** — `hybrid_search()`'un fallback hedefi |
| `SqlRagRepository.hybrid_search()` | ✅ **YAZILDI** (2026-08-20) — Supabase'de fonksiyon guncellenene kadar oradaki DB'ye karsi hata verir (bkz. §3, `gelecek-isler.md`) |
| `MarketResearchAgent._resolve_mode`, `task` semasi | Hala **Placeholder/Provisional** — router yapilandirilmis parametre uretmiyor |
| `InMemoryRagRepository`/`InMemoryMarketRepository` | **Kalici YEDEK** — DB tanimli/erisilebilir degilse otomatik devreye girer |
