import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Beklenmeyen bir hata olustu.",
                "request_id": request_id,
            }
        },
    )
