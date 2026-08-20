# Gelecek İşler

Faz 5 (RAG hibrit arama) çalışması sırasında ortaya çıkan, şimdilik kapsam
dışında bırakılan ama ileride ele alınması gereken maddelerin kaydı. Her
madde: ne eksik, neden önemli, nerede/nasıl çözülür.

## 1. `date_from`/`date_to` hiçbir yerde üretilmiyor

**Ne eksik:** `MarketResearchAgent`, `state.agent_tasks["market_research"]`
içinden `date_from`/`date_to` okuyup RAG aramasına iletebiliyor (Faz 5'te bu
alanların SQL katmanına kadar doğru şekilde taşınması sağlandı) - ama bu
alanları DOLDURAN hiçbir kod yok:

- Router henüz yapılandırılmış parametre üretmiyor (`market_research.py`
  modül docstring'i bunu açıkça belirtiyor).
- `build_task()` yalnızca `symbol` için bir metin-çıkarım fallback'ine sahip
  (`_extract_symbol` regex'i); "son bir hafta", "geçen ay" gibi ifadeleri
  tarihe çeviren eşdeğer bir mantık hiçbir yerde yok.

**Neden önemli:** kullanıcı "THYAO hakkında son bir haftadaki haberler" diye
sorsa bile, bugün bu istek tarih filtresiz çalışır - sessizce, hata vermeden.

**Nerede çözülür:** ya router'a yapılandırılmış parametre üretimi
eklendiğinde (orchestrator'ın router node'u), ya da
`MarketResearchAgent.build_task()`'a `symbol` ile aynı desende bir tarih
ifadesi → `date_from`/`date_to` çıkarım fonksiyonu eklenerek.

**Durum:** Faz 5 kapsamı dışında, plumbing hazır ama besleyen bir üretici yok.

## 2. Taranan (scraped) haberlerde `asset_id` hiç doldurulmuyor

**Ne eksik:** `rag.documents.asset_id`, bir dokümanın HANGİ şirket/varlıkla
ilgili olduğunu tutan asıl kolon (`assets` tablosuna FK). Ama scraper bu
alanı hiç doldurmuyor - 2026-08-20'de Supabase'e karşı doğrudan doğrulandı
(salt-okunur `BEGIN TRANSACTION READ ONLY` + `ROLLBACK`): 234 gerçek
dokümanın **234'ünde de `asset_id IS NULL`**.

**Neden önemli:** `SqlRagRepository.search()`'teki `assets` join'i (ve ileride
`rag.hybrid_search()`'ün `p_asset_id`'si) bu yüzden gerçek veride hiçbir zaman
eşleşmiyor - `sirket` filtresi tamamen `d.baslik ILIKE '%...%'` (başlık metin
eşleşmesi) fallback'ine bağımlı kalıyor. Gerçek semantik şirket etiketleme
YOK; bir haberin başlığı şirketin adını/sembolünü birebir içermezse (örn.
kısaltma, çekim eki, farklı yazım), doküman var olan bir eşleşmeyi
kaçırabilir.

**Nerede çözülür:** haber scraper'ında (`borsa-verisi-toplanması` /
ilgili scraping kodu) ingestion sırasında `asset_id` çözümlemesi eklenerek -
örn. başlık/metin içinde geçen sembol veya şirket adını `assets` tablosuyla
eşleştirip `rag.documents.asset_id`'yi doldurarak. Mevcut 234 dokümanı geriye
dönük doldurmak ayrı bir backfill işi olur.

**Durum:** Küçük öncelikli, kapsam dışı - not olarak bırakıldı, düzeltici bir
PR henüz planlanmadı.
