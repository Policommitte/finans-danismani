# SYSTEM ARCHITECTURE v3
## Akıllı Kişisel Finans Danışmanı


---

# 0 · SİSTEM HARİTASI

```mermaid
flowchart TB
    subgraph FE["🖥️ FRONTEND — React + Vite"]
        F1["Login"]
        F2["Chat"]
        F3["Dashboard<br/>Portföy · Piyasa · Risk"]
    end

    subgraph API["🌐 API KATMANI — FastAPI"]
        A1["REST<br/>/api/portfolio · /api/market"]
        A2["SSE<br/>/api/chat/stream"]
        A3["Auth<br/>JWT"]
    end

    subgraph ORC["🧠 ORCHESTRATOR — LangGraph"]
        O1["Güvenlik Girdi"]
        O2["Router"]
        O3["Ajanlar"]
        O4["Güvenlik Çıktı"]
        O5["Synthesizer"]
    end

    subgraph AG["🤖 AJANLAR"]
        G1["Portföy"]
        G2["Piyasa + RAG"]
        G3["Risk / Strateji"]
    end

    subgraph MCP["🔌 MCP SUNUCUSU"]
        M1["portfolio_*"]
        M2["market_*"]
        M3["rag_*"]
        M4["user_*"]
    end

    subgraph BG["⚙️ ARKA PLAN"]
        B1["Fiyat Simülatörü"]
        B2["RAG Ingestion"]
    end

    subgraph DB["🗄️ POSTGRESQL + PGVECTOR"]
        D1["Operasyonel<br/>users · portfolios · assets"]
        D2["Zaman serisi<br/>price_history"]
        D3["Vektör<br/>rag.chunks"]
        D4["Denetim<br/>tool_calls · security_events"]
    end

    FE --> API
    API --> ORC
    ORC --> AG
    AG --> MCP
    MCP --> DB
    BG --> DB

    style FE fill:#e3f2fd
    style API fill:#e8f5e9
    style ORC fill:#fff3e0
    style AG fill:#f3e5f5
    style MCP fill:#fce4ec
    style BG fill:#eceff1
    style DB fill:#e0f2f1
```

---

# 1 · KATMAN SORUMLULUKLARI

| Katman | Yapar | ASLA Yapmaz |
|---|---|---|
| **Frontend** | Görüntüler, kullanıcı girdisi alır, SSE tüketir | LLM'e doğrudan gitmez, hesap yapmaz |
| **API** | HTTP, JWT, oturum, kalıcılık | Ajan mantığı barındırmaz |
| **Orchestrator** | Karar verir, ajanları koordine eder, sentezler | DB'ye dokunmaz |
| **Ajanlar** | Kendi alanında analiz üretir | Birbirini çağırmaz, DB'ye dokunmaz |
| **MCP** | Veri ve domain servislerini dışa açar | İş mantığı barındırmaz |
| **Arka plan** | Fiyat üretir, doküman gömer | İstek akışına karışmaz |
| **DB** | Tek gerçek kaynağı, hesap view'ları | — |

---

# 2 · UÇTAN UCA AKIŞ

```mermaid
sequenceDiagram
    autonumber
    participant K as Kullanıcı
    participant F as Frontend
    participant A as FastAPI
    participant O as Orchestrator
    participant AJ as Ajanlar
    participant M as MCP
    participant D as PostgreSQL

    K->>F: "Portföyüm nasıl gidiyor?"
    F->>A: POST /api/chat/stream + JWT
    A->>A: Token doğrula → user_id
    A->>O: stream_request()

    O->>O: 🛡️ Güvenlik girdi kontrolü
    O-->>F: status: "Sorgu kontrol ediliyor"

    O->>O: 🧭 Router → hangi ajanlar?
    O-->>F: status: "Sorgu analiz ediliyor"

    par Paralel
        O->>AJ: Portföy Ajanı
        AJ->>M: portfolio_get_summary
        M->>D: v_portfolio_summary
        D-->>M: veri
        M-->>AJ: sonuç
    and
        O->>AJ: Piyasa Ajanı
        AJ->>M: rag_search
        M->>D: rag.hybrid_search
        D-->>M: chunk + kaynak
        M-->>AJ: sonuç
    end

    O->>AJ: Risk Ajanı (sıralı)
    Note over AJ: Portföy + piyasa verisi<br/>dolu geldi
    AJ-->>O: risk skoru

    O->>O: 🛡️ Güvenlik çıktı kontrolü
    O-->>F: sources
    loop Token akışı
        O-->>F: token
        F-->>K: metin akıyor
    end
    O-->>F: done
    O->>D: mesajı kaydet
```

---

# 3 · FRONTEND MİMARİSİ

## 3.1 Teknoloji

| Alan | Seçim |
|---|---|
| Framework | React 18 + TypeScript |
| Stil | Tailwind CSS + shadcn/ui |
| Sunucu durumu | TanStack Query |
| İstemci durumu | Zustand (chat akışı) |
| Grafik | Recharts |
| Yönlendirme | React Router |
| Form | React Hook Form + Zod |

## 3.2 Sayfa Haritası

```mermaid
flowchart LR
    L["/login"] -->|"JWT alındı"| C["/chat"]
    L --> D["/dashboard"]
    C <--> D
    D --> T1["Sekme: Portföy"]
    D --> T2["Sekme: Piyasa"]
    D --> T3["Sekme: Risk"]

    style L fill:#ffe0b2
    style C fill:#c8e6c9
    style D fill:#bbdefb
```

Piyasa ve Risk **ayrı sayfa değil, sekme**.

## 3.3 Bileşen Ağacı

```mermaid
flowchart TD
    APP["App"] --> AUTH["AuthProvider"]
    AUTH --> RT["Router"]
    RT --> LP["LoginPage"]
    RT --> SH["AppShell"]

    SH --> NAV["Sidebar + Topbar"]
    SH --> CP["ChatPage"]
    SH --> DP["DashboardPage"]

    CP --> CL["ConversationList"]
    CP --> MSG["MessageList"]
    CP --> INP["ChatInput"]
    MSG --> BUB["MessageBubble"]
    MSG --> STA["StatusIndicator"]
    MSG --> SRC["SourceCard"]

    DP --> SUM["SummaryCards"]
    DP --> PIE["AllocationPie"]
    DP --> TBL["HoldingsTable"]
    DP --> LNE["PriceChart"]
    DP --> RSK["RiskPanel"]

    style CP fill:#c8e6c9
    style DP fill:#bbdefb
```

## 3.4 Veri Akışı — Hangi Bileşen Nereden Beslenir

```mermaid
flowchart LR
    subgraph Q["TanStack Query — REST"]
        Q1["usePortfolioSummary"]
        Q2["useHoldings"]
        Q3["useAllocation"]
        Q4["useMarketHistory"]
        Q5["useConversations"]
    end
    subgraph Z["Zustand — SSE"]
        Z1["messages[]"]
        Z2["streamingText"]
        Z3["status"]
        Z4["sources[]"]
    end

    Q1 --> SUM["SummaryCards"]
    Q2 --> TBL["HoldingsTable"]
    Q3 --> PIE["AllocationPie"]
    Q4 --> LNE["PriceChart"]
    Q5 --> CL["ConversationList"]

    Z1 --> MSG["MessageList"]
    Z2 --> MSG
    Z3 --> STA["StatusIndicator"]
    Z4 --> SRC["SourceCard"]

    style Q fill:#e8f5e9
    style Z fill:#fff3e0
```

## 3.5 SSE Tüketim Durum Makinesi

```mermaid
stateDiagram-v2
    [*] --> Bosta
    Bosta --> Gonderiliyor: kullanıcı mesaj yazdı
    Gonderiliyor --> Baglandi: meta olayı
    Baglandi --> Calisiyor: status olayı
    Calisiyor --> Calisiyor: status güncellendi
    Calisiyor --> Kaynaklar: sources olayı
    Kaynaklar --> Akiyor: ilk token
    Akiyor --> Akiyor: token
    Akiyor --> Bitti: done olayı
    Calisiyor --> Hata: error olayı
    Baglandi --> Hata: bağlantı koptu
    Bitti --> Bosta
    Hata --> Bosta
```

## 3.6 ⚠️ Kritik Teknik Not

```mermaid
flowchart TD
    A["Native EventSource"] --> B{"POST + Authorization<br/>header destekliyor mu?"}
    B -->|"HAYIR"| C["❌ Kullanılamaz"]
    C --> D["✅ fetch + ReadableStream<br/>veya @microsoft/fetch-event-source"]
    style C fill:#ffcdd2
    style D fill:#c8e6c9
```

Chat ucu POST + JWT header gerektiriyor; tarayıcının yerleşik `EventSource`
yalnızca GET destekler ve header gönderemez.

## 3.7 Klasör Yapısı

```
web/src/
├── app/            router, providers, layout
├── pages/          login · chat · dashboard
├── features/
│   ├── auth/       useAuth, AuthProvider, token
│   ├── chat/       useChatStream, chatStore, bileşenler
│   ├── portfolio/  query hook'ları, tablo, pasta
│   └── market/     fiyat grafiği, varlık listesi
├── components/ui/  shadcn primitifleri
├── lib/            apiClient, sseClient, formatters
└── types/          API kontrat tipleri
```

---

# 4 · BACKEND — ORCHESTRATOR GRAFI

```mermaid
flowchart TD
    START([İstek]) --> SIN["🛡️ security_in"]
    SIN -->|güvensiz| REJ["reject"]
    SIN -->|güvenli| RTR["🧭 router"]

    RTR --> P["Portföy Ajanı"]
    RTR --> M["Piyasa Ajanı"]

    P --> R["Risk Ajanı"]
    M --> R

    R --> GATE["🛡️ security_gate"]
    GATE -->|sorunlu| SAFE["safe_response"]
    GATE -->|temiz| SYN["✍️ synthesizer<br/>STREAMING"]

    SYN --> END([Yanıt])
    REJ --> END
    SAFE --> END

    style SIN fill:#ffe0b2
    style GATE fill:#ffe0b2
    style RTR fill:#e1bee7
    style SYN fill:#c8e6c9
```

## 4.1 Ajan Bağımlılık Kuralı

```mermaid
flowchart LR
    A["Başka ajanın<br/>çıktısına ihtiyaç var mı?"] -->|Hayır| B["PARALEL"]
    A -->|Evet| C["SIRALI"]
    style B fill:#c8e6c9
    style C fill:#ffe0b2
```

| Ajan | İhtiyacı | Konum |
|---|---|---|
| Portföy | yok | Paralel |
| Piyasa | yok | Paralel |
| Risk | portföy + piyasa | **Sıralı** |
| Synthesizer | hepsi | En son |

## 4.2 AgentState

```mermaid
classDiagram
    class AgentState {
        +int user_id
        +int thread_id
        +str request_id
        +int portfolio_id
        +str user_query
        +list messages
        +list requested_agents
        +str intent
        +dict portfolio_data
        +dict market_data
        +dict risk_data
        +list~Source~ sources
        +list~AgentError~ agent_errors
        +bool is_input_safe
        +bool is_output_safe
        +str final_response
    }
```

| Alan | Reducer | Neden |
|---|---|---|
| `sources` | `operator.add` | İki ajan da yazabilir |
| `agent_errors` | `operator.add` | İki ajan da yazabilir |
| `messages` | `add_messages` | LangGraph standardı |
| `portfolio_data` / `market_data` / `risk_data` | yok | Her ajan kendi alanına yazar |

## 4.3 Kısmi Başarısızlık

```mermaid
flowchart LR
    A["Ajan çağrıldı"] --> B{"20 sn içinde<br/>döndü mü?"}
    B -->|Evet| C["Veri state'e"]
    B -->|Hayır| D["agent_errors'a yaz"]
    C --> E["Akış devam"]
    D --> E
    E --> F["Synthesizer eksiği<br/>dürüstçe söyler"]
    style D fill:#ffe0b2
    style F fill:#c8e6c9
```

## 4.4 Klasör Yapısı

```
api/app/
├── main.py           FastAPI, SSE ucu, lifespan
├── config.py         Settings
├── core/             context (user_id, request_id), logging, errors
├── schema/           AgentState, Source, AgentError, RouterDecision
├── auth/             JWT, bağımlılıklar
├── routes/           auth · portfolio · market · conversations · chat
├── mcp/              server.py (tool'lar) · client.py
├── agents/           base · portfolio · market_research · risk · security
├── engine/           orchestrator.py (graph, router, synthesizer)
├── rag/              ingestion.py · retrieval.py · embedding.py
└── market/           provider.py · scheduler.py
```

---

# 5 · MCP KATMANI

## 5.1 Yetkilendirme

```mermaid
flowchart LR
    A["JWT<br/>doğrulandı"] -->|"contextvar'a<br/>yaz"| B["user_id"]
    B --> C["Ajan"]
    C -->|"kod enjekte eder<br/>LLM görmez"| D["MCP Tool"]
    D --> E{"contextvar ile<br/>uyuşuyor mu?"}
    E -->|Evet| F[("DB")]
    E -->|Hayır| G["🚨 security_events<br/>action = block"]
    style G fill:#ffcdd2
    style E fill:#fff9c4
```

## 5.2 Tool Kataloğu

| # | Tool | LLM'in gördüğü | Kullanan |
|---|---|---|---|
| 1 | `user_get_profile` | — | Risk |
| 2 | `portfolio_get_summary` | — | Portföy |
| 3 | `portfolio_get_holdings` | — | Portföy |
| 4 | `portfolio_get_allocation` | — | Portföy |
| 5 | `portfolio_get_transactions` | `limit` | Portföy |
| 6 | `market_get_quote` | `symbol` | Piyasa · Risk |
| 7 | `market_get_history` | `symbol, days` | Piyasa · Risk |
| 8 | `rag_search` | `query, top_k, sirket?, tip?` | Piyasa |

**Dönüş zarfı (tümü aynı):**
```json
{ "ok": true, "data": {}, "error": null }
```

## 5.3 Ajan → Tool Matrisi

```mermaid
flowchart LR
    P["Portföy Ajanı"] --> T2["2 · 3 · 4 · 5"]
    M["Piyasa Ajanı"] --> T6["6 · 7 · 8"]
    R["Risk Ajanı"] --> T1["1 · 7"]
    S["Güvenlik Ajanı"] --> T0["— hiçbiri —"]
    style T0 fill:#ffcdd2
```

## 5.4 Kurallar

| Kural | |
|---|---|
| `user_id` tool şemasında **yok** | Prompt injection'ı engeller |
| Tüm parasal değerler **TRY normalize** | Alan adları `*_try` |
| `rag_search` **yapılandırılmış** döner | Kaynak metadata'sı kaybolmasın |
| `market_get_history` **özet** döner | LLM bağlamı şişmesin |
| Her çağrı `tool_calls`'a yazılır | Denetim + demo |

---

# 6 · RAG PIPELINE

## 6.1 Ingestion (çevrimdışı, arka plan)

```mermaid
flowchart LR
    A["Finansal doküman<br/>haber · bilanço · rapor"] --> B["rag.documents"]
    B --> C["Chunking<br/>800 token / 120 örtüşme"]
    C --> D["Lokal Embedding<br/>CPU · API kotası harcamaz"]
    D --> E["rag.chunks<br/>embedding + content_tsv"]
    E --> F["HNSW + GIN indeks"]
    style D fill:#c8e6c9
```

## 6.2 Retrieval (çevrimiçi, istek anında)

```mermaid
flowchart TD
    A["Kullanıcı sorusu"] --> B["Embed et"]
    B --> C["Dense arama<br/>vector cosine"]
    A --> D["BM25 arama<br/>content_tsv"]
    C --> E["RRF birleştirme"]
    D --> E
    E --> F["top_k chunk<br/>+ kaynak metadata"]
    F --> G["Piyasa Ajanı"]
    style E fill:#fff9c4
```

**Neden hibrit:** saf vektör araması `THYAO`, `2026 Q2` gibi tam eşleşme
gerektiren terimleri kaçırır.

## 6.3 LlamaIndex Sınırı

```mermaid
flowchart LR
    A["LlamaIndex"] --> B["✅ Doküman yükleme<br/>✅ Chunking"]
    A --> C["❌ PGVectorStore<br/>❌ Retrieval"]
    C --> D["Kendi tablosunu kurar,<br/>rag.chunks'ı görmez"]
    style B fill:#c8e6c9
    style C fill:#ffcdd2
```

---

# 7 · PİYASA VERİSİ KATMANI

```mermaid
flowchart TD
    T["⏱️ Tick<br/>her 60 sn"] --> P["MarketDataProvider"]
    P --> S["Simülatör<br/>rastgele yürüyüş<br/>sim_volatility"]
    P -.->|opsiyonel| A["API çapası<br/>günde 2-3 kez"]
    S --> U1["assets.current_price<br/>assets.prev_close"]
    S --> U2["assets.daily_change_pct<br/>weekly_change_pct"]
    S --> U3["price_history<br/>her 5 tick'te"]
    U1 --> D[("PostgreSQL")]
    U2 --> D
    U3 --> D
    D --> V["📊 Dashboard grafikleri<br/>🤖 market_* tool'ları"]
    style S fill:#c8e6c9
    style A fill:#eceff1
```

| Kural | |
|---|---|
| Varsayılan `simulated` | Kota yok, deterministik, çevrimdışı |
| `daily/weekly_change_pct` **yeniden hesaplanır** | Yoksa seed değerinde donar |
| Ajanlar fiyat **üretmez** | Sadece DB'den okur |
| Bu katman istek akışından **bağımsız** | Ayrı asyncio görevi |

---

# 8 · VERİ MODELİ

```mermaid
erDiagram
    users ||--o{ portfolios : sahip
    users ||--o{ chat_sessions : açar
    users ||--o{ watchlists : izler
    users ||--o{ user_alerts : kurar
    portfolios ||--o{ portfolio_assets : içerir
    portfolios ||--o{ transactions : geçmiş
    asset_categories ||--o{ assets : sınıflar
    assets ||--o{ portfolio_assets : ""
    assets ||--o{ price_history : "zaman serisi"
    assets ||--o{ rag_documents : "ilgili"
    chat_sessions ||--o{ chat_messages : ""
    rag_documents ||--o{ rag_chunks : "embed"
```

## 8.1 Tablo Sorumlulukları

| Grup | Tablolar | Sahip |
|---|---|---|
| Kimlik | `users` | Backend |
| Varlık | `asset_categories` · `assets` | Backend |
| Portföy | `portfolios` · `portfolio_assets` · `transactions` | Backend |
| Zaman serisi | `price_history` | Piyasa katmanı |
| Sohbet | `chat_sessions` · `chat_messages` | Orchestrator |
| Denetim | `tool_calls` · `security_events` | MCP + Güvenlik |
| Vektör | `rag.documents` · `rag.chunks` | RAG grubu |
| Kapsam dışı | `watchlists` · `user_alerts` | — |

## 8.2 Hesap Sahipliği

```mermaid
flowchart LR
    A["v_holdings_valued"] --> B["v_portfolio_allocation"]
    A --> C["v_portfolio_summary"]
    B --> D["🤖 MCP Tool"]
    B --> E["📊 Dashboard REST"]
    C --> D
    C --> E
    style A fill:#c8e6c9
```

> Hesap **tek yerde**: view. Ajan da dashboard da aynı view'ı okur.
> İki yerde hesaplarsanız iki farklı toplam görürsünüz.

## 8.3 Para Birimi

```mermaid
flowchart LR
    A["BTC · 0.5 · USD"] --> C["× v_fx_rates"]
    B["THYAO · 1000 · TRY"] --> C
    C --> D["market_value_try"]
    D --> E["✅ Tek birimde toplam"]
    style E fill:#c8e6c9
```

---

# 9 · GÜVENLİK

```mermaid
flowchart TD
    A["Kullanıcı girdisi"] --> B["🛡️ KAPI 1<br/>security_in"]
    B --> C{"Kural motoru<br/>LLM'siz"}
    C -->|temiz| D["Router"]
    C -->|şüpheli| E["Küçük LLM<br/>risk skoru"]
    E -->|güvenli| D
    E -->|riskli| F["🚫 Reddet"]

    D --> G["Ajanlar"]
    G --> H["🛡️ KAPI 2<br/>security_gate"]
    H --> I{"RAG içeriğinde<br/>enjeksiyon var mı?"}
    I -->|hayır| J["Synthesizer<br/>STREAMING"]
    I -->|evet| K["🚫 Güvenli yanıt"]

    F --> L[("security_events")]
    K --> L

    style B fill:#ffe0b2
    style H fill:#ffe0b2
    style F fill:#ffcdd2
    style K fill:#ffcdd2
```

| Tehdit | Kontrol |
|---|---|
| Prompt injection (kullanıcı) | Kapı 1 — kural motoru + LLM |
| Dolaylı injection (RAG dokümanı) | Kapı 2 — chunk metni taranır |
| Başka kullanıcının verisi | MCP contextvar doğrulaması |
| Yetkisiz konuşma erişimi | `conversation_id` sahiplik kontrolü |
| PII sızıntısı | Log ve `tool_calls.args` maskeleme |
| Yatırım tavsiyesi algısı | Synthesizer sistem promptu |

**Neden Kapı 2 sentezden önce:** token gönderildikten sonra geri alınamaz.

---

# 10 · KONTRATLAR

## 10.1 SSE Olayları

```jsonc
{"type":"meta",        "request_id":"…", "conversation_id":1}
{"type":"status",      "stage":"security|routing|agents|risk|synth", "message":"…"}
{"type":"sources",     "items":[{"doc_id","baslik","sirket","tarih","tip","score"}]}
{"type":"token",       "content":"Portföyünüzün "}
{"type":"agent_error", "agent":"market_research", "error_type":"timeout"}
{"type":"error",       "code":"LLM_UNAVAILABLE"}
{"type":"done",        "message_id":42, "latency_ms":8420}
```

**Sıra garantisi:** `meta` ilk · `sources` ilk `token`'dan önce · `done` son.

## 10.2 Router Kararı

```python
class RouterDecision(BaseModel):
    intent: Literal["portfoy","piyasa","risk","karma","sohbet","belirsiz"]
    agents: list[Literal["portfolio","market_research","risk_strategy"]]
    needs_clarification: bool = False
    clarifying_question: str | None = None
    reasoning: str
```

```mermaid
flowchart LR
    A["sohbet"] --> B["1-2 LLM çağrısı"]
    C["tam akış"] --> D["5-7 LLM çağrısı"]
    style B fill:#c8e6c9
    style D fill:#ffe0b2
```

## 10.3 REST Uçları

| Metot | Yol | Besler |
|---|---|---|
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | AppShell |
| GET | `/api/portfolio/summary` | SummaryCards |
| GET | `/api/portfolio/holdings` | HoldingsTable |
| GET | `/api/portfolio/allocation` | AllocationPie |
| GET | `/api/market/assets` | Piyasa sekmesi |
| GET | `/api/market/history` | PriceChart |
| GET | `/api/conversations` | ConversationList |
| GET | `/api/conversations/{id}/messages` | MessageList |
| POST | `/api/chat/stream` | Chat (SSE) |
| GET | `/health` | — |

---

# 11 · GENİŞLETME NOKTALARI

## 11.1 Yeni Ajan Ekleme

```mermaid
flowchart LR
    A["1· BaseAgent'tan türet"] --> B["2· AgentState'e<br/>çıktı alanı ekle"]
    B --> C["3· RouterDecision<br/>Literal'ına ekle"]
    C --> D["4· Graph'a node + kenar"]
    D --> E["5· Tool matrisine ekle"]
    E --> F["6· Synthesizer promptunu<br/>güncelle"]
```

**Kural:** Başka ajanın çıktısına ihtiyaç duyuyorsa sıralı, duymuyorsa paralel.

## 11.2 Yeni MCP Tool Ekleme

```mermaid
flowchart LR
    A["1· mcp/server.py'a<br/>@mcp.tool"] --> B["2· Ortak zarfı döndür"]
    B --> C["3· user_id'yi<br/>contextvar'dan al"]
    C --> D["4· Ajan tool<br/>listesine ekle"]
```

## 11.3 Yeni Sayfa / Grafik Ekleme

```mermaid
flowchart LR
    A["1· DB view'ı"] --> B["2· REST ucu"]
    B --> C["3· Query hook"]
    C --> D["4· Bileşen"]
```

## 11.4 Ölçeklenme Yolu (proje sonrası)

```mermaid
flowchart LR
    A["Modular Monolith<br/>tek container"] -.->|"gerekirse"| B["Ajan servisleri ayrılır"]
    A -.->|"gerekirse"| C["Vektör DB ayrılır"]
    A -.->|"gerekirse"| D["Redis cache + kuyruk"]
    style A fill:#c8e6c9
```
