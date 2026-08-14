"""PortfolioAgent - kullanicinin portfoyunu MCP tool'lari uzerinden analiz eder.

SOZLESME
    Node adi: `portfolio`. Bagimliligi YOKTUR, bu yuzden `market_research` ile
    PARALEL calisir (mimari v4 bolum 5.2). Yalnizca kendi alanina yazar:

        {"portfolio_data": {...}}

VERI ERISIMI
    Ajan veritabanina DOGRUDAN ERISMEZ (NFR-04); `portfolio_*` ve `user_*`
    tool'larini cagirir. `user_id` tool argumanlarinda GECMEZ - MCP katmani onu
    contextvar'dan alir (mimari v4 bolum 6.1), boylece bir prompt injection
    baskasinin portfoyunu isteyemez.

LLM KULLANIMI
    Bu ajan sayilari kendisi hesaplamaz ve LLM'e de hesaplatmaz: tum tutarlar
    DB view'larindan gelir. LLM yalnizca (bagliysa) kisa bir Turkce yorum
    yazar; bagli degilse deterministik bir ozet uretilir. Yorum uretilemese
    bile `portfolio_data` doludur - synthesizer rakamlarla calisabilir.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.base import BaseAgent
from app.mcp.server import CORE_SERVER_NAME
from app.orchestration.models import AgentError, AgentState

logger = logging.getLogger(__name__)

AGENT_NAME = "portfolio"

#: LLM yorumu icin gonderilecek en fazla varlik sayisi (baglam sismesin).
MAX_HOLDINGS_IN_PROMPT = 10


class PortfolioAgent(BaseAgent):
    """Portfoy ozeti, varlik listesi ve dagilim analizi."""

    name = AGENT_NAME

    def __init__(self, mcp_client, llm=None, timeout_seconds: int = 20) -> None:
        super().__init__(mcp_client=mcp_client, llm=llm, timeout_seconds=timeout_seconds)

    async def _execute(self, state: AgentState) -> dict:
        # Router bu ajani istemediyse ucuz no-op: tool/LLM cagrisi yapilmaz.
        if not self.is_requested(state):
            logger.debug("portfoy ajani atlandi", extra={"agent": self.name})
            return {}

        ozet = await self.call_tool(CORE_SERVER_NAME, "portfolio_get_summary")
        holdings = await self.call_tool(CORE_SERVER_NAME, "portfolio_get_holdings")
        dagilim = await self.call_tool(CORE_SERVER_NAME, "portfolio_get_allocation")

        portfolio_data: dict[str, Any] = {
            "summary": ozet,
            "holdings": holdings.get("holdings", []),
            "allocation": dagilim.get("allocation", []),
        }

        # Islem gecmisi YALNIZCA sorguda istendiginde cekilir: her istekte
        # cagirmak gereksiz tool yuku ve baglam sismesi demek.
        if self._islem_gecmisi_isteniyor(state.user_query):
            islemler = await self.call_tool(
                CORE_SERVER_NAME, "portfolio_get_transactions", {"limit": 10}
            )
            portfolio_data["transactions"] = islemler.get("transactions", [])

        yorum, hata = await self._yorumla(state.user_query, portfolio_data)
        portfolio_data["summary_text"] = yorum

        guncelleme: dict = {"portfolio_data": portfolio_data}
        if hata is not None:
            guncelleme["agent_errors"] = [hata]
        return guncelleme

    # ------------------------------------------------------------------
    # Yardimcilar
    # ------------------------------------------------------------------

    @staticmethod
    def _islem_gecmisi_isteniyor(query: str) -> bool:
        normalized = query.translate(_TR_TRANSLATION).lower()
        return any(k in normalized for k in ("islem", "alim", "satim", "gecmis", "hareket"))

    async def _yorumla(self, query: str, veri: dict) -> tuple[str, AgentError | None]:
        """Portfoy verisini kisa bir Turkce metne cevirir.

        LLM bagli degilse (model karari henuz verilmedi) deterministik ozet
        uretilir; rakamlar zaten hesaplanmis oldugu icin bilgi kaybi olmaz.
        """
        if self.llm is None:
            return self._deterministik_ozet(veri), None

        try:
            return await self.generate(_prompt_yaz(query, veri)), None
        except Exception as exc:  # noqa: BLE001 - LLM cokse de rakamlar korunmali
            logger.exception("portfoy yorumu uretilemedi", extra={"agent": self.name})
            return self._deterministik_ozet(veri), AgentError(
                agent_name=self.name,
                error_type="llm_error",
                message=f"Portfoy yorumu model tarafindan uretilemedi: {exc}",
            )

    @staticmethod
    def _deterministik_ozet(veri: dict) -> str:
        """LLM'siz ozet - yalnizca hesaplanmis rakamlari cumleye dokerr."""
        ozet = veri.get("summary") or {}
        satirlar: list[str] = []

        if ozet.get("total_value_try") is not None:
            satirlar.append(
                f"Portfoy toplam degeri {_tl(ozet['total_value_try'])}, "
                f"kar/zarar {_tl(ozet.get('total_pnl_try'))} "
                f"({_pct(ozet.get('total_pnl_pct'))})."
            )

        holdings = veri.get("holdings") or []
        if holdings:
            en_buyuk = holdings[0]
            satirlar.append(
                f"En buyuk pozisyon {en_buyuk['symbol']} "
                f"({_tl(en_buyuk.get('market_value_try'))})."
            )
            zararda = [h for h in holdings if (h.get("pnl_pct") or 0) < 0]
            if zararda:
                isimler = ", ".join(h["symbol"] for h in zararda[:3])
                satirlar.append(f"Zararda olan pozisyonlar: {isimler}.")

        dagilim = veri.get("allocation") or []
        if dagilim:
            parcalar = ", ".join(f"{d['asset_class']} %{d['class_pct']}" for d in dagilim)
            satirlar.append(f"Varlik dagilimi: {parcalar}.")

        return " ".join(satirlar) or "Portfoyde gosterilecek varlik bulunmuyor."

    async def get_tools(self) -> list:
        """Bu ajanin erisebilecegi tool'lar: `portfolio_*` ve `user_*`.

        Taban siniftaki "ajan adi + _" onek filtresi burada yeterlidir
        (`portfolio_`), ancak profil tool'u da gerektigi icin ad onegi yerine
        acik liste kullanilir. Piyasa ve RAG tool'lari bilincli olarak
        DISARIDA birakilmistir (mimari v4 bolum 6.3).
        """
        if self.mcp_client is None:
            return []

        tools = await self.mcp_client.get_tools(server=CORE_SERVER_NAME)
        return [t for t in tools if t["tool"].startswith(("portfolio_", "user_"))]


_TR_TRANSLATION = str.maketrans("çğıöşüÇĞİÖŞÜâîûÂÎÛ", "cgiosuCGIOSUaiuAIU")


def _tl(value) -> str:
    return f"{float(value):,.2f} TL".replace(",", ".") if value is not None else "bilinmiyor"


def _pct(value) -> str:
    return f"%{float(value):.2f}" if value is not None else "%-"


def _prompt_yaz(query: str, veri: dict) -> str:
    """Kaynaga dayali (grounded) portfoy yorumu prompt'u.

    Modelden ACIKCA yeni sayi URETMEMESI istenir; verilen rakamlarin disina
    cikmasi izlenebilirligi bozar ve dashboard ile ajan farkli rakam gosterir.
    """
    ozet = veri.get("summary") or {}
    holdings = (veri.get("holdings") or [])[:MAX_HOLDINGS_IN_PROMPT]

    satirlar = [
        f"Kullanici sorusu: {query}",
        "",
        "Portfoy ozeti (TRY):",
        f"- Toplam deger: {ozet.get('total_value_try')}",
        f"- Toplam maliyet: {ozet.get('total_cost_try')}",
        f"- Kar/zarar: {ozet.get('total_pnl_try')} ({ozet.get('total_pnl_pct')}%)",
        "",
        "Varliklar:",
    ]
    satirlar.extend(
        f"- {h['symbol']} ({h.get('asset_class')}): deger {h.get('market_value_try')} TL, "
        f"kar/zarar {h.get('pnl_pct')}%"
        for h in holdings
    )
    satirlar += [
        "",
        "Yukaridaki rakamlara dayanarak Turkce, kisa (en fazla 4 cumle) bir portfoy "
        "degerlendirmesi yaz. YENI SAYI URETME, yalnizca verilen rakamlari kullan. "
        "Yatirim tavsiyesi verme, yalnizca durumu betimle.",
        "",
        "Degerlendirme:",
    ]
    return "\n".join(satirlar)
