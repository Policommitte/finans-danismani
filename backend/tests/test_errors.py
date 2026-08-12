"""Hata formati testleri.

Buradaki /_test/* rotalari yalnizca testler calisirken uygulamaya eklenir
(include_in_schema=False oldugu icin /docs'ta da gorunmezler).
"""

from pydantic import BaseModel

from app.core.errors import BusinessRuleError, NotFoundError
from app.main import app


class _EchoBody(BaseModel):
    x: int


@app.get("/_test/not-found", include_in_schema=False)
async def _raise_not_found():
    raise NotFoundError("Kayit bulunamadi.")


@app.get("/_test/business-rule", include_in_schema=False)
async def _raise_business_rule():
    raise BusinessRuleError("Kural ihlali.")


@app.get("/_test/unhandled", include_in_schema=False)
async def _raise_unhandled():
    raise RuntimeError("beklenmeyen hata")


@app.post("/_test/validation", include_in_schema=False)
async def _validate(body: _EchoBody):
    return {"ok": True}


def test_unknown_path_error_format(client):
    response = client.get("/olmayan-adres")

    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "http_error"
    assert "message" in body["error"]
    assert "request_id" in body["error"]


def test_request_id_header_matches_body(client):
    response = client.get("/olmayan-adres")

    assert response.headers["X-Request-ID"] == response.json()["error"]["request_id"]


def test_not_found_error_format(client):
    response = client.get("/_test/not-found")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["message"] == "Kayit bulunamadi."
    assert "request_id" in error


def test_business_rule_error_format(client):
    response = client.get("/_test/business-rule")

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "business_rule_error"
    assert "request_id" in error


def test_validation_error_format_and_details(client):
    response = client.post("/_test/validation", json={"x": "sayi degil"})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert "request_id" in error
    assert error["details"], "validation hatasinda details bos olmamali"
    assert error["details"][0]["field"] == "x"


def test_unhandled_error_format_and_request_id_header(client_no_raise):
    response = client_no_raise.get("/_test/unhandled")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert response.headers["X-Request-ID"] == error["request_id"]
