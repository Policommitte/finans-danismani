"""Outbox yukunden e-posta konusu ve govdesi uretir.

Metinler SABIT ve DETERMINISTIKTIR - LLM kullanilmaz. Bildirim, kullanicinin
parasiyla ilgili bir olayin kaydidir; uretimi modele birakmak her gonderimde
farkli bir metin riski dogurur.

Her govde iki ibare tasir:
  1. SIMULE ISLEM - gercek para hareketi olmadigi her mesajda yazilir.
  2. Yatirim tavsiyesi degildir - finansal bilgi iceren cikti zorunlulugu.
"""

from __future__ import annotations

SIMULASYON_UYARISI = (
    "Bu bir SIMULE islemdir. Gercek bir aracı kuruma emir iletilmemis, "
    "gercek para hareketi olmamistir."
)
TAVSIYE_UYARISI = "Bu bilgiler yatirim tavsiyesi degildir."

_YON = {"BUY": "ALIS", "SELL": "SATIS"}


def build(event_type: str, payload: dict) -> tuple[str, str]:
    """(konu, govde) doner. Bilinmeyen olay tipi genel sablona duser."""
    if event_type == "ORDER_FILLED":
        return _filled(payload)
    if event_type == "ORDER_REJECTED":
        return _rejected(payload)
    if event_type == "ORDER_EXPIRED":
        return _expired(payload)
    return (
        "Polifin - emir bildirimi",
        f"Emrinizle ilgili bir guncelleme var.\n\n{SIMULASYON_UYARISI}\n{TAVSIYE_UYARISI}\n",
    )


def _filled(p: dict) -> tuple[str, str]:
    yon = _YON.get(p.get("side", ""), p.get("side", ""))
    sembol = p.get("symbol", "-")
    adet = _sayi(p.get("quantity"))
    fiyat = _para(p.get("price"))
    konu = f"Polifin - {sembol} {yon.lower()} emriniz gerceklesti"

    satirlar = [
        f"{sembol} ({p.get('asset_name', '-')}) icin {yon.lower()} emriniz gerceklesti.",
        "",
        f"  Yon            : {yon}",
        f"  Adet           : {adet}",
        f"  Gerceklesme    : {fiyat} TRY",
        f"  Komisyon       : {_para(p.get('commission'))} TRY",
        f"  Toplam         : {_para(p.get('total'))} TRY",
    ]
    if p.get("order_type"):
        satirlar.append(f"  Emir tipi      : {p['order_type']}")
    satirlar += [
        "",
        "Guncel portfoyunuzu ve nakit bakiyenizi Polifin panelinden gorebilirsiniz.",
        "",
        SIMULASYON_UYARISI,
        TAVSIYE_UYARISI,
        "",
    ]
    return konu, "\n".join(satirlar)


def _rejected(p: dict) -> tuple[str, str]:
    sembol = p.get("symbol", "-")
    yon = _YON.get(p.get("side", ""), p.get("side", ""))
    gerekce = p.get("rejection_reason") or "Emir kosullari saglanmadi."
    konu = f"Polifin - {sembol} {yon.lower()} emriniz gerceklesmedi"
    govde = "\n".join(
        [
            f"{sembol} icin {yon.lower()} emriniz gerceklesmedi.",
            "",
            f"  Adet    : {_sayi(p.get('quantity'))}",
            f"  Gerekce : {gerekce}",
            "",
            "Bloke edilen bakiye varsa serbest birakilmistir; yeni bir emir",
            "olusturabilirsiniz.",
            "",
            SIMULASYON_UYARISI,
            TAVSIYE_UYARISI,
            "",
        ]
    )
    return konu, govde


def _expired(p: dict) -> tuple[str, str]:
    sembol = p.get("symbol", "-")
    konu = f"Polifin - {sembol} emrinizin suresi doldu"
    govde = "\n".join(
        [
            f"{sembol} icin bekleyen emrinizin gecerlilik suresi doldu ve emir iptal edildi.",
            "",
            f"  Adet : {_sayi(p.get('quantity'))}",
            "",
            "Bloke edilen bakiye serbest birakilmistir.",
            "",
            SIMULASYON_UYARISI,
            TAVSIYE_UYARISI,
            "",
        ]
    )
    return konu, govde


def _para(value) -> str:
    try:
        return f"{float(value or 0):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except (TypeError, ValueError):
        return "-"


def _sayi(value) -> str:
    try:
        sayi = float(value or 0)
    except (TypeError, ValueError):
        return "-"
    # Tam sayiysa ondalik gosterme: "10" > "10,000000"
    return str(int(sayi)) if sayi == int(sayi) else f"{sayi:.6f}".rstrip("0").replace(".", ",")
