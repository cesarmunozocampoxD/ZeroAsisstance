"""Pone la raíz del repo en `sys.path` para que `tests/` importe `pet_logic`."""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
