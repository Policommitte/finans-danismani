"""TC Kimlik Numarasi (TCKN) ile ilgili paylasilan yardimcilar.

Iki ayri ozellik bu numarayla ilgilenir ve ikisi de AYNI checksum
algoritmasini kullanir - kod tekrarini onlemek icin buraya toplandi:

  1. `app/agents/security_agent.py` - kullanicinin sohbete TCKN yapistirmasini
     ENGELLEMEK icin (PII sizintisi tespiti, kimlik dogrulamayla ilgisizdir).
  2. `app/api/routes/auth.py` - kayit formundaki TCKN'i NVI'ye gondermeden
     ONCE ucretsiz, yerel bir on-elemeden gecirmek icin (bariz gecersiz bir
     numara icin NVI'ye hic istek atilmaz).
"""

from __future__ import annotations

import hashlib
import hmac

from app.config import settings


def tckn_checksum_valid(numara: str) -> bool:
    """TCKN'in resmi saglama (checksum) kurallarini dogrular.

    10. hane: (tek sirali hanelerin toplami * 7 - cift sirali hanelerin
    toplami) mod 10. 11. hane: ilk 10 hanenin toplami mod 10.

    `numara` tam olarak 11 haneli rakam dizisi OLMALIDIR (cagiran taraf
    - orn. Pydantic `pattern=r"^\\d{11}$"` - bunu zaten garanti eder).
    """
    haneler = [int(k) for k in numara]
    tek_toplam = sum(haneler[0:9:2])  # 1., 3., 5., 7., 9. haneler
    cift_toplam = sum(haneler[1:8:2])  # 2., 4., 6., 8. haneler
    if (tek_toplam * 7 - cift_toplam) % 10 != haneler[9]:
        return False
    return sum(haneler[:10]) % 10 == haneler[10]


def _pepper() -> str:
    """HMAC anahtari. Ayri bir sir yonetmek istemeyen kucuk ekipler icin
    `TCKN_HASH_PEPPER` bos birakilirsa `JWT_SECRET`'a duser."""
    return settings.tckn_hash_pepper.strip() or settings.jwt_secret


def hash_tckn(tckn: str) -> str:
    """TCKN'in saklama icin tek yonlu, DETERMINISTIK ozeti (HMAC-SHA256).

    Bcrypt'in aksine (rastgele salt -> ayni girdi her seferinde FARKLI hash
    uretir) burada ayni TCKN HER ZAMAN ayni hash'i uretir - boylece ayni
    kisinin farkli e-postalarla birden fazla hesap acmasi
    `users.tckn_hash` uzerindeki UNIQUE index ile engellenebilir (bkz.
    db/migrations/017_users_tckn_verification.sql). Anahtar (pepper) sunucu
    tarafinda kaldigi surece tek yonludur - DB sizintisi tek basina TCKN'i
    geri vermez.
    """
    return hmac.new(_pepper().encode("utf-8"), tckn.encode("utf-8"), hashlib.sha256).hexdigest()


def tckn_last4(tckn: str) -> str:
    """Ekranlarda/normal sorgularda gosterilecek TEK bicim - son 4 hane."""
    return tckn[-4:]
