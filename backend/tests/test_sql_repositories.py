"""PostgreSQL repository entegrasyon testleri (§14-11).

BU TESTLER GERCEK BIR VERITABANI ISTER ve `TEST_DATABASE_URL` tanimli degilse
ATLANIR - CI'nin Postgres'siz calismasi bilincli bir tercihtir (bellek ici
implementasyon ayni sozlesmeyi uygular ve hizli testlerle kapsanir).

Calistirmak icin:

    docker compose up -d db
    TEST_DATABASE_URL=postgresql+psycopg://finans:finans@localhost:5432/finans \\
        pytest tests/test_sql_repositories.py

Sema `db/v5_schema_and_data.sql` ile yuklenmis olmalidir (docker-compose ilk
kalkista otomatik yukler).

BURADA SINANAN SEY: SQL implementasyonunun bellek ici implementasyonla AYNI
sozlesmeyi ve AYNI sayilari uretmesi. Ikisi ayrisirsa DB'li ve DB'siz calisan
gelistiriciler farkli ekran gorur.
"""

import os

import pytest

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL tanimli degil (Postgres gerektiren entegrasyon testi)",
)

#: Seed'deki 1 numarali portfoyun ilk toplami. Testler bu SAYIYA bagli DEGILDIR:
#: fiyat gorevi calistiktan sonra toplam degisir ve testin bozulmasi yanlis
#: alarm olurdu. Sayi yalnizca belge amaclidir; testler tutarlilik sinar.
SEED_TOPLAMI = 1_638_585.00


@pytest.fixture
def sql_repolar(monkeypatch):
    """Repository'leri gercek DB'ye baglar."""
    from app.config import settings
    from app.repositories import deps

    monkeypatch.setattr(settings, "database_url", TEST_DATABASE_URL)
    deps.reset_repositories()
    yield deps
    deps.reset_repositories()


async def test_baglanti_calisiyor(sql_repolar):
    from app.db.session import ping

    assert await ping() is True


async def test_kullanici_eposta_ile_bulunur(sql_repolar):
    user = await sql_repolar.get_user_repository().get_by_email("mehmet@example.com")

    assert user["id"] == 1
    assert user["password_hash"].startswith("$2b$")


async def test_profil_sorgusu_sifre_hashini_dondurmez(sql_repolar):
    user = await sql_repolar.get_user_repository().get_by_id(1)

    assert "password_hash" not in user


async def test_ozet_varlik_satirlariyla_tutarli(sql_repolar):
    """Ozet ile varlik listesi AYNI view zincirinden gelmeli.

    Toplam sabit bir sayiyla karsilastirilmaz: fiyat gorevi calistiginda deger
    degisir. Sinanan sey hesabin TEK kaynaktan gelmesi - iki uc ayrisirsa
    dashboard'da iki farkli toplam gorunur.
    """
    repository = sql_repolar.get_portfolio_repository()
    ozet = await repository.get_summary(1)
    varliklar = await repository.get_holdings(1)

    assert ozet["holding_count"] == len(varliklar) == 3
    beklenen = sum(float(v["market_value_try"]) for v in varliklar)
    assert round(float(ozet["total_value_try"]), 2) == round(beklenen, 2)


async def test_kar_zarar_deger_ile_maliyet_farkina_esit(sql_repolar):
    ozet = await sql_repolar.get_portfolio_repository().get_summary(1)

    fark = float(ozet["total_value_try"]) - float(ozet["total_cost_try"])
    assert round(float(ozet["total_pnl_try"]), 2) == round(fark, 2)


async def test_varsayilan_portfoy_secilir(sql_repolar):
    repository = sql_repolar.get_portfolio_repository()

    assert await repository.get_default_portfolio_id(1) == 1


async def test_baska_kullanicinin_portfoyu_gorunmez(sql_repolar):
    """Derinlemesine savunma: portfolio_id gonderilse bile user_id filtresi var."""
    varliklar = await sql_repolar.get_portfolio_repository().get_holdings(user_id=2, portfolio_id=1)

    assert varliklar == []


async def test_dagilim_yuzdeleri_100_e_tamamlanir(sql_repolar):
    dagilim = await sql_repolar.get_portfolio_repository().get_allocation(1)

    toplam = sum(float(d["class_pct"]) for d in dagilim)
    assert abs(toplam - 100.0) < 0.05


async def test_fiyat_gecmisi_backfill_den_gelir(sql_repolar):
    seri = await sql_repolar.get_market_repository().get_history("THYAO", days=30)

    assert len(seri) > 100  # 4 saat cozunurluk -> gunde ~6 satir
    assert [s["ts"] for s in seri] == sorted(s["ts"] for s in seri)


async def test_rag_aramasi_bm25_ile_sonuc_doner(sql_repolar):
    """Embedding modeli secilene kadar arama BM25 ayagiyla calisir."""
    sonuclar = await sql_repolar.get_rag_repository().search("THYAO net kar", top_k=5)

    assert sonuclar
    assert {"doc_id", "baslik", "sirket", "tarih", "tip", "content", "score"} <= set(sonuclar[0])


async def test_rag_aramasi_sirket_filtresine_uyar(sql_repolar):
    """Filtre SEMBOL ile calismali.

    Dokumanlarda `sirket` alani UNVAN tasiyor ("Türk Hava Yolları"), ajanlar ise
    sorgudan SEMBOL cikariyor ("THYAO"). Yalnizca unvana bakan bir filtre, ajanin
    her filtreli aramasinda sessizce bos donerdi.
    """
    sonuclar = await sql_repolar.get_rag_repository().search("yolcu doluluk", sirket="THYAO")

    assert sonuclar, "sembol ile filtreleme unvanla yazilmis dokumani bulmali"
    assert all(s["symbol"] == "THYAO" for s in sonuclar)


async def test_rag_aramasi_turkce_kelimeleri_ORlar(sql_repolar):
    """plainto_tsquery AND'lerse dogal dildeki soru sessizce bos doner."""
    sonuclar = await sql_repolar.get_rag_repository().search(
        "THYAO yolcu doluluk oranı ne oldu", top_k=5
    )

    assert sonuclar, "tum kelimelerin ayni chunk'ta gecmesi beklenmemeli (OR)"


async def test_sohbet_kaydedilir_ve_okunur(sql_repolar):
    repository = sql_repolar.get_chat_repository()

    oturum = await repository.create_session(1, "Entegrasyon testi sohbeti")
    await repository.add_message(oturum["id"], "user", "Portfoyum nasil?")
    await repository.add_message(oturum["id"], "assistant", "Iyi gidiyor.", meta={"sources": []})

    mesajlar = await repository.list_messages(oturum["id"])
    assert [m["sender_role"] for m in mesajlar] == ["user", "assistant"]
    assert mesajlar[1]["meta"] == {"sources": []}


async def test_baskasinin_oturumu_okunamaz(sql_repolar):
    repository = sql_repolar.get_chat_repository()
    oturum = await repository.create_session(1, "Sahiplik testi")

    assert await repository.get_session(oturum["id"], user_id=2) is None


async def test_fiyat_guncellemesi_yazilir_ve_degisim_hesaplanir(sql_repolar):
    """Fiyat yazimi DESTRUKTIFTIR; test kendi degisikligini geri alir.

    Alinmasaydi bu testten sonra calisan toplam/dagilim testleri seed degerini
    degil guncellenmis fiyati gorurdu - hem de yalnizca sira degistiginde
    bozulan, bulunmasi zor bir bicimde.
    """
    repository = sql_repolar.get_market_repository()
    varliklar = await repository.get_prices_for_simulation()
    hedef = next(v for v in varliklar if v["symbol"] == "THYAO")
    eski_fiyat = round(float(hedef["current_price"]), 4)

    try:
        yeni_fiyat = round(eski_fiyat * 1.05, 4)
        await repository.apply_price_updates(
            [{"asset_id": hedef["asset_id"], "price": yeni_fiyat}], write_history=True
        )

        quote = await repository.get_quote("THYAO")
        assert round(float(quote["price"]), 4) == yeni_fiyat
        # daily_change_pct seed degerinde DONMAMALI (mimari v4 bolum 8.2)
        assert float(quote["daily_change_pct"]) != 1.2
    finally:
        await repository.apply_price_updates(
            [{"asset_id": hedef["asset_id"], "price": eski_fiyat}], write_history=False
        )


async def test_denetim_kayitlari_yazilir(sql_repolar):
    import uuid

    from sqlalchemy import text

    from app.db.session import get_session_factory

    request_id = str(uuid.uuid4())
    await sql_repolar.get_audit_repository().log_tool_call(
        {
            "request_id": request_id,
            "session_id": None,
            "user_id": 1,
            "agent_name": "portfolio",
            "tool_name": "core.portfolio_get_summary",
            "args": {"limit": 10},
            "success": True,
            "latency_ms": 12.5,
            "error": None,
        }
    )

    async with get_session_factory()() as session:
        sonuc = await session.execute(
            text("SELECT agent_name, args FROM tool_calls WHERE request_id = CAST(:r AS UUID)"),
            {"r": request_id},
        )
        satir = sonuc.mappings().one()

    assert satir["agent_name"] == "portfolio"
    assert satir["args"] == {"limit": 10}


async def test_sql_ve_bellek_ici_ayni_sozlesmeyi_uygular(sql_repolar):
    """Iki implementasyon ayrisirsa DB'li ve DB'siz gelistirici farkli ekran gorur.

    Fiyatlar (fiyat gorevi yuzunden) ayrisabilir; AYNI olmasi gerekenler
    sozlesme ve portfoy icerigidir: ayni alanlar, ayni varliklar, ayni maliyet.
    """
    from app.repositories.in_memory import InMemoryPortfolioRepository

    sql_repository = sql_repolar.get_portfolio_repository()
    bellek_repository = InMemoryPortfolioRepository()

    sql_varliklar = await sql_repository.get_holdings(1)
    bellek_varliklar = await bellek_repository.get_holdings(1)
    sql_ozet = await sql_repository.get_summary(1)
    bellek_ozet = await bellek_repository.get_summary(1)

    assert set(sql_ozet) >= set(bellek_ozet), "ozet alan kumeleri ayrisamaz"
    assert set(sql_varliklar[0]) >= set(bellek_varliklar[0]), "varlik alanlari ayrisamaz"

    # Fiyattan ve FX kurundan BAGIMSIZ olan alanlar birebir ayni olmali.
    # (Tutarlar karsilastirilmaz: fiyat gorevi calistiginda hem deger hem de
    # USD varliklarin TRY maliyeti degisir - bu bir uyusmazlik degil.)
    def _pozisyonlar(satirlar):
        return {
            v["symbol"]: (float(v["quantity"]), float(v["average_buy_price"])) for v in satirlar
        }

    assert _pozisyonlar(sql_varliklar) == _pozisyonlar(bellek_varliklar)
