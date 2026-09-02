"""Yuklenen gorseli (ekran goruntusu / tablo fotografi) METNE cevirir.

NEDEN AYRI BIR MODEL
--------------------
Sistemin ana beyni `nvidia/nemotron-3-super-120b-a12b` SALT METINDIR - NVIDIA
model karti acikca "Input Type(s): Text" der. Ona gorsel gondermek istegi 400
ile dusurur. Bu yuzden gorsel adimi `DOCUMENT_VISION_MODEL` ile tanimlanan
AYRI bir modele gider (onerilen: `moonshotai/kimi-k3` - NIM uzerinde native
text+image destegi var).

BORU HATTINDAKI YERI
--------------------
Gorsel modeli yalnizca "gordugunu YAZIYA dok" isini yapar. Finansal yorum,
gosterge cikarimi ve rapor metni yine ANA MODELDE uretilir:

    gorsel --(vision)--> duz metin tarif --(ana model)--> AnalizSonucu

Boylece iki fayda: (1) analiz kalitesi tek ve tutarli bir beyinde kalir,
(2) gorsel modeli degistirmek boru hattinin geri kalanini etkilemez.
"""

from __future__ import annotations

import logging

from app.config import settings
from app.documents.types import AyristirilmisBelge

logger = logging.getLogger(__name__)

#: Uzantidan MIME tipi. `data:` URI'sinde dogru tip ONEMLIDIR - yanlis tip
#: modelin gorseli cozememesine yol acar.
MIME_TIPLERI = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}

#: Gorsel modelinden ne istedigimiz. TARIF isteriz, YORUM degil - yorumu ana
#: model yapar (bkz. modul docstring'i).
GORSEL_PROMPT = """Bu görsel bir finansal ekran görüntüsü, tablo ya da grafik olabilir.

Görevin SADECE gördüğünü eksiksiz biçimde yazıya dökmek. Yorum yapma, tavsiye verme.

Şunları yaz:
1. Görselin ne olduğu (tablo, çizgi grafik, mum grafik, ekran görüntüsü vb.)
2. Başlıklar ve etiketler (aynen, değiştirmeden)
3. Tablo varsa TÜM satır ve sütunları, değerleriyle birlikte
4. Grafik varsa eksen isimleri, ölçek ve okunabilen veri noktaları
5. Görünen tarih, para birimi ve sembol bilgileri

Okunamayan bir kısım varsa "okunamadı" diye belirt, tahmin etme.
Türkçe yaz."""


class GorselCozumlemeHatasi(Exception):
    """Gorsel metne cevrilemedi - rapor uretilemez."""


def mime_tipi(dosya_adi: str) -> str:
    """Dosya adindan MIME tipi; taninmiyorsa PNG varsayilir."""
    nokta = dosya_adi.lower().rfind(".")
    uzanti = dosya_adi[nokta:].lower() if nokta >= 0 else ""
    return MIME_TIPLERI.get(uzanti, "image/png")


def gorsel_modeli_hazir_mi() -> bool:
    """Gorsel yolu yapilandirilmis mi?

    Cagiran taraf bunu ONCEDEN sorar ki kullaniciya "gorsel analizi su an
    kapali" denebilsin. Aksi halde kullanici dosyayi yukler, bekler ve
    sonunda anlamsiz bir hata alirdi.
    """
    return bool(settings.model_for("document_vision"))


async def gorseli_coz(icerik: bytes, dosya_adi: str, vision_llm) -> AyristirilmisBelge:
    """Gorseli metin tarifine cevirip `AyristirilmisBelge` olarak doner.

    Args:
        icerik: Ham gorsel baytlari.
        dosya_adi: Kullanicinin yukledigi ad (MIME tespiti ve rapor dipnotu).
        vision_llm: `generate_with_image` sunan istemci
            (`app.core.llm.VisionLLMClient`).

    Raises:
        GorselCozumlemeHatasi: Model yapilandirilmamis, gorsel destegi yok
            ya da cagri bos donmus.
    """
    if vision_llm is None:
        raise GorselCozumlemeHatasi(
            "Görsel analizi için model tanımlı değil. Yöneticinizin "
            "DOCUMENT_VISION_MODEL ayarını yapması gerekiyor."
        )

    # Salt metin bir model yanlislikla baglanmissa 400 beklemek yerine
    # burada, ANLASILIR bir mesajla duruyoruz.
    if not hasattr(vision_llm, "generate_with_image"):
        raise GorselCozumlemeHatasi(
            "Tanımlı görsel modeli görsel girdi desteklemiyor "
            "(salt metin bir model seçilmiş olabilir)."
        )

    try:
        tarif = await vision_llm.generate_with_image(GORSEL_PROMPT, icerik, mime_tipi(dosya_adi))
    except Exception as hata:  # noqa: BLE001 - saglayici istisnasi disariya sizmasin
        logger.exception("gorsel modeli cagrisi basarisiz", extra={"dosya": dosya_adi})
        raise GorselCozumlemeHatasi(f"Görsel okunamadı: {hata}") from hata

    if not (tarif or "").strip():
        raise GorselCozumlemeHatasi("Görsel modeli boş yanıt döndürdü.")

    return AyristirilmisBelge(
        tur="gorsel",
        dosya_adi=dosya_adi,
        metin=tarif.strip(),
        sayfa_sayisi=1,
        # Gorselden okunan her sey MODEL YORUMUDUR - PDF'ten cikarilan metin
        # gibi kesin degildir. Kullanici bunu bilmeli.
        uyarilar=[
            "İçerik görselden yapay zekâ ile okunmuştur; "
            "rakamları kaynağından doğrulamanız önerilir."
        ],
    )
