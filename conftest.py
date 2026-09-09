"""Pone la raíz del repo en `sys.path` para que `tests/` importe `pet_logic`.

NO es redundante: en modo de import `prepend`, pytest inserta el basedir de cada
módulo de test, que al no haber `tests/__init__.py` es `tests/` y no la raíz. Es
este conftest el que hace importable la raíz. Sin él, `pytest -q` falla con
`ModuleNotFoundError: No module named 'pet_logic'` (con `python -m pytest` no se
nota, porque ese sí añade el cwd a `sys.path`).
"""

import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
