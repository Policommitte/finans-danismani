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
    """Gercek piyasa verisi - Yahoo Finance (`app/market/yahoo.py`).

    TEK ISTEK: Tum semboller `yf.download` ile TEK cagrida gelir. 15 dakikalik
    tick ile gunde ~96 cagri eder; sembol basina ayri istek atilsaydi ~1.500
    cagri olurdu ve yfinance resmi API olmadigi icin engellenme riski dogardi.

    YEDEGE DUSME (fail-safe): Asagidaki durumlarda simulatore dusulur ve bu
    GIZLENMEZ - `son_kaynak` "simulated" olur, boylece `price_history`'ye
    yanlislikla "api" etiketi yazilmaz:
      * Gunluk kota (`MARKET_API_DAILY_QUOTA`) dolduysa,
      * Yahoo zaman asimina ugrar veya hata verirse,
      * Hicbir sembol icin fiyat donmezse.

    Yahoo'nun dondugu fiyatlar `assets.current_price` uzerine yazilir; yani
    gercek fiyat ayni zamanda BAZ fiyattir (mimari v4 bolum 8.2 "capa").
    """

    name = "api"

    def __init__(
        self,
        fallback: MarketDataProvider | None = None,
        kota_deposu=None,
    ) -> None:
        """
        Args:
            fallback: Yahoo kullanilamadiginda devreye giren saglayici.
            kota_deposu: `get_api_usage_today` / `record_api_usage` sunan
                depo. `None` ise calisma aninda `get_market_repository()`
                kullanilir (testte enjekte edilebilsin diye parametre var).
        """
        self._fallback = fallback or SimulatedMarketProvider()
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
                "gunluk api kotasi doldu, simulatore dusuluyor",
                extra={"kullanilan": kullanilan, "tavan": tavan},
            )
            return True
        return False

    async def _kotayi_isle(self, cagri: int = 1) -> None:
        """Cagriyi `market_api_usage` tablosuna islenir. Hata yutulur."""
        try:
            await self._depo().record_api_usage(cagri)
        except Exception:  # noqa: BLE001 - denetim kaydi asil isi dusurmemeli
            logger.exception("api kullanim sayaci yazilamadi")

    async def _yedege_dus(self, assets: list[dict]) -> list[dict]:
        self.son_kaynak = self._fallback.name
        return await self._fallback.next_prices(assets)

    async def next_prices(self, assets: list[dict]) -> list[dict]:
        from app.market import yahoo

        self.son_kaynak = self.name

        if await self._kota_doldu_mu():
            return await self._yedege_dus(assets)

        # Yahoo'da karsiligi olmayan varliklar (orn. tahvil) hic istenmez.
        istenen = [a for a in assets if a.get("symbol") in yahoo.desteklenen_semboller()]
        if not istenen:
            logger.warning("yahoo'da karsiligi olan varlik yok, simulatore dusuluyor")
            return await self._yedege_dus(assets)

        try:
            fiyatlar = await yahoo.canli_fiyatlar([a["symbol"] for a in istenen])
        except Exception as exc:  # noqa: BLE001 - ag hatasi gorevi durdurmamali
            logger.warning(
                "yahoo canli fiyat alinamadi, simulatore dusuluyor",
                extra={"hata": f"{type(exc).__name__}: {exc}"},
            )
            await self._kotayi_isle()
            return await self._yedege_dus(assets)

        await self._kotayi_isle()

        if not fiyatlar:
            logger.warning("yahoo bos sonuc dondurdu, simulatore dusuluyor")
            return await self._yedege_dus(assets)

        # Fiyati alinamayan varlik listeye EKLENMEZ; eski fiyati korunur.
        return [
            {"asset_id": a["asset_id"], "price": fiyatlar[a["symbol"]]}
            for a in istenen
            if a["symbol"] in fiyatlar
        ]


def build_provider(name: str | None = None) -> MarketDataProvider:
    """`MARKET_DATA_PROVIDER` ayarina gore saglayici uretir."""
    secim = (name or settings.market_data_provider or "simulated").lower()

    if secim in ("api", "hybrid"):
        return ApiMarketProvider()
    return SimulatedMarketProvider()
