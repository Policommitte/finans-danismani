"""MCP cagri baglami - `user_id` ve `request_id` icin contextvar'lar.

NEDEN CONTEXTVAR (mimari v4 bolum 6.1 ve 6.4):
    `user_id` MCP tool semasinda YER ALMAZ. Tool parametresi olsaydi LLM onu
    yazabilirdi ve "3 numarali kullanicinin portfoyunu getir" seklinde bir
    prompt injection dogrudan baska birinin verisini okuyabilirdi. Bunun yerine
    kimlik, kimlik dogrulama katmaninda contextvar'a yazilir; tool'lar onu
    koddan alir, modelden DEGIL.

`ContextVar` asyncio gorevleri arasinda otomatik olarak kopyalanir, yani
paralel calisan ajanlar ayni istegin kimligini gorur; farkli istekler ise
birbirinin degerini gormez.
"""

from __future__ import annotations

from contextvars import ContextVar

_current_user_id: ContextVar[int | None] = ContextVar("mcp_current_user_id", default=None)
_current_request_id: ContextVar[str] = ContextVar("mcp_current_request_id", default="")
_current_session_id: ContextVar[int | None] = ContextVar("mcp_current_session_id", default=None)


class MCPAuthorizationError(Exception):
    """Tool, kimligi cozulemeyen ya da uyusmayan bir cagri aldi.

    `security_events` tablosuna `action='block'` olarak yazilir.
    """


def set_current_user_id(user_id: int | None) -> None:
    _current_user_id.set(user_id)


def get_current_user_id() -> int | None:
    return _current_user_id.get()


def require_user_id() -> int:
    """Tool'larin kullandigi kati surum: kimlik yoksa cagri REDDEDILIR.

    Fail-closed: kimlik cozulemediyse "varsayilan kullanici" gibi bir kacamak
    yoktur; veri sizmasindansa istegin dusmesi yeglenir.
    """
    user_id = _current_user_id.get()
    if user_id is None:
        raise MCPAuthorizationError(
            "MCP tool cagrisi kimlik baglami olmadan yapildi (user_id contextvar bos)."
        )
    return user_id


def set_request_context(request_id: str = "", session_id: int | None = None) -> None:
    """Denetim kayitlari (`tool_calls`) icin istek/oturum baglamini yazar."""
    _current_request_id.set(request_id or "")
    _current_session_id.set(session_id)


def get_request_id() -> str:
    return _current_request_id.get()


def get_session_id() -> int | None:
    return _current_session_id.get()
