"""MarketResearchAgent testleri (app/agents/market_research.py).

Ajan iki sozlesmeye birden uymak zorundadir:
  1. BaseAgent  -> `run(state)` DICT doner, istisna SIZDIRMAZ, timeout uygular.
  2. AgentState -> yalnizca kendi alanina (`market_data`) ve reducer'li
     `sources` alanina yazar.

Testler ayrica halusinasyon korumasini sabitler: kaynak bulunamadiginda LLM'e
HIC gidilmez, boylece model bosluktan icerik uretemez.
"""

import pytest

from app.agents.market_research import (
    _ALAN_SOZLUGU,
    _ALAN_TERS,
    NO_RETRIEVAL_MESSAGE,
    MarketResearchAgent,
    _alandan_coz,
    _arama_metni,
    _technical_intent,
)
from app.mcp.client import MCPClient, MCPServer
from app.mcp.server import build_servers
from app.orchestration.models import AgentState, Source

pytestmark = pytest.mark.db


def build_mcp_client() -> MCPClient:
    """Gercek tool'lardan olusan MCP istemcisi (veri kaynagi: PostgreSQL)."""
    client = MCPClient()
    for server in build_servers():
        client.register_server(server)
    return client


class SahteLLM:
    """Gercek model cagrisi yapmadan sabit bir ozet doner."""

    def __init__(self, response: str = "Test ozeti.") -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        self.prompts.append(prompt)
        return self.response


class CokenLLM:
    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        raise RuntimeError("model kotasi doldu")


#: Seed'deki (`db/v5_schema_and_data.sql`) THYAO bilanco dokumanini bulan sorgu.
#: Dokumanlarda sirket UNVANI yazili ("Turk Hava Yollari"); yalnizca "THYAO"
#: aramak BM25 ayaginda sonuc dondurmez.
RAG_SORGUSU = "THYAO ikinci ceyrek karini nasil etkiledi"

#: Deterministik ozette alintilanan kaynak basligi.
RAG_KAYNAK_BASLIGI = "THYAO 2026 2. Çeyrek Finansal Sonuçları"


def _state(sorgu: str, **kwargs) -> AgentState:
    return AgentState(user_query=sorgu, user_id=1, thread_id=1, **kwargs)


def _ajan(llm=None, mcp_client=None) -> MarketResearchAgent:
    return MarketResearchAgent(
        mcp_client=mcp_client if mcp_client is not None else build_mcp_client(),
        llm=llm if llm is not None else SahteLLM(),
        timeout_seconds=5,
    )


def _gorev(**alanlar) -> dict:
    """Router'in uretecegi yapilandirilmis parametreleri taklit eder."""
    return {"agent_tasks": {"market_research": alanlar}}


# ---------------------------------------------------------------------------
# RAG yolu
# ---------------------------------------------------------------------------


async def test_rag_sorgusu_market_data_ve_kaynak_uretir():
    llm = SahteLLM()
    ajan = _ajan(llm=llm)

    sonuc = await ajan.run(_state(RAG_SORGUSU, **_gorev(mode="rag")))

    assert sonuc["market_data"]["summary"] == "Test ozeti."
    assert sonuc["market_data"]["live_data"] is None
    assert sonuc["market_data"]["confidence"] is not None
    assert len(llm.prompts) == 1


async def test_kaynaklar_source_modeli_olarak_doner():
    """Orchestrator `sources` alanini `Source` nesnesi olarak serilestirir."""
    ajan = _ajan()

    sonuc = await ajan.run(_state(RAG_SORGUSU, **_gorev(mode="rag", symbol="THYAO")))

    kaynaklar = sonuc["sources"]
    assert kaynaklar and all(isinstance(k, Source) for k in kaynaklar)
    assert all(k.doc_id and k.baslik for k in kaynaklar)
    assert kaynaklar[0].sirket == "THYAO"
    assert kaynaklar[0].tip == "bilanco"  # metadata.topic="earnings" eslemesi


async def test_kaynak_alintilari_market_data_icinde_de_tasinir():
    """security_gate ham veriyi tarar; alintilar orada olmazsa denetlenemez."""
    ajan = _ajan()

    sonuc = await ajan.run(_state(RAG_SORGUSU, **_gorev(mode="rag", symbol="THYAO")))

    alintilar = sonuc["market_data"]["sources"]
    assert alintilar and all(a["source"] and a["excerpt"] for a in alintilar)


async def test_bos_retrieval_da_llm_e_gidilmez():
    """Halusinasyon korumasi: kaynak yoksa model hic cagrilmaz."""
    llm = SahteLLM()
    ajan = _ajan(llm=llm)

    sonuc = await ajan.run(
        _state("bilinmeyen sirket haberi", **_gorev(mode="rag", symbol="YOKYOK"))
    )

    assert sonuc["sources"] == []
    assert sonuc["market_data"]["confidence"] == 0.0
    assert sonuc["market_data"]["summary"] == NO_RETRIEVAL_MESSAGE
    assert llm.prompts == []


# ---------------------------------------------------------------------------
# Canli veri yolu
# ---------------------------------------------------------------------------


async def test_canli_sorgu_fiyat_dondurur_ve_llm_cagirmaz():
    llm = SahteLLM()
    ajan = _ajan(llm=llm)

    sonuc = await ajan.run(_state("THYAO fiyati ne", **_gorev(mode="live", symbol="THYAO")))

    canli = sonuc["market_data"]["live_data"]
    assert canli["symbol"] == "THYAO"
    assert canli["price"] > 0
    assert sonuc["sources"] == []
    assert llm.prompts == []


async def test_both_modu_rag_ve_canli_veriyi_birlestirir():
    ajan = _ajan()

    sonuc = await ajan.run(_state(RAG_SORGUSU, **_gorev(mode="both", symbol="THYAO")))

    assert sonuc["market_data"]["live_data"] is not None
    assert sonuc["sources"]
    assert "THYAO" in sonuc["market_data"]["summary"]


async def test_bilinmeyen_sembolde_canli_veri_bos_doner_ama_hata_olmaz():
    ajan = _ajan()

    sonuc = await ajan.run(_state("XXXXX fiyati", **_gorev(mode="live", symbol="XXXXX")))

    assert sonuc["market_data"]["live_data"] is None
    assert "bulunamadi" in sonuc["market_data"]["summary"].lower()
    assert "agent_errors" not in sonuc


# ---------------------------------------------------------------------------
# Parametre cikarimi (router yapilandirilmis gorev vermediginde)
# ---------------------------------------------------------------------------


async def test_sembol_sorgudan_cikarilir():
    ajan = _ajan()

    sonuc = await ajan.run(_state("THYAO fiyati kac oldu, guncel"))

    assert sonuc["market_data"]["mode"] == "live"
    assert sonuc["market_data"]["live_data"]["symbol"] == "THYAO"


def test_bist_gibi_kisaltmalar_sembol_sayilmaz():
    ajan = _ajan()

    assert ajan._extract_symbol("BIST bugun nasil") is None
    assert ajan._extract_symbol("ASELS hisse yorumu") == "ASELS"


async def test_sembol_yoksa_rag_moduna_dusulur():
    """Canli fiyat yolu sembol olmadan anlamsizdir."""
    ajan = _ajan()

    sonuc = await ajan.run(_state("piyasada guncel fiyatlar nasil"))

    assert sonuc["market_data"]["mode"] == "rag"


async def test_router_gorevi_cikarimin_onune_gecer():
    ajan = _ajan()

    sonuc = await ajan.run(
        _state("SASA kapasite yatirimi fiyati ne", **_gorev(mode="rag", symbol="SASA"))
    )

    assert sonuc["market_data"]["mode"] == "rag"
    assert sonuc["sources"][0].sirket == "SASA"


# ---------------------------------------------------------------------------
# Router entegrasyonu - ucuz no-op
# ---------------------------------------------------------------------------


async def test_router_istemediyse_ajan_calismaz():
    ajan = _ajan()

    sonuc = await ajan.run(_state("Portfoyum nasil?", requested_agents=["portfolio"]))

    assert sonuc == {}


async def test_router_istediyse_ajan_calisir():
    ajan = _ajan()

    sonuc = await ajan.run(_state(RAG_SORGUSU, requested_agents=["market_research"]))

    assert sonuc["market_data"] is not None


# ---------------------------------------------------------------------------
# Graceful degradation
# ---------------------------------------------------------------------------


async def test_mcp_sunucusu_yoksa_tool_error_uretir():
    """MCP cokmesi akisi durdurmamali, dogru kategoriyle raporlanmali."""
    ajan = _ajan(mcp_client=MCPClient())

    sonuc = await ajan.run(_state(RAG_SORGUSU))

    hatalar = sonuc["agent_errors"]
    assert len(hatalar) == 1
    assert hatalar[0].agent_name == "market_research"
    assert hatalar[0].error_type == "tool_error"


async def test_tool_icinde_hata_olusursa_tool_error_uretir():
    async def bozuk_rag_search(query, top_k=5, filters=None):
        raise ValueError("indeks bozuk")

    sunucu = MCPServer(name="rag")
    sunucu.register_tool("rag_search", bozuk_rag_search)
    ajan = _ajan(mcp_client=MCPClient({"rag": sunucu}))

    sonuc = await ajan.run(_state(RAG_SORGUSU))

    assert sonuc["agent_errors"][0].error_type == "tool_error"


async def test_llm_cokerse_rag_verisi_korunur():
    """KRITIK: model cokse bile bulunan kaynaklar bosa gitmemeli."""
    ajan = _ajan(llm=CokenLLM())

    sonuc = await ajan.run(_state(RAG_SORGUSU, **_gorev(mode="rag", symbol="THYAO")))

    assert sonuc["sources"]  # kaynaklar duruyor
    assert sonuc["market_data"]["summary"]  # deterministik alintiya dusuldu
    assert sonuc["agent_errors"][0].error_type == "llm_error"


async def test_llm_yoksa_kaynaklardan_deterministik_ozet_uretilir():
    """LLM bagli olmamak bir HATA degildir; ajan alinti yaparak calisir."""
    ajan = MarketResearchAgent(mcp_client=build_mcp_client(), llm=None, timeout_seconds=5)

    sonuc = await ajan.run(_state(RAG_SORGUSU, **_gorev(mode="rag", symbol="THYAO")))

    assert "agent_errors" not in sonuc
    assert RAG_KAYNAK_BASLIGI in sonuc["market_data"]["summary"]


async def test_bos_sorgu_hata_dondurur_ama_firlatmaz():
    ajan = _ajan()

    sonuc = await ajan.run(_state("   "))

    assert sonuc["agent_errors"][0].error_type == "unknown"


# ---------------------------------------------------------------------------
# Tool kesfi - yetki ayrimi
# ---------------------------------------------------------------------------


async def test_ajan_yalnizca_rag_ve_market_tool_larini_gorur():
    """NFR-04: bu ajan portfoy sunucusuna ERISEMEZ."""
    client = build_mcp_client()
    client.register_server(MCPServer(name="portfolio"))
    ajan = _ajan(mcp_client=client)

    tools = await ajan.get_tools()

    assert {t["server"] for t in tools} == {"rag", "market"}


async def test_mcp_client_yoksa_tool_listesi_bostur():
    ajan = MarketResearchAgent(mcp_client=None, llm=None, timeout_seconds=5)

    assert await ajan.get_tools() == []


# ---------------------------------------------------------------------------
# Timeout - BaseAgent sozlesmesi ajan uzerinde de gecerli
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("sorgu", ["THYAO bilancosu", "THYAO fiyati guncel"])
async def test_yavas_tool_timeout_uretir(sorgu):
    import asyncio

    async def yavas(**kwargs):
        await asyncio.sleep(5)
        return {}

    sunucu_rag = MCPServer(name="rag")
    sunucu_rag.register_tool("rag_search", yavas)
    sunucu_market = MCPServer(name="market")
    sunucu_market.register_tool("market_get_quote", yavas)

    ajan = MarketResearchAgent(
        mcp_client=MCPClient({"rag": sunucu_rag, "market": sunucu_market}),
        llm=SahteLLM(),
        timeout_seconds=1,
    )

    sonuc = await ajan.run(_state(sorgu))

    assert sonuc["agent_errors"][0].error_type == "timeout"


# ---------------------------------------------------------------------------
# Kaynak alanlari - gercek MCP tool ciktisiyla (backend part 2)
# ---------------------------------------------------------------------------


def test_source_uses_document_id():
    """`Source.doc_id` DOKUMAN kimligidir; chunk numarasi kullaniciya yaramaz."""
    kaynak = MarketResearchAgent._to_source(
        {
            "chunk_id": "17",
            "doc_id": "DOC-001",
            "title": "THYAO 2026 2. Ceyrek",
            "tip": "bilanco",
            "date": "2026-07-28",
            "metadata": {"symbol": "THYAO", "topic": "earnings"},
            "score": 0.3,
        }
    )

    assert kaynak.doc_id == "DOC-001"


def test_source_keeps_type_given_by_tool():
    """Esleme tablosuna korukorune guvenilseydi bilanco 'haber' olurdu."""
    kaynak = MarketResearchAgent._to_source(
        {"chunk_id": "1", "doc_id": "DOC-001", "title": "x", "tip": "bilanco", "metadata": {}}
    )

    assert kaynak.tip == "bilanco"


def test_source_falls_back_to_legacy_topic_mapping_without_type():
    """Zarf oncesi yazilmis sunucular yalnizca `metadata.topic` donuyor."""
    kaynak = MarketResearchAgent._to_source(
        {"chunk_id": "1", "title": "x", "metadata": {"topic": "analyst"}}
    )

    assert kaynak.tip == "analist_raporu"


# ---------------------------------------------------------------------------
# Arama metni damitma (`_arama_metni`) ve sembolun filtre OLMAMASI
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu, beklenen",
    [
        # Yatirim cercevesi tamamen atilir, geriye varlik adi kalir.
        ("Türk Hava Yolları hissesini etkileyebilecek gelişmeler neler", "Türk Hava Yolları"),
        ("genel olarak aselsan hissesini etkileyebilecek olan haber yok mu", "aselsan"),
        # Sektor sorusunda konu kelimeleri KORUNUR - damitma konuyu silmez.
        ("savunma sanayi nasıl gidiyor", "savunma sanayi"),
    ],
)
def test_arama_metni_yatirim_cercevesini_atar(sorgu, beklenen):
    assert _arama_metni(sorgu) == beklenen


def test_arama_metni_turkce_karakterleri_korur():
    """Eslesme normalize metinde yapilir ama KESME orijinalde - diakritik kalmali.

    Normalize edilmis metni gommek gomme kalitesini dusururdu: korpusta
    "Türk Hava Yolları" diakritikli yaziliyor.
    """
    assert _arama_metni("Türk Hava Yolları hissesi") == "Türk Hava Yolları"


def test_arama_metni_varlik_adini_basa_ekler():
    """Kullanici kodu yazar ("THYAO"), korpusta unvan gecer."""
    sonuc = _arama_metni("THYAO bugün neden yükseldi", "Türk Hava Yolları")

    assert sonuc.startswith("Türk Hava Yolları")
    assert "THYAO" in sonuc


def test_arama_metni_ad_zaten_varsa_tekrarlamaz():
    assert _arama_metni("Aselsan hissesi", "Aselsan") == "Aselsan"


def test_arama_metni_her_sey_silinirse_ham_sorguya_doner():
    """Bos metni gommek her chunk'a esit uzaklikta anlamsiz bir vektor uretir."""
    assert _arama_metni("neler oluyor") == "neler oluyor"


async def test_sembol_rag_filtresi_olarak_GONDERILMEZ():
    """A: sembol filtresi `rag.hybrid_search` icinde havuzu tamamen bosaltiyordu.

    Filtre `assets.symbol`/`assets.name`/`documents.baslik` uzerinden eslesiyor
    ama `rag.documents.asset_id` uretimde hic doldurulmamis ve basliklarda ham
    kod gecmiyor - yani sembol DOGRU cozuldugunde bile sonuc her zaman bos
    donuyordu. Sembol artik arama metnine gider.
    """
    cagrilar: list[dict] = []

    async def kaydeden_rag_search(query, top_k=5, filters=None):
        cagrilar.append({"query": query, "filters": filters or {}})
        return {"chunks": []}

    sunucu = MCPServer(name="rag")
    sunucu.register_tool("rag_search", kaydeden_rag_search)
    ajan = _ajan(mcp_client=MCPClient({"rag": sunucu}))

    await ajan.run(_state("THYAO hissesini etkileyebilecek gelişmeler neler"))

    assert cagrilar, "rag_search hic cagrilmadi"
    assert "symbol" not in cagrilar[0]["filters"]
    assert "sirket" not in cagrilar[0]["filters"]
    # Sembol kaybolmaz - arama metnine tasinir.
    assert "THYAO" in cagrilar[0]["query"]


async def test_tarih_filtreleri_korunur():
    """Tarih `documents.tarih` uzerinden calisir; eksik metadataya bagli degil."""
    cagrilar: list[dict] = []

    async def kaydeden_rag_search(query, top_k=5, filters=None):
        cagrilar.append(filters or {})
        return {"chunks": []}

    sunucu = MCPServer(name="rag")
    sunucu.register_tool("rag_search", kaydeden_rag_search)
    ajan = _ajan(mcp_client=MCPClient({"rag": sunucu}))

    await ajan.run(
        _state("piyasa ozeti", **_gorev(mode="rag", date_from="2026-08-01", date_to="2026-08-17"))
    )

    assert cagrilar[0]["date_from"] == "2026-08-01"
    assert cagrilar[0]["date_to"] == "2026-08-17"


# ---------------------------------------------------------------------------
# Alan sozlugu (`_ALAN_SOZLUGU`) - ileri ve geri yon
# ---------------------------------------------------------------------------


def test_alan_sozlugunde_capraz_alt_dize_yok():
    """Bir ifade, BASKA bir sembolun ifadesinin alt dizesi olmamali.

    Olsaydi geri yon sessizce belirsizlesir ve `_alandan_coz` "birden cok
    eslesme" sayip sembolu HIC cozemezdi - hata vermeden, yalnizca ozellik
    calismayarak. Tablo elle buyutuldugu icin bu denetim gerekli.
    """
    cakisan = [
        (a, _ALAN_TERS[a], b, _ALAN_TERS[b])
        for a in _ALAN_TERS
        for b in _ALAN_TERS
        if a != b and a in b and _ALAN_TERS[a] != _ALAN_TERS[b]
    ]

    assert not cakisan, f"capraz alt dize: {cakisan}"


def test_alan_ifadeleri_katalog_sembolu_kullanir():
    """Tablo, gercek sembol kodlarina baglanmali (yazim hatasi erken yakalansin)."""
    assert "ASELS" in _ALAN_SOZLUGU
    assert "savunma sanayi" in _ALAN_SOZLUGU["ASELS"]


@pytest.mark.parametrize(
    "sorgu, beklenen",
    [
        ("savunma sanayi nasıl gidiyor", "ASELS"),
        ("havacılık sektörü nasıl", "THYAO"),
        ("bankacılık sektöründe durum ne", "GARAN"),
    ],
)
def test_alandan_coz_sektor_sorusunu_sembole_baglar(sorgu, beklenen):
    assert _alandan_coz(sorgu, {"ASELS", "THYAO", "GARAN"}) == beklenen


def test_alandan_coz_birden_cok_eslesmede_sembol_uretmez():
    """`task` TEKIL sembol tasir; yanlis birini secmektense sembolsuz devam."""
    sorgu = "yapay zeka çipi ve bulut bilişim hisseleri nasıl"

    assert _alandan_coz(sorgu, {"NVDA", "MSFT"}) is None


def test_alandan_coz_jenerik_kelimeye_takilmaz():
    assert _alandan_coz("teknoloji hisseleri nasıl", {"NVDA", "MSFT"}) is None
    assert _alandan_coz("sanayi nasıl", {"ASELS"}) is None


def test_alandan_coz_katalogda_olmayan_sembolu_uretmez():
    """`_takma_addan_coz` ile ayni kural: varlik silinirse tablo yanlis donmesin."""
    assert _alandan_coz("savunma sanayi nasıl gidiyor", {"THYAO"}) is None


def test_arama_metni_alan_kelimelerini_sona_ekler():
    """Sorunun konusu basta kalir, alan kelimeleri arkadan agirlik verir."""
    sonuc = _arama_metni("THYAO hissesi", "Türk Hava Yolları", ("havacılık", "uçuş ağı"))

    assert sonuc.startswith("Türk Hava Yolları")
    assert sonuc.endswith("havacılık uçuş ağı")


def test_arama_metni_ad_metinde_varsa_alan_yine_eklenir():
    """ "aselsan hissesi" -> ad zaten geciyor, tekrarlanmaz; alan yine de eklenir."""
    sonuc = _arama_metni("aselsan hissesi", "Aselsan", ("savunma sanayi",))

    assert sonuc == "aselsan savunma sanayi"


def test_arama_metni_zaten_gecen_alan_kelimesini_tekrarlamaz():
    sonuc = _arama_metni("savunma sanayi nasıl gidiyor", None, ("savunma sanayi",))

    assert sonuc.count("savunma sanayi") == 1


async def test_alandan_cozulen_sembol_rag_i_kapatmaz():
    """Alan sembolu tek basina "live"a dusmemeli - sektor sorusunun konusu haber.

    Dusseydi alan sozlugu kendi amacini baltalardi: "savunma sanayi hisseleri
    ne kadar yukseldi" salt fiyat dondururdu.
    """
    ajan = _ajan(mcp_client=build_mcp_client())
    gorev = {"query": "savunma sanayi hisseleri ne kadar yükseldi"}
    await ajan._resolve_symbol_from_catalog(gorev)

    assert gorev.get("symbol") == "ASELS"
    assert gorev.get("symbol_alandan") is True
    # Fiyat ipucu ("ne kadar yukseldi") olmasina RAGMEN canli yol acilmaz.
    assert ajan._resolve_mode(gorev, gorev["query"]) == "rag"


async def test_alandan_cozulen_sembol_arama_metnine_enjekte_edilmez():
    """Alandan CIKARILAN sembol arama metnine hicbir sey eklemez.

    Sorulan sirket katalogdakinden baskasi olabilir ve genisletme onun
    haberlerini eziyor - olculdu:

        "Baykar savunma sanayinde"                     -> 4/5 sonuc Baykar
        "Baykar savunma sanayinde savunma elektronigi"  -> 0/5 sonuc Baykar

    Ad enjekte edilmese bile duser; sucu tasiyan alan kelimeleri.
    """
    cagrilar: list[str] = []

    async def kaydeden_rag_search(query, top_k=5, filters=None):
        cagrilar.append(query)
        return {"chunks": []}

    sunucu = MCPServer(name="rag")
    sunucu.register_tool("rag_search", kaydeden_rag_search)
    ajan = _ajan(mcp_client=MCPClient({"rag": sunucu}))

    await ajan._run_rag(
        {"query": "savunma sanayi nasıl gidiyor", "symbol": "ASELS", "symbol_alandan": True},
        "savunma sanayi nasıl gidiyor",
    )

    # Yalnizca damitma - ne ad ne alan kelimesi.
    assert cagrilar == ["savunma sanayi"]


async def test_sorguda_adiyla_gecen_sembol_alan_kelimelerini_alir():
    """Kullanici sirketi ADIYLA yazdiysa belirsizlik YOK - takviye uygulanir.

    Olculdu: "aselsan" -> savunma haberi 3. siradan 1. siraya (0.345 -> 0.426).
    """
    cagrilar: list[str] = []

    async def kaydeden_rag_search(query, top_k=5, filters=None):
        cagrilar.append(query)
        return {"chunks": []}

    sunucu = MCPServer(name="rag")
    sunucu.register_tool("rag_search", kaydeden_rag_search)
    ajan = _ajan(mcp_client=MCPClient({"rag": sunucu}))

    await ajan._run_rag(
        {"query": "aselsan hissesi haberleri", "symbol": "ASELS"},
        "aselsan hissesi haberleri",
    )

    assert "savunma sanayi" in cagrilar[0]


# ---------------------------------------------------------------------------
# Teknik analiz yolu
#
# Kural: teknik analiz haber ODAKLI bir soruda kendiliginden calismaz. Once
# "haber yok" denir ve teklif edilir; kullanici onaylarsa calisir.
# ---------------------------------------------------------------------------


def test_teknik_niyet_siniflandirmasi():
    assert _technical_intent("THYAO teknik analizi yapar mısın") == "explicit"
    assert _technical_intent("THYAO RSI kaç") == "explicit"
    assert _technical_intent("THYAO ile ilgili son haberler ne diyor") == "news_only"
    assert _technical_intent("THYAO bilançosu nasıl") == "news_only"
    assert _technical_intent("THYAO hakkında kısa bir yatırım analizi yap") == "general"
    # "karsi" icindeki "rsi" teknik istek SAYILMAZ (kelime siniri).
    assert _technical_intent("THYAO'ya karşı ne düşünüyorsun") == "general"


def _rag_bos(ajan):
    """`_run_rag`'i "hicbir kaynak yok" donecek sekilde degistirir."""

    async def bos(task, query):
        return NO_RETRIEVAL_MESSAGE, [], [], 0.0, None

    ajan._run_rag = bos


def _katalog_sabitle(ajan):
    """Sembol katalogunu sabitler - teknik yol testleri DB hizina bagli kalmasin."""

    async def katalog():
        return [{"symbol": "THYAO", "ad": "Türk Hava Yolları", "asset_class": "STOCK"}]

    ajan._symbol_catalog = katalog


def _canli_bos(ajan):
    """`_run_live`'i sessizlestirir - teknik yol testleri fiyat ucuna gitmesin."""

    async def bos(task):
        return "", None

    ajan._run_live = bos


def _teknik_izle(ajan, sonuc=None):
    """`_run_technical` cagrilarini kaydeder; gercek tool'a gitmez."""
    cagrilar: list[str] = []

    async def sahte(sembol):
        cagrilar.append(sembol)
        return "THYAO teknik gorunum: Sat.", sonuc or {"sufficient": True, "symbol": sembol}

    ajan._run_technical = sahte
    return cagrilar


async def test_haber_odakli_soruda_teknik_analize_otomatik_gecilmez():
    ajan = _ajan()
    _katalog_sabitle(ajan)
    _rag_bos(ajan)
    cagrilar = _teknik_izle(ajan)

    sonuc = await ajan.run(_state("THYAO ile ilgili son haberler ne diyor"))

    assert cagrilar == []
    assert sonuc["market_data"]["technical"] is None
    ozet = sonuc["market_data"]["summary"]
    assert "teknik analiz" in ozet.lower()
    assert "onay" in ozet.lower()


async def test_genel_soruda_haber_yoksa_teknik_analize_dusulur():
    ajan = _ajan()
    _katalog_sabitle(ajan)
    _rag_bos(ajan)
    cagrilar = _teknik_izle(ajan)

    sonuc = await ajan.run(_state("THYAO hakkında kısa bir yatırım analizi yap"))

    assert cagrilar == ["THYAO"]
    assert sonuc["market_data"]["technical"] is not None
    assert "teknik gorunum" in sonuc["market_data"]["summary"]


async def test_haber_varken_teknik_veri_destekleyici_olarak_etiketlenir():
    """Haber bulgusu ana cevaptir; teknik veri onun ardina DESTEK olarak eklenir."""
    ajan = _ajan()
    _katalog_sabitle(ajan)
    _canli_bos(ajan)
    cagrilar = _teknik_izle(ajan)

    async def rag_dolu(task, query):
        return "THYAO yolcu sayisi rekor kirdi.", [], [], 0.8, None

    ajan._run_rag = rag_dolu

    sonuc = await ajan.run(_state("THYAO hakkında kısa bir yatırım analizi yap"))

    ozet = sonuc["market_data"]["summary"]
    assert cagrilar == ["THYAO"]
    assert ozet.startswith("THYAO yolcu sayisi rekor kirdi.")
    assert "Destekleyici teknik veri:" in ozet


async def test_haber_yokken_teknik_veri_etiketlenmez():
    ajan = _ajan()
    _katalog_sabitle(ajan)
    _rag_bos(ajan)
    _canli_bos(ajan)
    _teknik_izle(ajan)

    ozet = (await ajan.run(_state("THYAO hakkında kısa bir yatırım analizi yap")))["market_data"][
        "summary"
    ]

    assert "Destekleyici teknik veri:" not in ozet


async def test_teklife_verilen_onay_teknik_analizi_calistirir():
    """Onay turunda sembol soruda GECMEZ; onceki mesajlardan cikarilir."""
    from langchain_core.messages import AIMessage, HumanMessage

    ajan = _ajan()
    _katalog_sabitle(ajan)
    _rag_bos(ajan)
    _canli_bos(ajan)
    cagrilar = _teknik_izle(ajan)
    gecmis = [
        HumanMessage(content="THYAO ile ilgili haberler ne diyor"),
        AIMessage(content="THYAO için haber yok. İstersen teknik analiz yapabilirim."),
        HumanMessage(content="evet yap"),
    ]

    sonuc = await ajan.run(_state("evet yap", messages=gecmis))

    assert cagrilar == ["THYAO"]
    assert sonuc["market_data"]["technical"] is not None


async def test_onay_teklif_edilmemisken_teknik_analizi_tetiklemez():
    ajan = _ajan()
    _katalog_sabitle(ajan)
    _rag_bos(ajan)
    cagrilar = _teknik_izle(ajan)

    sonuc = await ajan.run(_state("evet", messages=[]))

    assert cagrilar == []
    assert sonuc["market_data"]["technical"] is None
