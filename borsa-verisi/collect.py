"""Yahoo Finance -> PostgreSQL tek seferlik veri toplama betigi.

KULLANIM
    python collect.py --kuru-calistir      # veritabanina YAZMAZ, ne yazacagini gosterir
    python collect.py                      # gercek calistirma (hisse+doviz+altin+ABD)
    python collect.py --kategori STOCK GOLD
    python collect.py --period 2y
    python collect.py --volatilite-guncelle

TASARIM NOTU
    Bu bir ARKA PLAN GOREVI DEGILDIR. Periyodik guncelleme
    `backend/app/market/scheduler.py` sorumlulugundadir ve bu betik oraya
    baglanmaz. Buradaki amac: veritabanini bir kez gercek piyasa verisiyle
    doldurup ajanlarin gercek veri uzerinde test edilebilmesini saglamak.
"""

from __future__ import annotations

import argparse
import logging
import sys

from symbols import ESLENMEYEN_SEMBOLLER, VARSAYILAN_KATEGORILER, eslesmeleri_getir
from yahoo import ToplamaSonucu, varliklari_topla

# NOT: `database` modulu BILINCLI olarak burada import EDILMEZ. Kuru
# calistirma veritabanina hic dokunmadigi icin psycopg surucusu kurulu
# olmadan da calisabilmelidir; import yazma anina ertelenir.

logger = logging.getLogger("borsa-verisi")


def _argumanlar() -> argparse.Namespace:
    ayristirici = argparse.ArgumentParser(
        description="Yahoo Finance'ten hisse/altin/doviz verisi cekip veritabanina yazar.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ayristirici.add_argument(
        "--kategori",
        nargs="+",
        metavar="KOD",
        help=f"Toplanacak kategoriler. Varsayilan: {' '.join(VARSAYILAN_KATEGORILER)}. "
        "Secenekler: STOCK FOREX GOLD USA_STOCK CRYPTO",
    )
    ayristirici.add_argument(
        "--period",
        default="2y",
        help="Yahoo gecmis araligi (1mo, 3mo, 6mo, 1y, 2y, 5y, max). Varsayilan: 2y.\n"
        "DIKKAT: yearly_change_pct 365 gun oncesine bakar; '1y' verilirse seri "
        "tam o tarihte basladigi icin yillik degisim BOS kalir. En az '2y' gerekir.",
    )
    ayristirici.add_argument(
        "--kuru-calistir",
        action="store_true",
        help="Veritabanina HIC yazma; yalnizca ne yazilacagini goster.",
    )
    ayristirici.add_argument(
        "--gecmis-yok",
        action="store_true",
        help="price_history'ye yazma, yalnizca assets tablosunu guncelle.",
    )
    ayristirici.add_argument(
        "--volatilite-guncelle",
        action="store_true",
        help="assets.sim_volatility alanini gercek oynaklikla guncelle "
        "(simulator davranisini degistirir - varsayilan KAPALI).",
    )
    ayristirici.add_argument("--dsn", help="PostgreSQL adresi. Varsayilan: DATABASE_URL")
    return ayristirici.parse_args()


def _tablo_yazdir(sonuc: ToplamaSonucu) -> None:
    """Cekilen veriyi okunabilir bir tabloda gosterir."""
    baslik = (
        f"{'SEMBOL':<12}{'FIYAT':>14}{'GUNLUK':>10}{'HAFTALIK':>11}"
        f"{'YILLIK':>10}{'OYNAKLIK':>11}{'GECMIS':>9}"
    )
    print("\n" + baslik)
    print("-" * len(baslik))

    for veri in sorted(sonuc.veriler, key=lambda v: (v.kategori, v.db_symbol)):
        isaret = " *" if veri.turetilmis else ""
        print(
            f"{veri.db_symbol + isaret:<12}"
            f"{veri.current_price:>14,.4f}"
            f"{_yuzde(veri.daily_change_pct):>10}"
            f"{_yuzde(veri.weekly_change_pct):>11}"
            f"{_yuzde(veri.yearly_change_pct):>10}"
            f"{veri.volatilite if veri.volatilite is not None else '-':>11}"
            f"{len(veri.gecmis):>9}"
        )

    if any(v.turetilmis for v in sonuc.veriler):
        print("\n  * = turetilmis fiyat (ons/USD -> gram/TRY, saf maden; iscilik haric)")


def _yuzde(deger: float | None) -> str:
    return "-" if deger is None else f"{deger:+.2f}%"


def _dsn_maskele(dsn: str) -> str:
    """Baglanti adresini ekrana basmadan once sifreyi gizler.

    `postgresql://kullanici:SIFRE@host/db` -> `postgresql://kullanici:***@host/db`.
    Loglarda/terminalde parola acikca gorunmesin diye.
    """
    if "://" not in dsn or "@" not in dsn:
        return dsn
    on, arka = dsn.split("@", 1)
    if ":" not in on:
        return dsn
    kullanici_kismi = on.rsplit(":", 1)[0]
    return f"{kullanici_kismi}:***@{arka}"


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    args = _argumanlar()

    eslesmeler = eslesmeleri_getir(args.kategori)
    if not eslesmeler:
        print("HATA: Secilen kategoride varlik yok.", file=sys.stderr)
        return 1

    print(f"Yahoo Finance'ten {len(eslesmeler)} varlik cekiliyor (period={args.period})...")
    sonuc = varliklari_topla(eslesmeler, period=args.period)

    if sonuc.veriler:
        _tablo_yazdir(sonuc)

    if sonuc.hatalar:
        print("\nCEKILEMEYEN VARLIKLAR:")
        for sembol, hata in sonuc.hatalar:
            print(f"  - {sembol}: {hata}")

    if ESLENMEYEN_SEMBOLLER:
        print(
            "\nEslenmemis semboller (Yahoo'da guvenilir karsiligi yok): "
            + ", ".join(ESLENMEYEN_SEMBOLLER)
        )

    if not sonuc.veriler:
        print("\nHicbir varlik cekilemedi, veritabanina yazilmadi.", file=sys.stderr)
        return 1

    toplam_gecmis = sum(len(v.gecmis) for v in sonuc.veriler)

    if args.kuru_calistir:
        print(
            f"\n[KURU CALISTIRMA] Veritabanina YAZILMADI.\n"
            f"  Gercek calistirmada guncellenecek: {len(sonuc.veriler)} varlik "
            f"(assets tablosu)\n"
            f"  price_history'ye eklenecek satir: "
            f"{0 if args.gecmis_yok else toplam_gecmis}\n"
            f"  Yahoo cagri sayisi: {sonuc.cagri_sayisi}"
        )
        return 0

    try:
        from database import api_kullanimi_kaydet, baglan, dsn_getir, varliklari_yaz
    except ImportError as exc:
        print(f"\nHATA: PostgreSQL surucusu yuklenemedi ({exc}).", file=sys.stderr)
        print("Kurulum: pip install -r requirements.txt", file=sys.stderr)
        print("Veritabani olmadan denemek icin: --kuru-calistir", file=sys.stderr)
        return 1

    print(f"\nVeritabanina yaziliyor: {_dsn_maskele(dsn_getir(args.dsn))}")
    try:
        with baglan(args.dsn) as conn:
            yazma = varliklari_yaz(
                conn,
                sonuc.veriler,
                gecmis_yaz=not args.gecmis_yok,
                volatilite_guncelle=args.volatilite_guncelle,
            )
            api_kullanimi_kaydet(conn, sonuc.cagri_sayisi)
            conn.commit()
    except Exception as exc:  # noqa: BLE001 - kullaniciya net mesaj gosterilir
        print(f"\nVERITABANI HATASI: {exc}", file=sys.stderr)
        print("Hicbir degisiklik kaydedilmedi (islem geri alindi).", file=sys.stderr)
        return 1

    print(
        f"\nTAMAMLANDI\n"
        f"  assets guncellenen satir : {yazma.guncellenen_varlik}\n"
        f"  price_history yazilan    : {yazma.yazilan_gecmis}\n"
        f"  Yahoo cagri sayisi       : {sonuc.cagri_sayisi}"
    )
    if yazma.bulunamayan_semboller:
        print("  Veritabaninda BULUNAMAYAN: " + ", ".join(yazma.bulunamayan_semboller))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
