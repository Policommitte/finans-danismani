import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import health
from app.config import settings
from app.core.errors import (
    AppError,
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import request_id_ctx, setup_logging

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

app = FastAPI(
    title="Akilli Kisisel Finans Danismani API",
    version="0.1.0",
    responses={
        400: ERROR_RESPONSE_SCHEMA,
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

# Yeni router'lar buraya eklenecek:
# app.include_router(portfolio.router)
# app.include_router(market.router)
# app.include_router(risk.router)
# app.include_router(chat.router)
