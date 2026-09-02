"""TimesFM 2.5 sarmalayicisi - agir bagimliliklari TEK NOKTADA izole eder.

NEDEN AYRI MODUL
----------------
`torch` + `timesfm` yaklasik 1-2 GB bellek ve ~200 MB indirme demektir.
Bunu uygulamanin zorunlu bagimliligi yapmak, tahmin ozelligini hic
kullanmayan bir dagitimi da (orn. kucuk bellekli Render/Railway plani)
cezalandirirdi. Bu yuzden:

  * import'lar GECIKMELI (fonksiyon icinde) - modul yuklenmesi ucuz
  * paket yoksa `yuklu_mu()` False doner, ozellik SESSIZCE kapanir
  * `FORECAST_MODEL` bos ise model hic indirilmez

Ayni desen LLM katmaninda da var (`app/core/llm.py`): anahtar/model
tanimli degilse sistem calisir, yalnizca o ozellik kapanir.

MODEL NEDEN TimesFM
-------------------
Olcume dayanir, tercihe degil. 42 varlik / 2 yillik gercek veri, sizintisiz
walk-forward: TimesFM naive'e EN YAKIN gelen model oldu (+%3,8), Chronos-Bolt
(+%11,7), GBM (+%8,8), ARIMA (+%7,2), Prophet (+%106) geride kaldi.
Shrinkage + TL drift ile birlestirildiginde naive'i GECTI (%6,93 vs %7,07).
"""

from __future__ import annotations

import logging
import threading

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

#: Model surecte BIR KEZ yuklenir (~2sn CPU) ve paylasilir. Kilit gerekli:
#: FastAPI ayni anda birden fazla istegi thread pool'da isleyebilir ve iki
#: es zamanli yukleme hem bellegi ikiye katlar hem yarisa girer.
_model = None
_kilit = threading.Lock()


def yuklu_mu() -> bool:
    """Tahmin ozelligi CALISABILIR durumda mi?

    Uc kosul: model adi tanimli, `timesfm` kurulu, `torch` kurulu.
    Herhangi biri eksikse ozellik kapalidir - bu bir HATA DEGILDIR.
    """
    if not settings.forecast_model.strip():
        return False
    try:
        import timesfm  # noqa: F401
        import torch  # noqa: F401
    except ImportError:
        return False
    return True


def _modeli_getir():
    """Modeli tembel yukler; ayni surecte tekrar yuklemez."""
    global _model
    if _model is not None:
        return _model

    with _kilit:
        # Cift kontrol: kilidi beklerken baska bir thread yuklemis olabilir.
        if _model is not None:
            return _model

        import timesfm

        logger.info("TimesFM yukleniyor", extra={"model": settings.forecast_model})
        model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(settings.forecast_model)
        model.compile(
            timesfm.ForecastConfig(
                max_context=settings.forecast_context_days,
                max_horizon=settings.forecast_horizon_days,
                normalize_inputs=True,
                # Kuantil basligi ZORUNLU: bant (alt/ust) bundan uretilir,
                # kapatilirsa yalnizca nokta tahmini kalir ve urunun asil
                # degerli parcasi (kalibre edilmis belirsizlik) kaybolur.
                use_continuous_quantile_head=True,
            )
        )
        _model = model
        logger.info("TimesFM hazir")
        return _model


def ham_tahmin(kapanislar: np.ndarray, ufuk: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Modelin HAM ciktisi: (medyan, q10, q90) - her biri `ufuk` uzunlugunda.

    ⚠️ KUANTIL SUTUN SIRASI DOGRULANDI (timesfm 3.0.0, canli test):
    `forecast()` `(nokta[1,H], kuantil[1,H,10])` doner. Kuantil eksenindeki
    10 sutun: index 0 = nokta tahmini (medyanla AYNI), index 1..9 =
    [0.1, 0.2, ..., 0.9] kuantilleri SIRAYLA. Yani %80 araligi icin
    index 1 (q0.10) ve index 9 (q0.90) kullanilir; index 5 medyandir.

    Bu sira KODA GOMULU BIR VARSAYIMDIR - timesfm surumu yukseltilirse
    `_kuantil_sirasi_dogrula()` testi ile yeniden dogrulanmalidir.
    """
    model = _modeli_getir()
    baglam = np.asarray(kapanislar[-settings.forecast_context_days :], dtype=np.float64)
    _, kuantil = model.forecast(horizon=ufuk, inputs=[baglam])

    medyan = np.asarray(kuantil[0, :, 5], dtype=np.float64)
    q10 = np.asarray(kuantil[0, :, 1], dtype=np.float64)
    q90 = np.asarray(kuantil[0, :, 9], dtype=np.float64)
    return medyan, q10, q90
