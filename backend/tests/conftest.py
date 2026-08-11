import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.repositories.deps import get_portfolio_repository


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class FakePortfolioRepository:
    def get_holdings(self, user_id: int) -> list[dict]:
        return [
            {"asset_type": "hisse", "symbol": "TEST", "quantity": 1, "current_value": 100.0, "weight_pct": 100.0}
        ]

    def get_summary(self, user_id: int) -> dict:
        return {"total_value": 100.0, "currency": "TRY", "holding_count": 1}


@pytest.fixture
def client_with_fake_repo() -> TestClient:
    app.dependency_overrides[get_portfolio_repository] = FakePortfolioRepository
    yield TestClient(app)
    app.dependency_overrides.clear()