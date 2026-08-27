"""Piyasa verisi saglayicilari (mimari v4 bolum 8).

SIMULATOR POLITIKASI:
    Simulator yalnizca `MARKET_DATA_PROVIDER=simulated` acikca secildiginde
    calisir. API modunda Yahoo kullanilamazsa fiyat uretilmez ve veritabaninda
    bulunan son dogrulanmis fiyat korunur. Boylece portfoy degeri sahte bir
    fiyatla sessizce degismez.

Ajanlar ve MCP tool'lari hangi implementasyonun calistigini BILMEZ; ikisi de
`assets` tablosunu okur.
"""

from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class MarketDataProvider(ABC):
    """Fiyat kaynagi soyutlamasi."""

    name = "base"

    @abstractmethod
    async def next_prices(self, assets: list[dict]) -> list[dict]:
        """Bir sonraki fiyat kumesini uretir.

        Args:
            assets: `{asset_id, symbol, current_price, sim_volatility}` kayitlari.

        Returns:
            `{asset_id, price, previous_close?}` kayitlari. Gercek saglayici
            onceki piyasa kapanisini da iletir. Fiyat uretilemeyen varlik
            listeye EKLENMEZ (eski fiyat korunur).
        """
        ...


class SimulatedMarketProvider(MarketDataProvider):
    """Rastgele yuruyus simulatoru.

    SABIT SEED kullanir: prova edilen demo senaryosu sunumda birebir ayni
    cikar. Seed `MARKET_SIM_SEED` ile degistirilebilir.

    Fiyat asla sifirin altina inmez ve tek adimda baz fiyatin %20'sinden fazla
    sapmaz - grafik gercekci kalir.
    """

    name = "simulated"

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed if seed is not None else settings.market_sim_seed)

    async def next_prices(self, assets: list[dict]) -> list[dict]:
        updates: list[dict] = []
        for asset in assets:
            fiyat = float(asset.get("current_price") or 0)
            if fiyat <= 0:
                continue

            oynaklik = float(asset.get("sim_volatility") or 0.015)
            adim = self._random.gauss(0, oynaklik)
            yeni = fiyat * (1 + max(-0.2, min(adim, 0.2)))
            updates.append({"asset_id": asset["asset_id"], "price": round(max(yeni, 0.0001), 4)})

        return updates


class ApiMarketProvider(MarketDataProvider):
    """Gercek piyasa verisi - Yahoo Finance (`app/market/yahoo.py`).

    CAGRI SAYISI: `yf.download` tek bir fonksiyon cagrisi gibi gorunse de
    iceride HER TICKER icin ayri bir HTTP istegi atar (bkz. `yahoo.py` modul
    docstring'i). Bu yuzden kota sayacina tick basina `1` degil, o tick'te
    cekilen TICKER SAYISI islenir; aksi halde `market_api_usage` gercegin
    ~16'da birini gosterir ve `MARKET_API_DAILY_QUOTA` tavani hic tetiklenmez.

    VERI YOK POLITIKASI: Asagidaki durumlarda bos guncelleme doner; `assets`
    ve portfoy degerleri son dogrulanmis fiyatlarda kalir:
      * Gunluk kota (`MARKET_API_DAILY_QUOTA`) dolduysa,
      * Yahoo zaman asimina ugrar veya hata verirse,
      * Hicbir sembol icin fiyat donmezse.

    Yahoo'nun dondugu fiyatlar `assets.current_price` uzerine yazilir; yani
    gercek fiyat ayni zamanda BAZ fiyattir (mimari v4 bolum 8.2 "capa").
    """

    name = "api"

    def __init__(
        self,
        kota_deposu=None,
    ) -> None:
        """
        Args:
            kota_deposu: `get_api_usage_today` / `record_api_usage` sunan
                depo. `None` ise calisma aninda `get_market_repository()`
                kullanilir (testte enjekte edilebilsin diye parametre var).
        """
        self._kota_deposu = kota_deposu
        #: Son `next_prices` cagrisinda GERCEKTEN kullanilan kaynak.
        #: `price_history.source` bu degerden yazilir.
        self.son_kaynak: str = self.name

    def _depo(self):
        if self._kota_deposu is not None:
            return self._kota_deposu
        from app.repositories.deps import get_market_repository

        return get_market_repository()

    async def _kota_doldu_mu(self) -> bool:
        """Gunluk cagri tavani asildi mi? Sayac okunamazsa AKIS DURMAZ."""
        tavan = settings.market_api_daily_quota
        if tavan <= 0:
            return False

        try:
            kullanilan = await self._depo().get_api_usage_today()
        except Exception:  # noqa: BLE001 - sayac hatasi fiyat cekmeyi engellemesin
            logger.exception("api kota sayaci okunamadi, cagri yine de denenecek")
            return False

        if kullanilan >= tavan:
            logger.warning(
                "gunluk api kotasi doldu, son fiyatlar korunuyor",
                extra={"kullanilan": kullanilan, "tavan": tavan},
            )
            return True
        return False

    async def _kotayi_isle(self, cagri: int) -> None:
        """Yapilan HTTP istegi sayisini `market_api_usage`'a isler. Hata yutulur.

        `cagri` her zaman GERCEK ticker sayisidir; varsayilani bilincli olarak
        yoktur ki yanlislikla tekrar `1` islenmesin.
        """
        try:
            await self._depo().record_api_usage(cagri)
        except Exception:  # noqa: BLE001 - denetim kaydi asil isi dusurmemeli
            logger.exception("api kullanim sayaci yazilamadi")

    async def _veri_yok(self) -> list[dict]:
        """API fiyat uretemediyse mevcut dogrulanmis fiyatlari korur."""
        self.son_kaynak = "unavailable"
        return []

    async def next_prices(self, assets: list[dict]) -> list[dict]:
        from app.market import yahoo

        self.son_kaynak = self.name

        if await self._kota_doldu_mu():
            return await self._veri_yok()

        # Yahoo'da karsiligi olmayan varliklar (orn. tahvil) hic istenmez.
        istenen = [a for a in assets if a.get("symbol") in yahoo.desteklenen_semboller()]
        if not istenen:
            logger.warning("yahoo'da karsiligi olan varlik yok, fiyatlar korunuyor")
            return await self._veri_yok()

        semboller = [a["symbol"] for a in istenen]

        # Yahoo'ya atilacak GERCEK istek sayisi: her ticker ayri bir HTTP
        # istegidir. Hata durumunda da islenir - istekler zaten yapilmistir.
        cagri_sayisi = len(yahoo.gerekli_tickerlar(semboller))

        try:
            kotasyonlar = await yahoo.canli_kotasyonlar(semboller)
        except Exception as exc:  # noqa: BLE001 - ag hatasi gorevi durdurmamali
            logger.warning(
                "yahoo canli fiyat alinamadi, son fiyatlar korunuyor: %s: %s",
                type(exc).__name__,
                exc,
            )
            await self._kotayi_isle(cagri_sayisi)
            return await self._veri_yok()

        await self._kotayi_isle(cagri_sayisi)

        if not kotasyonlar:
            logger.warning("yahoo bos sonuc dondurdu, son fiyatlar korunuyor")
            return await self._veri_yok()

        # Fiyati alinamayan varlik listeye EKLENMEZ; eski fiyati korunur.
        updates: list[dict] = []
        for asset in istenen:
            quote = kotasyonlar.get(asset["symbol"])
            if not quote:
                continue
            update = {"asset_id": asset["asset_id"], "price": quote["price"]}
            if quote.get("previous_close"):
                update["previous_close"] = quote["previous_close"]
            updates.append(update)
        return updates


def build_provider(name: str | None = None) -> MarketDataProvider:
    """`MARKET_DATA_PROVIDER` ayarina gore saglayici uretir."""
    secim = (name or settings.market_data_provider or "simulated").lower()

    if secim in ("api", "hybrid"):
        return ApiMarketProvider()
    return SimulatedMarketProvider()
