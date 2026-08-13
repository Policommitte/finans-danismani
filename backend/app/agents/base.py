"""Tum agent'lar icin ortak temel siniflar (BaseAgent, AgentResult)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from app.mcp.client import MCPClient


class AgentResult(BaseModel):
    """Her agent'in Orchestrator'a dondurdugu ortak sonuc zarfi.

    security_gate adimi, senteze gecmeden once success/error alanlarina
    bakarak bu sonucu isleme alip almayacagina karar verir.
    """

    agent_name: str
    data: dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    error: str | None = None


class BaseAgent(ABC):
    """MarketResearchAgent, PortfolioAgent, RiskStrategyAgent'in ortak temeli.

    Her agent kendi MCPClient'ini olusturmaz; paylasilan istemci Orchestrator
    tarafindan constructor'a enjekte edilir (dependency injection).
    """

    def __init__(self, name: str, mcp_client: MCPClient) -> None:
        self.name = name
        self._mcp_client = mcp_client

    @abstractmethod
    async def run(self, task: dict[str, Any]) -> AgentResult:
        """task, router'in bu agent icin urettigi eksiksiz ve bagimsiz talimattir.

        Bu agent, ayni istekte calisan diger agent'larin durumunu/ciktisini
        varsaymamalidir -- router bu agent'i hic cagirmayabilir ya da diger
        agent'lar olmadan tek basina cagirabilir.
        """
        raise NotImplementedError
