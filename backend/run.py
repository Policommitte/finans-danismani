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
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=["app"])
