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

    #: SQLAlchemy havuz siniri. VARSAYILANA BIRAKILAMAZ.
    #:
    #: SQLAlchemy varsayilani pool_size=5 + max_overflow=10, yani surec basina
    #: 15 baglanti. Supabase session pooler'inda TOPLAM 25 slot var ve ekip
    #: bunu paylasiyor - iki gelistirici backend acinca 30 > 25 olur ve havuz
    #: patlar. Patladiginda backend sessizce bellek ici veriye duser: sayfalar
    #: acilir ama portfoy, risk ve likit para BOS gorunur.
    #:
    #: 3 + 2 = surec basina en fazla 5 baglanti; bes gelistirici ayni anda
    #: calisabilir. Uygulamanin gercek es zamanlilik ihtiyaci bunun altinda.
    db_pool_size: int = 3
    db_max_overflow: int = 2

    #: Havuzdan baglanti beklerken asilma suresi (saniye).
    db_pool_timeout: int = 10

    #: Baglantilar bu sure sonunda yenilenir. Pooler kendi tarafinda kopardigi
    #: baglantiyi bize bildirmiyor; recycle olmadan olu baglanti havuzda kalir.
    db_pool_recycle_seconds: int = 900

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

    # --- Bulten gorselleri ------------------------------------------------
    # BOS birakilirsa haber gorseli eslestirme Pexels'e hic istek atmaz,
    # dogrudan kategori bazli sabit gorsellere duser (bkz. app/services/news.py
    # -> resolve_image). Ucretsiz Pexels hesabindan alinir.
    pexels_api_key: str = ""
    #: Sorgu-zamani embedding cagrisinin ust siniri. Ingestion'daki toplu
    #: embedding'den (backfill.py) FARKLI bir kaygi: kullanici akan bir sohbette
    #: bekliyor, bu yuzden kisa tutulur. Asilirsa/hata alirsa hibrit arama
    #: sessizce BM25'e (`SqlRagRepository.search`) duser - istek asla coker.
    rag_query_embedding_timeout_seconds: float = 3.0

    #: Bir chunk'in kaynak olarak GOSTERILEBILMESI icin gereken asgari kosinus
    #: benzerligi. `0` = filtre kapali (eski davranis).
    #:
    #: NEDEN GEREKLI: `rag.hybrid_search`'un dondurdugu `score` RRF'tir ve RANK
    #: tabanlidir - 1. sira her zaman 1/(60+1) eder, sonuc alakasiz olsa bile.
    #: Yani skor uzerinden "bu yeterince alakali mi?" sorusu YANITLANAMAZ. Esik
    #: bu yuzden ayri bir kolona (`cos_sim`) dayanir.
    #:
    #: NE COZER: BM25 ayagi `plainto_tsquery`yi OR'ladigi icin tek bir genel
    #: kelime ("sektor") alakasiz haberleri listeye sokuyordu - "bankacilik
    #: sektorundeki haberleri ozetle" sorgusu insaat/istihdam haberlerini kaynak
    #: gosteriyordu. Esik bunlari LLM'e gitmeden ve kullaniciya kaynak olarak
    #: gorunmeden eler.
    #:
    #: ⚠️ EMBEDDER YOKSA ETKISIZDIR. EMBEDDING_API_KEY/EMBEDDING_MODEL tanimli
    #: degilse arama saf BM25'e duser (`SqlRagRepository.search`), orada
    #: karsilastirilacak vektor yoktur ve esik UYGULANMAZ.
    #:
    #: ⚠️ DEGER KALIBRASYON ISTER. 0.40 seed veri uzerinde OLCULEREK secildi
    #: (havacilik sorgusu, DOC-002 vektoru referans alinarak):
    #:
    #:     DOC-002 havacilik haberi ......... 1.0000   <- konu
    #:     DOC-001 THYAO bilancosu .......... 0.4449   <- ILGILI (havayolu)
    #:     DOC-004 petrokimya raporu ........ 0.4420   <- sinirda (yakit)
    #:     DOC-006 bitcoin .................. 0.3414   <- alakasiz
    #:     DOC-003 SASA polyester ........... 0.3387   <- alakasiz
    #:     DOC-007 nvidia ................... 0.3083   <- alakasiz
    #:     DOC-005 gram altin ............... 0.2686   <- alakasiz
    #:
    #: 0.45 denendi ve ELENDI: THYAO'yu (0.4449) kesiyordu - havacilik sorusunda
    #: havayolu bilancosunu atmak acik bir yanlis negatif. 0.40 alakasiz kumeyi
    #: (<=0.3414) tamamen keser, ilgili olanlari birakir.
    #:
    #: ⚠️ BU OLCUM DOKUMAN-DOKUMAN benzerligidir. Gercek sorgular Cohere'e
    #: `input_type="search_query"` ile gider ve dokuman vektorleriyle ASIMETRIK
    #: eslesir - query->dokuman benzerlikleri tipik olarak DAHA DUSUKTUR. Canli
    #: veride bir kez dogrulayin: esik yuksek kalirsa "haber bulunamadi"
    #: yanitlari artar. Olcum sorgusu icin bkz.
    #: `db/migrations/017_hybrid_search_min_cosine.sql`.
    rag_min_similarity: float = 0.40

    # --- LLM ------------------------------------------------------------
    # KODA HICBIR MODEL ADI GOMULU DEGILDIR. Anahtar veya model tanimli
    # degilse ajanlar LLM'siz calisir (deterministik ozet/alinti uretirler) -
    # sistem ayaga kalkar, yalnizca yanit kalitesi duser.
    #
    # SAGLAYICI MODEL ADINDAN ANLASILIR (bkz. app/core/llm.py):
    #   gemini-3.5-flash-lite              -> gemini
    #   nvidia/nemotron-3-super-120b-a12b  -> nvidia (NIM)
    # NIM kimlikleri `yayinci/model` bicimindedir ve `/` icerir.
    llm_api_key: str = ""  # geriye donuk: Gemini anahtari (GEMINI_API_KEY yoksa)
    gemini_api_key: str = ""
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    #: Otomatik saglayici tespitini elle ezmek icin: "gemini" | "nvidia".
    #: Normalde BOS birakilir.
    llm_provider: str = ""
    default_model: str = ""

    #: Ornekleme sicakligi. Bu uygulamada DUSUK tutulmali: ajan promptlari
    #: "YENI SAYI URETME" ve "kaynakta olmayan bilgi uydurma" diyor, yuksek
    #: sicaklik ikisini de zorlastirir. (Not: Nemotron model karti tum
    #: gorevler icin 1.0 oneriyor - o modele gecerseniz olcup karar verin.)
    llm_temperature: float = 0.2
    llm_max_tokens: int = 2048
    #: NIM isteklerine dusunmeyi kapatan ek govde alani EKLENMESIN.
    #: Model o alani tanimayip 400 donerse true yapin (bkz. app/core/llm.py).
    llm_nvidia_extra_body_off: bool = False

    # Ajan bazli model secimi: ucuz model ajanlarda, guclu model synthesizer'da.
    # Ucretsiz API kotasini korumak icin bilincli bir tercihtir.
    portfolio_model: str = ""
    market_model: str = ""
    risk_model: str = ""
    synthesizer_model: str = ""  # en guclu model burada
    security_model: str = ""  # en kucuk/hizli model burada

    # --- Piyasa verisi katmani (mimari v4 bolum 8) ----------------------
    # Yalnizca Yahoo Finance'ten GERCEK fiyat kullanilir. Yahoo'ya
    # ulasilamazsa yeni fiyat yazilmaz ve son dogrulanmis fiyat korunur.
    market_data_provider: str = "api"

    #: Fiyat gorevinin calisma araligi. 5 dakika -> gunde 288 tick.
    #:
    #: DIKKAT: bir tick TEK istek DEGILDIR. yfinance her ticker icin ayri bir
    #: HTTP istegi atar (bkz. `app/market/yahoo.py`), yani 16 ticker x 288 tick
    #: = gunde ~4.608 istek. Bu araligi kisaltmak istek sayisini dogru orantili
    #: buyutur ve yfinance resmi bir API olmadigi icin engellenme riskini
    #: artirir.
    price_tick_seconds: int = 300

    #: Fiyat gorevi her N tick'te bir `live_prices`'a satir yazar.
    #: 1 = her tick (varsayilan ayarda 5 dakikada bir satir). Gun sonunda yalnizca son satir
    #: kalici fiyat gecmisine tasindigi icin bu cozunurluk makuldur.
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
    #: HESAP: 16 ticker x 288 tick = 4.608 istek/gun. Tavan yeniden
    #: baslatmalara, elle calistirmalara ve ayni veritabanini paylasan birden
    #: fazla gelistiriciye genis pay birakacak sekilde korunur.
    #: Onceki 400 degeri tick basina 1 sayildigi varsayimindan geliyordu ve
    #: gercek hacmin dortte birinden azdi - tavan hic tetiklenmiyordu.
    market_api_daily_quota: int = 7500

    # --- Otonom oneri motoru (AUT / D-02) --------------------------------
    #: Bu esigin ALTINDA kalan sinyal kullaniciya HIC ulasmaz; ic kayda
    #: alinir. Filtre SUNUCU tarafindadir - istemciye gonderilip orada
    #: gizlenmez (D-02 geliştirme notu 1).
    signal_confidence_threshold: float = 0.55

    #: BR-AUT-03: bir kullaniciya gunde en fazla kac oneri gonderilir.
    #: Kullanici bazinda `user_trading_limits` ile ezilebilir.
    #: Dokumandaki deger 3'tu; urun tarafi 4 istedi (3 kart ekranda tek basina
    #: seyrek duruyordu).
    max_daily_recommendations: int = 4

    #: BR-AUT-04: tarama bazli onerinin gecerlilik suresi (dakika).
    #: Haber bazli 60 dk olacaktir; haber hatti henuz yok (rag.documents
    #: .asset_id tum satirlarda BOS, bkz. docs/gelecek-isler.md madde 2).
    recommendation_ttl_minutes: int = 240

    #: FR-AUT-010: sessiz saatler - bu aralikta oneri URETILMEZ.
    #: Saat, `market_day_timezone` saat diliminde degerlendirilir.
    quiet_hours_start: int = 22
    quiet_hours_end: int = 8

    #: Tek tick'te en fazla kac kullanici taranir.
    #:
    #: NEDEN SINIR VAR: her kullanici icin en az bir, oneri uretilen her
    #: kullanici icin birkac veritabani gidis-donusu gerekiyor. 14 kullanicida
    #: ilk tur ~40 saniye suruyordu; fiyat gorevi bu sure boyunca bir sonraki
    #: tick'e gecemez. Kalan kullanicilar SONRAKI tick'te islenir - 5 dakikalik
    #: aralikta herkes birkac tur icinde kapsanir.
    recommendation_users_per_tick: int = 5

    #: Onerilen tutarin portfoy buyuklugune orani (ust sinir da limitlerden).
    recommendation_position_pct: float = 0.05

    # --- Bildirim kanali (mail koprusu) ----------------------------------
    # MAIL SU AN BAGLI DEGIL ve bu bir eksiklik degil, bilincli varsayilan.
    # Emir olaylari her durumda `notification_outbox` tablosuna yazilir;
    # asagidaki ayarlar tanimlanana kadar gonderim yapilmaz ve satirlar
    # SKIPPED olarak kapanir. SMTP geldiginde KOD degismez - yalnizca
    # NOTIFICATIONS_ENABLED=true ve SMTP_HOST tanimlanir.
    notifications_enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "Polifin <bildirim@polifin.local>"
    smtp_starttls: bool = True
    smtp_timeout_seconds: int = 10

    #: Bir olay bu yastan eskiyse gonderilmez, SKIPPED yazilir.
    #:
    #: NEDEN VAR: kanal haftalarca kapali kalip sonra acilirsa, birikmis tum
    #: gecmis gerceklesmeler tek seferde kullaniciya gider. Eski bir emir
    #: bildirimi kullanici icin bilgi degil gurultudur.
    notification_max_age_minutes: int = 60

    #: Tek turda islenecek azami outbox satiri (kuyruk tikanmasin diye).
    notification_batch_size: int = 50

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
    #
    # IKI KADEMELI. Neden tek bir sinir YETMIYOR:
    #
    #   Ajanlar once veriyi HESAPLAR (MCP tool'lari, hizli), sonra LLM'e
    #   yorum yazdirir (yavas), en sonda dondururler. Tek bir dis sinir
    #   `_execute`'un TAMAMINI sarar; LLM adimi butceyi asinca dis iptal
    #   devreye girer ve `return` satirina HIC ULASILAMAZ - yani ilk adimda
    #   zaten hesaplanmis DOGRU RAKAMLAR da cope gider. Ardindan risk ajani
    #   portfoy verisi bulamayip `tool_error` verir, sentezleyici "veriye
    #   ulasilamadi" der. Tek yavas LLM cagrisi, elde hazir duran veriyi
    #   goturur.
    #
    #   Ic sinir (`agent_llm_timeout_seconds`) YALNIZCA LLM cagrisini sarar
    #   (bkz. `BaseAgent.generate`). Sure asilirsa ajan kendi icinde yakalar,
    #   deterministik ozete duser ve HESAPLANMIS VERIYI DONDURUR. Dis sinir
    #   ise emniyet subabi olarak kalir: tool'lar ya da beklenmedik bir
    #   dongu asilirsa yine devreye girer.
    agent_timeout_seconds: int = 45

    #: Ajan ICINDEKI LLM cagrisinin ust siniri. 0 = `agent_timeout_seconds`
    #: uzerinden otomatik hesapla (bkz. `agent_llm_budget_seconds`).
    #:
    #: Elle deger verirken IC SINIR DIS SINIRDAN KUCUK OLMALI; aksi halde dis
    #: iptal once devreye girer ve iki kademeli yapinin tum anlami kaybolur.
    #: Bu yuzden deger `agent_llm_budget_seconds` icinde ayrica kirpilir.
    agent_llm_timeout_seconds: int = 0

    #: Sentez IC siniri: iki token ARASINDA en fazla ne kadar beklenir.
    #:
    #: Dis sinir (`synthesizer_timeout_seconds`) TOPLAM sureyi olcer ve uzun
    #: ama saglikli bir yaniti da keser. Asil belirti ise model ORTADA
    #: TAKILMASIDIR: token akisi durur, dis sinir dolana kadar bosuna beklenir
    #: ve kullanici yarim cumleyle kalir (canli testte olculdu, 27 Agustos
    #: 2026 - "Risk skoru 78/100 ile" diye kesildi).
    #:
    #: Ic sinir bu durumu ERKEN yakalar: akis durduysa beklemeyi birakip
    #: O ANA KADAR URETILEN METNI korur.
    synthesizer_stall_seconds: int = 20

    #: Sentez adiminin ust siniri. `asyncio.wait_for` TUM sentezi sarar, yani
    #: ilk token'a varis degil TAMAMLANMA suresidir.
    #:
    #: 40 sn'den yukseltildi: model secim testinde olculen iki beyin modeli de
    #: o siniri asiyordu ve asildiginda kullanici sessizce deterministik ozete
    #: dusuyordu. Sentez token token aktigi icin uzun sinir kotu bir bekleme
    #: yaratmaz - kullanici metnin yazildigini gorur.
    synthesizer_timeout_seconds: int = 90

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def email_enabled(self) -> bool:
        """Mail kanali gercekten gonderim yapabilir mi?

        Ikisi birden gerekir: ozellik acik OLMALI ve bir SMTP sunucusu
        tanimli OLMALI. Biri eksikse `NoopNotifier` secilir ve outbox
        satirlari SKIPPED olarak kapanir - sessizce birikmezler.
        """
        return bool(self.notifications_enabled and self.smtp_host.strip())

    @property
    def agent_llm_budget_seconds(self) -> int:
        """Ajan icindeki LLM cagrisina ayrilan sure.

        HER ZAMAN dis sinirdan (`agent_timeout_seconds`) KUCUKTUR. Aradaki
        pay bilincli: LLM'den once yapilan MCP tool cagrilari ve sonrasindaki
        deterministik ozet uretimi de dis sinirin icinde kalmali, yoksa ic
        sinir tetiklendigi halde dis iptal yine yetisip veriyi goturur.
        """
        pay = 5  # tool cagrilari + deterministik ozet + donus icin ayrilan pay
        tavan = max(3, self.agent_timeout_seconds - pay)

        if self.agent_llm_timeout_seconds > 0:
            return min(self.agent_llm_timeout_seconds, tavan)

        # Otomatik: dis sinirin %60'i. 45 sn -> 27 sn LLM, 18 sn pay.
        return max(3, min(int(self.agent_timeout_seconds * 0.6), tavan))

    @property
    def database_enabled(self) -> bool:
        """DB bagli mi? Bagli degilse repository'ler bellek ici veriye duser."""
        return bool(self.database_url.strip())

    def api_key_for(self, saglayici: str) -> str:
        """Saglayiciya ait API anahtari.

        `LLM_API_KEY` geriye donuk uyumluluk icin Gemini'nin yedegi olarak
        duruyor: eski `.env` dosyalari onu kullaniyordu.
        """
        if saglayici == "nvidia":
            return self.nvidia_api_key.strip()
        return (self.gemini_api_key or self.llm_api_key).strip()

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
