"""Piyasa ozeti prompt sozlesmesi: ozne haberleri ile sektor baglami AYRI tutulur.

`test_market_research_agent.py` yerine ayri dosya, cunku o modul `db` isaretli
ve baglanti yokken tamamen atlanir; buradaki testler veritabanina dokunmuyor.
"""

from app.agents.market_research import (
    MarketResearchAgent,
    _build_rag_prompt,
    _ozne_etiketi,
)
from app.mcp.client import MCPClient, MCPServer


class SahteLLM:
    """Gercek model cagrisi yapmadan sabit bir ozet doner; prompt'u saklar."""

    def __init__(self, response: str = "Test ozeti.") -> None:
        self.response = response
        self.prompts: list[str] = []

    async def generate(self, prompt: str, *, model: str | None = None) -> str:
        self.prompts.append(prompt)
        return self.response


def test_ozet_promptu_kaynaklari_dogrudan_ve_baglam_diye_ayirtir():
    """Kullanici sikayeti: "THYAO haberleri" sorusuna havacilik ozeti geliyor."""
    prompt = _build_rag_prompt(
        "Bu hafta çıkan THYAO haberlerini özetle",
        [{"source": "aa.com.tr", "date": "2026-08-13", "text": "İstanbul Havalimanı..."}],
        "Türk Hava Yolları (THYAO)",
    )

    assert "Sorunun öznesi: Türk Hava Yolları (THYAO)" in prompt
    assert "DOĞRUDAN" in prompt
    assert "BAĞLAM" in prompt
    # Ayrimi tasiyan ilke - kaybolursa prompt yine birlestirmeye doner.
    assert "sektöründen olmak tek başına DOĞRUDAN yapmaz" in prompt
    # Asil zarar: sektor haberi sessizce ozne haberi diye sunuluyordu.
    assert "Doğrudan haber YOKSA" in prompt


def test_olcut_haberin_konusu_degil_metnindeki_bilgidir():
    """Vergi rekortmenleri listesindeki "Garanti BBVA 3. sirada" satiri,
    haberin konusu baska olsa da dogrudan bilgidir.
    """
    prompt = _build_rag_prompt("GARAN haberleri", [], "Garanti BBVA (GARAN)")

    assert "BAŞLIĞI ya da ana konusu değil" in prompt
    assert "Haberin ana konusu başka bir şey olsa bile buraya girer" in prompt
    # Ters yon: puf ad gecisi dogrudan sayilmasin.
    assert "adının geçmesi de yetmez" in prompt


def test_dogrudan_haber_yoksa_baglam_haberleri_yine_ozetlenir():
    """Canlida goruldu (GARAN): model "doğrudan haber yok" deyip bankacilik
    haberlerini hic ozetlemedi, kaynak kartlari bos duruyordu.
    """
    prompt = _build_rag_prompt("GARAN hakkında haberler", [], "Garanti BBVA (GARAN)")

    assert "özetlemeye devam et" in prompt
    assert "özetlemeden bırakma" in prompt


def test_ozne_bilinmiyorsa_modelden_soruyu_yorumlamasi_istenir():
    """Sembolsuz sorularda ozne yoktur; model soruyu kendisi yorumlar."""
    prompt = _build_rag_prompt("havacılık sektöründe neler oluyor", [])

    assert "Sorunun öznesi:" not in prompt
    assert "Sorunun öznesini kullanıcının sorusundan kendin çıkar." in prompt


def test_ozne_etiketi_kodu_adin_icinde_geciyorsa_tekrarlamaz():
    """ "Ham Petrol (BRENT) (BRENT)" gibi bir etiket modele hicbir sey anlatmaz."""
    assert _ozne_etiketi("Türk Hava Yolları", "THYAO") == "Türk Hava Yolları (THYAO)"
    assert _ozne_etiketi("Ham Petrol (BRENT)", "BRENT") == "Ham Petrol (BRENT)"
    assert _ozne_etiketi(None, "THYAO") == "THYAO"
    assert _ozne_etiketi(None, None) is None


async def test_alandan_cozulen_sembol_ozet_promptuna_ozne_yazilmaz():
    """Alandan cozulen sembol ozne olarak kullanilmaz: "Baykar savunma
    sanayinde" ASELS'e cozuluyor ama sorulan sirket o degil.
    """

    async def sabit_rag_search(query, top_k=5, filters=None):
        return {"chunks": [{"source": "aa.com.tr", "date": "2026-08-13", "text": "..."}]}

    sunucu = MCPServer(name="rag")
    sunucu.register_tool("rag_search", sabit_rag_search)
    llm = SahteLLM()
    ajan = MarketResearchAgent(
        mcp_client=MCPClient({"rag": sunucu}),
        llm=llm,
        timeout_seconds=5,
    )

    await ajan._run_rag(
        {"query": "savunma sanayi nasıl gidiyor", "symbol": "ASELS", "symbol_alandan": True},
        "savunma sanayi nasıl gidiyor",
    )

    assert "ASELS" not in llm.prompts[0]
    assert "Sorunun öznesini kullanıcının sorusundan kendin çıkar." in llm.prompts[0]
