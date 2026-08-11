# Akilli Kisisel Finans Danismani - Sistem Mimarisi

## Genel Sistem Mimarisi

Bu mimaride ajanlar birbirlerini dogrudan cagirmamaktadir. Tum ajan cagirilari Orchestrator uzerinden yonetilir. MCP katmani ajanlarin servis ve veri kaynaklarina standart tool cagrilariyla erismesini saglar. LLM API ise yorumlama, ozetleme ve metin uretimi icin kullanilir.

```mermaid
flowchart TD
    U["Kullanici"] --> FE["Frontend / Web Arayuzu"]
    FE --> API["Backend API"]
    API --> ORC["Orchestrator"]

    ORC --> PA["Portfoy Ajani"]
    ORC --> RA["Risk Ajani"]
    ORC --> MA["Piyasa Ajani"]
    ORC --> REPA["Rapor Ajani"]

    PA --> MCP["MCP Server / Tools"]
    RA --> MCP
    MA --> MCP
    REPA --> MCP

    PA -.-> LLM["LLM API"]
    RA -.-> LLM
    MA -.-> LLM
    REPA -.-> LLM

    MCP --> PS["Portfolio Service"]
    MCP --> RS["Risk Service"]
    MCP --> RAGS["RAG Service"]
    MCP --> REPS["Report Service"]

    PS --> DB["Database / Dummy Data"]
    RS --> DB
    RAGS -- "Indexleme / Kaydetme" --> VDB["Vector DB"]
    VDB -- "Retrieval / Chunk Donusu" --> RAGS
    REPS --> FILES["Rapor Dosyalari"]

    DOCS["Finansal Dokumanlar"] --> RAGS

    API -. "Streaming Response" .-> FE
```

## Mimari Kararlar

- Ajanlar birbirleriyle dogrudan haberlesmez.
- Orchestrator, hangi ajanin ne zaman calisacagina karar verir.
- Portfolio Agent portfoy hesaplamalarindan sorumludur.
- Risk Agent risk skoru ve strateji onerilerinden sorumludur.
- Piyasa Agent finansal haber ve rapor bilgilerini RAG uzerinden kullanir.
- Rapor Agent portfoy, risk ve piyasa ciktilarindan anlamli rapor icerigi uretir.
- MCP, veri ve tool erisimi icin kullanilir.
- LLM API, yorumlama, ozetleme ve metin uretimi icin kullanilir.
- Streaming Response, backend'den frontend'e cevabin parca parca aktarilmasini ifade eder.

## RAG Service Notu

Ana mimari diyagraminda sadelik icin dokuman isleme adimlari detaylandirilmamistir. RAG Service, finansal dokumanlarin sisteme alinmasi, parcalara bolunmesi, embedding olusturulmasi, Vector DB'ye kaydedilmesi ve kullanici sorularinda ilgili parcalarin geri getirilmesi sureclerini yonetir.

### Ingestion Sureci

```mermaid
flowchart TD
    DOC["Finansal Dokumanlar / Haberler"] --> ING["Document Ingestion"]
    ING --> CHUNK["Chunk + Embedding"]
    CHUNK --> VDB["Vector DB"]
```

### Retrieval Sureci

```mermaid
flowchart TD
    Q["Kullanici Sorusu"] --> MA["Piyasa Ajani"]
    MA --> MCP["MCP Server / Tools"]
    MCP --> RAGS["RAG Service"]
    RAGS -- "Benzerlik Aramasi" --> VDB["Vector DB"]
    VDB -- "Relevant Chunks" --> RAGS
    RAGS --> MA
    MA --> LLM["LLM API"]
    LLM --> ANS["Kaynakli Cevap"]
```

## Kisa Aciklama

Kullanici istegi frontend uzerinden Backend API'ye gelir. Backend API istegi Orchestrator'a iletir. Orchestrator istegin turune gore ilgili ajanlari cagirir. Ajanlar veri veya servis erisimi gerektiginde MCP tool'larini kullanir. Yorumlama, ozetleme veya rapor metni uretimi gereken durumlarda LLM API'den yararlanilir. Sonuc Backend API uzerinden frontend'e doner.
