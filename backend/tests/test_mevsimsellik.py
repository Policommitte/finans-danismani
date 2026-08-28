"""Sembol cozumleme + mevsimsellik testleri.

Bu dosya tek bir gercek sikayetten dogdu: "yaz baslamadan THYAO almayi
dusunuyorum, son yillarin yaz donemine bakarak tavsiye eder misin?" sorusuna
sistem tamamen genel bir yanit veriyordu. Sebep modelin zayifligi DEGILDI -
veri yollarinin hepsi kapaliydi:

  1. Sorgudan sembol "HISSE" olarak cikariliyordu ("hissesi" kelimesi + Turkce
     ek deseni). Yanlis sembol RAG aramasini olmayan bir sirkete filtreliyor,
     fiyat sorgusunu da bosa dusuruyordu.
  2. Takvimin belirli bir dilimini yillar boyunca karsilastiracak HICBIR arac
     yoktu; `market_get_history` yalnizca "bugunden geriye N gun" verir.

Buradaki testler iki duzeltmeyi de sabitler.
"""

from datetime import date, timedelta

import pytest

import app.mcp.server as srv
from app.agents.market_research import (
    _MEVSIMSEL_ASGARI_YIL,
    MarketResearchAgent,
    _mevsim_araligi,
    sembol_coz,
)
from app.mcp.client import MCPClientError, MCPToolExecutionError
from app.orchestration.models import AgentState

KATALOG = [
    {"symbol": "THYAO", "ad": "Türk Hava Yolları"},
    {"symbol": "SASA", "ad": "Sasa Polyester"},
    {"symbol": "ASELS", "ad": "Aselsan Elektronik"},
    {"symbol": "BTC", "ad": "Bitcoin"},
]


# ---------------------------------------------------------------------------
# sembol_coz - katalogdan cozumleme
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu, beklenen",
    [
        # Sikayete yol acan sorgunun kendisi. Eski regex "HISSE" doneuyordu.
        ("yaz başlamadan thyao hissesi almayı düşünüyorum", "THYAO"),
        ("thyao hissesi hakkında ne düşünüyorsun", "THYAO"),
        ("THYAO hissesi hakkında ne düşünüyorsun", "THYAO"),
        ("bana thyaonun son 1 yıldaki karlılığını söyler misin", "THYAO"),
        # Eski desen 4-5 harf ARADIGI ve EK SARTI kostugu icin bunlari
        # tamamen kaciriyordu.
        ("sasa neden bu kadar düştü", "SASA"),
        ("sasanın durumu ne", "SASA"),
        # Sirket ADIYLA eslesme - kullanici kodu bilmek zorunda degil.
        ("aselsan hisselerinde son durum ne", "ASELS"),
        ("türk hava yolları ne durumda", "THYAO"),
        ("bitcoin yükselir mi", "BTC"),
    ],
)
def test_katalogdaki_sembol_bulunur(sorgu, beklenen):
    assert sembol_coz(sorgu, KATALOG) == beklenen


@pytest.mark.parametrize(
    "sorgu",
    [
        # Eski desenin urettigi YANLIS POZITIFLER. Hepsi None olmali:
        # katalogda BORSA, VERI, HISSE, DURUM diye bir varlik yok.
        "borsanın genel durumu nasıl",  # -> BORSA idi
        "enflasyon verisi ne zaman açıklanacak",  # -> VERI idi
        "hangi hisseyi almalıyım",  # -> HISSE idi
        "portföyümdeki hisselerin dağılımı nedir",
        "faiz kararı piyasayı nasıl etkiler",
    ],
)
def test_katalogda_olmayan_kelime_sembol_sayilmaz(sorgu):
    assert sembol_coz(sorgu, KATALOG) is None


def test_bos_katalogda_sembol_bulunmaz():
    assert sembol_coz("THYAO nasıl", []) is None


def test_tam_eslesme_ekli_eslesmeden_once_gelir():
    """Iki sembol de gecerse sorguda ONCE geceni ve tam olani sec."""
    assert sembol_coz("sasa ve thyao", KATALOG) == "SASA"
    assert sembol_coz("thyao ve sasa", KATALOG) == "THYAO"


# ---------------------------------------------------------------------------
# _mevsim_araligi - mevsim/ay penceresi cikarimi
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "sorgu, bas, bit",
    [
        ("son yıllardaki yaz dönemi oynamalarına bakarak", 6, 8),
        ("son yıllarda yaz aylarında thyao nasıl hareket etti", 6, 8),
        ("kış aylarında altın mevsimsel olarak yükselir mi", 12, 2),
        ("geçmiş yılların ilkbahar döneminde borsa", 3, 5),
        ("sonbahar aylarında genelde ne olur", 9, 11),
        ("temmuz ayında borsa genelde nasıl olur", 7, 7),
    ],
)
def test_mevsim_penceresi_cikarilir(sorgu, bas, bit):
    mevsim = _mevsim_araligi(sorgu)
    assert mevsim is not None
    assert (mevsim["start_month"], mevsim["end_month"]) == (bas, bit)


@pytest.mark.parametrize(
    "sorgu",
    [
        # "yaz" ayrica bir FIILDIR; mevsimsel isaret yoksa mevsim sayilmamali.
        "bana bir şiir yaz",
        "rapor yazar mısın",
        # Donem sorusu ama mevsimsel degil - `history_days` yolu bunu karsilar.
        "thyao son 1 yıldaki karlılığı",
        "portföyüm nasıl",
    ],
)
def test_mevsimsel_olmayan_sorgu_pencere_uretmez(sorgu):
    assert _mevsim_araligi(sorgu) is None


def test_yaz_kelimesi_yazilim_kelimesini_yakalamaz():
    """`\\byaz\\w*` deseni kullanilsaydi 'yazilim' da mevsim sayilirdi."""
    assert _mevsim_araligi("son yıllarda yazılım sektörü nasıl") is None


def test_yil_sayisi_sorgudan_okunur():
    assert _mevsim_araligi("son 3 yılın yaz döneminde thyao")["years"] == 3
    assert _mevsim_araligi("son yıllardaki yaz dönemi")["years"] == 5


# ---------------------------------------------------------------------------
# market_get_seasonality tool'u
# ---------------------------------------------------------------------------


class SahteMarketRepo:
    """`yil` yillik gunluk seri uretir; yazlar bilincli olarak farklidir."""

    def __init__(self, yil: int = 3) -> None:
        self.yil = yil
        self.en_erken = date.today() - timedelta(days=365 * yil)

    async def list_assets(self, category=None):
        return [{"symbol": k["symbol"], "name": k["ad"], "asset_class": "EQUITY"} for k in KATALOG]

    async def get_quote(self, symbol: str):
        if symbol.upper() != "THYAO":
            return None
        return {
            "symbol": "THYAO",
            "name": "Türk Hava Yolları",
            "price": 301.5,
            "currency": "TRY",
            "daily_change_pct": 1.2,
            "weekly_change_pct": 3.0,
            "ts": "2026-08-24T10:00:00",
        }

    async def get_history(self, symbol: str, days: int = 30):
        return await self.get_history_range(
            symbol,
            (date.today() - timedelta(days=days)).isoformat(),
            date.today().isoformat(),
        )

    async def get_history_range(self, symbol: str, start: str, end: str):
        if symbol.upper() != "THYAO":
            return []
        bas = max(date.fromisoformat(start), self.en_erken)
        son = date.fromisoformat(end)
        seri, gun = [], bas
        while gun <= son:
            fiyat = 100 + (gun - self.en_erken).days * 0.02
            if 6 <= gun.month <= 8:
                fiyat += (10 if gun.year % 2 == 0 else -6) * ((gun.month - 6) / 2 + 0.1)
            seri.append({"ts": gun.isoformat(), "price": round(fiyat, 2)})
            gun += timedelta(days=1)
        return seri


@pytest.fixture
def sahte_repo(monkeypatch):
    def _kur(yil: int = 3) -> SahteMarketRepo:
        repo = SahteMarketRepo(yil)
        monkeypatch.setattr(srv, "get_market_repository", lambda: repo)
        return repo

    return _kur


async def test_mevsimsellik_yillara_gore_getiri_dondurur(sahte_repo):
    sahte_repo(3)

    zarf = await srv.market_get_seasonality("THYAO", 6, 8, 5)

    assert zarf["ok"]
    veri = zarf["data"]
    # `year_count` TAMAMLANMIS yillari sayar; suren donem listede yer alir ama
    # "kac yila bakiyoruz" sorusunun cevabina dahil degildir.
    assert veri["year_count"] == len([d for d in veri["periods"] if not d["partial"]])
    assert all(d["change_pct"] is not None for d in veri["periods"])
    assert veri["average_change_pct"] is not None


async def test_devam_eden_donem_raporlanmaz(sahte_repo):
    """Yarim bir yazi tamamlanmis yillarla ayni tabloda gostermek ortalamayi bozar."""
    sahte_repo(3)

    veri = (await srv.market_get_seasonality("THYAO", 6, 8, 5))["data"]

    bugun = date.today()
    for donem in veri["periods"]:
        assert date.fromisoformat(donem["end"]) <= bugun


async def test_donemi_bastan_sona_kapsamayan_yil_atlanir(sahte_repo):
    """Veritabaninin basladigi yil, yazin yalnizca son gunlerini icerir.

    Kapsama denetimi olmasa o yil "tamamlanmis bir yaz" gibi tabloya girer;
    olculdu: 7 gunluk veri "+%0,13" olarak raporlanmisti.
    """
    sahte_repo(3)

    veri = (await srv.market_get_seasonality("THYAO", 6, 8, 5))["data"]

    assert veri["insufficient_periods"] >= 1
    # Kalan donemlerin hepsi gercekten dolu olmali.
    assert all(d["point_count"] > 60 for d in veri["periods"])


async def test_kis_donemi_yil_sinirini_asar(sahte_repo):
    """12 -> 2 penceresi bir sonraki yila tasar; etiket BASLADIGI yildir."""
    sahte_repo(3)

    veri = (await srv.market_get_seasonality("THYAO", 12, 2, 5))["data"]

    for donem in veri["periods"]:
        bas, bitis = date.fromisoformat(donem["start"]), date.fromisoformat(donem["end"])
        assert bas.year == donem["year"]
        assert bitis.year == donem["year"] + 1


async def test_veri_olmayan_sembol_hata_zarfi_dondurur(sahte_repo):
    sahte_repo(3)

    zarf = await srv.market_get_seasonality("YOKBU", 6, 8, 5)

    assert zarf["ok"] is False
    assert "YOKBU" in (zarf["error"] or "")


# ---------------------------------------------------------------------------
# Ajan entegrasyonu
# ---------------------------------------------------------------------------


class SahteMCPClient:
    """Gercek `MCPClient` gibi zarfi acar, `ok=False` degerini istisnaya cevirir."""

    def __init__(self, katalog_hatasi: bool = False) -> None:
        self.cagrilar: list[tuple[str, dict]] = []
        self.katalog_hatasi = katalog_hatasi

    async def call_tool(self, server, tool, arguments=None, agent=None):
        self.cagrilar.append((tool, dict(arguments or {})))
        if tool == "market_list_symbols" and self.katalog_hatasi:
            raise MCPClientError("katalog tool'u kayitli degil")
        if tool == "rag_search":
            return {"chunks": []}
        zarf = await getattr(srv, tool)(**(arguments or {}))
        if not zarf.get("ok"):
            raise MCPToolExecutionError(server, tool, RuntimeError(zarf.get("error") or tool))
        return zarf["data"]

    def arguman(self, tool: str) -> dict | None:
        for ad, arg in self.cagrilar:
            if ad == tool:
                return arg
        return None


SIKAYET_SORUSU = (
    "yaz başlamadan thyao hissesi almayı düşünüyorum bana son yıllardaki "
    "yaz dönemi oynamalarına bakarak thyao almamı tavsiye eder misin"
)


def _state(sorgu: str) -> AgentState:
    return AgentState(
        user_query=sorgu, user_id=1, thread_id=1, requested_agents=["market_research"]
    )


async def test_rag_filtresi_dogru_sembolu_alir(sahte_repo):
    """Hatanin ozu: RAG aramasi 'HISSE' sirketine filtreleniyordu."""
    sahte_repo(3)
    istemci = SahteMCPClient()

    await MarketResearchAgent(mcp_client=istemci)._execute(_state(SIKAYET_SORUSU))

    assert istemci.arguman("rag_search")["filters"]["symbol"] == "THYAO"


async def test_mevsimsellik_tool_u_cagrilir(sahte_repo):
    sahte_repo(3)
    istemci = SahteMCPClient()

    await MarketResearchAgent(mcp_client=istemci)._execute(_state(SIKAYET_SORUSU))

    arg = istemci.arguman("market_get_seasonality")
    assert arg == {"symbol": "THYAO", "start_month": 6, "end_month": 8, "years": 5}


async def test_ozet_gercek_sayilar_ve_gozlem_sayisi_icerir(sahte_repo):
    """Genel cumleler yerine olculmus getiriler; ve kac yila dayandigi."""
    sahte_repo(3)
    istemci = SahteMCPClient()

    sonuc = await MarketResearchAgent(mcp_client=istemci)._execute(_state(SIKAYET_SORUSU))
    ozet = sonuc["market_data"]["summary"]

    assert "yaz (Haziran-Agustos)" in ozet
    assert "%" in ozet
    mevsim = sonuc["market_data"]["live_data"]["seasonality"]
    assert mevsim["year_count"] >= 1
    # Az gozlem varsa kullanici bunu ACIKCA gormeli.
    if mevsim["year_count"] < _MEVSIMSEL_ASGARI_YIL:
        assert "yeterli" in ozet.lower()


async def test_katalogda_sembol_yoksa_regex_tahmini_dusurulur(sahte_repo):
    """'hangi hisseyi almaliyim' -> eski kod RAG'i HISSE'ye filtreliyordu."""
    sahte_repo(3)
    istemci = SahteMCPClient()

    await MarketResearchAgent(mcp_client=istemci)._execute(_state("hangi hisseyi almalıyım"))

    assert istemci.arguman("rag_search")["filters"] == {}


async def test_katalog_okunamazsa_ajan_calismaya_devam_eder(sahte_repo):
    """Yeni tool baglanmamis bir ortamda ajan cokmemeli (kademeli bozulma)."""
    sahte_repo(3)
    istemci = SahteMCPClient(katalog_hatasi=True)

    sonuc = await MarketResearchAgent(mcp_client=istemci)._execute(_state(SIKAYET_SORUSU))

    assert sonuc["market_data"]["summary"]
    assert istemci.arguman("rag_search") is not None


async def test_katalog_onbellege_alinir(sahte_repo):
    """Her sorguda katalog tool'u tekrar cagrilmamali."""
    sahte_repo(3)
    istemci = SahteMCPClient()
    ajan = MarketResearchAgent(mcp_client=istemci)

    await ajan._execute(_state("thyao nasıl"))
    await ajan._execute(_state("sasa nasıl"))

    assert sum(1 for ad, _ in istemci.cagrilar if ad == "market_list_symbols") == 1


# ---------------------------------------------------------------------------
# Suren donem: "bu yaz" tamamen atilmamali
#
# Kullanici sikayeti: "son yillar deyince elindeki TUM veriye baksin, sadece
# gecen yila degil." Agustos sonunda o yilin yazi %93 bitmis oluyordu ama
# takvimde bitmedigi icin tabloya hic girmiyordu.
# ---------------------------------------------------------------------------


class IkiYillikRepo(SahteMarketRepo):
    """DB'de tam 2 yillik veri - kullanicinin gercek durumu."""

    def __init__(self) -> None:
        super().__init__(yil=2)


@pytest.fixture
def iki_yillik(monkeypatch):
    repo = IkiYillikRepo()
    monkeypatch.setattr(srv, "get_market_repository", lambda: repo)
    return repo


async def test_suren_donem_partial_isaretiyle_raporlanir(iki_yillik):
    veri = (await srv.market_get_seasonality("THYAO", 6, 8, 5))["data"]

    surenler = [d for d in veri["periods"] if d["partial"]]
    assert len(surenler) == 1
    assert surenler[0]["year"] == date.today().year
    # Bitis BUGUNE cekilir; ileri bir tarih raporlanmaz.
    assert date.fromisoformat(surenler[0]["end"]) <= date.today()


async def test_suren_donem_ortalamaya_katilmaz(iki_yillik):
    """Yarim donemi tamamlanmislarla ayni kefeye koymak ortalamayi kaydirir."""
    veri = (await srv.market_get_seasonality("THYAO", 6, 8, 5))["data"]

    tamamlanan = [d for d in veri["periods"] if not d["partial"]]
    assert veri["year_count"] == len(tamamlanan)
    beklenen = round(sum(d["change_pct"] for d in tamamlanan) / len(tamamlanan), 2)
    assert veri["average_change_pct"] == beklenen


async def test_henuz_baslamamis_donem_raporlanmaz(iki_yillik):
    """Aralik-Subat penceresi Agustos'ta daha baslamamistir."""
    veri = (await srv.market_get_seasonality("THYAO", 12, 2, 5))["data"]

    assert all(date.fromisoformat(d["end"]) <= date.today() for d in veri["periods"])


async def test_ajan_metni_suren_donemi_ayirt_eder(iki_yillik):
    istemci = SahteMCPClient()

    sonuc = await MarketResearchAgent(mcp_client=istemci)._execute(_state(SIKAYET_SORUSU))
    ozet = sonuc["market_data"]["summary"]

    assert "devam ediyor" in ozet
    assert "Tamamlanmis yillarin ortalamasi" in ozet


async def test_ajan_metni_elenen_donemleri_aciklar(iki_yillik):
    """Kullanici 'ama 2 yillik verim var' demeden once sebebini gormeli."""
    istemci = SahteMCPClient()

    sonuc = await MarketResearchAgent(mcp_client=istemci)._execute(_state(SIKAYET_SORUSU))

    assert "Hesaba katilamayan" in sonuc["market_data"]["summary"]
