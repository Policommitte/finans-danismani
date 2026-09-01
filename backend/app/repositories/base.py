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

from datetime import date
from typing import Protocol


class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> dict | None:
        """`password_hash` DAHIL kullanici kaydi (yalnizca auth katmani kullanir).

        Donen sozlukte `role` alani da vardir ('customer' | 'advisor'),
        `tckn_last4`/`birth_date`/`phone_number` de vardir - `tckn_hash`
        YOKTUR (password_hash gibi hicbir zaman disari donmez).
        """
        ...

    async def get_by_id(self, user_id: int) -> dict | None:
        """Profil bilgisi - `password_hash`/`tckn_hash` ICERMEZ, `role` alani vardir."""
        ...

    async def get_by_tckn_hash(self, tckn_hash: str) -> dict | None:
        """Ayni TCKN ile ikinci bir hesap acilip acilmadigini kontrol icin.

        `hash_tckn` DETERMINISTIK oldugundan (bkz. app/core/tckn.py) ayni
        TCKN her zaman ayni hash'i uretir - bu yuzden esitlik sorgusu
        anlamlidir (bcrypt'in aksine).
        """
        ...

    async def create(
        self,
        first_name: str,
        last_name: str,
        email: str,
        password_hash: str,
        tckn_hash: str,
        tckn_last4: str,
        birth_date: date,
        phone_number: str,
    ) -> dict:
        """Yeni kullanici olusturur; `onboarding_completed=false` ile baslar.

        `tckn_hash`/`tckn_last4` cagiran taraftan (route katmani, `password_hash`
        ile AYNI desen) ZATEN islenmis gelir - bu katman hash mantigi bilmez,
        yalnizca yazar. Donen sozlukte `password_hash`/`tckn_hash` YOKTUR.
        """
        ...

    async def complete_onboarding(self, user_id: int, risk_tolerance: str) -> dict | None:
        """`risk_tolerance` yazar ve `onboarding_completed`'i tek islemde true yapar."""
        ...

    async def mark_tour_seen(self, user_id: int) -> dict | None:
        """`has_seen_tour`'u true yapar - urun turu (ProductTour) bir daha
        otomatik acilmaz. Tur ilk kez KAPANDIGINDA (bitirilsin ya da
        gecilsin, fark etmez) cagrilir - bkz. app/api/routes/auth.py
        `/tour-seen`."""
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

    async def get_history_range(self, symbol: str, start: str, end: str) -> list[dict]:
        """Iki TARIH ARASI zaman serisi (eskiden yeniye, her iki uc DAHIL).

        `get_history` yalnizca "bugunden geriye N gun" penceresi verir; takvime
        bagli sorular ("gecmis yillarin yaz aylari") bunu kullanamaz - o pencere
        her zaman bugune yapisiktir. Ayni veriyi tarih araligiyla okumak icin
        bu metot var.

        Args:
            start / end: "YYYY-AA-GG".
        """
        ...

    async def get_candles(self, symbol: str, interval: str = "5m", days: int = 5) -> list[dict]:
        """Gercek OHLCV mumlari (eskiden yeniye)."""
        ...

    async def upsert_candles(self, candles: list[dict], source: str = "yahoo") -> int:
        """Sembol ve zaman araligina gore OHLCV mumlarini ekler/gunceller."""
        ...

    async def prune_candles(self, interval: str, keep_days: int) -> int:
        """Belirtilen araliktaki eski mumlari kayan saklama penceresinden siler."""
        ...

    async def get_assets_for_price_update(self) -> list[dict]:
        """Gercek fiyat gorevinin ihtiyaci: id, symbol ve mevcut fiyat."""
        ...

    async def apply_price_updates(self, updates: list[dict], write_live: bool, source: str) -> int:
        """Dogrulanmis fiyatlari yazar.

        `updates`: `{asset_id, price, previous_close?}` kayitlari. Gercek veri
        saglayicisi onceki piyasa kapanisini iletebilir.

        `assets` her cagirmada guncellenir. `write_live` True ise ayrica
        `live_prices` tablosuna GUN ICI bir satir eklenir - `price_history`'ye
        DEGIL. Gecmis tabloya yalnizca gun kapanisi yazilir
        (bkz. `close_out_day`).

        `source` yazilan satirin gercek kaynagini belirtir. Calisma zamaninda
        sentetik fiyat kabul edilmez.
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


class TradingRepository(Protocol):
    async def get_account(self, user_id: int) -> dict | None: ...

    async def get_order_context(self, user_id: int, symbol: str) -> dict | None: ...

    async def create_market_order(
        self,
        user_id: int,
        symbol: str,
        side: str,
        quantity: float,
        idempotency_key: str,
        commission_rate: float,
        order_type: str = "MARKET",
        limit_price: float | None = None,
        validity: str = "GTC",
        expires_at: object | None = None,
        stop_loss_price: float | None = None,
    ) -> dict: ...

    async def list_orders(self, user_id: int, limit: int = 20) -> list[dict]: ...

    async def cancel_order(self, user_id: int, order_id: int) -> dict: ...

    async def process_pending_orders(self, updates: list[dict], commission_rate: float) -> int: ...


class RecommendationRepository(Protocol):
    """Otonom oneri motorunun kalici durumu (AUT / D-02, D-07).

    Kural mantigi burada DEGIL `services/recommendation.py` ve
    `signals/engine.py` icindedir; burasi yalnizca okur ve yazar.
    """

    # --- kill-switch (FR-AUT-034) ---
    async def kill_switch_active(self) -> bool: ...

    async def set_kill_switch(self, active: bool, reason: str | None, actor: str) -> dict: ...

    # --- kullanici limitleri (FR-PRF-014, FR-AUT-026) ---
    async def get_limits(self, user_id: int) -> dict:
        """Satir yoksa VARSAYILAN limitleri doner - cagiran None beklemez."""
        ...

    async def upsert_limits(self, user_id: int, fields: dict) -> dict: ...

    # --- sinyal ---
    async def assets_for_scan(self) -> list[dict]: ...

    async def save_signals(self, signals: list[dict]) -> list[dict]:
        """Tumunu yazar, YALNIZCA yayinlanabilir olanlari id'leriyle doner."""
        ...

    # --- oneri uretimi ---
    async def autonomous_users(self) -> list[dict]:
        """Otonom akisi acik, portfoyu olan kullanicilar ve baglamlari."""
        ...

    async def daily_stats(self, user_id: int) -> dict:
        """BR-AUT-03 gunluk adet ve gunluk toplam tutar."""
        ...

    async def open_recommendation_asset_ids(self, user_id: int) -> list[int]:
        """Ayni varliga acik bir oneri varken ikincisi uretilmez."""
        ...

    async def create_recommendation(self, row: dict) -> dict: ...

    # --- okuma ---
    async def list_recommendations(
        self, user_id: int, status: str | None = None, limit: int = 50
    ) -> list[dict]: ...

    async def counts_by_status(self, user_id: int) -> dict: ...

    async def get_recommendation(self, user_id: int, recommendation_id: int) -> dict | None: ...

    # --- durum gecisleri (D-07) ---
    async def mark_viewed(self, user_id: int, recommendation_id: int) -> dict | None: ...

    async def reject(self, user_id: int, recommendation_id: int, reason: str) -> dict: ...

    async def attach_order(self, user_id: int, recommendation_id: int, order_id: int) -> dict:
        """BR-AUT-08: bir oneri en fazla BIR emir dogurur (tekil kisit)."""
        ...

    async def expire_due(self, now) -> int:
        """BR-AUT-04: TTL dolan acik onerileri kapatir."""
        ...

    async def halt_open(self, reason: str) -> int:
        """FR-AUT-034: kill-switch aktifken bekleyen onerileri durdurur."""
        ...

    # --- denetim (FR-AUT-032) ---
    async def log_audit(self, record: dict) -> None: ...


class NotificationRepository(Protocol):
    """`notification_outbox` okuma/kapatma sozlesmesi.

    Outbox satirini YAZAN taraf burasi DEGILDIR: yazim, emrin gerceklestigi
    transaction'in icinde `TradingRepository` tarafindan yapilir. Burasi
    yalnizca bekleyenleri alip sonucu isler.
    """

    async def claim_pending(self, limit: int, max_attempts: int = 5) -> list[dict]:
        """Bekleyen satirlari alir ve deneme sayacini artirir.

        Ayni anda birden fazla surec calisabilir; uygulama ayni satiri iki
        kez vermemelidir (SQL tarafinda `FOR UPDATE SKIP LOCKED`).
        """
        ...

    async def mark(self, outbox_id: int, status: str, error: str | None = None) -> None:
        """Satiri SENT / SKIPPED / FAILED olarak kapatir."""
        ...

    async def list_for_user(self, user_id: int, limit: int = 20) -> list[dict]:
        """Kullanicinin bildirim gecmisi (bildirim merkezi ekrani icin)."""
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

        Bu yol ayrica `cos_sim` (gercek kosinus benzerligi) dondurebilir;
        `score` RRF oldugu ve rank tabanli calistigi icin alaka esigi
        `cos_sim` uzerinden kurulur (bkz. `settings.rag_min_similarity`).
        BM25'e dusuldugunde alan bulunmaz - ZORUNLU DEGILDIR.
        """
        ...

    async def list_news(self, limit: int = 20, kategori: str | None = None) -> list[dict]:
        """Bulten sayfasi icin en yeni haberler (arama DEGIL, duz liste).

        `rag.documents` satirlarini tarihe gore azalan sirayla doner. Her
        satir: id, baslik, sirket, symbol, tarih, tip, kategori, kaynak_url,
        raw_text, image_url.
        """
        ...

    async def set_news_image(self, document_id: int, image_url: str) -> None:
        """Pexels'ten cozulen gorseli kalici olarak `image_url`'e yazar.

        Bu ayni zamanda cache mekanizmasidir: bir sonraki `list_news`
        cagrisinda satirin `image_url`'i artik dolu gelir, Pexels'e TEKRAR
        istek atilmaz (ucretsiz plan kotasini korur).
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


class ContestRepository(Protocol):
    """Sans Yatirimda oyunu veri erisimi.

    Tablolar: `topic`, `question`, `contest`, `contest_topic`,
    `contest_question`, `contest_agreement`, `participation`, `answer`,
    `payout`, `donation_purchase`, `user_powerup`, `powerup_purchase`.

    BILINCLI OLARAK YOK: rakip oyuncu simulasyonu (isim/skor/yuzde) icin
    hicbir metot. "Kac kisi yariste" / "%X dogru bildi" gibi gorunumler
    frontend'de KALMAYA DEVAM EDER - gercek rakip verisi degil, gorsel
    canlandirma. Bu katman yalnizca kullanicinin KENDI kaydini tasir.
    """

    # --- soru havuzu / oturum tanimi ---
    async def get_active_contest(self) -> dict | None:
        """Bu aksam (veya su an) acik olan `contest` satiri - yoksa None."""
        ...

    async def get_contest_topics(self, contest_id: int) -> list[dict]:
        """`contest_topic` uzerinden bu oturuma bagli calisma notu konulari."""
        ...

    async def get_contest_questions(self, contest_id: int) -> list[dict]:
        """`contest_question` sirasina gore bu oturumun SABIT soru listesi.

        Onemli: bu liste TUM katilimcilar icin AYNIDIR - eskiden frontend
        her oyuncu icin ayri rastgele 5 soru cekiyordu (bkz. `prepareQuestions`
        client tarafinda), bu artik gecerli degil; siralama backend'den gelir.
        """
        ...

    # --- kural onayi ---
    async def has_agreement(self, user_id: int) -> bool: ...

    async def create_agreement(self, user_id: int) -> None: ...

    # --- katilim ---
    async def count_participants(self, contest_id: int) -> int:
        """`participation` satir sayisi - GERCEK katilimci sayisi.

        Frontend'deki "297 kisi yariste" gorseli bununla KARISTIRILMAMALI:
        o sayi kucuk gercek kullanici tabaninda gerceci durmaz diye bilerek
        simule ediliyor. Bu metot yalnizca gercek sayiyi doner; simulasyonla
        harmanlamak (ya da harmanlamamak) servis katmaninin karari.
        """
        ...

    async def register_participation(self, contest_id: int, user_id: int) -> dict:
        """Yeni `participation` satiri acar (skor=0, won=false ile baslar)."""
        ...

    async def get_participation(self, participation_id: int) -> dict | None:
        """ID ile tek katilim. Servis katmani bunu YETKI kontrolu icin kullanir
        (`participation.user_id` istek sahibiyle ayni mi) - baska hicbir amacla
        cagrilmamali."""
        ...

    async def reset_todays_participation(self, user_id: int) -> None:
        """DEMO/GELISTIRME icin: kullanicinin BUGUNKU katilimini (+ cevaplari
        + odulu, cascade ile) siler - gunluk hak yeniden kullanilabilir olur.
        Servis katmani bunu `settings.app_env == "production"` iken REDDEDER;
        bu metot kendisi bir kontrol yapmaz, cagrildiginda kosulsuz siler."""
        ...

    async def submit_answer(
        self,
        participation_id: int,
        contest_question_id: int,
        selected_index: int | None,
        is_correct: bool,
        points_earned: int,
        elapsed_seconds: float,
    ) -> dict:
        """`answer` satiri yazar. `selected_index=None` -> sure doldu (timeout).

        `is_correct` / `points_earned` BURADA HESAPLANMAZ - dogru cevap ve
        puanlama formulu is kuralidir, servis katmaninin isi (bkz. LeadRepository
        docstring'indeki ayni ilke). Bu metot yalnizca SONUCU kaydeder.
        """
        ...

    async def list_answers(self, participation_id: int) -> list[dict]:
        """Bir katilimin TUM cevaplarini soru sirasina (`sort_order`) gore doner.

        Servis, yarismayi bitirirken (final_score, eliminated_at_question)
        istemciye GUVENMEK yerine buradan toplar - `submit_answer` her
        cagrida dogru sonucu zaten SUNUCU tarafinda hesaplayip yazdigi icin
        bu liste tek dogru kaynaktir.
        """
        ...

    async def finalize_participation(
        self,
        participation_id: int,
        won: bool,
        final_score: int,
        eliminated_at_question: int | None,
    ) -> dict:
        """`participation` satirini kapatir (skor, kazandi/kaybetti, elenilen soru)."""
        ...

    # --- odul ---
    async def create_payout(self, participation_id: int, payout_points: int) -> None:
        """`payout` satiri yazar - havuz payi, yarisma BITINCE BIR KEZ."""
        ...

    async def get_leaderboard(self, period: str) -> list[dict]:
        """Gercek katilimcilarin skorlarindan siralama (`period`: gunluk/haftalik/tumzamanlar)."""
        ...

    async def list_participations(self, user_id: int, limit: int = 20) -> list[dict]:
        """Kullanicinin gecmis katilimlari, EN YENI ustte.

        Her satirda o katilimin payout'u DAHIL (yoksa 0) - "Puan gecmisi"
        ekraninin TEK veri kaynagi; skor ile kazanilan puan ayri ayri
        hesaplanmaz, ikisi de burada BIRLIKTE doner.
        """
        ...

    # --- cuzdan (ayri tablo yok - turetilir) ---
    async def get_points_balance(self, user_id: int) -> int:
        """`payout` toplami eksi `powerup_purchase` + `donation_purchase` toplami."""
        ...

    # --- jokerler ---
    async def get_user_powerups(self, user_id: int) -> dict[str, int]:
        """`user_powerup` - joker basina mevcut adet, ör. `{"doublePoints": 1, "fiftyFifty": 0}`."""
        ...

    async def consume_powerup(self, user_id: int, kind: str) -> bool:
        """Elindeki adedi 1 azaltir (>0 ise). Adet zaten 0/yoksa False doner -
        yarisma icinde bir joker KULLANILDIGINDA cagrilir (satin alma DEGIL,
        o `record_powerup_purchase`'in isi). Boylece sayfa yenilense bile
        kullanilan joker geri gelmez."""
        ...

    async def record_powerup_purchase(self, user_id: int, kind: str, price_points: int) -> None:
        """`powerup_purchase` satiri yazar VE `user_powerup` adedini artirir (TEK islemde)."""
        ...

    async def list_powerup_purchases(self, user_id: int, limit: int = 20) -> list[dict]:
        """`powerup_purchase` satirlari, EN YENI ustte - 'Puan gecmisi' ekraninda
        harcama satiri olarak katilim/odul satirlariyla BIRLESTIRILIR (bkz.
        services/contest.py::get_history)."""
        ...

    # --- bagis / rozet ---
    async def get_user_badges(self, user_id: int) -> list[str]:
        """`donation_purchase` uzerinden kazanilan rozet etiketleri."""
        ...

    async def record_donation_purchase(
        self, user_id: int, donation_key: str, badge_label: str, price_points: int
    ) -> None:
        """`donation_purchase` satiri yazar - rozet KALICIDIR, geri alinmaz."""
        ...

    async def list_donation_purchases(self, user_id: int, limit: int = 20) -> list[dict]:
        """`donation_purchase` satirlari, EN YENI ustte - `list_powerup_purchases`
        ile ayni amaç, 'Puan gecmisi' harcama satirlari icin."""
        ...


class EconomicCalendarRepository(Protocol):
    """Turkiye'ye ozel ekonomik olaylar (`economic_events` tablosu).

    Global (yfinance kaynakli) olaylar BURADA DEGIL - onlar
    `app/services/economic_calendar.py::fetch_global_events` ile canli
    cekilir; ikisi `app/api/routes/economic_calendar.py`'de birlestirilir.
    """

    async def list_events(self, start: date, end: date) -> list[dict]:
        """`start`/`end` arasindaki (dahil) TR'ye ozel olaylar, tarihe gore artan."""
        ...
