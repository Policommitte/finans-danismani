"""NIM baglanti taniligi - "llm_error" sessizligini kirar.

NEDEN VAR
---------
Ajanlar LLM hatasini yakalayip deterministik ozete duserek devam ediyor;
kullaniciya giden SSE olayi ise yalnizca `error_type` tasiyor, hata METNINI
tasimiyor (bilincli: istisna metni ic ayrinti sizdirabilir). Iyi bir tasarim
ama gelistirirken "llm_error" tek basina hicbir sey soylemiyor.

Bu betik ayni istegi ELLE atip sunucunun DONDURDUGU hatayi oldugu gibi basar.

KULLANIM
    cd backend
    python nim-tani.py

GUVENLIK
    API anahtari EKRANA BASILMAZ - yalnizca uzunlugu ve onekinin beklenen
    bicimde olup olmadigi gosterilir.
"""

from __future__ import annotations

import os
import pathlib
import sys

KOK = pathlib.Path(__file__).resolve().parent


def env_yukle() -> None:
    """`.env`'i ortama yukler (degerleri BASMADAN)."""
    yol = KOK / ".env"
    if not yol.exists():
        print(f"UYARI: {yol} bulunamadi.")
        return
    for cizgi in yol.read_text(encoding="utf-8").splitlines():
        cizgi = cizgi.strip()
        if not cizgi or cizgi.startswith("#") or "=" not in cizgi:
            continue
        anahtar, _, deger = cizgi.partition("=")
        os.environ.setdefault(anahtar.strip(), deger.strip().strip('"').strip("'"))


def baslik(metin: str) -> None:
    print(f"\n{'=' * 70}\n{metin}\n{'=' * 70}")


def main() -> int:
    env_yukle()

    baslik("1) Paketler")
    import importlib.util as u

    eksik = []
    for paket in ("openai", "langchain_openai", "langchain_core", "langgraph"):
        var = u.find_spec(paket) is not None
        print(f"  {paket:<20} {'KURULU' if var else 'YOK'}")
        if not var:
            eksik.append(paket)
    if eksik:
        print("\n  -> Once kurun:  pip install -r requirements.txt")
        print(f"     (eksik: {', '.join(eksik)})")
    if "openai" in eksik:
        return 1

    baslik("2) Ayarlar")
    anahtar = (os.environ.get("NVIDIA_API_KEY") or "").strip()
    taban = (os.environ.get("NVIDIA_BASE_URL") or "https://integrate.api.nvidia.com/v1").strip()
    varsayilan = (os.environ.get("DEFAULT_MODEL") or "").strip()
    sentez = (os.environ.get("SYNTHESIZER_MODEL") or "").strip()

    # Anahtar BASILMAZ; yalnizca bicim kontrolu.
    onek = "evet" if anahtar.startswith("nvapi-") else "HAYIR"
    print(
        f"  NVIDIA_API_KEY      {'tanimli' if anahtar else 'YOK'}"
        f"  (uzunluk {len(anahtar)}, onek 'nvapi-' {onek})"
    )
    print(f"  NVIDIA_BASE_URL     {taban}")
    print(f"  DEFAULT_MODEL       {varsayilan or '(bos)'}")
    print(f"  SYNTHESIZER_MODEL   {sentez or '(bos)'}")

    for ad, deger in (("DEFAULT_MODEL", varsayilan), ("SYNTHESIZER_MODEL", sentez)):
        if deger and "/" not in deger:
            print(
                f"\n  ⚠️  {ad} '/' ICERMIYOR -> sistem bunu GEMINI sanar (bkz. saglayici_belirle)."
            )

    if not anahtar:
        print("\n  -> NVIDIA_API_KEY tanimli degil; devam edilemiyor.")
        return 1

    from openai import OpenAI

    istemci = OpenAI(api_key=anahtar, base_url=taban, timeout=60.0)

    baslik("3) Sunucudaki model kimlikleri (nemotron gecenler)")
    try:
        modeller = sorted(m.id for m in istemci.models.list().data)
    except Exception as exc:  # noqa: BLE001
        print(f"  MODEL LISTESI ALINAMADI: {type(exc).__name__}: {exc}")
        modeller = []
    else:
        nemotron = [m for m in modeller if "nemotron" in m.lower()]
        for m in nemotron:
            print(f"  {m}")
        if not nemotron:
            print(f"  (nemotron yok; toplam {len(modeller)} model listelendi)")

    hedef = varsayilan or sentez
    if modeller and hedef and hedef not in modeller:
        print(f"\n  ⚠️  '{hedef}' SUNUCU LISTESINDE YOK. Dogru kimligi yukaridan secin.")

    baslik(f"4) Gercek istek denemeleri  (model: {hedef})")
    denemeler = [
        ("ek govde YOK", None),
        (
            "chat_template_kwargs (kodun su anki hali)",
            {"chat_template_kwargs": {"enable_thinking": False}},
        ),
        ("enable_thinking (top-level, ESKI hali)", {"enable_thinking": False}),
        (
            "ikisi birden (400 bekleniyor)",
            {"enable_thinking": False, "chat_template_kwargs": {"enable_thinking": False}},
        ),
    ]

    for etiket, ek in denemeler:
        try:
            yanit = istemci.chat.completions.create(
                model=hedef,
                messages=[{"role": "user", "content": "Tek cumleyle merhaba de."}],
                temperature=0.2,
                max_tokens=64,
                **({"extra_body": ek} if ek else {}),
            )
            mesaj = yanit.choices[0].message
            icerik = (mesaj.content or "").strip()
            dusunce = (getattr(mesaj, "reasoning_content", "") or "").strip()
            durum = "OK"
            if not icerik and dusunce:
                durum = "OK ama content BOS (yanit reasoning_content'te - dusunme KAPANMAMIS)"
            print(f"  [{durum}] {etiket}")
            print(f"        content: {icerik[:90] or '(bos)'}")
            if dusunce:
                print(f"        reasoning_content uzunlugu: {len(dusunce)}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [HATA] {etiket}")
            print(f"        {type(exc).__name__}: {str(exc)[:400]}")

    baslik("5) Ozet")
    print(
        "  - Butun denemeler HATA verdiyse: model kimligi ya da anahtar sorunu (3. bolume bakin)."
    )
    print("  - Yalnizca ek govdeli denemeler hata verdiyse: .env icinde")
    print("      LLM_NVIDIA_EXTRA_BODY_OFF=1")
    print("    yapin; ya da app/core/llm.py icindeki _NIM_DUSUNME_KAPALI'yi")
    print("    calisan tek varyantla sinirlayin.")
    print("  - content bos gelip reasoning_content doluysa: dusunme kapanmamis;")
    print("    calisan bayrak varyantini kullanin, yoksa sentez suresi uzar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
