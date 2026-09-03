"""1 aylik fiyat tahmini (TimesFM 2.5 + shrinkage + TL drift).

Moduller:
    types   Ortak sozlesme (Tahmin, TahminNoktasi) - frontend bunu gorur
    model   TimesFM sarmalayicisi; AGIR bagimliliklari (torch) izole eder
    engine  Ham cikti -> urun: shrinkage, TL drift, band kaydirma
    service Veri cekme + onbellek + portfoy toplama

⚠️ OZELLIK VARSAYILAN OLARAK KAPALIDIR. `FORECAST_MODEL` bos ya da
`torch`/`timesfm` kurulu degilse `model.yuklu_mu()` False doner ve tum
katman sessizce devre disi kalir - uygulama normal calisir, grafiklerde
yalnizca kesikli tahmin cizgisi cizilmez.

Model secimi OLCUME dayanir (42 varlik, 2 yil, 378 kesit sizintisiz
walk-forward): uretim yapilandirmasi %6,93 MAPE / %59,5 yon isabeti /
%79,1 bant kapsami ile naive tabanini (%7,07) gecen TEK yapilandirmadir.
Ayrinti: `engine.py` modul docstring'i.
"""
