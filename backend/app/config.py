"""Uygulama ayarlari.

Tum ortam degiskenleri tek yerde toplanir; kod icinde `os.getenv` cagrilmaz.
Ayarlarin cogu BOS varsayilanla gelir ve bos olmasi bir hata degildir: sistem
DB'siz, LLM'siz ve embedding modelsiz de uctan uca calisir (bkz. asagidaki
"kademeli calisma" notlari). Boylece ekip birbirini beklemez.
"""

from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Veritabani -----------------------------------------------------
    # BOS birakilirsa repository katmani bellek ici veriye duser (bkz.
    # `app/repositories/deps.py`). Testler ve DB'siz gelistirme boylece calisir.
    # Ornek: postgresql+psycopg://finans:finans@localhost:5432/finans
    database_url: str = ""
    db_echo: bool = False

    # --- Kimlik dogrulama ----------------------------------------------
    # Uretimde MUTLAKA ortam degiskeniyle verilmelidir; varsayilan yalnizca
    # yerel gelistirme icindir.
    jwt_secret: str = "gelistirme-icin-gecici-anahtar-en-az-32-bayt"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 720

    # --- RAG / Vector DB ------------------------------------------------
    # Model secildi: Cohere embed-v4 (output_dimension=1024 - vector(1024)
    # semasiyla degisiklik gerekmeden eslesir). EMBEDDING_API_KEY bos oldugu
    # surece `rag_search` yalnizca BM25 (tam eslesme) ayagiyla calisir;
    # hibrit arama (dense + BM25 -> RRF) anahtar tanimlaninca acilir.
    embedding_model: str = ""
    embedding_dim: int = 1024
    embedding_api_key: str = ""

    #: Sorgu-zamani embedding cagrisinin ust siniri. Ingestion'daki toplu
    #: embedding'den (backfill.py) FARKLI bir kaygi: kullanici akan bir sohbette
    #: bekliyor, bu yuzden kisa tutulur. Asilirsa/hata alirsa hibrit arama
    #: sessizce BM25'e (`SqlRagRepository.search`) duser - istek asla coker.
    rag_query_embedding_timeout_seconds: float = 3.0

    # --- LLM ------------------------------------------------------------
    # MODEL SECIMI HENUZ YAPILMADI: bu alanlar bilincli olarak BOS birakilir,
    # koda hicbir model adi gomulmez. Anahtar veya model tanimli degilse
    # ajanlar LLM'siz calisir (deterministik ozet/alinti uretirler) - sistem
    # ayaga kalkar, yalnizca yanit kalitesi duser.
    llm_api_key: str = ""
    default_model: str = ""

    # Ajan bazli model secimi: ucuz model ajanlarda, guclu model synthesizer'da.
    # Ucretsiz API kotasini korumak icin bilincli bir tercihtir.
    portfolio_model: str = ""
    market_model: str = ""
    risk_model: str = ""
    synthesizer_model: str = ""  # en guclu model burada
    security_model: str = ""  # en kucuk/hizli model burada

    # --- Piyasa verisi katmani (mimari v4 bolum 8) ----------------------
    # api       : Yahoo Finance'ten GERCEK fiyat (varsayilan)
    # simulated : rastgele yuruyus - yalnizca agsiz gelistirme/test icin
    #
    # "api" seciliyken Yahoo'ya ulasilamazsa son dogrulanmis fiyat korunur;
    # portfoy degeri simule fiyatlarla degistirilmez.
    #
    # ⚠️ SIMULE FIYAT VERITABANINA HIC YAZILMAZ - "simulated" bilerek
    # secilse bile. Scheduler kaynagi gorup tick'i atlar
    # (bkz. `app/market/scheduler.py` -> YAZILABILIR_KAYNAKLAR).
    market_data_provider: str = "api"

    #: Fiyat gorevinin calisma araligi. 15 dakika -> gunde 96 tick.
    #:
    #: DIKKAT: bir tick TEK istek DEGILDIR. yfinance her ticker icin ayri bir
    #: HTTP istegi atar (bkz. `app/market/yahoo.py`), yani 16 ticker x 96 tick
    #: = gunde ~1.536 istek. Bu araligi kisaltmak istek sayisini dogru orantili
    #: buyutur ve yfinance resmi bir API olmadigi icin engellenme riskini
    #: artirir.
    price_tick_seconds: int = 900

    market_sim_seed: int = 20260813

    #: Fiyat gorevi her N tick'te bir `live_prices`'a satir yazar.
    #: 1 = her tick (15 dakikada bir satir). Tick araligi 60 sn iken bu deger
    #: 5'ti; 15 dakikaya cikinca her tick'te yazmak makul cozunurluk verir.
    #:
    #: NOT: satir artik dogrudan `price_history`'ye DEGIL `live_prices`'a
    #: gider; `price_history`'ye gun bitiminde yalnizca gunun KAPANISI yazilir
    #: (bkz. `market_day_timezone` ve `app/market/scheduler.py`). Ortam
    #: degiskeninin adi geriye donuk uyumluluk icin ayni birakildi.
    price_history_every_n_ticks: int = 1

    #: Gun sinirinin belirlendigi saat dilimi. Bu saat diliminde gun
    #: degistiginde `live_prices`'taki o gune ait satirlarin SONUNCUSU
    #: `price_history`'ye gunun kapanisi olarak yazilir ve o gunun canli
    #: satirlari silinir.
    #:
    #: Neden ayar: veritabani sunucusu UTC calisiyor (Supabase oyle), ama
    #: kullanicilar ve BIST Turkiye saatinde. Gun sinirini UTC'ye birakmak
    #: "kapanis"i saat 03:00'e kaydirirdi.
    market_day_timezone: str = "Europe/Istanbul"

    #: Portfoy performans grafiginde guvenilir kabul edilen ilk fiyat kaydi.
    #: Bu esikten onceki gelistirme/simulasyon kayitlari grafige dahil edilmez.
    portfolio_performance_valid_from: datetime = datetime.fromisoformat("2026-08-21T10:41:00+03:00")

    #: Gunluk HTTP istegi tavani (kota korumasi). Sayac TICKER bazlidir.
    #:
    #: HESAP: 16 ticker x 96 tick = 1.536 istek/gun. Tavan yeniden
    #: baslatmalara, elle calistirmalara ve ayni veritabanini paylasan birden
    #: fazla gelistiriciye pay birakacak sekilde ~%60 ustune konuldu.
    #: Onceki 400 degeri tick basina 1 sayildigi varsayimindan geliyordu ve
    #: gercek hacmin dortte birinden azdi - tavan hic tetiklenmiyordu.
    market_api_daily_quota: int = 2500

    # --- Lead motoru (BSD kuyrugu / otonom davet) ------------------------
    # Esik degerleri (varlik, gelir, hareketsizlik, sogutma) burada DEGIL,
    # `app/services/lead_rules.py` icinde sabit - risk.py ile ayni desen
    # (bkz. ASSET_CLASS_RISK). Burada yalnizca ZAMANLAMA ve DIS SERVIS
    # (Gmail) ayarlari var.
    lead_engine_enabled: bool = False

    #: Acilistan sonra ilk taramanin baslamasi icin bekleme suresi. Fiyat
    #: gorevinin ilk tick'iyle ayni saniyede yarismasin diye kucuk bir pay.
    lead_scan_startup_delay_seconds: int = 10

    #: Bu dakikadan daha yeni bir tarama varsa, yeni istek (acilis ya da
    #: `force=false` ile POST) taramayi ATLAR. `run.py` `reload=True` ile
    #: calistigi icin (her dosya kaydinda uygulama yeniden baslar) bu deger
    #: olmadan bir gelistirme oturumu onlarca gereksiz tarama acardi.
    lead_scan_min_interval_minutes: int = 60

    # --- Gmail SMTP (bos ise mail GONDERILMEZ, uygulama dusmez) ----------
    gmail_sender_email: str = ""
    gmail_app_password: str = ""
    gmail_smtp_host: str = "smtp.gmail.com"
    gmail_smtp_port: int = 465
    gmail_timeout_seconds: int = 15

    #: Doluysa TUM lead mailleri bu adrese gider (asil alici govde icinde
    #: yazar). Seed kullanicilarinin adresleri @example.com (teslim
    #: edilemeyen ayrilmis alan adi) - demoda bu ayar pratikte ZORUNLUDUR.
    lead_email_redirect_to: str = ""

    # --- Timeout — bir ajan asilirsa tum istek dusmesin -------------------
    agent_timeout_seconds: int = 20
    synthesizer_timeout_seconds: int = 40

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_enabled(self) -> bool:
        """DB bagli mi? Bagli degilse repository'ler bellek ici veriye duser."""
        return bool(self.database_url.strip())

    def model_for(self, agent: str) -> str:
        """Ajana atanmis model adi; tanimli degilse `default_model`.

        Ikisi de bos olabilir - bu durumda LLM HIC olusturulmaz (bkz.
        `app.core.llm.get_llm_client`). Model karari verilene kadar normal
        calisma modu budur.
        """
        overrides = {
            "portfolio": self.portfolio_model,
            "market": self.market_model,
            "risk": self.risk_model,
            "synthesizer": self.synthesizer_model,
            "security": self.security_model,
        }
        return overrides.get(agent) or self.default_model


settings = Settings()
