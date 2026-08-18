# Backend Kararları

Mimari oturumu yapılmadan önce backend ekibinin (Eren, Berat, Yağız) aldığı
kararlar. Oturumda girdi olarak kullanılacak; itiraz gelirse revize edilir.

## 1. Dil ve framework

**Python 3.13 + FastAPI**

Gerekçe: Ajanlar ve RAG Python ekosisteminde yazılacak. Backend de Python
olduğunda ajanlar doğrudan import edilip çağrılabiliyor, araya HTTP katmanı
girmiyor. Ayrıca otomatik Swagger dokümantasyonu, Pydantic doğrulaması ve
yerleşik async/streaming desteği geliyor.

Python 3.13 seçildi. `crypt` modülü bu sürümde kaldırıldığı için şifre
hash'lemede `passlib` yerine doğrudan `bcrypt` kullanılacak.

## 2. Klasör yapısı

```
app/
  api/routes/     endpoint tanımları
  auth/           JWT, get_current_user
  core/           errors, logging, llm
  orchestration/  AgentState + ortak orkestrasyon modelleri
  schemas/        REST request/response modelleri (Pydantic)
  services/       ekran verisi domain servisleri
  repositories/   veri erişim katmanı (base / in_memory / sql / deps)
  agents/         ajanlar
  engine/         orchestrator + wiring
  mcp/            client · server (tool grupları) · context
  market/         fiyat sağlayıcı + periyodik görev
  db/             async oturum yönetimi
  config.py       ayarlar
  main.py         uygulama girişi
```

> `orchestration/` eskiden `schema/` adındaydı ve `schemas/` ile yan yana
> duruyordu; tek harf farkı kalıcı karışıklık üretiyordu (mimari v4 §12).

Katmanlar arası kural: `routes` → `services` → `repositories`. Endpoint'ler
veriye doğrudan erişmez.

## 3. Veri erişimi — repository deseni

Veri erişimi `Protocol` ile tanımlı bir arayüzün arkasında.

- `repositories/base.py` — arayüz (sözleşme)
- `repositories/in_memory.py` — bellekteki sabit veri, şu an kullanılan
- `repositories/deps.py` — FastAPI `Depends` ile enjeksiyon

DB hazır olduğunda aynı arayüzü uygulayan `sql.py` yazılacak ve `deps.py`
içinde dönen sınıf değiştirilecek. Endpoint ve servis kodunda değişiklik
gerekmeyecek.

Bu desen frontend ve DB ekiplerinin birbirini beklemesini de engelliyor.

## 4. Hata formatı

Tüm hatalar aynı gövdeyle döner:

```json
{
  "error": {
    "code": "not_found",
    "message": "Kayit bulunamadi.",
    "request_id": "3f2b1c8e-9a4d-4e21-b7c5-0d6e8a1f2b3c"
  }
}
```

Tanımlı hata kodları:

| Kod | HTTP | Ne zaman |
|---|---|---|
| `not_found` | 404 | Kayıt bulunamadı |
| `business_rule_error` | 422 | İş kuralı ihlali |
| `validation_error` | 422 | İstek gövdesi geçersiz |
| `http_error` | değişken | FastAPI/Starlette kaynaklı |
| `internal_error` | 500 | Yakalanmayan hata |

Kendi hata sınıfları `core/errors.py` içinde: `AppError`, `NotFoundError`,
`BusinessRuleError`.

`request_id` hem gövdede hem `X-Request-ID` header'ında dönüyor (500 dahil).
Kullanıcı hata bildirdiğinde bu id ile loglarda tam o istek bulunabiliyor.
Yakalanmayan hatalarda traceback, request_id ile birlikte JSON loga yazılıyor.

`validation_error` yanıtı ayrıca `details` listesi içerir; her öğe `field`,
`message` ve `type` alanlarından oluşur. Frontend form hatalarını alan bazında
bu listeden gösterebilir. *(Öneri — şema sözleşmesinde frontend ile birlikte
kesinleşecek.)*

## 5. Endpoint isimlendirme

- Çoğul kaynak adı: `/portfolio`, `/market`, `/risk`
- Alt kaynak: `/portfolio/history`
- Aksiyonlar `/actions` altında: `/actions/rebalance`, `/actions/report`
- **Sürüm ön eki YOK: `/api/...`** *(güncellendi — mimari v4 §10.2)*

Gerekçe: tek sürüm var, dış tüketici yok. İleride gerekirse router prefix'lerine
tek satırla eklenir. Uçların tam listesi: [`api-sozlesmesi.md`](api-sozlesmesi.md).

## 5.1 JSON alan adlandırma

**Her yerde `snake_case`** *(mimari v4 §10.3)*. DB, orkestrasyon modelleri ve SSE
olayları zaten snake_case; REST'i camelCase yapmak frontend'e iki ayrı sözleşme
taşıtırdı.

## 6. Loglama

JSON formatlı, her satırda `request_id`. Middleware her isteği metot, path,
status ve süre (ms) ile logluyor.

## 7. Ajanların konumu

Öneri: ajanlar backend ile **aynı serviste** çalışsın, `app/agents/` altında
dursun ve fonksiyon çağrısıyla erişilsin.

Gerekçe: ikisi de Python, farklı dil gerekmiyor. Ayrı servis olması timeout
yönetimi, iki katmanlı streaming ve ek deployment yükü getiriyor; karşılığında
bu proje ölçeğinde kazanç sağlamıyor.

Karar mimari oturumunda kesinleşecek. Ayrı servis çıkarsa yalnızca
`services/orchestrator.py` içeriği değişir; endpoint ve frontend etkilenmez.

## 8. Kimlik doğrulama *(karar verildi)*

**JWT (HS256) + bcrypt.** Token içinde yalnızca `sub` (kullanıcı id) taşınır;
yetki kararı her istekte DB'deki güncel kayda göre verilir — böylece kullanıcı
silindiğinde elde kalmış token yetki taşımaya devam etmez.

`user_id` hiçbir zaman URL veya gövdede taşınmaz. `get_current_user`
bağımlılığı kimliği çözer ve **MCP contextvar'ına** yazar; MCP tool şemalarında
`user_id` parametresi YOKTUR (prompt injection başkasının verisini isteyemez).

Python 3.13'te `crypt` modülü kaldırıldığı için `passlib` yerine doğrudan
`bcrypt` kullanılıyor (bkz. §1).

> Product Backlog'da kullanıcı yönetimi kartı hâlâ yok; kayıt (register) ucu
> bilinçli olarak yazılmadı, dummy kullanıcılarla giriş yapılıyor
> (şifre: `demo1234`).

## 9. Risk skoru nerede hesaplanır *(karar verildi)*

**Backend'de, deterministik olarak** (`app/services/risk.py`); ajan yalnızca
yorumlar. Dashboard'daki RiskPanel ile sohbetteki risk ajanı aynı fonksiyonu
çağırır — iki yerde hesaplansaydı iki farklı sayı görünürdü.

## 10. Veri erişimi: DB varsa SQL, yoksa bellek *(karar verildi)*

`DATABASE_URL` doluysa `repositories/sql.py`, boşsa `repositories/in_memory.py`
devreye girer; seçim `repositories/deps.py` içinde **tek yerde** yapılır.
Endpoint, servis, MCP tool ve ajan kodu bu ayrımı görmez.

Bellek içi veri, `db/v5_schema_and_data.sql` seed'inin alt kümesidir ve **aynı
rakamları** üretir. Böylece CI Postgres'siz çalışır ve DB'siz gelişen bir
geliştirici DB'li geliştiriciyle aynı ekranı görür.

## 11. Açık konular

- LLM modeli seçilmedi — kodda hiçbir model adı sabit değil, `.env` boş olduğu
  sürece ajanlar LLM'siz çalışıyor.
- Embedding modeli seçilmedi — `rag_search` şimdilik yalnızca BM25 ayağıyla
  çalışıyor, hibrit arama karar sonrası açılacak.
- `/chat` isteğinde bağlam (seçili varlık, tarih aralığı) gönderilecek mi?
- "Yeniden Dengele" ve "Detaylı Rapor" düz metin mi, yapısal veri mi
  döndürecek? (`POST /api/reports` Sprint 4'e ertelendi.)
- Gerçek piyasa API sağlayıcısı: `MARKET_DATA_PROVIDER=simulated` varsayılan;
  `api`/`hybrid` PO onayı ve lisans kontrolü gerektiriyor.