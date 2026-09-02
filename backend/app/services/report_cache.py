"""Belge analiz ajaninin urettigi PDF raporlari GECICI olarak tutar.

NEDEN BELLEK ICI (kalici DEGIL)
--------------------------------
SSE govdesi metindir; ikili PDF icerigi orada tasinamaz (bkz.
`orchestrator.py::stream_request` - `done` olayina yalnizca dosya adi/boyutu
konur). Kullanici PDF'i indirebilsin diye baytlarin BIR YERDE durmasi
gerekiyor.

Kalici cozum (Supabase Storage) HENUZ KURULMADI - bu proje hic dosya deposu
kullanmiyor, bucket + erisim politikasi ayri bir is. Bu modul o zamana kadar
kopru gorevi gorur:

    ⚠️ SUNUCU YENIDEN BASLAYINCA RAPORLAR KAYBOLUR. Tek surecte, bellekte
    tutulur - birden fazla worker/replica calisan bir dagitimda calismaz
    (her worker kendi onbellegini gorur). Gelistirme ve tek-instance
    dagitim icin yeterlidir.

SINIR NEDEN VAR
----------------
Rapor boyutu genelde 50-150KB (grafik + birkac sayfa metin/tablo) ama
kullanicinin sinirsiz istek atmasi hafiza sizintisina donusur. `AZAMI_KAYIT`
asilinca EN ESKI kayit atilir (basit FIFO, LRU degil - trafik hacmi bunu
gerektirmiyor).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

#: Bellekte tutulacak azami rapor sayisi. Asilinca en eski kayit silinir.
AZAMI_KAYIT = 200

#: Bir kaydin azami omru (saniye). Kullanici raporu indirmeden kapatirsa
#: bellek sonsuza dek dolu kalmasin - 2 saat, ayni oturumda rahat indirmeye
#: yeter.
AZAMI_OMUR_SANIYE = 2 * 60 * 60


@dataclass
class _Kayit:
    pdf_bytes: bytes
    dosya_adi: str
    olusturulma: float


class _RaporOnbellegi:
    """Thread-safe, sinirli boyutlu, FIFO tahliyeli bellek ici onbellek.

    `threading.Lock` KULLANILIR (asyncio.Lock DEGIL): FastAPI'nin thread
    pool'unda calisan senkron kod da bu onbellege erisebilir; asyncio.Lock
    yalnizca event loop icinden kullanilabilirdi.
    """

    def __init__(self) -> None:
        self._kayitlar: dict[str, _Kayit] = {}
        self._sira: list[str] = []  # FIFO tahliye sirasi
        self._kilit = threading.Lock()

    def kaydet(self, anahtar: str, pdf_bytes: bytes, dosya_adi: str) -> None:
        with self._kilit:
            self._suresi_dolanlari_temizle()
            if anahtar not in self._kayitlar and len(self._sira) >= AZAMI_KAYIT:
                en_eski = self._sira.pop(0)
                self._kayitlar.pop(en_eski, None)

            self._kayitlar[anahtar] = _Kayit(
                pdf_bytes=pdf_bytes, dosya_adi=dosya_adi, olusturulma=time.monotonic()
            )
            if anahtar not in self._sira:
                self._sira.append(anahtar)

    def al(self, anahtar: str) -> tuple[bytes, str] | None:
        with self._kilit:
            kayit = self._kayitlar.get(anahtar)
            if kayit is None:
                return None
            if time.monotonic() - kayit.olusturulma > AZAMI_OMUR_SANIYE:
                self._kayitlar.pop(anahtar, None)
                if anahtar in self._sira:
                    self._sira.remove(anahtar)
                return None
            return kayit.pdf_bytes, kayit.dosya_adi

    def _suresi_dolanlari_temizle(self) -> None:
        """`kaydet()` icinde cagrilir - kilit ZATEN ALINMIS durumda olmali."""
        simdi = time.monotonic()
        suresi_dolan = [
            anahtar
            for anahtar, kayit in self._kayitlar.items()
            if simdi - kayit.olusturulma > AZAMI_OMUR_SANIYE
        ]
        for anahtar in suresi_dolan:
            self._kayitlar.pop(anahtar, None)
            if anahtar in self._sira:
                self._sira.remove(anahtar)


#: Uygulama genelinde TEK onbellek. Modul seviyesinde singleton - FastAPI
#: dependency injection'a gerek yok, `report_cache.kaydet(...)` her yerden
#: cagrilabilir.
_onbellek = _RaporOnbellegi()


def kaydet(anahtar: str, pdf_bytes: bytes, dosya_adi: str) -> None:
    """Raporu anahtar (genelde `message_id` veya `request_id`) ile kaydeder."""
    _onbellek.kaydet(anahtar, pdf_bytes, dosya_adi)


def al(anahtar: str) -> tuple[bytes, str] | None:
    """Kaydedilmis raporu doner; yok ya da suresi dolmussa `None`."""
    return _onbellek.al(anahtar)
