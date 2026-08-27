"""Test modullerinin ust klasordeki modulleri import edebilmesi icin yol ayari.

`borsa-verisi/` bir Python paketi degil, bagimsiz bir betik klasorudur; bu
yuzden `symbols`, `yahoo` gibi moduller sys.path'e elle eklenir.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
