# Backend — Akıllı Kişisel Finans Danışmanı

FastAPI tabanlı Orchestrator / Backend API katmanı.

## Gereksinimler

- Python 3.13

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
- Health: http://localhost:8000/health

## Test

```bash
pytest -q
```

## Ortam değişkenleri

| Değişken | Varsayılan | Açıklama |
|---|---|---|
| `APP_ENV` | `development` | Çalışma ortamı |
| `LOG_LEVEL` | `INFO` | Log seviyesi |
| `CORS_ORIGINS` | `http://localhost:3000` | Virgülle ayrılmış frontend adresleri |
| `LLM_API_KEY` | boş | LLM entegrasyonunda doldurulacak |
| `DEFAULT_MODEL` | boş | LLM entegrasyonunda doldurulacak |
| `PORTFOLIO_MODEL` | boş | Boşsa `DEFAULT_MODEL` kullanılır |
| `MARKET_MODEL` | boş | Boşsa `DEFAULT_MODEL` kullanılır |
| `RISK_MODEL` | boş | Boşsa `DEFAULT_MODEL` kullanılır |

`DATABASE_URL` ve `VECTOR_DB_URL` şu an devre dışı.

## Klasör yapısı

```
app/
  api/routes/     endpoint tanımları
  core/           errors, logging
  repositories/   veri erişim katmanı
  schemas/        Pydantic request/response modelleri
  services/       iş mantığı
  agents/         ajanlar
  mcp/            MCP server
  db/             DB oturumu — şu an devre dışı
  config.py       ayarlar
  main.py         uygulama girişi
tests/
```

## Yeni endpoint eklerken

Veriye doğrudan erişme, repository katmanını kullan:

```python
from fastapi import APIRouter, Depends

from app.repositories.base import PortfolioRepository
from app.repositories.deps import get_portfolio_repository

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio(repo: PortfolioRepository = Depends(get_portfolio_repository)):
    return repo.get_summary(user_id=1)
```

Router'ı `app/main.py` içinde `include_router` ile ekle.

## Bilinen durum

- Veri bellekte sabit tutuluyor (`repositories/in_memory.py`)
- DB entegrasyonu bekliyor; `app/db/session.py` ve `/health/db` yoruma alınmış durumda
- Kimlik doğrulama henüz yok