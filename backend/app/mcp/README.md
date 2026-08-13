# MCP client ve server'lar

- `client.py` — `MCPClient`/`MCPServer`: agent'larin paylastigi, adlandirilmis
  sunuculara (server="rag", "market", ...) yonlendirme yapan in-process tool
  cagri katmani. Gercek disaridan MCP sunucularina (JSON-RPC/stdio) baglanan
  bir transport degildir; bkz. modul docstring'i.
- `servers/rag.py` — MCP Server 1 (LlamaIndex RAG) icin mock `rag_search` tool'u
- `servers/market.py` — MCP Server 3 (Borsa & KAP) icin mock `market_get_quote`
  ve `market_get_kap_disclosures` tool'lari
- `mock.py` — `build_mock_mcp_client()`: yukaridaki iki mock sunucuyu ayaga
  kaldirip gelistirme/test icin hazir bir `MCPClient` doner

MCP Server 2 (Portfoy DB / PostgreSQL) `PortfolioAgent`'in sorumlulugundadir,
bu klasorde yer almaz.
