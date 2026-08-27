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
        """`password_hash` DAHIL kullanici kaydi (yalnizca auth katmani kullanir).

        Donen sozlukte `role` alani da vardir ('customer' | 'advisor').
        """
        ...

    async def get_by_id(self, user_id: int) -> dict | None:
        """Profil bilgisi - `password_hash` ICERMEZ, `role` alani vardir."""
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
        self, updates: list[dict], write_live: bool, source: str = "simulated"
    ) -> int:
        """Uretilen fiyatlari yazar.

        `updates`: `{asset_id, price, previous_close?}` kayitlari. Gercek veri
        saglayicisi onceki piyasa kapanisini iletir; simulator bu alani atlar.

        `assets` her cagirmada guncellenir. `write_live` True ise ayrica
        `live_prices` tablosuna GUN ICI bir satir eklenir - `price_history`'ye
        DEGIL. Gecmis tabloya yalnizca gun kapanisi yazilir
        (bkz. `close_out_day`).

        `source` yazilan satirin kaynagini belirtir ve GERCEKTEN kullanilan
        kaynak olmalidir ("api" | "simulated"). Gercek veri "simulated"
        etiketlenirse ileride hangi satirin guvenilir oldugu ayirt edilemez;
        tersi ise sahte veriyi gercek gostermek olur.
        """
        ...

    async def pending_close_days(self) -> list[str]:
        """Kapanisi henuz yazilmamis gunler (`YYYY-AA-GG`, eskiden yeniye).

        `live_prices` icinde BUGUNDEN once kalan her gun kapanmayi bekliyor
        demektir; ayri bir durum tablosu tutulmaz. Uygulama hafta sonu
        boyunca kapali kalsa bile acilista bekleyen gunlerin hepsi burada
        gorunur.
        """
        ...

    async def close_out_day(self, day: str) -> int:
        """Gunu kapatir; kapanis yazilan varlik sayisini doner.

        TEK transaction icinde sirasiyla:
          1. o gunun SON canli fiyatini `price_history`'ye kapanis olarak yaz
          2. `assets.prev_close`'u bu kapanisa esitle
          3. o gune ait `live_prices` satirlarini sil

        Once yazip sonra silmek onemlidir: ters sirada bir hata veriyi
        geri donusu olmayan bicimde kaybettirir. `TRUNCATE` HICBIR ZAMAN
        kullanilmaz - yalnizca kapanan gunun satirlari silinir, o an akan
        yeni gunun satirlarina dokunulmaz.
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
        """Haber/rapor arama - yalnizca BM25 (tam eslesme). Kaynak metadata'si
        YAPILANDIRILMIS doner (FR-RAG-04)."""
        ...

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        sirket: str | None = None,
        tip: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[dict]:
        """Dense (anlamsal) + BM25 -> RRF birlesimi (`rag.hybrid_search`).

        `rag_search` MCP tool'unun cagirdigi BIRINCIL yol budur - `search()`
        yerini almaz, onun UZERINE kurulur: embedding modeli/anahtari tanimli
        degilse ya da sorgu-zamani embedding cagrisi basarisiz/zaman asimina
        ugrarsa DOGRUDAN `search()`'e (BM25) duser. Bu yuzden `search()` hala
        kalici bir sozlesmedir, cagrilan yer degistirmez.

        Donus seklinin `search()` ile AYNI olmasi zorunludur (FR-RAG-04):
        `chunk_id`, `doc_id`, `baslik`, `sirket`, `symbol`, `tarih`, `tip`,
        `content`, `score` - `mcp/server.py::_chunk_payload` ikisini de
        ayirt etmeden isler.
        """
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


class LeadRepository(Protocol):
    """Lead motoru veri erisimi (`lead_scans`, `lead_queue_entries`,
    `lead_contacts`, `v_lead_user_signals`).

    Kural DEGERLENDIRMESI burada YAPILMAZ - o `app/services/lead_rules.py`
    icinde. Bu katman yalnizca okur/yazar.
    """

    async def list_lead_signals(self) -> list[dict]:
        """`v_lead_user_signals` satirlari - kural motorunun girdisi."""
        ...

    async def last_contacted_map(self, cooldown_days: int) -> dict[int, object]:
        """Soğutma penceresi icindeki en son temas tarihleri.

        Yalnizca `channel = 'EMAIL'` VE `status = 'SENT'` olan, `cooldown_days`
        icinde kalan satirlar dahildir. Donen sozluk `{user_id: created_at}`
        bicimindedir; soğutma disindaki/hic temas edilmemis kullanicilar
        sozlukte YOKTUR.

        Kanal filtresi onemli: BSD kuyruguna dusmek artik `lead_contacts`'a
        kayit acmaz, ama eski taramalardan kalmis `BSD_QUEUE` satirlari
        veritabaninda durabilir - filtre olmasa o kisiler hic mail
        almadiklari halde 180 gun boyunca sogutmada kalirdi.
        """
        ...

    async def start_scan(self, trigger: str) -> int:
        """Yeni bir `lead_scans` satiri acar, id'sini doner."""
        ...

    async def finish_scan(
        self,
        scan_id: int,
        counts: dict[str, int],
        error: str | None = None,
    ) -> None:
        """`lead_scans` satirini `finished_at` + sayaclarla kapatir."""
        ...

    async def latest_scan(self) -> dict | None:
        """En son tamamlanan (`finished_at IS NOT NULL`) tarama."""
        ...

    async def minutes_since_last_scan(self) -> float | None:
        """Son taramanin uzerinden gecen dakika; hic tarama yoksa None."""
        ...

    async def record_decision(self, scan_id: int, entry: dict) -> None:
        """Bir kullanici icin `lead_queue_entries`'e tek satir yazar.

        `entry`: `user_id`, `decision`, `exclusion_reason`, `score`,
        `score_components`, `reasons`, `total_value_try`, `monthly_income`,
        `days_since_activity` alanlarini tasir.
        """
        ...

    async def claim_email_contact(
        self, user_id: int, scan_id: int, to_email: str, subject: str
    ) -> int | None:
        """Gunluk tekillik iddiasi (once-claim-sonra-gonder deseni).

        `lead_contacts`'a `status='SENT'` ile INSERT dener. Ayni kullaniciya
        bugun zaten bir SENT satiri varsa (kismi unique index engeller)
        `None` doner - cagiran taraf gondermeden vazgecmeli. Basarili olursa
        yeni satirin id'sini doner.
        """
        ...

    async def mark_contact_failed(self, contact_id: int, error: str) -> None:
        """Basarisiz gonderimde claim'i serbest birakir (`status='FAILED'`).

        Kismi unique index yalnizca `status='SENT'`'e baktigi icin bu,
        sonraki taramada ayni kullaniciya tekrar denenebilmesini saglar.
        """
        ...

    async def mark_contact_skipped(self, contact_id: int) -> None:
        """Gmail yapilandirilmamisken claim'i serbest birakir (`status='SKIPPED'`).

        `mark_contact_failed` ile ayni amac: kismi unique index yalnizca
        `status='SENT'`'e baktigi icin, mail hic denenmediyse claim'i
        kalici olarak "gonderildi" gibi birakmamak lazim - Gmail ayarlari
        yapilandirildiginda sonraki taramada tekrar denenebilsin.
        """
        ...

    async def list_queue(self, decision: str, limit: int = 100) -> list[dict]:
        """En son taramadaki `decision` (`BSD`|`AUTONOMOUS`|`EXCLUDED`)
        satirlarini, kullanici bilgisiyle birlikte doner."""
        ...

    async def list_emailed(self, days: int, limit: int = 100) -> list[dict]:
        """Son `days` gun icinde GERCEKTEN mail gonderilen kullanicilar.

        `list_queue("AUTONOMOUS", ...)`'dan farki: kaynak `lead_contacts`
        (fiilen gonderilmis mailler), en son tarama DEGIL. Mail gonderilen
        kisi sogutma penceresine girdigi icin sonraki taramalarda
        `EXCLUDED` olur ve son taramanin AUTONOMOUS listesinden duserdi -
        oysa danisman "kime mail gitti" listesini gormeye devam etmeli.

        Kullanici basina EN SON mail kaydi doner; siralama gonderim
        tarihine gore (en yeni ustte).
        """
        ...
