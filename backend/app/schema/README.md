# schema/ — Ortak veri modelleri

Orkestrasyon katmanının tüm bileşenlerinin paylaştığı Pydantic modelleri.

| Model | Açıklama |
|---|---|
| `AgentState` | LangGraph graph'i boyunca taşınan ortak durum |
| `Source` | RAG yanıtının dayandığı kaynak doküman (FR-RAG-04) |
| `AgentError` | Bir ajanın başarısızlığı — akışı durdurmaz |
| `ToolResult` | MCP tool çağrısının sonucu |

## ⚠️ Reducer kuralı — değiştirmeden önce okuyun

Paralel çalışan node'lar **aynı alana** yazarsa LangGraph çakışma hatası verir.

- Her ajan **kendi alanına** yazar (`portfolio_data` / `market_data` /
  `risk_data`) → çakışma yok, reducer gerekmez.
- Birden fazla node'un yazdığı alanlar (`sources`, `agent_errors`,
  `security_flags`) `Annotated[..., operator.add]` ile reducer taşımak
  **zorundadır**. Reducer kaldırılırsa kod hata vermez ama ikinci yazan
  birincinin verisini **sessizce siler**.

Bu kural `tests/test_schema_models.py` içinde testle sabitlenmiştir.
