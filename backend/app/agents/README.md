# agents/ — Ajan katmanı

## Mevcut

| Dosya | Açıklama |
|---|---|
| `base.py` | `BaseAgent` — tüm ajanların türediği soyut sınıf. Timeout ve hata yakalamayı merkezî olarak yapar. |
| `security_agent.py` | `SecurityAgent` — girdi ve çıktı güvenlik denetimi. Fan-out'un parçası değildir; graph'ta iki ayrı node olarak yer alır. |

## Beklenen (ayrı çalışma dalında geliştiriliyor)

| Dosya | Sorumluluk |
|---|---|
| `market_research_agent.py` | RAG üzerinden haber/bilanço araması, kaynak metadata aktarımı |
| `portfolio_agent.py` | MCP `portfolio_*` tool çağrıları, dağılım hesaplama |
| `risk_strategy_agent.py` | Risk skorlama, yeniden dengeleme önerisi |

## Yeni ajan yazarken

1. `BaseAgent`'tan türet, `name` sınıf değişkenini doldur.
2. Yalnızca `_execute(state) -> dict` metodunu yaz — `run()` timeout ve hata
   yönetimini zaten hallediyor.
3. **Sadece değişen alanları** içeren bir sözlük döndür. Tüm state'i
   döndürmek paralel çalışmada üzerine yazma hatasına yol açar.
4. Veritabanına **doğrudan erişme** (NFR-04) — tüm veri erişimi paylaşılan
   MCP client üzerinden yapılır.
5. Ajanı orchestrator'a bağlamak için `app/engine/orchestrator.py` içindeki
   `PARALLEL_AGENTS` / `SEQUENTIAL_AGENTS` listelerine adını ekle. Kural:
   başka bir ajanın çıktısına ihtiyaç duyuyorsa **sıralı**, duymuyorsa
   **paralel**.
