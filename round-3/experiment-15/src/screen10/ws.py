"""exp10 workspace bridge, patched: canon from the writable copy screen10/canon, exp10 data/results read-only."""
import sys
from pathlib import Path

WS10 = Path(__file__).resolve().parent.parent / "inputs" / "exp10"
CANON = Path(__file__).resolve().parent / "canon"
DATA = WS10 / "data"
RESULTS = WS10 / "results"
if str(CANON) not in sys.path:
    sys.path.insert(0, str(CANON))
import common as C  # noqa: E402,F401


def model_path() -> str:
    from src.ws import model_path as mp
    return mp()
