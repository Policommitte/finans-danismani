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
  core/           errors, logging
  repositories/   veri erişim katmanı
  schemas/        Pydantic request/response modelleri
  services/       iş mantığı
  agents/         ajanlar
  mcp/            MCP server
  db/             DB oturumu — şu an devre dışı
  config.py       ayarlar
  main.py         uygulama girişi
```

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
- Sürüm ön eki kullanılacak: `/api/v1/...`

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

## 8. Açık konular

- Kimlik doğrulama henüz yok. Product Backlog'da kullanıcı yönetimi kartı
  bulunmuyor, eklenmesi gerekiyor.
- Risk skorunun nerede hesaplanacağı netleşmedi. Öneri: sayı backend'de
  deterministik olarak hesaplansın, ajan yalnızca yorumlasın.
- `/chat` isteğinde bağlam (seçili varlık, tarih aralığı) gönderilecek mi?
- "Yeniden Dengele" ve "Detaylı Rapor" düz metin mi, yapısal veri mi
  döndürecek?
- Piyasa verisi gerçek kaynaktan mı, dummy generator'dan mı gelecek?