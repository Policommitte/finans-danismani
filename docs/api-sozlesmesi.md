# API Sözleşmesi — Frontend ↔ Backend

*Kaynak: `SYSTEM_ARCHITECTURE_v4.md` §10. Bu dosya sözleşmenin **çalışan koda
karşılık gelen** hâlidir; kod ile doküman ayrışırsa kod düzeltilir.*

## Genel kurallar

| Konu | Karar |
|---|---|
| Ön ek | `/api` — **sürüm ön eki yok** (tek sürüm var, dış tüketici yok) |
| Alan adlandırma | Her yerde **`snake_case`** (REST, SSE, DB — tek sözleşme) |
| Para birimi | Tüm tutarlar TRY'ye normalize; alan adları `*_try` ile biter |
| Kimlik | `user_id` **hiçbir zaman** URL veya gövdede taşınmaz; JWT'den çözülür |
| Kimlik doğrulama | `Authorization: Bearer <token>` — `/health` ve `/api/auth/login` hariç zorunlu |
| İzlenebilirlik | Her yanıt `X-Request-ID` header'ı taşır; hata gövdesinde de aynı id vardır |

## Hata gövdesi

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

| Kod | HTTP | Ne zaman |
|---|---|---|
| `unauthorized` | 401 | Token yok / geçersiz / süresi dolmuş |
| `forbidden` | 403 | Kimlik doğru, yetki yok |
| `not_found` | 404 | Kayıt bulunamadı (başkasının kaydı da **404** döner) |
| `validation_error` | 422 | İstek gövdesi geçersiz — ek olarak `details[]` taşır |
| `business_rule_error` | 422 | İş kuralı ihlali |
| `internal_error` | 500 | Yakalanmayan hata |

`validation_error` yanıtındaki `details` listesi alan bazlı form hataları
içindir: `[{"field": "email", "message": "...", "type": "..."}]`.

> Başkasının kaydına erişimde bilinçli olarak **404** dönülür; 403 demek
> "bu id var ama senin değil" bilgisini sızdırırdı.

---

## REST uçları

### Kimlik

| Metot | Yol | Açıklama |
|---|---|---|
| POST | `/api/auth/login` | `{email, password}` → `{access_token, token_type, expires_in}` |
| GET | `/api/auth/me` | `{id, first_name, last_name, email, risk_tolerance, monthly_income}` |

Demo kullanıcılar: `mehmet@example.com` … şifre `demo1234`. Danışman
rolündeki demo hesap: `danisman@example.com` (aynı şifre) — yalnızca bu
hesap `/danisman` ekranına ve `/api/leads/*` uçlarına erişebilir.

### Dashboard

| Metot | Yol | Açıklama |
|---|---|---|
| GET | `/api/dashboard/summary` | İlk yükleme: `{summary, holdings[], allocation[], risk, movers[]}` |

Sekmeler ve tazeleme granüler uçları kullanır; bu uç yalnızca ilk açılışın
4 isteğini 1'e indirir.

### Portföy

| Metot | Yol | Yanıt |
|---|---|---|
| GET | `/api/portfolio/summary` | `{portfolio_id, holding_count, total_value_try, total_cost_try, total_pnl_try, total_pnl_pct}` |
| GET | `/api/portfolio/holdings` | `{items[], total_value_try}` |
| GET | `/api/portfolio/allocation` | `{items: [{asset_class, class_value_try, class_pct}]}` |
| GET | `/api/portfolio/transactions?limit=` | `{items[], limit}` |

`holdings[]` satırı: `symbol, asset_name, asset_class, currency, quantity,
average_buy_price, current_price, daily_change_pct, market_value_try,
cost_basis_try, pnl_try, pnl_pct`.

### Piyasa

| Metot | Yol | Yanıt |
|---|---|---|
| GET | `/api/market/assets?category=` | `{items: [{symbol, name, asset_class, currency, current_price, daily_change_pct, weekly_change_pct, yearly_change_pct}]}` |
| GET | `/api/market/history?symbol=&days=` | `{symbol, days, points: [{ts, price}]}` |
| POST | `/api/market/search` | `{query, top_k, sirket?, tip?}` → `{query, items: [{doc_id, baslik, sirket, symbol, tarih, tip, excerpt, score}]}` |

`sirket` filtresi hem sembol ("THYAO") hem unvan ("Türk Hava Yolları") ile
eşleşir.

### Risk

| Metot | Yol | Yanıt |
|---|---|---|
| GET | `/api/risk/profile` | `{risk_score, risk_level, risk_tolerance, tolerance_alignment, holding_count, top_class, top_class_pct, avg_volatility_pct, components, reasons[], suggestions[]}` |

`risk_score` 0–100 (yüksek = riskli) ve **deterministiktir**: backend'de
hesaplanır, sohbetteki risk ajanı da aynı fonksiyonu kullanır. Dashboard ile
sohbet **aynı** skoru gösterir.

### Lead motoru

| Metot | Yol | Yanıt |
|---|---|---|
| GET | `/api/leads/bsd-queue?limit=` | `{items[], count, scan}` |
| GET | `/api/leads/autonomous-queue?limit=` | `{items[], count, scan}` |
| GET | `/api/leads/excluded?limit=` | `{items[], count, scan}` |
| POST | `/api/leads/scan` | `{force?: bool}` → `LeadScanSummary` |

`items[]` satırı: `user_id, first_name, last_name, email, decision,
exclusion_reason, score, score_components, reasons[], total_value_try,
monthly_income, likit_para, days_since_activity, mail_gonderildi,
created_at`. `scan`, en son taramanın özetidir (`LeadScanSummary`), üç
liste ucunda da aynı şekilde döner.

Hedefleme kriteri **`likit_para`** (atıl banka bakiyesi) üzerindendir,
`total_value_try` değil: motor "hiç yatırım yapmamış ama bankada 120K-1M
TL arası parası duran" kullanıcıyı arar. `total_value_try > 0` olan
kullanıcı `already_invested` ile dışlanır — yani kuyruğa düşen her lead
için bu alan tanımı gereği `0`'dır.

`bsd-queue` ve `excluded` **en son taramanın** satırlarını döner.
`autonomous-queue` ise iki kaynağın birleşimidir: son 180 günde gerçekten
mail gönderilenler (`lead_contacts`) **artı** son taramada otonom kuyruğa
girip henüz mail gönderilememiş olanlar (kota/ardışık hata freni/Gmail
ayarsız). `mail_gonderildi` alanı bu ikisini ayırır.

`POST /scan`, asgari tarama aralığı dolmadıysa **hata değil**,
`skipped: true` + `skip_reason` ile normal bir yanıt döner (`force: true`
bu kontrolü atlar, soğutma kuralını atlamaz). `LEAD_ENGINE_ENABLED=false`
iken de **her zaman** `skipped: true` döner — `force: true` bunu da
atlamaz; motor kapalıyken hiçbir yoldan tarama çalışmaz. Bu ayarın
varsayılanı **`false`**'tur: ortak veritabanına bağlı her geliştiricinin
backend'i açar açmaz gerçek mail göndermesini önlemek için (bkz.
`.env.example`).

Bu uçlar yalnızca `role='advisor'` olan hesaplara açıktır — müşteri
hesapları 403 alır (bkz. `backend/app/auth/deps.py::CurrentAdvisor`).
Kayıt ucu olmadığı için danışman hesabı doğrudan SQL ile açılır: şifre
`bcrypt` ile hash'lenip (`python3 -c "import bcrypt, getpass; ..."` —
düz metin şifre komut satırına YAZILMAZ, `getpass` ile sorulur)
`INSERT INTO users (..., role) VALUES (..., 'advisor')` çalıştırılır.
Fresh/CI veritabanında hazır bir hesap vardır:
`danisman@example.com` · `demo1234`.


### Sohbet

| Metot | Yol | Yanıt |
|---|---|---|
| GET | `/api/conversations?limit=` | `{items: [{id, title, created_at, updated_at, message_count}]}` |
| GET | `/api/conversations/{id}/messages` | `{conversation_id, items: [{id, sender_role, message_content, meta, created_at}]}` |
| POST | `/api/chat/stream` | **SSE** — aşağıya bakın |

`meta` alanı asistan mesajlarında `{sources: [...], agent_errors: [...]}` taşır.

---

## SSE — `POST /api/chat/stream`

**İstek:** `{"message": "...", "conversation_id": 12 | null}`
`conversation_id` boş bırakılırsa yeni sohbet açılır ve id'si `meta` olayında
döner.

**Yanıt:** `text/event-stream`, her olay bir satır:

```
data: {"type":"meta","request_id":"…","conversation_id":12}

data: {"type":"status","stage":"security","message":"Sorgu guvenlik denetiminden gecti."}

data: {"type":"sources","items":[{"doc_id":"DOC-001","baslik":"…","sirket":"…","tarih":"2026-07-28","tip":"bilanco","score":0.3}]}

data: {"type":"token","content":"Portföyünüzün "}

data: {"type":"agent_error","agent":"market_research","error_type":"timeout"}

data: {"type":"error","code":"ORCHESTRATOR_FAILED","message":"…"}

data: {"type":"done","latency_ms":8420,"message_id":42,"mentioned_assets":["TUPRS"]}
```

| Olay | Ne zaman | Frontend davranışı |
|---|---|---|
| `meta` | Akış başlarken | `request_id` saklanır (hata bildiriminde kullanılır), `conversation_id` yeni sohbette id verir |
| `status` | Bir aşama tamamlandığında | Durum mesajı gösterilir. `stage`: `security` · `routing` · `agents` · `risk` · `synth` |
| `sources` | Kaynaklar hazır olduğunda | Kaynak kartları yerleştirilir |
| `token` | Yanıt üretilirken | Mesaja parça parça eklenir |
| `agent_error` | Tek ajan timeout/hata verdiğinde | **Kısmi başarısızlık uyarısı** — sohbet fail edilmez, akış devam eder |
| `error` | Graph hiç çalışamazsa | Genel hata mesajı, akış kapanır |
| `done` | Akış bittiğinde | Stream kapatılır; `message_id` ile mesaj kalıcı hâle getirilir; `mentioned_assets` doluysa cevabın altında varlık kartı gösterilir (bkz. `market_research` ajanının katalogla doğruladığı sembol) |

**Sıra garantisi:** `meta` ilk · `sources` ilk `token`'dan önce · `done` en son.

**Bilinmesi gerekenler**

- `[DONE]` sentinel'i **yoktur**; bitiş JSON `done` olayıdır (`message_id` ve
  `latency_ms` taşıyabilmesi için).
- Ayrı bir `final` olayı **yoktur**: reddedilen istek ve güvenli yanıt metni de
  `token` olarak gider — frontend'in tek render yolu olur.
- `error` olayı istisna metni **taşımaz**; yalnızca `code` + kullanıcıya
  gösterilecek `message`. Ayrıntı sunucu logunda `request_id` ile bulunur.
- `agent_error` bir hata olayı **değildir**: bir uzman veri üretemedi ama yanıt
  yine geliyor demektir.

### ⚠️ Tarayıcının `EventSource`'u kullanılamaz

Uç **POST** + `Authorization` header gerektiriyor; yerleşik `EventSource`
yalnızca GET destekler ve header gönderemez. `fetch` + `ReadableStream` ya da
`@microsoft/fetch-event-source` kullanılmalı.

```ts
const res = await fetch("/api/chat/stream", {
  method: "POST",
  headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
  body: JSON.stringify({ message, conversation_id: conversationId }),
});

const reader = res.body!.getReader();
// satırları "data: " ön ekine göre ayır, JSON.parse et, type'a göre dağıt
```

---

## Kapsam dışı (bu sürümde yok)

| Uç | Durum |
|---|---|
| `POST /api/reports` | Sprint 4 (FR-RISK-04) |
| `POST /api/actions/rebalance` | Kapsam dışı — gerçek emir/işlem yok |
| Kullanıcı kaydı (`/api/auth/register`) | Product Backlog'da kart yok |
