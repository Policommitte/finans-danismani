# borsa-verisi — Yahoo Finance → PostgreSQL veri toplama

Veritabanındaki **2 · Varlık & Piyasa** tablolarını gerçek piyasa verisiyle
**bir kez** dolduran bağımsız betik. Amaç: ajanları sentetik dummy data yerine
gerçek fiyatlar üzerinde test edebilmek.

> **Bu klasör uygulamanın parçası değildir.** `backend/app/` içindeki hiçbir
> dosyaya dokunmaz, import edilmez, CI'da çalışmaz. Periyodik fiyat güncellemesi
> ayrı bir sorumluluktur ve `backend/app/market/scheduler.py` içindedir.

---

## Ne yapar

| Tablo | İşlem | Ne yazılır |
|---|---|---|
| `assets` | UPDATE | `current_price`, `prev_close`, `daily/weekly/yearly_change_pct`, `price_updated_at` |
| `price_history` | INSERT | Günlük kapanışlar, `source='api'` |
| `market_api_usage` | UPSERT | Günlük çağrı sayacı |

**Dokunulmayanlar:** portföy, sohbet, RAG, kullanıcı tabloları. `assets`
tablosunda da yalnızca fiyat sütunları güncellenir — `symbol`, `name`,
`category_id`, `currency` değiştirilmez. Veritabanında olmayan bir sembol
gelirse **atlanır**, yeni varlık yaratılmaz.

---

## Kurulum ve çalıştırma

```bash
cd borsa-verisi
pip install -r requirements.txt
```

```bash
python collect.py --kuru-calistir
```

Önce **her zaman** kuru çalıştırma yapın: Yahoo'dan gerçek veriyi çeker,
veritabanına ne yazılacağını gösterir, **hiçbir şey yazmaz**. Veritabanı
sürücüsü kurulu olmasa bile çalışır.

```bash
python collect.py
```

Gerçek çalıştırma. Bağlantı adresi sırayla: `--dsn` → `DATABASE_URL` ortam
değişkeni → `postgresql://finans:finans@localhost:5432/finans`.

Tüm yazma **tek işlemde** yapılır: bir hata olursa hiçbir değişiklik kalıcı
olmaz (rollback).

### Seçenekler

| Bayrak | Ne yapar |
|---|---|
| `--kuru-calistir` | Veritabanına yazmaz, yalnızca gösterir |
| `--kategori STOCK GOLD` | Yalnızca seçilen grupları çeker |
| `--period 5y` | Yahoo geçmiş aralığı (varsayılan `2y`) |
| `--gecmis-yok` | `price_history`'ye yazmaz, sadece `assets` |
| `--volatilite-guncelle` | `sim_volatility`'yi gerçek oynaklıkla günceller |
| `--dsn ...` | PostgreSQL adresi |

---

## Sembol eşlemesi

`symbols.py` tek kaynaktır. 16 varlık eşlenmiştir (13'ü varsayılan çalıştırmada, 3 kripto `--kategori CRYPTO` ile):

| Grup | Semboller | Yahoo |
|---|---|---|
| `STOCK` | THYAO, GARAN, TCELL, SASA, ASELS, EREGL | `.IS` eki (`THYAO.IS`) |
| `FOREX` | USD/TRY, EUR/TRY | `USDTRY=X`, `EURTRY=X` |
| `GOLD` | GRAM_ALTIN, GUMUS | **türetilmiş** — aşağı bakın |
| `USA_STOCK` | AAPL, TSLA, NVDA | doğrudan |
| `CRYPTO` | BTC, ETH, SOL | `BTC-USD` — varsayılanda **kapalı**, `--kategori CRYPTO` ile çekilir |

> **`TR10Y` (tahvil) veritabanından tamamen silindi** (16 Ağustos 2026).
> Yahoo'da Türkiye 10 yıllık tahvil getirisi için sürekli/güvenilir veri
> dönen bir sembol yoktu; dummy veri olarak kalması yerine kaldırılması
> tercih edildi. Silmeden önce bağlı portföy/işlem/alarm/izleme kaydı
> olmadığı doğrulandı. Tahvil verisi ileride ayrı bir kaynaktan ele alınabilir.

### Altın ve gümüş neden türetiliyor?

Yahoo'da "TRY cinsinden gram altın" diye bir sembol **yoktur**. Fiyat şöyle
hesaplanır:

```
gram_TRY = (ons_USD / 31.1034768) × USD/TRY
```

Örnek: 4458.10 USD/ons ÷ 31.1034768 = 143.33 USD/gram × 47.8960 = **6.864 TL/gram**

Kaynak `GC=F` (COMEX altın vadeli) ve `SI=F` (gümüş vadeli). Bu **saf maden**
değeridir — kuyumcu makası ve işçilik payı **içermez**, bu yüzden kuyumcuda
görülen fiyattan bir miktar düşüktür. Vadeli fiyat spot fiyattan küçük bir
primle işlem görür.

Altın ve gümüş için USD/TRY serisi bir kez çekilip yeniden kullanılır. İki
seri farklı günlerde işlem görebildiği için (vadeli piyasa Pazar akşamı açılır,
döviz neredeyse kesintisiz) kur serisi altın tarihlerine hizalanır ve boşluklar
**son bilinen kurla** doldurulur — kur uydurulmaz.

---

## Metrik kuralları

Şemadaki (`db/v5_schema_and_data.sql` bölüm 2) sözleşmeye uyulur:

| Alan | Nasıl hesaplanır |
|---|---|
| `current_price` | Serinin son kapanışı |
| `prev_close` | Bir önceki kapanış |
| `daily_change_pct` | `(current / prev_close − 1) × 100` |
| `weekly_change_pct` | 7 **takvim** günü öncesine göre |
| `yearly_change_pct` | 365 **takvim** günü öncesine göre |
| `price_updated_at` | Yazma anında `now()` |

Şemadaki `prev_close = current_price / (1 + daily_change_pct/100)` bağı
korunur — iki değer de aynı seriden türer.

> ⚠️ **Takvim günü ≠ işlem günü.** Borsa hafta sonu ve tatilde kapalıdır;
> "7 satır geriye git" yanlış sonuç verir. Referans, hedef tarihteki **veya
> ondan önceki** en yakın işlem günüdür. Seri o tarihe kadar geriye gitmiyorsa
> değer `None` kalır — **uydurulmaz**.

> ⚠️ **`--period 1y` tuzağı.** Yıllık değişim 365 gün öncesine bakar; `1y`
> verilirse seri tam o tarihte başladığı için referans bulunamaz ve yıllık
> değişim boş kalır. Varsayılan bu yüzden `2y`'dir.

`sim_volatility` **varsayılan olarak güncellenmez**: bu alan simülatörün adım
büyüklüğüdür, gerçek veriyle değiştirmek demo davranışını değiştirir.
`--volatilite-guncelle` ile açıkça istenebilir.

---

## Bilinmesi gerekenler

**Gerçek fiyatlar dummy data'dan çok farklı.** Örneğin şemada `SASA` 45.20 TL,
gerçekte ~2.36 TL (sermaye artırımı); `GRAM_ALTIN` 2.550 TL, gerçekte ~6.858 TL;
`USD/TRY` 33.55, gerçekte ~47.90. Bu betik çalıştıktan sonra **portföy
değerleri tamamen değişir** — `db/README.md`'deki "Portföy 1 ≈ 1,64M TL"
doğrulaması artık tutmayacaktır. Beklenen davranıştır.

**Sentetik `backfill` satırları silinmez.** `price_history` içinde eski
`source='backfill'` satırları (90 gün × 4 saat) durmaya devam eder ve yeni
`source='api'` satırlarıyla birlikte grafikte görünür. İstenirse elle
temizlenebilir:

```sql
DELETE FROM price_history WHERE source = 'backfill';
```

Betik bu silmeyi **kendisi yapmaz** — veri silmek geri alınamaz.

**Tekrar çalıştırılabilir.** `price_history` `ON CONFLICT (asset_id, ts)` ile
yazılır, aynı gün ikinci kez çalıştırmak hata vermez.

**Yahoo resmî bir API değildir.** `yfinance` Yahoo'nun genel uçlarını kullanır;
sembol adları ve veri sürekliliği garanti değildir. Art arda hızlı istek geçici
engellemeye yol açabildiği için çağrılar arasında 0.4 sn beklenir.

---

## Testler

```bash
python -m pytest tests/ -q
```

44 test — **ağ ve veritabanı gerektirmez**. Hesaplama mantığını (takvim günü
referansı, altın türetmesi, yıllık değişim sınırı) ve SQL sözleşmesini
(kapsam dışı tabloya yazmama, tekrar çalıştırılabilirlik) sabitler.

Testler **CI'da da koşar**: `.github/workflows/backend-ci.yml` içindeki
`borsa-verisi` job'ı ruff + black + pytest çalıştırır. (Backend job'ının her
adımı `working-directory: backend` olduğu için bu klasör ayrı bir job ister —
aksi halde buradaki kod hiç kontrol edilmezdi.)

> Sembol eşlemesi (`symbols.py`) backend'deki `app/market/yahoo.py` ile aynı
> tabloyu tutar. İkisi elle senkron tutulur; ayrışırlarsa backend'deki
> `test_sembol_tablosu_borsa_verisi_ile_ayni` testi CI'da hata verir.
