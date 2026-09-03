"""`app.core.tckn` - checksum, HMAC ozeti ve maskeleme.

Iki ozellik ayni algoritmayi kullanir: guvenlik ajaninin PII sizinti
tespiti ve kayit formunun NVI oncesi on-elemesi.

⚠️ Buradaki numaralar UYDURMADIR - checksum kuralini saglayacak sekilde
uretildi, gercek bir kisiye ait degildir.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.core.tckn import hash_tckn, tckn_checksum_valid, tckn_last4


def _checksum_tamamla(ilk_dokuz: str) -> str:
    """Ilk 9 haneden gecerli bir 11 haneli numara uretir."""
    h = [int(k) for k in ilk_dokuz]
    onuncu = ((sum(h[0:9:2]) * 7) - sum(h[1:8:2])) % 10
    onbirinci = (sum(h) + onuncu) % 10
    return f"{ilk_dokuz}{onuncu}{onbirinci}"


GECERLI = _checksum_tamamla("102030405")


def test_uretilen_numara_checksum_kuralini_saglar():
    assert tckn_checksum_valid(GECERLI)


def test_onuncu_hane_bozulursa_reddedilir():
    bozuk = GECERLI[:9] + str((int(GECERLI[9]) + 1) % 10) + GECERLI[10]
    assert not tckn_checksum_valid(bozuk)


def test_onbirinci_hane_bozulursa_reddedilir():
    bozuk = GECERLI[:10] + str((int(GECERLI[10]) + 1) % 10)
    assert not tckn_checksum_valid(bozuk)


@pytest.mark.parametrize("numara", ["11111111111", "12345678901", "98765432109"])
def test_bariz_sahte_numaralar_on_elemede_yakalanir(numara):
    """Bu numaralar icin NVI'ye HIC istek atilmaz - ucretsiz on-eleme."""
    assert not tckn_checksum_valid(numara)


def test_checksum_tek_basina_yeterli_degildir():
    """⚠️ SINIRIN BELGESI: `00000000000` checksum kuralini SAGLAR (tum
    haneler 0 oldugundan her iki denklem de 0=0'a duser) ama gecerli bir
    kimlik DEGILDIR.

    Bu bir hata degil, algoritmanin dogasidir - on-eleme yalnizca BARIZ
    hatali girisi ucretsiz eler, son soz her zaman NVI'nindir
    (`app/services/nvi.py`). Kayit akisi bu fonksiyonun `True` donusunu
    'kimlik dogrulandi' saymamalidir."""
    assert tckn_checksum_valid("00000000000")


# --- HMAC ozeti -----------------------------------------------------------


def test_hash_deterministiktir():
    """Bcrypt'ten farki bu: ayni TCKN HER ZAMAN ayni hash'i verir, boylece
    `users.tckn_hash` uzerindeki UNIQUE index mukerrer hesabi engeller."""
    assert hash_tckn(GECERLI) == hash_tckn(GECERLI)


def test_farkli_numaralar_farkli_hash_uretir():
    assert hash_tckn(GECERLI) != hash_tckn(_checksum_tamamla("102030406"))


def test_hash_ham_numarayi_icermez():
    """Tek yonluluk: DB sizintisi tek basina TCKN'i geri vermemeli."""
    ozet = hash_tckn(GECERLI)
    assert GECERLI not in ozet
    assert len(ozet) == 64  # sha256 hex


def test_pepper_degisince_hash_degisir(monkeypatch):
    onceki = hash_tckn(GECERLI)
    monkeypatch.setattr(settings, "tckn_hash_pepper", "baska-bir-anahtar")
    assert hash_tckn(GECERLI) != onceki


def test_pepper_bos_ise_jwt_secret_e_duser(monkeypatch):
    """Ayri bir sir yonetmek istemeyen ekipler icin bilincli yedek."""
    monkeypatch.setattr(settings, "tckn_hash_pepper", "   ")
    monkeypatch.setattr(settings, "jwt_secret", "birinci-secret")
    birinci = hash_tckn(GECERLI)

    monkeypatch.setattr(settings, "jwt_secret", "ikinci-secret")
    assert hash_tckn(GECERLI) != birinci


def test_last4_yalnizca_son_dort_haneyi_verir():
    assert tckn_last4(GECERLI) == GECERLI[-4:]
    assert len(tckn_last4(GECERLI)) == 4
