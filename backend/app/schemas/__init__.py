"""REST istek/yanit modelleri (Pydantic).

⚠️ Bu paket ile `app/orchestration/` karistirilmamalidir: burasi HTTP
sinirindaki sozlesme, orasi graph icinde tasinan durum modelleri.

ALAN ADLANDIRMA: her yerde `snake_case` (mimari v4 bolum 10.3). DB, orkestrasyon
modelleri ve SSE olaylari zaten snake_case; REST'i camelCase yapmak frontend'e
IKI ayri sozlesme tasitirdi.
"""
