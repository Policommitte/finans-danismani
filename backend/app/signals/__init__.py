"""Sinyal uretimi (D-02'nin ilk iki kutusu).

Sinyal ENSTRUMAN bazlidir ve kullanicidan bagimsizdir (FR-SIG-026);
kisisellestirme bir ust katmanda, `services/recommendation.py` icinde yapilir.
"""

from app.signals.engine import KURAL_ADLARI, generate_signals, rule_name

__all__ = ["KURAL_ADLARI", "rule_name", "generate_signals"]
