"""Sahte bagimliliklar.

NEDEN `unittest.mock.AsyncMock` DEGIL
------------------------------------
`AsyncMock` her cagriya sessizce bir `Mock` doner. Repository sozlesmesi
degisip bir metodun adi degistiginde test COKMEZ - sahte nesne yeni adi da
memnuniyetle karsilar ve test yesil kalir. `StubRepo` yalnizca ACIKCA
tanimlanan metotlari tasir; tanimsiz bir metot cagrilirsa `AttributeError`
firlar ve sozlesme kaymasi ANINDA gorunur.
"""

from __future__ import annotations

import inspect
from typing import Any


class StubRepo:
    """Yalnizca verilen metotlari tasiyan sahte repository.

    Deger verilirse metot onu `await` edilebilir sekilde doner; cagrilabilir
    verilirse (senkron ya da async) oldugu gibi cagrilir.

        repo = StubRepo(get_holdings=[{"symbol": "THYAO"}], get_summary=None)
        await repo.get_holdings(1)      -> [{"symbol": "THYAO"}]
        repo.cagrilar["get_holdings"]   -> [((1,), {})]

    Tanimlanmayan bir metoda erisim `AttributeError` verir - sozlesme
    degisikligi sessizce gecmez.
    """

    def __init__(self, **metotlar: Any) -> None:
        #: {metot_adi: [(args, kwargs), ...]} - cagri kaydi.
        self.cagrilar: dict[str, list[tuple[tuple, dict]]] = {}
        for ad, deger in metotlar.items():
            setattr(self, ad, self._sar(ad, deger))

    def _sar(self, ad: str, deger: Any):
        async def _metot(*args, **kwargs):
            self.cagrilar.setdefault(ad, []).append((args, kwargs))
            if callable(deger):
                sonuc = deger(*args, **kwargs)
                if inspect.isawaitable(sonuc):
                    return await sonuc
                return sonuc
            return deger

        _metot.__name__ = ad
        return _metot

    def cagri_sayisi(self, ad: str) -> int:
        return len(self.cagrilar.get(ad, []))

    def son_cagri(self, ad: str) -> tuple[tuple, dict]:
        return self.cagrilar[ad][-1]


def repo_yamala(monkeypatch, **saglayicilar: Any) -> None:
    """`app.repositories.deps` saglayicilarini sahte repo'larla degistirir.

        repo_yamala(monkeypatch, get_portfolio_repository=StubRepo(...))

    `deps` icindeki isim yamalanir; servisler onu MODUL UZERINDEN cagirdigi
    icin (`from app.repositories.deps import get_x` yapan modullerde ayrica
    o modul de yamalanmalidir) her saglayici icin hem `deps` hem cagiran
    modul adi verilebilir.
    """
    from app.repositories import deps

    for ad, repo in saglayicilar.items():
        monkeypatch.setattr(deps, ad, lambda _repo=repo: _repo)


class SahteLLM:
    """`app.core.llm` istemcisinin yerine gecen minimal sahte.

    Gercek istemci `ainvoke` (tam yanit) ve `astream` (parca parca) sunar.
    Sahte ikisini de destekler ve gonderilen prompt'lari `istekler`
    listesinde tutar - "ajan LLM'e neyi sordu" iddiasi test edilebilsin.
    """

    def __init__(self, yanit: str = "sahte yanit", parcalar: list[str] | None = None) -> None:
        self.yanit = yanit
        self.parcalar = parcalar
        self.istekler: list[Any] = []

    async def ainvoke(self, mesajlar, **kwargs):
        self.istekler.append(mesajlar)
        return type("Yanit", (), {"content": self.yanit})()

    async def astream(self, mesajlar, **kwargs):
        self.istekler.append(mesajlar)
        for parca in self.parcalar or [self.yanit]:
            yield type("Parca", (), {"content": parca})()


class SahteEmbedder:
    """Deterministik, aga cikmayan embedder.

    Vektor metnin uzunlugundan turetilir: ayni metin ayni vektoru verir,
    farkli metinler farkli vektor verir - benzerlik siralamasi test
    edilebilir kalir.
    """

    def __init__(self, boyut: int = 8) -> None:
        self.boyut = boyut
        self.cagrilar: list[str] = []

    async def embed_query(self, metin: str) -> list[float]:
        self.cagrilar.append(metin)
        tohum = sum(ord(k) for k in metin) or 1
        return [((tohum * (i + 1)) % 97) / 97 for i in range(self.boyut)]


class SahtePiyasaSaglayici:
    """`son_kaynak = "api"` bildiren, aga cikmayan fiyat saglayici.

    Scheduler YALNIZCA gercek kaynakli tick'leri veritabanina yazar
    (`app/market/scheduler.py`); simulator tick'i hicbir sey yazmaz. YAZMA
    yolunu test edebilmek icin "gercek" gibi davranan bir saglayici sart.

    Carpani SABITTIR - simulatorun rastgeleligi beklentileri gereksiz yere
    kirilgan yapiyordu.
    """

    name = "api"
    son_kaynak = "api"

    def __init__(self, carpan: float = 1.01) -> None:
        self._carpan = carpan
        self.cagrilar = 0

    async def next_prices(self, assets: list[dict]) -> list[dict]:
        self.cagrilar += 1
        return [
            {
                "asset_id": a["asset_id"],
                "price": round(float(a["current_price"]) * self._carpan, 4),
            }
            for a in assets
            if float(a.get("current_price") or 0) > 0
        ]
