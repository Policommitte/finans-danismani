from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://finans:finans@localhost:5432/finans"

    vector_db_url: str = "http://localhost:8001"
    embedding_model: str = ""

    llm_api_key: str = ""
    default_model: str = ""

    portfolio_model: str = ""
    market_model: str = ""
    risk_model: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def model_for(self, agent: str) -> str:
        overrides = {
            "portfolio": self.portfolio_model,
            "market": self.market_model,
            "risk": self.risk_model,
        }
        return overrides.get(agent) or self.default_model


settings = Settings()
