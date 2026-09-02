"""`rag.documents.baslik` alanindaki scraping artiklarini temizler ve bos
basliklari doldurur.

NEDEN TEK SEFERLIK BIR SCRIPT
    Haber korpusu SABITTIR: bir kez birkac site scrape edilip DB'ye yazilmis,
    akan yeni veri yok. Bu yuzden dogru cozum her istekte goruntu katmaninda
    kirpmak degil, veriyi BIR KEZ duzeltmektir. Kalici bir ingestion hattı
    olsaydi bu mantik oraya tasinmaliydi.

NE DUZELTIR
    1. ZAMAN ETIKETI ARTIKLARI - liste sayfasindaki "1 gun once" rozeti
       basliga yapismis geliyor ve arada BOSLUK YOK:

           "1 gün önceBakan Uraloğlu: 24 yılda ..."
           "5 sa önce5 yıldır zirve değişmedi... İşt"

    2. BOS BASLIKLAR - `baslik` kolonu NOT NULL ama bos string ('') gecebiliyor;
       234 dokumanin 82'si (%35) boyle olculdu. Bunlar `raw_text`'in ilk
       cumlesinden doldurulur.

NEDEN ONEMLI
    Baslik yalnizca goruntu meselesi degil: `_to_source` kaynak kartinda onu
    gosteriyor, ve korpus yeniden gomulurse (baslik chunk metnine onek olarak
    eklenerek) baslik hem BM25 indeksine hem embedding'e girer. Yani temiz
    baslik = daha iyi arama.

KULLANIM
    Once RAPOR (varsayilan - hicbir sey yazmaz):

        cd backend && venv/bin/python -m scripts.temizle_dokuman_basliklari

    Sonuclari inceleyip uygula:

        cd backend && venv/bin/python -m scripts.temizle_dokuman_basliklari --uygula

⚠️ YAZMADAN ONCE YEDEK ALIN:
       CREATE TABLE rag.documents_yedek AS SELECT * FROM rag.documents;
"""

from __future__ import annotations

import argparse
import asyncio
import re

from sqlalchemy import text

from app.config import settings

# `icerikten_baslik` `market_research._to_source` icinde de kullaniliyor;
# kopyalamak yerine ORTAK moduldan ithal ediliyor, aksi halde ayni dokuman
# arayuzde baska, veritabaninda baska bir baslik tasirdi.
#
# ⚠️ `app.core.metin`DEN ithal edilir, `app.agents.market_research`ten DEGIL:
# ajan modulu `app.orchestration.models` uzerinden langgraph'i yukluyor ve bu
# script yalnizca DB'ye baglanip metin kirpiyor - o yigina ihtiyaci yok
# (denendi: `ModuleNotFoundError: No module named 'langgraph'`).
from app.core.metin import icerikten_baslik
from app.db.session import get_session_factory

#: Baslik basina yapisan goreli zaman rozeti.
#:
#: ⚠️ SONDAKI `\s*` YANILTICI: gercek veride bosluk YOK ("1 gün önceBakan"),
#: bu yuzden desen "once"den hemen sonra biter ve kalan metin oldugu gibi
#: korunur - kirpma sonrasi ayrica `strip()` uygulanir.
#:
#: ⚠️ `(?-i:(?![a-zçğıöşü]))` ZORUNLU - "önceki" KELIMESINI KORUR.
#: Bu lookahead olmadan "5 yıl önceki verilerle karsilastirma" basligi
#: "ki verilerle karsilastirma"ya donusuyordu (test edildi): desen "5 yıl önce"
#: kismini rozet sanip kirpiyor, geriye "ki" kaliyordu.
#: Ayrim su: rozetten SONRA her zaman baslik gelir ve baslik buyuk harfle ya da
#: rakamla baslar ("...önceBakan", "...önce5 yıldır"); kucuk harf geliyorsa
#: "önce" aslinda daha uzun bir kelimenin parcasidir.
#: `(?-i:...)` kapsamli bayragi sart: `re.IGNORECASE` altinda `[a-z]` BUYUK
#: harfleri de eslestirir ve lookahead her seyi bloklardi.
#:
#: Birimler gozlemlenen veriden ("gün", "sa") ve ayni rozetin yaygin
#: varyantlarindan olusur. Turkce karakterler BILEREK korunur: bu desen HAM
#: baslik uzerinde calisir, `normalize()` ciktisinda degil.
_ZAMAN_ROZETI = re.compile(
    r"^\s*\d+\s*(?:sn|saniye|dk|dakika|sa|saat|gün|gun|hafta|ay|yıl|yil)\s*"
    r"önce(?-i:(?![a-zçğıöşü]))\s*",
    re.IGNORECASE,
)


def temizle(baslik: str) -> str:
    """Baslik basindaki zaman rozetlerini kirpar.

    DONGU: cift scrape edilmis kayitlarda rozet ust uste binebiliyor
    ("1 gün önce5 sa önceBaslik"). Tek gecis ilkini alir, ikincisi kalirdi.
    """
    onceki = None
    sonuc = baslik or ""
    while sonuc != onceki:
        onceki = sonuc
        sonuc = _ZAMAN_ROZETI.sub("", sonuc).strip()
    return sonuc


def yeni_baslik(baslik: str | None, raw_text: str | None) -> str:
    """Bir dokumanin olmasi gereken basligi.

    Sira onemli: ONCE rozet kirpilir, SONRA bosluk kontrolu yapilir. Tersi
    sirada "1 gün önce" gibi TAMAMEN rozetten ibaret bir baslik "dolu"
    sayilir ve icerikten uretim adimina hic gelmezdi.
    """
    temiz = temizle(baslik or "")
    if temiz:
        return temiz
    return icerikten_baslik(raw_text or "")


_SEC_SQL = text(
    """
    SELECT id, external_id, baslik, raw_text
    FROM rag.documents
    ORDER BY id
    """
)

_GUNCELLE_SQL = text("UPDATE rag.documents SET baslik = :baslik WHERE id = :id")


async def calistir(uygula: bool, limit: int | None = None) -> int:
    """Degisiklikleri hesaplar, raporlar ve (istenirse) yazar.

    Returns:
        Degistirilecek/degistirilen dokuman sayisi.
    """
    session_factory = get_session_factory()

    async with session_factory() as session:
        satirlar = (await session.execute(_SEC_SQL)).mappings().all()
        if limit is not None:
            satirlar = satirlar[:limit]

        rozetli: list[tuple[int, str, str]] = []
        bostan: list[tuple[int, str, str]] = []
        cozulemeyen: list[tuple[int, str]] = []

        for satir in satirlar:
            mevcut = satir["baslik"] or ""
            hedef = yeni_baslik(mevcut, satir["raw_text"])

            if hedef == mevcut.strip():
                continue
            if not hedef:
                # Ne rozet kirpilabildi ne icerikten baslik uretilebildi -
                # `raw_text` de bos demektir. Bunlari SESSIZCE gecmiyoruz:
                # bos baslik kalmasi bir veri sorunudur, raporda gorunmeli.
                cozulemeyen.append((satir["id"], satir["external_id"] or "-"))
                continue

            kayit = (satir["id"], mevcut, hedef)
            (bostan if not mevcut.strip() else rozetli).append(kayit)

        _rapor_yaz(rozetli, bostan, cozulemeyen, len(satirlar))

        degisecek = rozetli + bostan
        if not uygula:
            print("\nRAPOR MODU - hicbir sey yazilmadi.")
            print("Uygulamak icin: --uygula  (once rag.documents yedegi alin)")
            return len(degisecek)

        for doc_id, _, hedef in degisecek:
            await session.execute(_GUNCELLE_SQL, {"id": doc_id, "baslik": hedef})
        await session.commit()
        print(f"\n{len(degisecek)} dokumanin basligi guncellendi.")
        return len(degisecek)


def _rapor_yaz(
    rozetli: list[tuple[int, str, str]],
    bostan: list[tuple[int, str, str]],
    cozulemeyen: list[tuple[int, str]],
    toplam: int,
) -> None:
    """Ne degisecegini ORNEKLERIYLE yazar - koru koruna UPDATE calistirmamak icin."""
    print(f"Taranan dokuman: {toplam}")
    print(f"  zaman rozeti kirpilacak : {len(rozetli)}")
    print(f"  icerikten doldurulacak  : {len(bostan)}")
    print(f"  cozulemeyen (raw_text bos): {len(cozulemeyen)}")

    if rozetli:
        print("\n--- ZAMAN ROZETI KIRPILACAK (ilk 10) ---")
        for doc_id, eski, yeni in rozetli[:10]:
            print(f"  #{doc_id}\n    eski: {eski[:70]!r}\n    yeni: {yeni[:70]!r}")

    if bostan:
        print("\n--- BOS BASLIK, ICERIKTEN URETILECEK (ilk 10) ---")
        for doc_id, _, yeni in bostan[:10]:
            print(f"  #{doc_id}  -> {yeni[:70]!r}")

    if cozulemeyen:
        print("\n--- COZULEMEYEN (raw_text de bos) ---")
        for doc_id, external in cozulemeyen[:10]:
            print(f"  #{doc_id}  external_id={external}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--uygula",
        action="store_true",
        help="Degisiklikleri GERCEKTEN yazar. Verilmezse yalnizca rapor uretilir.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Yalnizca ilk N dokumani isle (kucuk olcekte deneme icin).",
    )
    args = parser.parse_args()

    if not settings.database_enabled:
        raise SystemExit(
            "DATABASE_URL tanimli degil - backend/.env icinde ayarlayip tekrar deneyin."
        )

    asyncio.run(calistir(uygula=args.uygula, limit=args.limit))
