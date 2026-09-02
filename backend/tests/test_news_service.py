import asyncio

from app.services.news import FALLBACK_TITLE_LENGTH, _fallback_title, _haber


def test_fallback_title_uses_first_sentence_and_normalizes_whitespace():
    title = _fallback_title(
        "  Altın fiyatları haftaya yükselişle başladı.\nİkinci cümle özette kalmalı.  "
    )

    assert title == "Altın fiyatları haftaya yükselişle başladı."


def test_fallback_title_removes_simple_author_prefix():
    title = _fallback_title(
        "Eren SAKARYA Küresel piyasalarda altın yükselişini sürdürdü. Ayrıntılar açıklandı."
    )

    assert title == "Küresel piyasalarda altın yükselişini sürdürdü."


def test_fallback_title_summarizes_long_sentence_without_cutting_it():
    title = _fallback_title(
        "Değerli metallerde hafta başında küresel gelişmelerin etkisiyle "
        "fiyatların yeniden yukarı yönlü hareket etmesi yükselişi destekledi."
    )

    assert title == "Küresel gelişmeler değerli metallerdeki yükselişi destekliyor"
    assert len(title) <= FALLBACK_TITLE_LENGTH


def test_fallback_title_uses_category_when_topic_is_not_explicit():
    title = _fallback_title(
        "Haftanın ilk işlem gününde yatırımcıların temkinli tutumu ve artan "
        "oynaklık fiyatlamalar üzerinde etkili olmaya devam etti.",
        "doviz",
    )

    assert title == "Döviz piyasası hareketli seyrediyor"


def test_fallback_title_prefers_last_trend_signal_in_sentence():
    title = _fallback_title(
        "Orta Doğu'daki gerilimin azalmasıyla güvenli liman talebi değişirken "
        "altın fiyatlarında yükseliş hız kazandı."
    )

    assert title == "Altın fiyatları yükselişte"


def test_fallback_title_does_not_confuse_falling_bond_yields_with_gold():
    title = _fallback_title(
        "Değerli metallerde enflasyonist endişelerin hafiflemesi yükselişi "
        "desteklerken gerileyen tahvil faizleri de altına güç verdi."
    )

    assert title == "Küresel gelişmeler değerli metallerdeki yükselişi destekliyor"


def test_fallback_title_recognizes_inflected_increase_word():
    title = _fallback_title(
        "Spot altının ons fiyatı sabah saatlerinde yüzde 0,44 yükselerek son "
        "fiyatlamalarda 4 bin 393 dolara çıktı."
    )

    assert title == "Ons altın yüzde 0,44 yükseldi"


def test_fallback_title_uses_multi_month_high_as_distinguishing_detail():
    title = _fallback_title(
        "İvme kazanan altın fiyatları perşembe günü iki ayın en yüksek "
        "seviyelerine yakın seyretti ve güçlü görünümünü korudu."
    )

    assert title == "Altın fiyatları son iki ayın zirvesine yaklaştı"


def test_fallback_title_keeps_rally_duration():
    title = _fallback_title(
        "Küresel piyasalarda altın güçlü bir başlangıç yaparak yükseliş "
        "serisini üçüncü güne taşıdı ve haftalık kazançlarını korudu."
    )

    assert title == "Altın fiyatları yükselişini üçüncü güne taşıdı"


def test_fallback_title_describes_bist_content_instead_of_only_result():
    title = _fallback_title(
        "Borsa İstanbul'da BIST 100 endeksi haftayı yüzde 2,85 artışla "
        "tamamladı. Hafta boyunca teknoloji, sanayi ve mali sektör endeksleri "
        "farklı performanslar gösterdi.",
        "hisse",
    )

    assert title == "BIST 100 ve sektörlerin haftalık görünümü"


def test_fallback_title_uses_event_even_when_category_is_misleading():
    title = _fallback_title(
        "Türkiye Cumhuriyet Merkez Bankası ikinci çeyrek TGFE verilerini "
        "açıkladı. Konut fiyatları çeyreklik ve yıllık bazda değerlendirildi.",
        "hisse",
    )

    assert title == "TCMB ticari gayrimenkul fiyat verilerini açıkladı"


def test_fallback_title_describes_company_disclosure():
    title = _fallback_title(
        "OYAK Çimento, TCC Group Holdings'in yeni yapılanma kararına ilişkin "
        "açıklama yayımladı. Şirket ayrıntıları KAP üzerinden paylaştı.",
        "hisse",
    )

    assert title == "OYAK Çimento'dan yeni yapılanma açıklaması"


def test_fallback_title_describes_geopolitical_market_context():
    title = _fallback_title(
        "Orta Doğu kaynaklı jeopolitik gelişmeler piyasaların yönü üzerinde "
        "belirleyici olmaya devam ediyor ve belirsizliği artırıyor.",
        "hisse",
    )

    assert title == "Jeopolitik gelişmeler piyasaların yönünü belirliyor"


def test_fallback_title_has_safe_empty_value():
    assert _fallback_title("  \n ") == "Piyasa haberi"


def test_news_response_generates_title_only_when_stored_title_is_empty():
    article = asyncio.run(
        _haber(
            {
                "id": 1,
                "baslik": "   ",
                "raw_text": "Piyasalar güne yükselişle başladı. Ayrıntılar gün içinde izlenecek.",
                "image_url": "/news/test.jpg",
            },
            {},
        )
    )

    assert article.baslik == "Piyasalar güne yükselişle başladı."


def test_news_response_preserves_existing_title():
    article = asyncio.run(
        _haber(
            {
                "id": 2,
                "baslik": "Mevcut haber başlığı",
                "raw_text": "İlk cümle farklı bir metin içeriyor.",
                "image_url": "/news/test.jpg",
            },
            {},
        )
    )

    assert article.baslik == "Mevcut haber başlığı"


# ---------------------------------------------------------------------------
# Gorsel cozumlemesi istek DISINDA
#
# Eskiden gorseli olmayan her haber icin `_haber` Pexels'i istek icinde
# bekliyordu (5'lik semafor, 6 sn timeout, sonra UPDATE); soguk tabloda
# GET /api/market/news onlarca saniye suruyor ve bulten perdesi asili
# kaliyordu. Artik yanit aninda doner, arama arka plana birakilir.
# ---------------------------------------------------------------------------


def test_gorselsiz_haber_pexelsi_beklemez(monkeypatch):
    import app.services.news as news_modulu

    async def yavas_pexels(*_args, **_kwargs):
        await asyncio.sleep(5)
        return "https://pexels.example/asla-gelmez.jpg"

    baslatilan: list[int] = []

    def sahte_arka_plan(document_id, kategori, baslik):
        baslatilan.append(document_id)

    monkeypatch.setattr(news_modulu, "search_photo", yavas_pexels)
    monkeypatch.setattr(news_modulu, "gorseli_arka_planda_coz", sahte_arka_plan)

    async def calistir():
        return await asyncio.wait_for(
            _haber(
                {
                    "id": 7,
                    "baslik": "Bütçe uygulama sonuçları açıklandı",
                    "raw_text": "Metin.",
                    "kategori": "ekonomi",
                    "image_url": None,
                },
                {},
            ),
            timeout=1.0,
        )

    article = asyncio.run(calistir())

    assert article.image_url  # kategori/yerel gorsel HEMEN dondu
    assert "pexels" not in article.image_url
    assert baslatilan == [7]  # arama arka plana birakildi


def test_arka_plan_cozumlemesi_ayni_belge_icin_tekrar_baslamaz(monkeypatch):
    import app.services.news as news_modulu

    cagri = 0

    async def sahte_resolve(document_id, kategori, baslik):
        nonlocal cagri
        cagri += 1
        await asyncio.sleep(0.05)
        return "x"

    monkeypatch.setattr(news_modulu, "resolve_image", sahte_resolve)
    news_modulu._devam_eden_cozumlemeler.clear()

    async def senaryo():
        news_modulu.gorseli_arka_planda_coz(99, "hisse", "Deneme")
        news_modulu.gorseli_arka_planda_coz(99, "hisse", "Deneme")  # surerken: yok sayilir
        await asyncio.sleep(0.2)
        news_modulu.gorseli_arka_planda_coz(99, "hisse", "Deneme")  # bitti: yeniden baslar
        await asyncio.sleep(0.2)

    asyncio.run(senaryo())

    assert cagri == 2
    assert news_modulu._devam_eden_cozumlemeler == set()


def test_yerel_gorselli_haber_icin_arka_plan_gorevi_acilmaz():
    import app.services.news as news_modulu

    news_modulu._devam_eden_cozumlemeler.clear()

    baslik = "THY yeni uçak siparişi verdi"
    # On kosul: baslik gercekten yerel gorsele dusuyor (Pexels gerekmez).
    assert news_modulu._local_keyword_image(baslik)

    async def senaryo():
        news_modulu.gorseli_arka_planda_coz(5, "hisse", baslik)
        return set(news_modulu._devam_eden_cozumlemeler)

    assert asyncio.run(senaryo()) == set()
