"""Belge/gorsel analiz ve PDF rapor ajani.

BORU HATTI
----------
    ekli dosya
      |-- pdf/excel --> parser.ayristir      --.
      |-- gorsel     --> vision.gorseli_coz  --'--> AyristirilmisBelge
                                                        |
                                          ANA MODEL (nemotron) - yapilandirilmis JSON
                                                        |
                                                   AnalizSonucu
                                                    /         \\
                                          charts.grafik_ciz   report.rapor_uret
                                                    \\         /
                                                     PDF baytlari

NEDEN JSON ISTIYORUZ
--------------------
Rapor tablo ve grafik icerir; ikisi de SAYI ister. Serbest metinden sayi
ayiklamak ("net kar 1,42 milyar TL'ye yukseldi" cumlesinden 1420000000
uretmek) sessiz hata kaynagidir - model rakami yaziyla yazdiginda grafik bos
cikar ve kimse fark etmez. Bu yuzden modelden `AnalizSonucu` semasinda JSON
istenir ve savunmali ayristirilir.

LLM YOKSA NE OLUR
-----------------
Diger ajanlarla ayni ilke: sistem LLM'siz de calisir. Model bagli degilse
ajan belgeden DETERMINISTIK bir ozet (tablo basliklari, satir sayilari)
uretir ve PDF yine olusur - yalnizca yorum metni yerine ham dokum konur.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile

from app.agents.base import AgentLLMTimeout, BaseAgent
from app.config import settings
from app.documents import charts, parser, report, vision
from app.documents.types import AnalizSonucu, AyristirilmisBelge, Gosterge, Grafik
from app.orchestration.models import AgentError, AgentState, Source

logger = logging.getLogger(__name__)

#: Modelden istenen JSON semasi. Prompt icine GOMULUR; alan adlari
#: `AnalizSonucu` ile birebir ayni olmak zorundadir.
ISTENEN_SEMA = """{
  "baslik": "kısa rapor başlığı",
  "sade_aciklama": "finans bilmeyen birine 2-3 cümleyle ne anlama geldiği",
  "ozet": "belgenin 2-4 cümlelik özeti",
  "bulgular": ["önemli bulgu", "..."],
  "gostergeler": [{"ad": "Net Kâr", "deger": "1,42 milyar TL", "sayisal": 1420}],
  "grafik": {"tur": "bar", "baslik": "...", "etiketler": ["2024","2025"],
             "degerler": [980, 1200], "eksen_adi": "..."},
  "riskler": ["dikkat edilmesi gereken nokta", "..."]
}"""

ANALIZ_PROMPT = """Sen bir finans analistisin. Aşağıdaki belgeyi analiz et.

ÇOK ÖNEMLİ KURALLAR:
- Kullanıcı finans terimi BİLMİYOR. "sade_aciklama" alanını günlük konuşma
  diliyle yaz; terim kullanman gerekirse parantez içinde açıkla.
- SADECE belgede olan bilgiyi kullan. Belgede olmayan rakam ÜRETME.
- Rakamları belgede yazdığı gibi aktar, yuvarlama yapma.
- "sayisal" alanına sadece grafiğe konabilecek saf sayıyı yaz (birim yok).
- Grafiğe koyacak en az 2 karşılaştırılabilir sayı yoksa "grafik": null yaz.
- Belge finansal değilse bunu "ozet" alanında dürüstçe belirt.

YANITINI SADECE ŞU JSON ŞEMASINDA VER, başka hiçbir şey yazma:
{sema}

--- BELGE: {dosya_adi} ---
{icerik}
--- BELGE SONU ---"""


class DocumentAnalysisAgent(BaseAgent):
    """Ekli PDF/Excel/gorseli analiz edip PDF rapor ureten ajan.

    Diger ajanlardan iki farki var:
      1. Anahtar kelimeyle DEGIL, ekli dosyanin varliğiyla tetiklenir
         (bkz. `Orchestrator.route_node`).
      2. Ciktisi yalnizca metin degil, aynı zamanda bir PDF DOSYASIDIR;
         `document_data["pdf_bytes"]` icinde tasinir.
    """

    name = "document_analysis"

    def __init__(
        self,
        mcp_client,
        llm,
        timeout_seconds: int,
        llm_timeout_seconds: int | None = None,
        vision_llm=None,
    ) -> None:
        super().__init__(mcp_client, llm, timeout_seconds, llm_timeout_seconds)
        #: Gorsel okuma modeli. `None` ise gorsel yolu kapalidir; PDF/Excel
        #: yolu bundan ETKILENMEZ.
        self.vision_llm = vision_llm

    async def get_tools(self) -> list:
        """Bu ajan MCP tool KULLANMAZ.

        Veri kaynagi kullanicinin yukledigi dosyadir; veritabanina ya da
        piyasa servislerine gitmez. Taban sinifin `document_analysis_*`
        onekli tool arayan varsayilani bos donerdi ama acikca belirtmek
        niyeti gorunur kilar.
        """
        return []

    # ------------------------------------------------------------------
    # Ana akis
    # ------------------------------------------------------------------

    async def _execute(self, state: AgentState) -> dict:
        belge_girdisi = getattr(state, "belge", None)
        if not belge_girdisi:
            # Ajan kayitli ama bu turda dosya yok - sessiz no-op.
            return {}

        dosya_adi = belge_girdisi.get("dosya_adi") or "belge"
        icerik = belge_girdisi.get("icerik") or b""
        if not icerik:
            return self._hata("Yüklenen dosya boş görünüyor.")

        # 1) Ayristirma
        try:
            belge = await self._belgeyi_coz(icerik, dosya_adi)
        except (parser.BelgeAyristirmaHatasi, vision.GorselCozumlemeHatasi) as hata:
            return self._hata(str(hata))

        # 2) Analiz (LLM varsa yapilandirilmis, yoksa deterministik)
        sonuc, llm_hatasi = await self._analiz_et(belge, state.user_query)

        # 3) Grafik + 4) PDF
        pdf_baytlari, grafik_var = self._rapor_derle(sonuc, belge)

        rapor_adi = self._rapor_dosya_adi(dosya_adi)
        cikti: dict = {
            # METIN tarafi: sentezleyici ve deterministik yanit bunu okur.
            # `summary_text` ZORUNLU - `_ajan_metni()` onu bulamazsa sozlugun
            # tamamini `str()` ile dokerdi.
            "document_data": {
                "summary_text": self._ozet_cumlesi(sonuc, belge, rapor_adi),
                "dosya_adi": dosya_adi,
                "tur": belge.tur,
                "baslik": sonuc.baslik,
                "ozet": sonuc.ozet,
                "sade_aciklama": sonuc.sade_aciklama,
                "bulgular": sonuc.bulgular,
                "gosterge_sayisi": len(sonuc.gostergeler),
                "grafik_var": grafik_var,
                "uyarilar": belge.uyarilar,
                "rapor_dosya_adi": rapor_adi,
            },
            # IKILI taraf: metin yollarindan hicbiri bu alani okumaz.
            "document_report": {"pdf_bytes": pdf_baytlari, "dosya_adi": rapor_adi},
            # Kaynak izlenebilirligi: yanitin dayandigi belge kullaniciya
            # kaynak kartinda gosterilir (FR-RAG-04 ile ayni ilke).
            "sources": [
                Source(
                    doc_id=f"upload:{dosya_adi}",
                    baslik=sonuc.baslik or dosya_adi,
                    sirket=None,
                    tip="belge",
                )
            ],
        }
        if llm_hatasi:
            cikti["agent_errors"] = [llm_hatasi]
        return cikti

    async def _belgeyi_coz(self, icerik: bytes, dosya_adi: str) -> AyristirilmisBelge:
        """Dosyayi turune gore dogru ayristiriciya yollar."""
        tur = parser.belge_turu(dosya_adi)
        if tur == "gorsel":
            return await vision.gorseli_coz(icerik, dosya_adi, self.vision_llm)
        # pdfplumber/openpyxl SENKRON ve CPU-yogun: event loop'u bloklamamak
        # icin ayri bir thread'e alinir. Bloklasaydi ayni anda akan diger
        # sohbetlerin token'lari da dururdu.
        import asyncio

        return await asyncio.to_thread(parser.ayristir, icerik, dosya_adi)

    # ------------------------------------------------------------------
    # Analiz
    # ------------------------------------------------------------------

    async def _analiz_et(
        self, belge: AyristirilmisBelge, kullanici_sorusu: str
    ) -> tuple[AnalizSonucu, AgentError | None]:
        """Belgeyi `AnalizSonucu`'na cevirir; LLM yoksa/coktuyse deterministik."""
        if self.llm is None:
            return self._deterministik_ozet(belge), None

        icerik = belge.ozet_girdi(settings.document_max_input_chars)
        prompt = ANALIZ_PROMPT.format(sema=ISTENEN_SEMA, dosya_adi=belge.dosya_adi, icerik=icerik)
        if kullanici_sorusu.strip():
            prompt += (
                f"\n\nKullanıcının bu belgeyle ilgili sorusu: {kullanici_sorusu.strip()}\n"
                "Cevabını 'ozet' alanına dahil et."
            )

        try:
            ham = await self.generate(prompt)
        except AgentLLMTimeout as hata:
            logger.warning("belge analizi LLM zaman asimi", extra={"agent": self.name})
            return self._deterministik_ozet(belge), AgentError(
                agent_name=self.name, error_type="timeout", message=str(hata)
            )
        except Exception as hata:  # noqa: BLE001 - LLM cokse de rapor uretilmeli
            logger.exception("belge analizi LLM cagrisi coktu", extra={"agent": self.name})
            return self._deterministik_ozet(belge), AgentError(
                agent_name=self.name,
                error_type="llm_error",
                message=f"Belge analizi üretilemedi: {hata}",
            )

        sonuc = self._json_coz(ham)
        if sonuc is None or sonuc.bos_mu():
            logger.warning(
                "model gecerli JSON uretmedi, deterministik ozete dusuluyor",
                extra={"agent": self.name},
            )
            return self._deterministik_ozet(belge), AgentError(
                agent_name=self.name,
                error_type="llm_error",
                message="Model beklenen biçimde yanıt vermedi; ham özet kullanıldı.",
            )
        return sonuc, None

    @staticmethod
    def _json_coz(ham: str) -> AnalizSonucu | None:
        """Model ciktisindan `AnalizSonucu` ayiklar; basarisizsa `None`.

        SAVUNMALI olmak zorunda: modeller JSON'u ```json cercevesine alir,
        basina "Iste analiz:" yazar ya da sonuna aciklama ekler. Ham
        `json.loads` bu durumlarin HEPSINDE patlar.
        """
        if not ham:
            return None

        metin = ham.strip()
        # ```json ... ``` cercevesini soy.
        cerceve = re.search(r"```(?:json)?\s*(.+?)\s*```", metin, re.DOTALL)
        if cerceve:
            metin = cerceve.group(1).strip()

        # Ilk '{' ile son '}' arasi: cevresindeki aciklama metnini atar.
        bas, son = metin.find("{"), metin.rfind("}")
        if bas == -1 or son <= bas:
            return None

        try:
            veri = json.loads(metin[bas : son + 1])
        except json.JSONDecodeError:
            logger.warning("model ciktisi JSON olarak cozulemedi")
            return None

        if not isinstance(veri, dict):
            return None

        try:
            return AnalizSonucu(
                baslik=str(veri.get("baslik") or "Belge Analiz Raporu"),
                ozet=str(veri.get("ozet") or ""),
                sade_aciklama=str(veri.get("sade_aciklama") or ""),
                bulgular=[str(b) for b in (veri.get("bulgular") or []) if str(b).strip()],
                riskler=[str(r) for r in (veri.get("riskler") or []) if str(r).strip()],
                gostergeler=DocumentAnalysisAgent._gostergeleri_coz(veri.get("gostergeler")),
                grafik=DocumentAnalysisAgent._grafigi_coz(veri.get("grafik")),
            )
        except Exception:  # noqa: BLE001 - bozuk alan tum rapora mal olmasin
            logger.exception("model JSON'u modele cevrilemedi")
            return None

    @staticmethod
    def _gostergeleri_coz(ham) -> list[Gosterge]:
        """Gosterge listesini savunmali cevirir; bozuk kayitlari ATLAR."""
        if not isinstance(ham, list):
            return []

        gostergeler: list[Gosterge] = []
        for kayit in ham:
            if not isinstance(kayit, dict):
                continue
            ad = str(kayit.get("ad") or "").strip()
            deger = str(kayit.get("deger") or "").strip()
            if not ad or not deger:
                continue

            sayisal = kayit.get("sayisal")
            try:
                sayisal = float(sayisal) if sayisal is not None else None
            except (TypeError, ValueError):
                # Model "1,4 milyar" gibi bir sey yazdiysa sayisal deger
                # kaybedilir ama METIN deger tabloda dogru gorunur.
                sayisal = None

            gostergeler.append(Gosterge(ad=ad, deger=deger, sayisal=sayisal))
        return gostergeler

    @staticmethod
    def _grafigi_coz(ham) -> Grafik | None:
        """Grafik onerisini cevirir; gecersizse `None` (rapor grafiksiz cikar)."""
        if not isinstance(ham, dict):
            return None

        try:
            degerler = [float(d) for d in (ham.get("degerler") or [])]
        except (TypeError, ValueError):
            return None

        grafik = Grafik(
            tur=str(ham.get("tur") or "bar").lower().strip(),
            baslik=str(ham.get("baslik") or ""),
            etiketler=[str(e) for e in (ham.get("etiketler") or [])],
            degerler=degerler,
            eksen_adi=str(ham.get("eksen_adi") or ""),
        )
        return grafik if grafik.gecerli_mi() else None

    @staticmethod
    def _deterministik_ozet(belge: AyristirilmisBelge) -> AnalizSonucu:
        """LLM'siz/LLM coktugunde uretilen ham ama DURUST ozet.

        Yorum icermez - yalnizca belgeden kesin olarak bilinenleri listeler.
        Kullanici bos bir rapor yerine en azindan belgenin yapisini gorur.
        """
        bulgular: list[str] = []
        for tablo in belge.tablolar[:5]:
            basliklar = ", ".join(tablo.basliklar[:6]) if tablo.basliklar else "başlıksız"
            bulgular.append(f"{tablo.kaynak}: {len(tablo.satirlar)} satır ({basliklar})")

        if belge.metin.strip():
            ilk = " ".join(belge.metin.split())[:400]
            bulgular.append(f"Belge metninin başlangıcı: {ilk}…")

        return AnalizSonucu(
            baslik=f"{belge.dosya_adi} — Belge Dökümü",
            ozet=(
                "Yapay zekâ yorumu şu anda üretilemedi; aşağıda belgeden "
                "doğrudan çıkarılan bilgiler yer alıyor."
            ),
            sade_aciklama=(
                "Bu rapor, belgenizden okunabilen bilgilerin ham dökümüdür. " "Yorum içermez."
            ),
            bulgular=bulgular,
        )

    # ------------------------------------------------------------------
    # Rapor derleme
    # ------------------------------------------------------------------

    def _rapor_derle(self, sonuc: AnalizSonucu, belge: AyristirilmisBelge) -> tuple[bytes, bool]:
        """Grafik + PDF uretir. Grafik basarisiz olsa da PDF DONER."""
        with tempfile.TemporaryDirectory(prefix="polifin_rapor_") as gecici:
            grafik_yolu = charts.grafik_ciz(sonuc.grafik, gecici) if sonuc.grafik else None
            try:
                pdf = report.rapor_uret(sonuc, belge, grafik_yolu)
            except Exception:  # noqa: BLE001
                logger.exception("PDF derlenemedi, grafiksiz yeniden deneniyor")
                # Grafik gomme adimi (bozuk PNG, oran hatasi) tek basina
                # cokerse metin raporunu kurtarmayi dene.
                pdf = report.rapor_uret(sonuc, belge, None)
                return pdf, False
            return pdf, grafik_yolu is not None

    @staticmethod
    def _ozet_cumlesi(sonuc: AnalizSonucu, belge: AyristirilmisBelge, rapor_adi: str) -> str:
        """Sohbet akisinda gosterilecek kisa metin.

        Raporun TAMAMI buraya konmaz: kullanici ayrintiyi PDF'te gorur,
        sohbette yalnizca ne yapildigini ve ozeti okur.
        """
        tur_adi = {"pdf": "PDF belgesi", "excel": "Excel dosyası", "gorsel": "görsel"}.get(
            belge.tur, "belge"
        )
        satirlar = [f"{belge.dosya_adi} adlı {tur_adi} incelendi."]

        if sonuc.sade_aciklama:
            satirlar.append(sonuc.sade_aciklama)
        elif sonuc.ozet:
            satirlar.append(sonuc.ozet)

        if sonuc.bulgular:
            satirlar.append("Öne çıkanlar: " + "; ".join(sonuc.bulgular[:3]))

        satirlar.append(f"Ayrıntılı özet raporu hazırlandı: {rapor_adi}")
        return " ".join(satirlar)

    @staticmethod
    def _rapor_dosya_adi(kaynak_adi: str) -> str:
        """Kaynak dosya adindan guvenli bir rapor adi turetir.

        Dizin ayraclari ve tehlikeli karakterler TEMIZLENIR: ad ileride bir
        HTTP `Content-Disposition` basligina ya da dosya yoluna girebilir.
        """
        koku = os.path.splitext(os.path.basename(kaynak_adi))[0]
        guvenli = re.sub(r"[^\w\s.-]", "", koku, flags=re.UNICODE).strip() or "belge"
        return f"{guvenli}_analiz_raporu.pdf"

    def _hata(self, mesaj: str) -> dict:
        """Kullaniciya gosterilebilir bir ajan hatasi uretir."""
        return {
            "agent_errors": [
                AgentError(agent_name=self.name, error_type="tool_error", message=mesaj)
            ]
        }
