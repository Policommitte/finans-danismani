import asyncio
import contextlib
import logging
import time
import uuid
from contextlib import asynccontextmanager

# WINDOWS NOTU: event loop policy duzeltmesi bilerek BURADA DEGIL, `run.py`
# icindedir - gerekcesi orada anlatilir. Windows'ta yerel gelistirme icin
# `uvicorn app.main:app` yerine `python run.py` calistirin.
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import auth, chat, dashboard, health, market, portfolio, risk
from app.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import request_id_ctx, setup_logging
from app.db.session import dispose_engine
from app.market.scheduler import run_price_scheduler
from app.mcp.context import set_request_context
from app.repositories.deps import describe_backend

setup_logging()
logger = logging.getLogger("app")

ERROR_RESPONSE_SCHEMA = {
    "description": "Hata yaniti",
    "content": {
        "application/json": {
            "example": {
                "error": {
                    "code": "not_found",
                    "message": "Kayit bulunamadi.",
                    "request_id": "3f2b1c8e-9a4d-4e21-b7c5-0d6e8a1f2b3c",
                }
            }
        }
    },
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Uygulama omru: arka plan fiyat gorevi burada baslar ve durur.

    Fiyat gorevi ISTEK AKISINDAN BAGIMSIZDIR (mimari v4 bolum 8): sohbet
    gelmese de fiyatlar ilerler. Gorev hicbir kosulda uygulamayi dusurmez;
    baslatilamazsa loglanir ve API normal calismaya devam eder.
    """
    logger.info(
        "uygulama basliyor",
        extra={"data_source": describe_backend(), "provider": settings.market_data_provider},
    )

    gorev: asyncio.Task | None = None
    if settings.price_tick_seconds > 0:
        gorev = asyncio.create_task(run_price_scheduler())

    try:
        yield
    finally:
        if gorev is not None:
            gorev.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await gorev
        if settings.database_enabled:
            await dispose_engine()


app = FastAPI(
    title="Akilli Kisisel Finans Danismani API",
    version="0.2.0",
    lifespan=lifespan,
    responses={
        400: ERROR_RESPONSE_SCHEMA,
        401: ERROR_RESPONSE_SCHEMA,
        404: ERROR_RESPONSE_SCHEMA,
        422: ERROR_RESPONSE_SCHEMA,
        500: ERROR_RESPONSE_SCHEMA,
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request_id_ctx.set(request_id)
    # Denetim kayitlari (`tool_calls`) bu id ile eslesir; kullanici kimligi
    # `get_current_user` bagimliliginda yazilir.
    set_request_context(request_id=request_id)

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Yakalanmayan hatalar disaridaki ServerErrorMiddleware'de yanita cevrilir;
        # oraya gitmeden once traceback'i request_id ile birlikte JSON loga dusuruyoruz.
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.exception(
            "request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
            },
        )
        raise
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(portfolio.router)
app.include_router(market.router)
app.include_router(risk.router)
app.include_router(chat.router)
