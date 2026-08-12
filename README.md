# Akıllı Kişisel Finans Danışmanı

InternTech 2026 — çoklu ajan mimarisi, RAG ve MCP tabanlı kişisel finans danışmanı.

## Proje yapısı

```
backend/     FastAPI — orchestrator, agent'lar, MCP server, RAG pipeline
frontend/    Web arayüzü — Dashboard, Portföy, Piyasa, Risk, AI Chat
docs/        Gereksinim dokümanı, sprint planları, mimari
data/        Dummy data üreticisi ve RAG doküman seti
```

## Hızlı başlangıç

```bash
cp .env.example backend/.env
cd backend
python3.13 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app
```

API dokümantasyonu: http://localhost:8000/docs

Detaylı backend kurulumu: [backend/README.md](backend/README.md)

## Mevcut durum

Veritabanı entegrasyonu **geçici olarak devre dışı**. Şema hazır olana kadar
backend veriyi bellekteki repository katmanından okuyor
(`backend/app/repositories/in_memory.py`), bu yüzden uygulamayı çalıştırmak
için Postgres'e ihtiyaç yok.

Devre dışı bırakılanlar:

- `backend/app/db/session.py` — dosya duruyor, hiçbir yerden çağrılmıyor
- `/health/db` endpoint'i — yoruma alındı
- `sqlalchemy`, `psycopg`, `alembic` — `requirements.txt`'ten çıkarıldı
- `.env` içindeki `DATABASE_URL` ve `VECTOR_DB_URL` — yoruma alındı

Şema hazır olduğunda: paketler geri eklenir, yoruma alınan satırlar açılır ve
`repositories/deps.py` içindeki implementasyon SQL sürümüyle değiştirilir.
Endpoint ve servis kodunda değişiklik gerekmez.

## Dokümanlar

- [Gereksinim dokümanı](docs/gereksinimler.md)
- [Sprint 1 planı](docs/sprint-1.md)
- [Backend kararları](docs/backend-kararlar.md)
- [Katkı rehberi](CONTRIBUTING.md)