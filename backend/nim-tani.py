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
    python nim-tani.py            # .env'deki modeli sina
    python nim-tani.py --tara     # ek olarak aday modelleri TOPLUCA sina
    python nim-tani.py --akis     # SENTEZ akis yolunu birebir olc
    python nim-tani.py --akis a/b,c/d   # verilen modelleri akista KARSILASTIR

GUVENLIK
    API anahtari EKRANA BASILMAZ - yalnizca uzunlugu ve onekinin beklenen
    bicimde olup olmadigi gosterilir.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

KOK = pathlib.Path(__file__).resolve().parent

#: `--tara` ile sinanan aday modeller.
#:
#: Katalogda 83 model var ama cogu gomme, gorsel, kod ya da eski kusak.
#: Buradakiler sohbet yapabilen, guncel ve bu proje icin makul olanlar.
#: Listeyi elle guncelleyin - katalog haftalik degisiyor.
ADAY_MODELLER = [
    "google/gemma-4-31b-it",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-nano-3-30b-a3b",
    "moonshotai/kimi-k3",
    "deepseek-ai/deepseek-v4-flash-0731",
    "openai/gpt-oss-120b",
    "mistralai/mistral-large-2-instruct",
    "minimaxai/minimax-m3",
    "stepfun-ai/step-3.7-flash",
    "ai21labs/jamba-1.5-large-instruct",
]

#: Tarama prompt'u TURKCE ve projeye yakin secildi: ayni kosuda hem
#: erisilebilirlik, hem gecikme, hem TURKCE KALITESI gorulsun.
TARAMA_PROMPTU = (
    "THYAO hissesi son 1 yilda %12 dustu. Bunu tek cumleyle, "
    "yatirimciya sade bir Turkce ile acikla."
)

#: Tarama basina ust sinir. Kisa tutuluyor: amac kaliteyi olcmek degil,
#: modelin AYAKTA olup olmadigini ve kabaca ne kadar surdugunu gormek.
TARAMA_TIMEOUT = 25.0


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

    baslik("3) Sunucudaki TUM model kimlikleri (yayinciya gore)")
    try:
        modeller = sorted(m.id for m in istemci.models.list().data)
    except Exception as exc:  # noqa: BLE001
        print(f"  MODEL LISTESI ALINAMADI: {type(exc).__name__}: {exc}")
        modeller = []
    else:
        # Yayinci = kimligin "/" oncesi parcasi (nvidia, meta, qwen, mistralai...).
        # ONCEDEN yalnizca "nemotron" gecenler basiliyordu ve kataloğun geri
        # kalani hic gorunmuyordu - baska yayincilarin modelleri de aday.
        gruplar: dict[str, list[str]] = {}
        for m in modeller:
            yayinci = m.split("/")[0] if "/" in m else "(yayincisiz)"
            gruplar.setdefault(yayinci, []).append(m)

        for yayinci in sorted(gruplar, key=lambda y: (-len(gruplar[y]), y)):
            print(f"\n  --- {yayinci}  ({len(gruplar[yayinci])}) ---")
            for m in gruplar[yayinci]:
                print(f"    {m}")
        print(f"\n  TOPLAM: {len(modeller)} model, {len(gruplar)} yayinci")

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

    if "--tara" in sys.argv:
        adaylari_tara(anahtar, taban)

    if "--akis" in sys.argv:
        yer = sys.argv.index("--akis")
        arkasi = sys.argv[yer + 1] if len(sys.argv) > yer + 1 else ""
        modeller = [m.strip() for m in arkasi.split(",") if m.strip() and "/" in m]
        akis_olc(modeller or None)

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
    print("  - Timeout: model katalogda listeli ama o uca kapasite ayrilmamis")
    print("    ya da soguk baslangicta olabilir. `--tara` ile hangi adaylarin")
    print("    gercekten ayakta oldugunu toplu gorebilirsiniz.")
    return 0


def adaylari_tara(anahtar: str, taban: str) -> None:
    """Aday modelleri PARALEL sinar: ayakta mi, ne kadar suruyor, Turkcesi nasil.

    Neden paralel: 12 modeli sirayla denemek, olu bir uc basina 25 saniye
    demek - bes dakikayi bulur. Es zamanli kosunca tarama ~30 saniyede biter.

    Neden Turkce prompt: erisilebilirlik ve gecikmeyi olcerken Turkce
    kalitesini de AYNI kosuda gormek icin. Katalogdaki modellerin cogu
    Turkce'yi resmi destek listesinde saymiyor; kagit uzerinde secip sonra
    hayal kirikligi yasamaktansa ciktiya bakmak daha hizli.
    """
    from openai import OpenAI

    # Uygulamanin GONDERDIGI ek govdeyi birebir kullan. Ilk surumde hic
    # gonderilmiyordu ve Nemotron adaylari haksiz yere kotu gorunuyordu:
    # dusunme acik kaldigi icin Lightning yanit yerine ham dusunce zincirini
    # (Ingilizce) basiyordu. Tani betigi uretimden FARKLI bir istek atarsa
    # olctugu sey uretim davranisi olmaz.
    try:
        from app.core.llm import _nim_ek_govde
    except Exception:  # noqa: BLE001 - betik app olmadan da calisabilmeli

        def _nim_ek_govde(model: str) -> dict:
            if "nemotron" in (model or "").lower():
                return {"chat_template_kwargs": {"enable_thinking": False}}
            return {}

    baslik(f"6) Aday tarama ({len(ADAY_MODELLER)} model, es zamanli)")
    print(f"  Prompt: {TARAMA_PROMPTU}")
    print("  (Nemotron modellerine dusunme-kapali bayragi gonderiliyor)\n")

    istemci = OpenAI(api_key=anahtar, base_url=taban, timeout=TARAMA_TIMEOUT, max_retries=0)

    def dene(model: str) -> tuple[str, str, float, str]:
        bas = time.perf_counter()
        govde = _nim_ek_govde(model)
        try:
            yanit = istemci.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": TARAMA_PROMPTU}],
                temperature=0.2,
                max_tokens=120,
                **({"extra_body": govde} if govde else {}),
            )
            sure = time.perf_counter() - bas
            mesaj = yanit.choices[0].message
            metin = (mesaj.content or "").strip()
            if not metin:
                dusunce = (getattr(mesaj, "reasoning_content", "") or "").strip()
                return model, "BOS", sure, f"(content bos, reasoning {len(dusunce)} krkt)"
            return model, "OK", sure, metin.replace("\n", " ")
        except Exception as exc:  # noqa: BLE001
            return model, "HATA", time.perf_counter() - bas, type(exc).__name__

    with ThreadPoolExecutor(max_workers=len(ADAY_MODELLER)) as havuz:
        sonuclar = list(havuz.map(dene, ADAY_MODELLER))

    # Once calisanlar, hizliya gore sirali - secim yaparken en ustteki en iyi aday.
    sonuclar.sort(key=lambda s: (s[1] != "OK", s[2]))

    for model, durum, sure, metin in sonuclar:
        isaret = {"OK": "  ", "BOS": "??", "HATA": "XX"}[durum]
        print(f"{isaret} {model:<42} {durum:<5} {sure:6.1f} sn")
        print(f"      {metin[:150]}")

    calisan = sum(1 for s in sonuclar if s[1] == "OK")
    print(f"\n  {calisan}/{len(sonuclar)} model yanit verdi.")
    print("  Turkce ciktilarini karsilastirin: dogru dilbilgisi, dogru sayi (%12),")
    print("  tek cumle kurabilme. Hizli ama Turkcesi bozuk bir model ise yaramaz.")


#: `--akis` icin sentez benzeri baglam.
#:
#: Kucuk bir prompt ile olcum YANILTIR: `--tara` Kimi K3'u 120 token ve tek
#: cumlelik istekle 2.6 saniyede olctu, sentez ise ayni modelde 90 saniyeyi
#: doldurdu. Fark prompt buyuklugunde ve `max_tokens`'ta; bu yuzden buradaki
#: baglam gercek bir sentez isteginin boyutuna yakin tutulur.
AKIS_BAGLAM = """Kullanicinin sorusu: Turk Hava Yollari hissesi ne kadar?

--- Piyasa arastirmasi ---
THYAO guncel fiyat: 309.75 TRY (+2.57%)
Gunluk islem hacmi: 1.240.000 lot
52 haftalik aralik: 241.10 - 336.80 TRY
Son 1 ay getiri: +%8.4
Sektor: Havacilik

--- Portfoy analizi ---
Toplam deger: 184.320 TRY
THYAO pozisyonu: 120 adet, ortalama maliyet 268.40 TRY, guncel deger 37.170 TRY
Portfoydeki agirligi: %20.2
Diger pozisyonlar: ASELS %18.4, GARAN %15.1, nakit %12.0

--- Risk degerlendirmesi ---
Portfoy volatilitesi: orta-yuksek
Havacilik sektoru yogunlasmasi dikkat gerektiriyor
"""


def _akis_istemcisi(model: str):
    """Verilen model icin uretimdekiyle AYNI akitan istemciyi kurar.

    `get_streaming_llm` modeli ayarlardan okur; karsilastirma yaparken ise
    modeli disaridan vermek gerekiyor. Bu yuzden ayni yapilandirma burada
    tekrarlanir - degistirirseniz `app/core/llm.py::get_streaming_llm` ile
    BIRLIKTE degistirin, yoksa tani betigi uretimden farkli bir sey olcer.
    """
    from langchain_openai import ChatOpenAI

    from app.config import settings
    from app.core.llm import _nim_ek_govde

    govde = _nim_ek_govde(model)
    return ChatOpenAI(
        model=model,
        api_key=settings.api_key_for("nvidia"),
        base_url=settings.nvidia_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        streaming=True,
        **({"extra_body": govde} if govde else {}),
    )


async def _akis_kos(llm, mesajlar, sinir: float) -> dict:
    """Tek bir modeli akitir ve zamanlama olcumlerini doner."""
    olcum: dict = {
        "ilk_parca": None,
        "ilk_icerik": None,
        "parca": 0,
        "icerik": [],
        "dusunce": 0,
        "hata": None,
        "kesildi": False,
    }
    bas = time.perf_counter()
    try:
        akis = llm.astream(mesajlar)
        while True:
            kalan = sinir - (time.perf_counter() - bas)
            if kalan <= 0:
                olcum["kesildi"] = True
                break
            try:
                parca = await asyncio.wait_for(akis.__anext__(), timeout=kalan)
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                olcum["kesildi"] = True
                break

            simdi = time.perf_counter() - bas
            olcum["parca"] += 1
            if olcum["ilk_parca"] is None:
                olcum["ilk_parca"] = simdi

            icerik = getattr(parca, "content", "") or ""
            if icerik:
                if olcum["ilk_icerik"] is None:
                    olcum["ilk_icerik"] = simdi
                olcum["icerik"].append(str(icerik))

            ek = getattr(parca, "additional_kwargs", None) or {}
            olcum["dusunce"] += len(ek.get("reasoning_content") or "")
    except Exception as exc:  # noqa: BLE001
        olcum["hata"] = f"{type(exc).__name__}: {str(exc)[:300]}"

    olcum["toplam"] = time.perf_counter() - bas
    olcum["metin"] = "".join(olcum["icerik"])
    uretim = olcum["toplam"] - (olcum["ilk_icerik"] or olcum["toplam"])
    olcum["hiz"] = len(olcum["metin"]) / uretim if uretim > 0.05 else 0.0
    return olcum


def akis_olc(modeller: list[str] | None = None) -> None:
    """Sentezin AKIS yolunu uretimdeki haliyle kosar ve zamanlamayi cikarir.

    NEDEN AYRI BIR MOD
    ------------------
    `--tara` tek seferlik `chat.completions.create` cagirir. Sentez ise
    LangChain `ChatOpenAI.astream` kullanir (bkz. `app/core/llm.py::
    get_streaming_llm`). Ikisi FARKLI yollar ve olculen fark buyuk oldu:
    Kimi K3 taramada 2.6 saniyede yanit verdi, akista ayni model 75 saniye
    surdu. Bir modeli tek seferlik olcup akista kullanmak yaniltiyor.

    EN ONEMLI SAYI: URETIM HIZI (karakter/saniye)
    ---------------------------------------------
    Toplam sure tek basina yaniltir - uzun yanit da yavas model de sureyi
    buyutur. Hiz ikisini ayirir: ilk icerik geldikten SONRA saniyede kac
    karakter aktigini olcer. Kimi K3'te bu 4.7 cikti; saglikli bir uc
    50-150 arasi verir.

    IKINCI SAYI: ILK ICERIGE KADAR GECEN SURE
    -----------------------------------------
    `Orchestrator._stream_llm` yalnizca `chunk.content` biriktirir. Dusunen
    modeller dusunce zincirini AYRI alanda (`reasoning_content`) akitir; o
    sirada `content` bos gelir ve disaridan model durmus gibi gorunur.
    `reasoning` sutunu bunu ayirt eder.
    """
    baslik("7) Sentez akis yolu (uretimdeki `ChatOpenAI.astream`)")

    try:
        sys.path.insert(0, str(KOK))
        from app.config import settings
        from app.engine.orchestrator import SYNTHESIZER_SYSTEM_PROMPT
    except Exception as exc:  # noqa: BLE001
        print(f"  [HATA] uygulama modulleri yuklenemedi: {type(exc).__name__}: {exc}")
        print("        Bu modu backend/ dizininden calistirin.")
        return

    from langchain_core.messages import HumanMessage, SystemMessage

    sinir = float(settings.synthesizer_timeout_seconds)
    mesajlar = [
        SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
        HumanMessage(content=AKIS_BAGLAM),
    ]

    if modeller is None:
        from app.core.llm import get_streaming_llm

        if get_streaming_llm("synthesizer") is None:
            print("  get_streaming_llm() None dondu -> sentez AKMAZ, tek seferlik")
            print("  istemciye duser. Sebep: model tanimsiz, saglayici nvidia degil,")
            print("  anahtar yok ya da langchain-openai kurulu degil.")
            return
        modeller = [settings.model_for("synthesizer")]

    print(f"  max_tokens   : {settings.llm_max_tokens}")
    print(f"  zaman siniri : {sinir:.0f} sn (SYNTHESIZER_TIMEOUT_SECONDS)")
    print(
        f"  baglam       : {len(AKIS_BAGLAM)} krkt + {len(SYNTHESIZER_SYSTEM_PROMPT)} krkt prompt"
    )
    if len(modeller) > 1:
        print(f"\n  {len(modeller)} model SIRAYLA olculuyor - es zamanli kosmak")
        print("  ayni hesabin hiz sinirini paylastirir ve olcumu bozardi.")

    sonuclar: list[tuple[str, dict]] = []
    for model in modeller:
        print(f"\n  --- {model} ---")
        try:
            llm = _akis_istemcisi(model)
        except Exception as exc:  # noqa: BLE001
            print(f"      istemci kurulamadi: {type(exc).__name__}: {exc}")
            continue

        olcum = asyncio.run(_akis_kos(llm, mesajlar, sinir))
        sonuclar.append((model, olcum))

        def sn(deger) -> str:
            return f"{deger:.1f} sn" if deger is not None else "HIC GELMEDI"

        print(f"      ilk parca       : {sn(olcum['ilk_parca'])}")
        print(f"      ilk ICERIK      : {sn(olcum['ilk_icerik'])}")
        print(f"      toplam          : {olcum['toplam']:.1f} sn")
        print(f"      uretim hizi     : {olcum['hiz']:.1f} krkt/sn")
        print(f"      icerik / parca  : {len(olcum['metin'])} krkt / {olcum['parca']} parca")
        if olcum["dusunce"]:
            print(f"      reasoning       : {olcum['dusunce']} krkt")
        if olcum["kesildi"]:
            print(f"      >> {sinir:.0f} sn SINIRINDA KESILDI - canlida da timeout verir")
        if olcum["hata"]:
            print(f"      HATA            : {olcum['hata']}")
        print(f"      metin: {olcum['metin'][:160].replace(chr(10), ' ') or '(bos)'}")

    if not sonuclar:
        return

    if len(sonuclar) > 1:
        baslik("8) Karsilastirma")
        print(f"  {'model':<40} {'ilk icerik':>11} {'toplam':>8} {'hiz':>10} {'durum':>9}")
        siralı = sorted(sonuclar, key=lambda s: (s[1]["kesildi"], -s[1]["hiz"]))
        for model, o in siralı:
            ilk = f"{o['ilk_icerik']:.1f} sn" if o["ilk_icerik"] is not None else "-"
            durum = "KESILDI" if o["kesildi"] else ("HATA" if o["hata"] else "tamam")
            print(
                f"  {model:<40} {ilk:>11} {o['toplam']:>7.1f}s " f"{o['hiz']:>7.1f}/sn {durum:>9}"
            )
        print("\n  Secim olcutu: once KESILMEYENLER, sonra en yuksek uretim hizi.")
        print("  Turkce kalitesini yukaridaki metin orneklerinden karsilastirin -")
        print("  hizli ama Turkcesi bozuk bir model sentezde ise yaramaz.")
        return

    model, olcum = sonuclar[0]
    baslik("8) Teshis")
    if olcum["hata"]:
        print("  Akis istisnayla dustu - yukaridaki hata metnine bakin.")
    elif not olcum["metin"]:
        print("  ICERIK HIC GELMEDI. Model yalnizca dusunce uretmis olabilir.")
        print("  -> Bu modelde dusunmeyi kapatan bayragi bulup")
        print("     app/core/llm.py::_nim_ek_govde icine ekleyin; bulunamazsa")
        print("     SYNTHESIZER_MODEL'i dusunmeyen bir modele cevirin.")
    elif olcum["kesildi"]:
        print(f"  {sinir:.0f} saniyede bitmedi - canlida aldiginiz timeout budur.")
        print(f"  Uretim hizi {olcum['hiz']:.1f} krkt/sn.")
        print("  -> Sinir yukseltmek kullaniciyi daha uzun bekletir, cozmez.")
        print("     Baska modelleri akista olcun:")
        print("     python nim-tani.py --akis modelA,modelB,modelC")
    elif olcum["hiz"] < 20:
        print(f"  Akis TAMAMLANDI ama cok yavas: {olcum['hiz']:.1f} krkt/sn.")
        print(f"  Saglikli bir uc 50-150 krkt/sn verir. {len(olcum['metin'])} karakterlik")
        print(f"  kisa bir yanit {olcum['toplam']:.0f} saniye surduyse, biraz daha uzun")
        print("  bir yanit siniri asar - yani bu model canlida guvenilmez.")
        print("  -> Baska modelleri akista olcun:")
        print("     python nim-tani.py --akis modelA,modelB,modelC")
    elif olcum["ilk_icerik"] is not None and olcum["ilk_icerik"] > sinir * 0.5:
        print(f"  Ilk icerik {olcum['ilk_icerik']:.0f}. saniyede geldi - sinirin yarisindan")
        print(f"  sonra. Bu sirada {olcum['dusunce']} karakter dusunce akti.")
        print("  -> Dusunmeyi kapatin ya da modeli degistirin.")
    else:
        print(f"  Akis saglikli: ilk icerik {olcum['ilk_icerik']:.1f} sn, toplam")
        print(f"  {olcum['toplam']:.1f} sn, hiz {olcum['hiz']:.1f} krkt/sn.")
        print("  Canlida yine de zaman asimi aliyorsaniz sorun modelde degil;")
        print("  ajan asamasina ya da baglam boyutuna bakin.")


if __name__ == "__main__":
    sys.exit(main())
