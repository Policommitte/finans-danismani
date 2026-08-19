"""Uygulamayi baslatir - Windows'ta `uvicorn app.main:app` YERINE bunu calistirin.

    python run.py

NEDEN GEREKLI (yalnizca Windows)
    psycopg'nin async surucusu, Windows'un VARSAYILAN event loop'u olan
    ProactorEventLoop ile calismaz. Duzeltme normalde
    `asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())` ama bu
    satir `app/main.py` icine konursa ISE YARAMAZ: `uvicorn app.main:app`
    komutu once KENDI event loop'unu `asyncio.run()` ile olusturur, `app.main`
    modulunu ise o loop'un ICINDE, gecikmeli import eder (Config.load()).
    Yani policy o zaman ayarlansa bile loop ZATEN kurulmus olur.

    Bu betik policy'yi uvicorn'un KENDI event loop'unu olusturmasindan
    (`uvicorn.run()` cagrisindan) ONCE ayarlar - dogru sira budur.

Linux/macOS'ta (CI, production, Docker) bu dosyaya GEREK YOKTUR;
`uvicorn app.main:app` orada sorunsuz calisir ve Dockerfile'daki CMD
degistirilmedi.
"""

from __future__ import annotations

import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn

if __name__ == "__main__":
    # 127.0.0.1 - bu betik YEREL gelistirme icindir. "0.0.0.0" sunucuyu ayni
    # agdaki herkese acar; kafe/okul agindayken JWT_SECRET varsayilaniyla
    # calisan bir API disariya acik olur. Docker/production'da adres
    # Dockerfile'daki CMD ile verilir, bu dosya oraya hic girmez.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=["app"])
