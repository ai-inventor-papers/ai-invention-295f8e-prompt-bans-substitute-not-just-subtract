"""Replace machine-specific absolute paths in logs/ with portable placeholders before publishing."""

import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
subs = [(str(ROOT), "<workspace>")]
for var in ("HF_HUB_CACHE", "HF_HOME", "UV_CACHE_DIR", "TORCH_HOME"):
    v = os.environ.get(var)
    if v:
        subs.append((v, f"${var}"))
subs.append((re.escape(str(ROOT.parents[4]) + "/"), "<runs>/"))  # the shared runs folder of the pipeline
n = 0
for p in sorted((ROOT / "logs").rglob("*")):
    if not p.is_file():
        continue
    try:
        t = p.read_text()
    except UnicodeDecodeError:
        continue
    t2 = t
    for a, b in subs:
        t2 = re.sub(a if a.startswith("<runs>") or "\\" in a else re.escape(a), b, t2)
    if t2 != t:
        p.write_text(t2)
        n += 1
print(f"sanitized {n} log files")
