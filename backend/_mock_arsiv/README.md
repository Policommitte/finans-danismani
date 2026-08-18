# `_mock_arsiv/` — karantinaya alinan sahte MCP sunuculari

Bu klasor **calisan kodun parcasi DEGILDIR**. Icindeki hicbir modul `app/`
altindan import edilmez. Ihtiyac kalmadigina karar verildiginde tek islemle
silinebilir:

```bash
rm -rf backend/_mock_arsiv
```

Silindiginde geride kirik referans kalmaz.

## Icerik

| Arsivdeki dosya | Eski yeri | Ne yapiyordu |
|---|---|---|
| `mcp/mock.py` | `app/mcp/mock.py` | `build_mock_mcp_client()` — asagidaki iki sahte sunucuyu kaydeden MCP istemcisi. |
| `mcp/servers/rag.py` | `app/mcp/servers/rag.py` | `_MOCK_CHUNKS`: elle yazilmis 3 haber/KAP metni. |
| `mcp/servers/market.py` | `app/mcp/servers/market.py` | `_MOCK_QUOTES` / `_MOCK_DISCLOSURES`: THYAO ve ASELS icin sabit fiyat ve bildirim. |

## Neden bunlar gereksiz

Bu dosyalar tool katmaninin IKINCI bir implementasyonuydu: ajanlar testte
buradan, uretimde `app/mcp/server.py`'den geciyordu. Gercek tool'lar zaten
repository katmanina konusuyor; repository de DB yoksa bellek ici veriye
dusuyor (bkz. `app/repositories/deps.py`). Yani sahte veriye dusme ihtiyaci
TEK yerde, repository katmaninda karsilaniyor - tool'lari ikinci kez yazmaya
gerek yok.

| Arsivdeki sahte tool | Yerine gelen |
|---|---|
| `mcp/servers/rag.py::rag_search` | `app/mcp/server.py::rag_search` -> RagRepository |
| `mcp/servers/market.py::market_get_quote` | `app/mcp/server.py::market_get_quote` -> MarketRepository |
| `mcp/servers/market.py::market_get_kap_disclosures` | `app/mcp/server.py::market_get_kap_disclosures` -> RagRepository (`tip='duyuru'`) |

> `in_memory.py` bu klasorde DEGILDIR: `app/repositories/in_memory.py` olarak
> yerinde duruyor ve veritabani calismadiginda YEDEK plan olarak devreye
> giriyor.
