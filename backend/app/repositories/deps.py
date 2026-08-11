from app.repositories.base import PortfolioRepository
from app.repositories.in_memory import InMemoryPortfolioRepository

_portfolio_repository = InMemoryPortfolioRepository()


def get_portfolio_repository() -> PortfolioRepository:
    return _portfolio_repository
