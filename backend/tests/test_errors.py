def test_not_found_error_format(client):
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