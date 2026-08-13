"""Piyasa verisi saglayicilari (mimari v4 bolum 8).

NEDEN SIMULATOR VARSAYILAN?
    BIST verisi ucretsiz kaynaklarda zaten 15 dk gecikmeli, yani "anlik" degil.
    Ucretsiz katmanlar ayda ~500 cagriya izin verir; dakikada bir guncelleme
    ayda ~43.000 cagri eder - kotanin ~80 kati. Cozum: API gunde 2-3 kez CAPA
    atar, simulator arayi doldurur. API cokerse veya kota biterse sistem
    simulatorle devam eder; demo gunu risk sifirlanir.

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
            `{asset_id, price}` kayitlari. Fiyat uretilemeyen varlik listeye
            EKLENMEZ (eski fiyat korunur).
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
    """Gercek piyasa API'si - HENUZ BAGLANMADI.

    ⚠️ Gercek saglayici kullanimi PO onayi ve lisans kontrolu gerektirir
    (mimari v4 bolum 8.3). Saglayici secildiginde YALNIZCA bu sinif yazilir;
    scheduler, tool'lar ve dashboard degismez.

    Uygulanirken ZORUNLU olanlar:
      * Gunluk cagri sayaci (`market_api_usage` tablosu) - kota asilirsa
        simulatore dus.
      * Timeout ve hata durumunda simulatore dusme (demo gunu kesinti olmasin).
      * Cekilen gercek fiyatin baz fiyat olarak yazilmasi (capa).
    """

    name = "api"

    def __init__(self, fallback: MarketDataProvider | None = None) -> None:
        self._fallback = fallback or SimulatedMarketProvider()

    async def next_prices(self, assets: list[dict]) -> list[dict]:
        logger.warning(
            "gercek piyasa API saglayicisi baglanmadi, simulatore dusuldu",
            extra={"provider": settings.market_data_provider},
        )
        return await self._fallback.next_prices(assets)


def build_provider(name: str | None = None) -> MarketDataProvider:
    """`MARKET_DATA_PROVIDER` ayarina gore saglayici uretir."""
    secim = (name or settings.market_data_provider or "simulated").lower()

    if secim in ("api", "hybrid"):
        return ApiMarketProvider()
    return SimulatedMarketProvider()
