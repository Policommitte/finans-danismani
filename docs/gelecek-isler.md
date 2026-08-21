# Gelecek İşler

RAG hibrit arama çalışması (Faz 4+5, 2026-08-19 → 2026-08-20) sırasında
ortaya çıkan, şimdilik kapsam dışında bırakılan ama ileride ele alınması
gereken maddelerin kaydı. Her madde: ne eksik, neden önemli, nerede/nasıl
çözülür.

## 1. `date_from`/`date_to` hiçbir yerde üretilmiyor

**Güncelleme (2026-08-20):** Bu alanlar önceden MCP tool katmanında
(`mcp/server.py::rag_search`) sessizce DÜŞÜYORDU — ajan `filters` sözlüğü
içinde gönderse bile hiçbir yerde okunmuyordu. Hibrit arama kablolaması
sırasında bu gerçek bir bug olarak bulundu ve düzeltildi: `rag_search` artık
`date_from`/`date_to`'yu hem doğrudan parametre hem `filters` sözlüğü
üzerinden kabul edip `SqlRagRepository.hybrid_search()`/`search()`'e kadar
doğru taşıyor (bkz. `test_mcp_server.py::test_rag_search_tarih_parametrelerini_kabul_eder`).
Aşağıdaki asıl eksik ise HÂLÂ AÇIK: bu alanları dolduran hiçbir üretici yok.

**Ne eksik:** `MarketResearchAgent`, `state.agent_tasks["market_research"]`
içinden `date_from`/`date_to` okuyup RAG aramasına iletebiliyor (bu alanların
MCP tool'a ve SQL katmanına kadar doğru şekilde taşınması artık uçtan uca
sağlandı) - ama bu alanları DOLDURAN hiçbir kod yok:

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

**Durum:** Kapsam dışı bırakıldı. Plumbing artık UÇTAN UCA hazır (MCP tool +
SQL katmanı) ama besleyen bir üretici hâlâ yok.

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
PR henüz planlanmadı. `rag.hybrid_search()`'ün `p_asset_id` parametresi de
aynı sebeple pratikte ölü (bkz. madde 3).

## 3. Supabase'deki `rag.hybrid_search()` genişletilmiş imzayı taşımıyor

**Ne eksik:** `db/v5_schema_and_data.sql`'deki `rag.hybrid_search()`
2026-08-20'de `p_sirket`/`p_tip`/`p_date_from`/`p_date_to` ile genişletildi
(yerel Docker DB'de zaten hand-apply edilmişti, dosya bu hâliyle senkron
edildi - bkz. `SqlRagRepository.hybrid_search()`). **Bu değişiklik Supabase'e
UYGULANMADI** - kullanıcının açık onayı bekleniyor (paylaşılan, gerçek bir
kaynak; bkz. embedding pipeline oturum notları, "Supabase gerçek, paylaşılan
bir kaynak" uyarısı).

**Neden önemli:** `DATABASE_URL` Supabase'e bağlıyken (bugünkü
`backend/.env` durumu budur) `rag_search` çağrıldığında sorgu embedding'i
BAŞARIYLA üretilir (Cohere API'ye erişim Supabase'in şemasından bağımsız),
ama ardından SQL fonksiyon çağrısı `UndefinedFunction` hatasıyla PATLAR -
çünkü Supabase'deki fonksiyon hâlâ eski (`p_asset_id`/`p_k_rrf`'e kadar olan)
imzayı taşıyor. Bu, embedding-hatası fallback'inin (BM25'e sessiz düşüş) YAKALAMADIĞI
bir hatadır: hata embedding adımında değil SQL çağrısında oluşur, bu yüzden
`MCPToolExecutionError` → `AgentError(error_type="tool_error")` olarak
`market_research` ajanının o turki RAG bacağının TAMAMEN başarısız olmasına
yol açar (kısmi başarısızlık olarak raporlanır, sohbet çökmez, ama o turda
RAG verisi hiç gelmez).

**Nerede çözülür:** Supabase'e karşı `DROP FUNCTION rag.hybrid_search(text,
vector, integer, integer, integer)` (eski 5 parametreli imza) ardından
`db/v5_schema_and_data.sql`'deki güncel `CREATE OR REPLACE FUNCTION
rag.hybrid_search(...)` bloğu çalıştırılarak - yerel Docker DB'de aynı adımlar
zaten doğrulandı (bkz. embedding pipeline oturum notları, "`CREATE OR
REPLACE FUNCTION` parametre listesi değişince overload yaratır" uyarısı).

**Durum:** Kullanıcının açık onayı bekleniyor, henüz uygulanmadı.

## 4. `/api/market/search` (REST) hâlâ yalnızca BM25

**Ne eksik:** `app/services/market.py`, `SqlRagRepository.search()`'ü
çağırıyor - `.hybrid_search()`'ü DEĞİL. Yalnızca sohbet ajanının kullandığı
`rag_search` MCP tool yolu (`mcp/server.py`) hibrit aramaya bağlandı; dashboard/
REST üzerinden yapılan piyasa araması hâlâ tam eşleşmeyle sınırlı.

**Neden önemli:** Aynı arama özelliğinin iki farklı giriş noktası (sohbet vs.
dashboard) farklı kalitede sonuç üretiyor - kullanıcı sohbette bulduğu bir
haberi dashboard aramasında bulamayabilir (ya da tam tersi, sırf farklı
arama stratejisi kullanıldığı için).

**Nerede çözülür:** `services/market.py`'deki `.search()` çağrısı
`.hybrid_search()` ile değiştirilerek - mekanik bir değişiklik, `rag_search`
tool'unda yapılanın aynısı.

**Durum:** Bilinçli olarak kapsam dışı bırakıldı (bu session'ın odağı sohbet/
MCP yoluydu), düzeltici bir PR henüz planlanmadı.
