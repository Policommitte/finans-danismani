"""FastAPI kimlik dogrulama bagimliliklari.

`get_current_user` her korumali endpoint'te calisir ve iki is yapar:

  1. Token'i cozup kullaniciyi DB'den okur.
  2. Kullanici kimligini MCP contextvar'ina yazar (mimari v4 bolum 6.1).

Ikinci adim guvenligin temelidir: `user_id` MCP tool semasinda YOKTUR, yani
LLM onu goremez ve baskasinin kimligini yazamaz. Tool'lar kimin adina
calistiklarini yalnizca bu contextvar'dan ogrenir.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.security import decode_access_token
from app.core.errors import AuthenticationError, AuthorizationError
from app.mcp.context import set_current_user_id
from app.repositories.deps import get_user_repository

#: `auto_error=False`: eksik header'da FastAPI'nin kendi 403'u yerine bizim
#: hata sozlesmemize uyan 401 yanitini uretiyoruz.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict:
    """Gecerli token'dan kullanici kaydini uretir; aksi halde 401.

    Donen sozlukte `password_hash` YOKTUR (`UserRepository.get_by_id`
    sozlesmesi).
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Kimlik dogrulama gerekli.")

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise AuthenticationError("Oturum gecersiz veya suresi dolmus.")

    user = await get_user_repository().get_by_id(user_id)
    if user is None:
        raise AuthenticationError("Oturum gecersiz veya suresi dolmus.")

    # MCP yetkilendirmesi buradan beslenir - tool'lar user_id'yi LLM'den DEGIL
    # bu contextvar'dan alir.
    set_current_user_id(user["id"])
    request.state.user_id = user["id"]

    return user


CurrentUser = Annotated[dict, Depends(get_current_user)]


async def get_current_advisor(user: CurrentUser) -> dict:
    """`CurrentUser` ile ayni, ustune role='advisor' kontrolu ekler.

    Musteri hesabi bu bagimliligi kullanan bir endpoint'e istek atarsa 403
    alir - lead motoru verilerine (isim/e-posta/gelir/portfoy) sadece
    danisman rolundeki hesaplar erisebilir.
    """
    if user.get("role") != "advisor":
        raise AuthorizationError("Bu kaynak yalnizca danismanlara aciktir.")
    return user


CurrentAdvisor = Annotated[dict, Depends(get_current_advisor)]
