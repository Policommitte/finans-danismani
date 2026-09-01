import uuid

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Uygulama ici hatalarin temel sinifi."""

    code = "app_error"
    status_code = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404


class BusinessRuleError(AppError):
    code = "business_rule_error"
    status_code = 422


class AuthenticationError(AppError):
    """Kimlik dogrulanamadi (token yok / gecersiz / suresi dolmus).

    Yanit gövdesi hicbir zaman NEDEN'i ayirt etmez ("token suresi doldu" ile
    "imza gecersiz" ayrimi saldirgana bilgi verir); ayrinti yalnizca logdadir.
    """

    code = "unauthorized"
    status_code = 401


class AuthorizationError(AppError):
    """Kimlik dogru ama bu kaynaga erisim yetkisi yok."""

    code = "forbidden"
    status_code = 403


class ConflictError(AppError):
    """Kaynak zaten var (orn. e-posta kayitli)."""

    code = "conflict"
    status_code = 409


class ServiceUnavailableError(AppError):
    """Dis servise (orn. NVI kimlik dogrulama) ulasilamadi - GECICI bir
    durum, kullanicinin hatasi DEGIL. Cagiran taraf tekrar denemeyi
    onerebilir."""

    code = "service_unavailable"
    status_code = 503


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def _error_response(
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: list[dict] | None = None,
) -> JSONResponse:
    error: dict = {
        "code": code,
        "message": message,
        "request_id": request_id,
    }
    if details is not None:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={"error": error},
        headers={"X-Request-ID": request_id},
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _error_response(exc.status_code, exc.code, exc.message, _request_id(request))


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error_response(exc.status_code, "http_error", str(exc.detail), _request_id(request))


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in err.get("loc", []) if part != "body"),
            "message": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        }
        for err in exc.errors()
    ]
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "validation_error",
        "Gecersiz istek.",
        _request_id(request),
        details=details,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        500,
        "internal_error",
        "Beklenmeyen bir hata olustu.",
        _request_id(request),
    )
