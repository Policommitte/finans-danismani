"""Sifre dogrulama ve JWT uretimi/cozumu.

Sifreler bcrypt ile saklanir (`users.password_hash`). Python 3.13'te `crypt`
modulu kaldirildigi icin `passlib` yerine dogrudan `bcrypt` kullanilir
(docs/backend-kararlar.md bolum 1).

Token icinde YALNIZCA kullanici kimligi tasinir; yetki kararlari her istekte
DB'den okunan guncel kayda gore verilir. Boylece kullanici silindiginde veya
degistiginde elde kalmis bir token yetki tasimaya devam etmez.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

logger = logging.getLogger(__name__)

TOKEN_TYPE = "bearer"


#: bcrypt ozeti SABIT BICIMLIDIR: "$2<varyant>$<iki haneli maliyet>$" ardindan
#: 22 karakter tuz + 31 karakter ozet = 53 karakter. Toplam 60 karakter.
_BCRYPT_OZET_DESENI = re.compile(r"^\$2[abxy]?\$\d{2}\$[./A-Za-z0-9]{53}$")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Sifreyi hash ile karsilastirir.

    Bozuk/eksik hash durumunda istisna firlatmaz, `False` doner: giris ucu
    "gecersiz kimlik bilgisi" demeli, 500 vermemelidir.

    ⚠️ BICIM ONCE KENDIMIZ DOGRULANIR, `bcrypt`e SONRA gidilir.
    `bcrypt==4.2.1` (requirements.txt'te sabitlenen surum) kirpilmis bir
    ozette Rust tarafinda PANIKLER; PyO3 bunu `pyo3_runtime.PanicException`
    olarak yuzeye cikarir ve o sinif `Exception`'dan DEGIL dogrudan
    `BaseException`'dan turer - yani ne `except (ValueError, TypeError)` ne de
    `except Exception` onu yakalar. Sonuc: `users.password_hash` bir sekilde
    bozulmussa giris ucu 401 yerine 500 veriyordu (CI'da yakalandi,
    `$2b$12$kisa` girdisiyle).

    Ayni girdi `bcrypt==5.0.0`'da `ValueError` veriyor - yani davranis SURUME
    BAGLI. Bu yuzden kutuphanenin hata davranisina hic guvenilmiyor: bicim
    desene uymuyorsa `bcrypt` cagrilmaz bile. `except` yine de duruyor,
    desenden gecen ama yine de reddedilen girdiler icin.
    """
    if not plain_password or not password_hash:
        return False
    if not _BCRYPT_OZET_DESENI.match(password_hash):
        logger.warning("gecersiz sifre hash formati")
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        logger.warning("gecersiz sifre hash formati")
        return False


def hash_password(plain_password: str) -> str:
    """Yeni kullanici kaydi icin (kayit ucu eklendiginde kullanilacak)."""
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(user_id: int, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes or settings.jwt_expire_minutes)

    payload = {
        "sub": str(user_id),  # JWT standardi: `sub` string olmali
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Token'i dogrular ve `user_id` doner; gecersizse `None`.

    Cozum hatasinin AYRINTISI cagirana verilmez (suresi doldu / imza yanlis /
    bicim bozuk ayrimi saldirgana bilgi verir); yalnizca loga yazilir.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        logger.info("token dogrulanamadi", extra={"neden": type(exc).__name__})
        return None

    subject = payload.get("sub")
    try:
        return int(subject)
    except (TypeError, ValueError):
        logger.warning("token icindeki sub sayisal degil")
        return None
