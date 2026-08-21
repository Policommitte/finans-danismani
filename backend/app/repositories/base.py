"""Veri erisim sozlesmeleri (Protocol).

Katman kurali: `routes -> services -> repositories`. Endpoint'ler ve MCP
tool'lari veriye DOGRUDAN erismez; hepsi bu protokollerin arkasindaki bir
implementasyona konusur.

Iki implementasyon vardir ve ikisi de AYNI sozlesmeyi uygular:

    sql.py        -> PostgreSQL (db/v5_schema_and_data.sql semasi) - BIRINCIL
    in_memory.py  -> bellek ici veri - YEDEK (DB tanimli degilse ya da
                     baglanti kurulamiyorsa devreye girer)

Secim `deps.py` icinde TEK yerde yapilir; servis ve endpoint kodu degismez.

Tum metodlar `async`: SQL implementasyonu asenkron surucu kullanir, bellek ici
implementasyon ise async imzayi tasiyip anlik doner. Boylece cagiran taraf
hangi implementasyonun bagli oldugunu bilmek zorunda kalmaz.

Parasal degerler her yerde TRY'ye normalize edilmis olarak doner ve alan adlari
`*_try` ile biter (mimari v4 bolum 6.4).
"""

from __future__ import annotations

from typing import Protocol


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> dict | None:
        """`password_hash` DAHIL kullanici kaydi (yalnizca auth katmani kullanir)."""
        ...

    async def get_by_id(self, user_id: int) -> dict | None:
        """Profil bilgisi - `password_hash` ICERMEZ."""
        ...


class PortfolioRepository(Protocol):
    async def get_default_portfolio_id(self, user_id: int) -> int | None: ...

    async def get_summary(self, user_id: int, portfolio_id: int | None = None) -> dict | None:
        """`v_portfolio_summary` satiri: toplam deger, maliyet, kar/zarar."""
        ...

    async def get_holdings(self, user_id: int, portfolio_id: int | None = None) -> list[dict]:
        """`v_holdings_valued` satirlari."""
        ...

    async def get_allocation(self, user_id: int, portfolio_id: int | None = None) -> list[dict]:
        """`v_portfolio_allocation` satirlari (varlik sinifi bazinda dagilim)."""
        ...

    async def get_transactions(
        self, user_id: int, portfolio_id: int | None = None, limit: int = 20
    ) -> list[dict]: ...

    async def get_performance_history(
        self, user_id: int, portfolio_id: int | None = None, hours: int = 24
    ) -> list[dict]:
        """Mevcut pozisyonlarin gercek fiyat gecmisiyle TL bazli degeri."""
        ...


class MarketRepository(Protocol):
    async def list_assets(self, category: str | None = None) -> list[dict]: ...

    async def get_quote(self, symbol: str) -> dict | None: ...

    async def get_history(self, symbol: str, days: int = 30) -> list[dict]:
        """Zaman serisi: `[{"ts": ..., "price": ...}, ...]` (eskiden yeniye)."""
        ...

    async def get_prices_for_simulation(self) -> list[dict]:
        """Fiyat gorevinin ihtiyaci: id, symbol, current_price, sim_volatility."""
        ...

    async def apply_price_updates(
        self, updates: list[dict], write_history: bool, source: str = "simulated"
    ) -> int:
        """Uretilen fiyatlari yazar.

        `updates`: `{asset_id, price, previous_close?}` kayitlari. Gercek veri
        saglayicisi onceki piyasa kapanisini iletir; simulator bu alani atlar.

        `source` `price_history.source` sutununa yazilir ve GERCEKTEN
        kullanilan kaynagi belirtmelidir ("api" | "simulated"). Gercek veri
        "simulated" etiketlenirse ileride hangi satirin guvenilir oldugu
        ayirt edilemez.
        """
        ...

    async def get_api_usage_today(self) -> int:
        """Bugun dis piyasa API'sine kac cagri yapildi (kota korumasi)."""
        ...

    async def record_api_usage(self, calls: int = 1) -> None:
        """Gunluk cagri sayacini artirir (`market_api_usage`)."""
        ...


class RagRepository(Protocol):
    async def search(
        self,
        query: str,
        top_k: int = 5,
        sirket: str | None = None,
        tip: str | None = None,
    ) -> list[dict]:
        """Haber/rapor arama. Kaynak metadata'si YAPILANDIRILMIS doner (FR-RAG-04)."""
        ...


class ChatRepository(Protocol):
    async def list_sessions(self, user_id: int, limit: int = 50) -> list[dict]: ...

    async def create_session(self, user_id: int, title: str) -> dict: ...

    async def get_session(self, session_id: int, user_id: int) -> dict | None:
        """Sahiplik kontrolu ICERIR: baska kullanicinin oturumu icin None doner."""
        ...

    async def list_messages(self, session_id: int, limit: int = 200) -> list[dict]: ...

    async def add_message(
        self,
        session_id: int,
        sender_role: str,
        content: str,
        meta: dict | None = None,
        request_id: str | None = None,
    ) -> dict: ...


class AuditRepository(Protocol):
    """Denetim kayitlari (mimari v4 bolum 9.1 - `tool_calls`, `security_events`).

    Denetim yazimi hicbir zaman istegi DUSURMEZ: implementasyonlar hatayi
    yutup loglar.
    """

    async def log_tool_call(self, record: dict) -> None: ...

    async def log_security_event(self, record: dict) -> None: ...
