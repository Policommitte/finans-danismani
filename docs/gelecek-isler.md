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
