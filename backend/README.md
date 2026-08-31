# Backend — Akıllı Kişisel Finans Danışmanı

FastAPI + LangGraph tabanlı API ve orkestrasyon katmanı.
Mimari referans: [`../SYSTEM_ARCHITECTURE_v4.md`](../SYSTEM_ARCHITECTURE_v4.md).

## Gereksinimler

- Python 3.13 (CI bu sürümde çalışır)
- PostgreSQL 16 + pgvector — **opsiyonel**, aşağıya bakın

## Kurulum

```bash
cd backend
python3.13 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
```

## Çalıştırma

```bash
uvicorn app.main:app --reload --reload-dir app
```

- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health · http://localhost:8000/health/db

### Kademeli çalışma — hiçbiri zorunlu değil

Sistem üç şey olmadan da **uçtan uca çalışır**; her biri bağımsız olarak
açılabilir. Ekip birbirini beklemez:

| Eksik olan | Ne olur |
|---|---|
| `DATABASE_URL` yok | Repository katmanı bellek içi temel kayıtlara düşer; fiyat veya performans geçmişi üretmez. `/health` `data_source: in-memory` döner. |
| `LLM_API_KEY` / model adı yok | Ajanlar LLM'siz çalışır: kaynaklardan deterministik alıntı/özet üretirler. Akış, olaylar ve testler etkilenmez. |
| `EMBEDDING_MODEL` / `EMBEDDING_API_KEY` yok | `rag_search` yalnızca BM25 (tam eşleşme) ayağıyla çalışır. Tanımlıysa (bugün: Cohere `embed-v4.0`) `rag_search` hibrit aramayı (dense + BM25 → RRF, `SqlRagRepository.hybrid_search`) kullanır; sorgu-zamanı embedding çağrısı başarısız/zaman aşımına uğrarsa istek düşmez, sessizce BM25'e döner. |

> ⚠️ **LLM modeli henüz seçilmedi.** Kodda hiçbir model adı sabit yazılı
> değildir; `DEFAULT_MODEL` boş olduğu sürece LLM hiç oluşturulmaz. Karar
> verildiğinde tek yapılacak `.env` dosyasına model adını yazmaktır.

### Veritabanıyla çalıştırma

```bash
docker compose up -d db          # şema + dummy data ilk kalkışta yüklenir
export DATABASE_URL=postgresql+psycopg://finans:finans@localhost:5432/finans
uvicorn app.main:app --reload --reload-dir app
```

> **2026-08-20 güncelleme:** `rag.chunks` seed verisi artık elle yazılmış
> metin değil — `db/v5_schema_and_data.sql`'deki 8 örnek dokümanın
> `raw_text`'i dolduruldu ve chunk'lar + embedding'ler gerçek pipeline'dan
> (`app.ingestion.backfill`, Cohere embed-v4) üretildi. Yani taze bir
> `docker compose up -d db` sonrası lokal DB'de hibrit/dense arama da
> gerçek vektörlerle test edilebilir — ayrıca backfill çalıştırmaya gerek
> yok. `raw_text`'i değiştirirseniz chunk/embedding tutarsız kalır; yeniden
> üretmek için `db/v5_schema_and_data.sql`'deki "13 · RAG ÖRNEK
> DOKÜMANLARI" bölümündeki talimatı izleyin.

## Test

```bash
pytest -q                        # DB gerekmez (bellek içi repository'ler)

# PostgreSQL entegrasyon testleri (opsiyonel):
TEST_DATABASE_URL=postgresql+psycopg://finans:finans@localhost:5432/finans pytest -q
```

Lint: `ruff check . && black --check .`

## Demo kullanıcı

Dummy data'daki tüm kullanıcıların şifresi `demo1234`.

```bash
curl -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"mehmet@example.com","password":"demo1234"}'
```

## Endpoint'ler

Sözleşme: [`../docs/api-sozlesmesi.md`](../docs/api-sozlesmesi.md)

| Metot | Yol | Besler |
|---|---|---|
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | AppShell |
| GET | `/api/dashboard/summary` | Dashboard ilk yükleme (birleşik) |
| GET | `/api/portfolio/summary` · `/holdings` · `/allocation` · `/transactions` | Portföy sekmesi |
| GET | `/api/market/assets` · `/history` | Piyasa sekmesi |
| POST | `/api/market/search` | RAG destekli piyasa araması |
| GET | `/api/risk/profile` | Risk paneli |
| GET | `/api/conversations` · `/{id}/messages` | Sohbet listesi |
| POST | `/api/chat/stream` | Chat (SSE) |

## Klasör yapısı

```
app/
  api/routes/     endpoint tanımları
  auth/           JWT, get_current_user
  core/           errors, logging, llm
  orchestration/  AgentState + ortak modeller (REST modelleri DEĞİL)
  schemas/        REST request/response modelleri
  services/       ekran verisi domain servisleri
  repositories/   veri erişim katmanı (base / in_memory / sql / deps)
  agents/         base · market_research · portfolio · risk_strategy · security_agent
  engine/         orchestrator (graph, router, sentez) · factory (wiring)
  mcp/            client · server (tool grupları) · context (user_id contextvar)
  market/         provider · scheduler (periyodik fiyat görevi)
  db/             async oturum yönetimi
  config.py       ayarlar
  main.py         uygulama girişi
tests/
```

> `orchestration/` ile `schemas/` karıştırılmamalı: ilki graph içinde taşınan
> durum, ikincisi HTTP sınırındaki sözleşme. (Eskiden `schema/` + `schemas/`
> yan yanaydı; tek harf farkı kalıcı karışıklık üretiyordu.)

## Yeni endpoint eklerken

Katman kuralı: **`routes → services → repositories`**. Endpoint veriye
doğrudan erişmez.

```python
from fastapi import APIRouter

from app.auth.deps import CurrentUser
from app.services import portfolio as service

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/summary")
async def summary(user: CurrentUser):
    return await service.ozet_getir(user["id"])
```

Router'ı `app/main.py` içinde `include_router` ile ekle.

## Yeni MCP tool eklerken

1. `app/mcp/server.py` içine handler yaz, `TOOL_GROUPS`'a ekle.
2. Ortak zarfı döndür: `ok({...})` / `fail("...")`.
3. `user_id`'yi **parametre alma** — `require_user_id()` ile contextvar'dan al.
4. Mimari v4 §6.2'deki tool kataloğunu güncelle.

## Bilinen durum / açık işler

- LLM modeli seçilmedi (mimari v4 §16). Embedding modeli seçildi (Cohere
  `embed-v4.0`) ve `rag_search` hibrit aramayı kullanıyor; Supabase'deki
  paylaşılan DB'nin `rag.hybrid_search()` fonksiyonu bu genişletilmiş haliyle
  henüz güncellenmedi (yalnızca yerel Docker DB'de uygulandı) — bkz.
  `db/v5_schema_and_data.sql`.
- Synthesizer LangChain uyumlu bir chat modeli bekler; model kararına kadar
  deterministik özet üretilir.
- Gerçek piyasa API sağlayıcısı bağlanmadı (`ApiMarketProvider` simülatöre
  düşer) — PO onayı ve lisans kontrolü gerekiyor.
- `POST /api/reports` (FR-RISK-04) Sprint 4'e ertelendi.
