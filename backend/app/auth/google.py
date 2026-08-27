"""Google ile giris - erisim tokeni dogrulama.

`@react-oauth/google`'in `useGoogleLogin` (implicit) akisindan gelen bir
OAuth2 ERISIM tokeni (`access_token`) alinir; bu bir kimlik (ID) tokeni
DEGILDIR, imzali degildir. Bu yuzden iki adimda dogrulanir:

  1. `tokeninfo` ucu: tokenin GERCEKTEN bizim `google_client_id`'imiz icin
     verildigini (`aud`) teyit eder. Bu adim ATLANIRSA, BASKA bir uygulama
     icin verilmis gecerli bir Google erisim tokeni tasiyan herkes bizim
     backend'imize o kullanici olarak girebilir - audience kontrolu bu
     acigi kapatir.
  2. `userinfo` ucu: dogrulanmis token ile e-posta/isim bilgisini getirir.

Ikisi de `httpx` ile senkron olmayan (async) istek atar; yeni bir Python
bagimliligi GEREKMEZ (google-auth kutuphanesi kullanilmaz).
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
_TIMEOUT_SANIYE = 8


async def fetch_google_profile(access_token: str) -> dict | None:
    """Erisim tokenini dogrular ve profil doner; gecersizse `None`.

    Donen sozluk: `{email, given_name, family_name, email_verified}`.
    """
    if not access_token or not settings.google_client_id:
        return None

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SANIYE) as client:
            tokeninfo = await client.get(_TOKENINFO_URL, params={"access_token": access_token})
            if tokeninfo.status_code != 200:
                logger.info("google tokeninfo basarisiz", extra={"status": tokeninfo.status_code})
                return None

            if tokeninfo.json().get("aud") != settings.google_client_id:
                logger.warning("google tokeni baska bir client icin verilmis (aud uyumsuz)")
                return None

            userinfo = await client.get(
                _USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            if userinfo.status_code != 200:
                logger.info("google userinfo basarisiz", extra={"status": userinfo.status_code})
                return None

            profile = userinfo.json()
    except httpx.HTTPError as exc:
        logger.warning("google profili alinamadi", extra={"hata": f"{type(exc).__name__}: {exc}"})
        return None

    email = profile.get("email")
    if not email:
        return None

    return {
        "email": email,
        "given_name": profile.get("given_name") or "",
        "family_name": profile.get("family_name") or "",
        "email_verified": bool(profile.get("email_verified")),
    }
