# Veritabanı şeması

`v5_schema_and_data.sql` — PostgreSQL 16+ / pgvector şeması, view'ları, hibrit arama
fonksiyonu ve dummy data. Eşlik ettiği doküman: [`../docs/SYSTEM_ARCHITECTURE_v3.md`](../docs/SYSTEM_ARCHITECTURE_v3.md).

## Çalıştırma

```bash
docker compose up -d db          # şema ilk kalkışta otomatik yüklenir
```

Şema yalnızca **boş** bir volume'de çalışır. Sıfırdan yüklemek için:

```bash
docker compose down -v && docker compose up -d db
```

Elle yüklemek:

```bash
psql -U finans -d finans -f db/v5_schema_and_data.sql
```

> Dosya baştaki `DROP` blokuyla kendi tablolarını siler — mevcut veriyi götürür.

## Bilinmesi gerekenler

| Konu | Not |
|---|---|
| `vector(1024)` | **İki yerde** geçer (`rag.chunks.embedding` ve `rag.hybrid_search`). Embedding modeli seçilince ikisi de aynı anda değişmeli. |
| `embedding` NULL | Örnek dokümanlarda boş; ingestion dolduracak. Boşken hibrit aramanın dense ayağı devre dışı, BM25 ayağı çalışır. |
| Hesaplar | `v_holdings_valued` → `v_portfolio_allocation` / `v_portfolio_summary`. Toplamlar **sadece** bu view'lardan okunur; ajan ve dashboard aynı kaynağı kullanır. |
| Para birimi | USD varlıklar `v_fx_rates` üzerinden TRY'ye çevrilir (`market_value_try`). |
| `price_history` | 90 gün × 4 saat ≈ 9.200 satır backfill. Yükleme birkaç saniye sürer. |
| Doğrulama | Dosyanın 14. bölümündeki sorgular. Portföy 1 (Mehmet) ≈ **1,64M TL** çıkmalı. |

## Test durumu

Şema PostgreSQL 16.13 + pgvector 0.6.0 üzerinde uçtan uca çalıştırıldı: hatasız
yüklendi, doğrulama sorguları (a) ve (b) boş döndü, `rag.hybrid_search` her iki
ayakla (dense + BM25) sonuç üretti.
