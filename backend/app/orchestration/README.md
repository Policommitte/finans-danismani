# orchestration/ — Ortak orkestrasyon modelleri

LangGraph graph'i boyunca taşınan durum ve ajanların ürettiği yardımcı yapılar.

> Bu klasör önceden `schema/` adındaydı ve REST modellerini tutan `schemas/` ile
> yan yana duruyordu; tek harf farkı kalıcı karışıklık üretiyordu (mimari v4
> bölüm 12). **REST istek/yanıt modelleri `app/schemas/` altındadır.**

| Model | Açıklama |
|---|---|
| `AgentState` | LangGraph graph'i boyunca taşınan ortak durum |
| `Source` | RAG yanıtının dayandığı kaynak doküman (FR-RAG-04) |
| `AgentError` | Bir ajanın başarısızlığı — akışı durdurmaz |
| `ToolResult` | MCP tool çağrısının sonucu |
| `RouterDecision` | Router'ın kural tabanlı kararı (mimari v4 §10.4) |

## ⚠️ Reducer kuralı — değiştirmeden önce okuyun

Paralel çalışan node'lar **aynı alana** yazarsa LangGraph çakışma hatası verir.

- Her ajan **kendi alanına** yazar (`portfolio_data` / `market_data` /
  `risk_data`) → çakışma yok, reducer gerekmez.
- Birden fazla node'un yazdığı alanlar (`sources`, `agent_errors`,
  `security_flags`) `Annotated[..., add_or_reset]` ile reducer taşımak
  **zorundadır**. Reducer kaldırılırsa kod hata vermez ama ikinci yazan
  birincinin verisini **sessizce siler**.

## ⚠️ Tur başı sıfırlama

Reducer'lı alanlar checkpointer'da **birikir**. Giriş state'ine `[]` yazmak
sıfırlamaz — LangGraph giriş değerini reducer ile *uygular* ve `[] + mevcut`
"hiçbir şey ekleme" demektir. Bu yüzden `add_or_reset` bir sentinel tanır:

```python
{"sources": [RESET]}          # kanalı temizle
{"sources": [RESET, kaynak]}  # temizle + yaz
```

`Orchestrator.stream_request` her turun başında bunu gönderir. Kural
`tests/test_orchestration_models.py` içinde testle sabitlenmiştir.
