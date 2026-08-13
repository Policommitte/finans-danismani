from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    # DB entegrasyonu hazır olunca aktif edilecek:
    # database_url: str = "postgresql+psycopg://finans:finans@localhost:5432/finans"

    # RAG / Vector DB entegrasyonunda aktif edilecek:
    # vector_db_url: str = "http://localhost:8001"
    # embedding_model: str = ""

    # LLM entegrasyonunda kullanılacak (ajanlar sprint ?'te bağlanacak):
    llm_api_key: str = ""
    default_model: str = ""

    # Ajan bazlı model seçimi: ucuz model ajanlarda, güçlü model synthesizer'da.
    # Ücretsiz API kotasını korumak için bilinçli bir tercihtir.
    portfolio_model: str = ""
    market_model: str = ""
    risk_model: str = ""
    synthesizer_model: str = ""  # en güçlü model burada
    security_model: str = ""  # en küçük/hızlı model burada

    # Timeout — bir ajan asılırsa tüm istek düşmesin (graceful degradation).
    agent_timeout_seconds: int = 20
    synthesizer_timeout_seconds: int = 40

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def model_for(self, agent: str) -> str:
        overrides = {
            "portfolio": self.portfolio_model,
            "market": self.market_model,
            "risk": self.risk_model,
            "synthesizer": self.synthesizer_model,
            "security": self.security_model,
        }
        return overrides.get(agent) or self.default_model


settings = Settings()
