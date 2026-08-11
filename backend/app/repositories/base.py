from typing import Protocol


class PortfolioRepository(Protocol):
    def get_holdings(self, user_id: int) -> list[dict]: ...

    def get_summary(self, user_id: int) -> dict: ...