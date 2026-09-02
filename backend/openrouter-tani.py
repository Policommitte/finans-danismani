"""OpenRouter baglanti ve TURKCE KALITE taniligi.

NEDEN VAR
---------
`nim-tani.py` ile ayni felsefe: bir modeli `.env`'e yazmadan once ELDE
sinamak. OpenRouter'da ek iki soru var:

  1. Ucretsiz (`:free`) modellerde GUNDE 50 istek siniri var; sinir anahtar
     basina. Modeli ana yola baglamadan once bunu bilerek karar verin.
  2. Bu projenin tum ciktisi TURKCE. Cin merkezli modellerin model
     kartlarinda Turkce destegi BELGELENMIYOR - varsayim degil, olcum
     konusu. Betik gercek bir risk-ajani promptu gonderip cikti dilini
     olcer.

KULLANIM
    cd backend
    python openrouter-tani.py
    python openrouter-tani.py --model inclusionai/ling-3.0-flash-fin:free
    python openrouter-tani.py --akis          # token akisini da sina

GUVENLIK
    API anahtari EKRANA BASILMAZ - yalnizca uzunlugu ve onek bicimi.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import time

KOK = pathlib.Path(__file__).resolve().parent
VARSAYILAN_MODEL = "inclusionai/ling-3.0-flash-fin:free"
UC = "https://openrouter.ai/api/v1"

#: Gercek bir risk/strateji ajani promptunun kisaltilmis hali. Tek satirlik
#: "merhaba" testi ise yaramaz: modelin TURKCE FINANS terimlerini dogru
#: kullanip kullanmadigi ancak boyle gorunur.
TURKCE_PROMPT = """Sen bir kişisel finans asistanısın. Aşağıdaki portföy için
kısa bir risk değerlendirmesi yaz. YENİ SAYI ÜRETME, yalnızca verilenleri kullan.

Portföy: %45 BIST hisse senedi, %30 döviz (USD), %15 altın, %10 nakit TRY.
Yatırımcı profili: orta risk, 5 yıllık vade.

Üç madde halinde, Türkçe, en fazla 120 kelime."""


def env_oku(anahtar: str) -> str:
    """`.env`'den tek bir degeri okur (pydantic'e bagimli olmadan)."""
    dosya = KOK / ".env"
    if not dosya.exists():
        return ""
    for satir in dosya.read_text(encoding="utf-8", errors="replace").splitlines():
        satir = satir.strip()
        if satir.startswith(f"{anahtar}="):
            return satir.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def turkce_puan(metin: str) -> tuple[int, str]:
    """Ciktinin Turkce olup olmadigina dair kaba ama yeterli bir olcum."""
    if not metin.strip():
        return 0, "cikti BOS"
    if re.search(r"[一-鿿]", metin):
        return 0, "CINCE karakter var - model dili tutturamamis"
    ozel = len(re.findall(r"[çğıöşüÇĞİÖŞÜ]", metin))
    tr_kelime = len(
        re.findall(
            r"\b(ve|için|ile|bir|bu|risk|portföy|oran|yatırım|değer|olarak|"
            r"nedeniyle|artış|azalış|öneri|dağılım)\b",
            metin,
            re.IGNORECASE,
        )
    )
    if ozel == 0 and tr_kelime < 3:
        return 1, "Turkce gorunmuyor (ozel karakter yok, TR kelime yok)"
    if ozel < 3:
        return 2, f"zayif (ozel karakter {ozel}, TR kelime {tr_kelime})"
    return 3, f"iyi (ozel karakter {ozel}, TR kelime {tr_kelime})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=VARSAYILAN_MODEL)
    ap.add_argument("--akis", action="store_true", help="Token akisini da sina")
    ap.add_argument("--max-tokens", type=int, default=1500, dest="max_tokens")
    ap.add_argument(
        "--dusunme-kapali",
        action="store_true",
        dest="dusunme_kapali",
        help="OpenRouter `reasoning.enabled=false` gonder",
    )
    a = ap.parse_args()

    print("=" * 68)
    print("1) Anahtar")
    print("=" * 68)
    anahtar = env_oku("OPENROUTER_API_KEY")
    if not anahtar:
        print("  OPENROUTER_API_KEY BOS.")
        print(f"  Beklenen yer: {KOK / '.env'}")
        print("  Anahtar: https://openrouter.ai/settings/keys")
        return 2
    print(
        f"  tanimli  (uzunluk {len(anahtar)}, 'sk-or-' oneki: "
        f"{'evet' if anahtar.startswith('sk-or-') else 'HAYIR - bicim supheli'})"
    )
    print(f"  model    {a.model}")
    print(f"  uc       {UC}")

    try:
        from openai import OpenAI
    except ImportError:
        print("\n  openai paketi kurulu degil: pip install openai")
        return 2

    istemci = OpenAI(api_key=anahtar, base_url=UC, timeout=90.0)

    print()
    print("=" * 68)
    print("2) Baglanti + Turkce kalite")
    print("=" * 68)
    basla = time.time()
    try:
        yanit = istemci.chat.completions.create(
            model=a.model,
            messages=[{"role": "user", "content": TURKCE_PROMPT}],
            temperature=0.2,
            max_tokens=a.max_tokens,
            **({"extra_body": {"reasoning": {"enabled": False}}} if a.dusunme_kapali else {}),
        )
    except Exception as hata:  # noqa: BLE001 - taniligin isi hatayi GOSTERMEK
        print(f"  [HATA] {type(hata).__name__}: {hata}")
        print("\n  429 ise: gunluk 50 istek siniri dolmus olabilir.")
        print("  404 ise: model kimligi yanlis ya da model kaldirilmis.")
        print("  401 ise: anahtar gecersiz.")
        return 1
    sure = time.time() - basla

    mesaj = yanit.choices[0].message if yanit.choices else None
    icerik = (getattr(mesaj, "content", "") or "") if mesaj else ""
    dusunce = ""
    if mesaj:
        dusunce = getattr(mesaj, "reasoning", None) or getattr(mesaj, "reasoning_content", "") or ""

    # ETKIN METIN: `NvidiaLLMClient.generate` ile AYNI sirayi izler
    # (content -> reasoning_content -> reasoning). Turkce puani bunun
    # uzerinden verilir; ham `content` uzerinden vermek YANLIS ALARM uretir -
    # alan bos olsa bile uygulama dolu metni aliyor.
    metin = icerik or dusunce
    puan, aciklama = turkce_puan(metin)

    print(f"  [OK] {sure:.1f} sn")
    kullanim = getattr(yanit, "usage", None)
    if kullanim:
        print(f"  token: giris {kullanim.prompt_tokens}, cikis {kullanim.completion_tokens}")
    print(f"  Turkce: {'*' * puan}{'.' * (3 - puan)}  {aciklama}")
    print(
        f"  API alanlari: content={'dolu' if icerik else 'BOS'}, "
        f"dusunce={'dolu (' + str(len(dusunce)) + ' krkt)' if dusunce else 'bos'}"
    )
    if not icerik and dusunce:
        print("  -> `content` bos, dusunce alani dolu. Bu NORMAL ve KARSILANDI:")
        print("     `NvidiaLLMClient.generate` content -> reasoning_content -> reasoning")
        print("     sirasiyla okur, yani ajan asagidaki metni ALIR.")
    if not metin.strip():
        print("  [SORUN] Hicbir alan dolu degil - model bu istekte bir sey uretmedi.")
        print("          --max-tokens degerini artirip tekrar deneyin.")
    print("  --- AJANIN ALACAGI METIN ---")
    for satir in (metin.strip() or "(BOS)").splitlines():
        print(f"  | {satir}")

    if a.akis:
        print()
        print("=" * 68)
        print("3) Token akisi (sentez yolu bu sekilde calisir)")
        print("=" * 68)
        basla = time.time()
        ilk = None
        parca = 0
        dusunce_parca = 0
        try:
            akis = istemci.chat.completions.create(
                model=a.model,
                messages=[{"role": "user", "content": TURKCE_PROMPT}],
                temperature=0.2,
                max_tokens=a.max_tokens,
                stream=True,
                **({"extra_body": {"reasoning": {"enabled": False}}} if a.dusunme_kapali else {}),
            )
            for olay in akis:
                if not olay.choices:
                    continue
                delta = olay.choices[0].delta
                if getattr(delta, "reasoning", None) or getattr(delta, "reasoning_content", None):
                    dusunce_parca += 1
                if delta.content:
                    parca += 1
                    if ilk is None:
                        ilk = time.time() - basla
        except Exception as hata:  # noqa: BLE001
            print(f"  [HATA] {type(hata).__name__}: {hata}")
            return 1

        toplam = time.time() - basla
        if ilk is None:
            print(
                f"  {toplam:.1f} sn'de hic ICERIK token'i gelmedi "
                f"({dusunce_parca} dusunce parcasi geldi)."
            )
            print("  -> SYNTHESIZER_MODEL OLAMAZ: `_extract_token` yalnizca")
            print("     `chunk.content` biriktirir, ekrana hicbir sey yazilmaz.")
            print("  -> AJAN slotlari (RISK_MODEL vb.) icin SORUN DEGIL: ajanlar")
            print("     akitmaz, tek seferlik `generate()` cagirir. Nihai metni")
            print("     zaten sentezleyici (NIM) yazar.")
        else:
            print(
                f"  [OK] ilk icerik {ilk:.1f} sn, toplam {toplam:.1f} sn, "
                f"{parca} icerik / {dusunce_parca} dusunce parcasi"
            )
            print("  NOT: NFR-01 ilk token icin ~3 sn hedefliyor.")

    print()
    print("=" * 68)
    print("4) Karar notu")
    print("=" * 68)
    print("  Ucretsiz katmanda GUNDE 50 istek var (dakikada 20) ve sinir ANAHTAR")
    print("  basinadir. Tam bir sohbet akisi 5-7 LLM cagrisi harciyor.")
    print("  -> DEFAULT_MODEL / SYNTHESIZER_MODEL yapmayin.")
    print("  -> Tek bir dusuk hacimli ajana baglayin, orn. backend/.env icinde:")
    print(f"       RISK_MODEL=openrouter:{a.model}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
