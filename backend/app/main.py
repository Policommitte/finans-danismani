import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.config import settings
from app.core.errors import unhandled_exception_handler
from app.core.logging import setup_logging

setup_logging()

app = FastAPI(
    title="Akilli Kisisel Finans Danismani API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, unhandled_exception_handler)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


app.include_router(health.router)

# Yeni router'lar buraya eklenecek:
# app.include_router(portfolio.router)
# app.include_router(market.router)
# app.include_router(risk.router)
# app.include_router(chat.router)
