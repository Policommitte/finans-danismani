"""`app.auth.security` - sifre dogrulama ve JWT.

Bcrypt KASITLI OLARAK yavastir (~100 ms/hash). Bu dosyada hash uretimi
MODUL SEVIYESINDE bir kez yapilir; her testte yeniden uretmek suiteye
saniyeler eklerdi.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.config import settings

PAROLA = "demo1234"
#: Tek sefer uretilir - bcrypt maliyeti suite basina bir kez odenir.
HASH = hash_password(PAROLA)


def test_dogru_parola_dogrulanir():
    assert verify_password(PAROLA, HASH)


def test_yanlis_parola_reddedilir():
    assert not verify_password("yanlis-parola", HASH)


@pytest.mark.parametrize(
    "parola,ozet",
    [
        ("", HASH),  # parola bos
        (PAROLA, ""),  # hash bos
        (PAROLA, "bcrypt-olmayan-metin"),  # bozuk format
        (PAROLA, "$2b$12$kisa"),  # kirpilmis hash
    ],
)
def test_bozuk_girdide_istisna_degil_false_doner(parola, ozet):
    """Giris ucu 'gecersiz kimlik bilgisi' demeli, 500 vermemeli."""
    assert verify_password(parola, ozet) is False


def test_hash_her_seferinde_farklidir():
    """Bcrypt rastgele salt kullanir - ayni parola farkli ozet uretir."""
    assert hash_password(PAROLA) != HASH
    assert verify_password(PAROLA, hash_password(PAROLA))


# --- JWT ------------------------------------------------------------------


def test_uretilen_token_cozulur():
    assert decode_access_token(create_access_token(42)) == 42


def test_sub_string_olarak_kodlanir():
    """JWT standardi `sub`'in string olmasini ister; int yazmak bazi
    kutuphanelerde dogrulamayi bozar."""
    yuk = jwt.decode(
        create_access_token(7), settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert yuk["sub"] == "7"
    assert yuk["exp"] > yuk["iat"]


def test_suresi_dolmus_token_reddedilir():
    assert decode_access_token(create_access_token(1, expires_minutes=-1)) is None


def test_baska_anahtarla_imzalanan_token_reddedilir():
    sahte = jwt.encode(
        {"sub": "1", "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())},
        # 32+ bayt: kisa anahtar PyJWT'de uyari uretir, testin konusu o degil.
        "saldirganin-anahtari-en-az-otuziki-bayt",
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(sahte) is None


@pytest.mark.parametrize("token", ["", "bozuk", "a.b.c", "Bearer x.y.z"])
def test_bicimi_bozuk_token_reddedilir(token):
    assert decode_access_token(token) is None


def test_sayisal_olmayan_sub_reddedilir():
    """`sub` DB'deki `users.id`'ye karsilik gelir; sayiya cevrilemiyorsa
    token guvenilmezdir."""
    sahte = jwt.encode(
        {
            "sub": "admin",
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    assert decode_access_token(sahte) is None


def test_token_yalnizca_kimlik_tasir():
    """Yetki kararlari her istekte DB'den okunur; token'a rol gomulmez -
    kullanici degistiginde elde kalmis token yetki tasimaya devam etmesin."""
    yuk = jwt.decode(
        create_access_token(3), settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert set(yuk) == {"sub", "iat", "exp"}
