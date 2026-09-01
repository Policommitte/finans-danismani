"""NVI (Nufus ve Vatandaslik Isleri Genel Mudurlugu) kimlik dogrulama servisi.

Ucretsiz, herkese acik SOAP 1.1 servisi - anahtar gerektirmez. Kayit
formundaki TC Kimlik No + Ad + Soyad + Dogum Yili'nin nufus kayitlariyla
eslesip eslesmedigini dogrular (bkz. app/api/routes/auth.py::register).

`app/services/pexels.py` ile AYNI felsefe: dis servis ASLA istegi
cokertmez. Hata ASLA disari firlatilmaz - `None` doner ve cagiran taraf
bunu "servise ulasilamadi" olarak yorumlar (KESIN "false" ile KARISTIRILMAZ,
cunku biri "kimlik uyusmuyor", digeri "su an bilmiyoruz" demektir).
"""

from __future__ import annotations

import asyncio
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_WSDL_URL = "https://tckimlik.nvi.gov.tr/Service/DogrulamaSoapWs.asmx?wsdl"

#: zeep.Client WSDL'i ayristirmak icin agir bir nesne - istek basina degil,
#: surec basina BIR KEZ olusturulur (tembel/lazy, ilk gercek cagrida).
_client = None


def _get_client():
    global _client
    if _client is None:
        import zeep

        _client = zeep.Client(wsdl=_WSDL_URL)
    return _client


def _call_sync(tckn: str, ad: str, soyad: str, dogum_yili: int) -> bool:
    """zeep senkrondur - bu fonksiyon `asyncio.to_thread` icinde calistirilir."""
    client = _get_client()
    return bool(
        client.service.TCKimlikNoDogrula(
            TCKimlikNo=int(tckn),
            Ad=ad,
            Soyad=soyad,
            DogumYili=dogum_yili,
        )
    )


async def verify_identity(tckn: str, ad: str, soyad: str, dogum_yili: int) -> bool | None:
    """NVI TCKimlikNoDogrula ile kimlik dogrulamasi yapar.

    Donus degerleri:
      True  -> bilgiler nufus kayitlariyla eslesiyor.
      False -> bilgiler EsLESMIYOR (kayit reddedilmeli).
      None  -> servise ulasilamadi/zaman asimi/beklenmeyen hata - bu KESIN
               bir "false" DEGILDIR, cagiran taraf kullaniciya "doğrulama
               servisine ulaşılamıyor" gibi FARKLI bir mesaj gostermelidir.

    `settings.nvi_verification_enabled=False` ise (SADECE yerel gelistirme/
    test icin - gercek TC Kimlik No olmadan US15 akisini test edebilmek
    icin bilincli bir kacis kapisi) servise HIC gidilmez, dogrudan True
    doner.
    """
    if not settings.nvi_verification_enabled:
        return True

    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_call_sync, tckn, ad, soyad, dogum_yili),
            timeout=settings.nvi_timeout_seconds,
        )
    except Exception as exc:  # noqa: BLE001 - dis SOAP servisinin hata yuzeyi
        # (WSDL yuklenemedi, agdaki her turlu kopukluk, beklenmeyen XML)
        # httpx.HTTPError'dan cok daha genis; bu sinir HICBIR sekilde
        # cokmemeli, bu yuzden bilincli olarak genis yakalanir.
        logger.warning(
            "nvi dogrulama istegi basarisiz",
            extra={"hata": f"{type(exc).__name__}: {exc}"},
        )
        return None
