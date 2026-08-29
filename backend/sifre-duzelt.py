"""Kullanici sifrelerini demo sifresine esitler.

Kullanim (backend/ klasorunun ICINDEN):

    python sifre-duzelt.py                 # SADECE RAPOR - hicbir sey degistirmez
    python sifre-duzelt.py --uygula        # eslesmeyenleri duzeltir
    python sifre-duzelt.py --uygula --sifre baskabirsifre

Neden gerekli
-------------
`db/v5_schema_and_data.sql` icindeki seed hash'leri DOGRU: hepsi "demo1234"un
bcrypt hash'i ve CI'daki giris testi bu yuzden geciyor. Ama ekibin paylasilan
Supabase veritabani daha eski bir semadan turedi (bkz.
`db/migrations/001_assets_fiyat_kolonlari.sql`), yani oradaki `users` satirlari
seed dosyasindan GELMEDI - `password_hash` degerleri baska bir kaynaktan.

Bu betik hash'i uygulamanin KENDI fonksiyonuyla (`app.auth.security
.hash_password`, bcrypt) uretir; boylece giris ucu ile birebir ayni algoritma
ve format kullanilir.

Guvenlik
--------
* Hicbir hash ekrana TAM yazilmaz, yalnizca algoritma oneki gosterilir.
* Varsayilan calisma DENEME modudur; `--uygula` verilmeden tek satir bile
  degismez.
* Her kullaniciya AYRI salt uretilir (ayni sifre -> farkli hash).
* Yalnizca `password_hash` guncellenir; isim, e-posta, portfoy, hicbir sey
  degismez.
* Bunlar demo/seed hesaplaridir ve sifreleri repoda zaten belgeli. Gercek
  kullanici verisi iceren bir veritabaninda CALISTIRMAYIN.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

# WINDOWS: psycopg'nin async surucusu varsayilan ProactorEventLoop ile
# calismaz (ayni duzeltme uygulama tarafinda `run.py` icinde).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

VARSAYILAN_SIFRE = "demo1234"


def _algoritma(hash_degeri: str | None) -> str:
    """Hash'in yalnizca ALGORITMA onekini doner - gizli kisim gosterilmez."""
    if not hash_degeri:
        return "(bos/NULL)"
    if hash_degeri.startswith("$2"):
        parcalar = hash_degeri.split("$")
        return (
            f"bcrypt ${parcalar[1]}$ maliyet {parcalar[2]}" if len(parcalar) > 3 else "bcrypt (?)"
        )
    if hash_degeri.startswith("$argon2"):
        return "argon2"
    if hash_degeri.startswith("pbkdf2"):
        return "pbkdf2"
    if len(hash_degeri) == 64 and all(c in "0123456789abcdefABCDEF" for c in hash_degeri):
        return "sha256 gibi duz hash (bcrypt DEGIL)"
    return f"taninmayan bicim ({len(hash_degeri)} karakter)"


async def main(uygula: bool, sifre: str) -> int:
    try:
        from sqlalchemy import text

        from app.auth.security import hash_password, verify_password
        from app.db.session import get_session_factory
        from app.repositories.deps import describe_backend
    except Exception as exc:  # pragma: no cover
        print(f"HATA: modul yuklenemedi ({exc}). backend/ icinden calistirin.")
        return 1

    if describe_backend() != "postgresql":
        print("HATA: veritabanina baglanilamadi (bellek ici yedege dusuldu).")
        print("      backend/.env icindeki DATABASE_URL'i kontrol edin ve")
        print("      komutu backend/ klasorunun ICINDEN calistirin.")
        return 1

    fabrika = get_session_factory()

    async with fabrika() as oturum:
        satirlar = (
            (await oturum.execute(text("SELECT id, email, password_hash FROM users ORDER BY id")))
            .mappings()
            .all()
        )

    if not satirlar:
        print("users tablosu BOS - giris yapilacak hesap yok.")
        return 2

    print(f"{len(satirlar)} kullanici bulundu. Denenen sifre: {sifre!r}\n")
    print(f"  {'id':>3}  {'e-posta':<26} {'hash bicimi':<28} {'giris':<8}")
    print(f"  {'-'*3}  {'-'*26} {'-'*28} {'-'*8}")

    bozuk: list[dict] = []
    for s in satirlar:
        olur = verify_password(sifre, s["password_hash"] or "")
        if not olur:
            bozuk.append(s)
        print(
            f"  {s['id']:>3}  {s['email']:<26} {_algoritma(s['password_hash']):<28} "
            f"{'OK' if olur else 'OLMUYOR':<8}"
        )

    if not bozuk:
        print(f"\nSONUC: hepsi zaten {sifre!r} ile giris yapabiliyor. Yapacak bir sey yok.")
        return 0

    print(f"\n{len(bozuk)} kullanicinin sifresi {sifre!r} ile eslesmiyor.")

    if not uygula:
        print("\nDENEME MODU - hicbir sey degistirilmedi.")
        print("Duzeltmek icin:  python sifre-duzelt.py --uygula")
        return 3

    # --- Uygula ---------------------------------------------------------
    print("\nDuzeltiliyor...")
    async with fabrika() as oturum:
        for s in bozuk:
            await oturum.execute(
                text("UPDATE users SET password_hash = :h WHERE id = :i"),
                {"h": hash_password(sifre), "i": s["id"]},
            )
        await oturum.commit()

    # --- Dogrula --------------------------------------------------------
    # Yazdiktan sonra DB'den TEKRAR okuyup kontrol ediyoruz: "UPDATE calisti"
    # ile "giris artik yapilabiliyor" ayni sey degil.
    async with fabrika() as oturum:
        yeni = (
            (await oturum.execute(text("SELECT id, email, password_hash FROM users ORDER BY id")))
            .mappings()
            .all()
        )

    basarisiz = [s for s in yeni if not verify_password(sifre, s["password_hash"] or "")]
    print(f"  {len(yeni) - len(basarisiz)}/{len(yeni)} kullanici {sifre!r} ile giris yapabiliyor")

    if basarisiz:
        print("  HALA OLMAYANLAR: " + ", ".join(s["email"] for s in basarisiz))
        return 4

    print("\nSONUC: TAMAM. Arayuz ekibi su hesaplardan biriyle girebilir:")
    for s in yeni[:3]:
        print(f"  {s['email']}  /  {sifre}")
    if len(yeni) > 3:
        print(f"  ... ve {len(yeni) - 3} hesap daha (hepsi ayni sifre)")
    return 0


if __name__ == "__main__":
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument(
        "--uygula", action="store_true", help="Degisiklikleri gercekten yaz (varsayilan: deneme)"
    )
    ayristirici.add_argument(
        "--sifre",
        default=VARSAYILAN_SIFRE,
        help=f"Ayarlanacak sifre (varsayilan: {VARSAYILAN_SIFRE})",
    )
    args = ayristirici.parse_args()
    sys.exit(asyncio.run(main(uygula=args.uygula, sifre=args.sifre)))
