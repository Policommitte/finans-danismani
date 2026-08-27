"""Sinyal uretimi (D-02'nin ilk iki kutusu).

Sinyal ENSTRUMAN bazlidir ve kullanicidan bagimsizdir (FR-SIG-026);
kisisellestirme bir ust katmanda, `services/recommendation.py` icinde yapilir.
"""

from app.signals.engine import sinyal_uret

__all__ = ["sinyal_uret"]
