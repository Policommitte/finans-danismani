from app.config import settings


def test_cors_origin_list_parses_comma_separated(ayar):
    ayar(cors_origins="http://a.com, http://b.com ,")

    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]


def test_model_for_falls_back_to_default_model(ayar):
    ayar(default_model="genel-model", portfolio_model="")

    assert settings.model_for("portfolio") == "genel-model"


def test_model_for_prefers_agent_override(ayar):
    ayar(default_model="genel-model", portfolio_model="ozel-model")

    assert settings.model_for("portfolio") == "ozel-model"
