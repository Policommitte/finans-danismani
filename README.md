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
cp .env.example .env      # değerleri doldurun
docker compose up -d      # postgres + vector db
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload
```

API dokümantasyonu: http://localhost:8000/docs

## Dokümanlar

- [Gereksinim dokümanı](docs/gereksinimler.md)
- [Sprint 1 planı](docs/sprint-1.md)
- [Katkı rehberi](CONTRIBUTING.md)
