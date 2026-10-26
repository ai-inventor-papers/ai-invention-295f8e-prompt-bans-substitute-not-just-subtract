import sys
from pathlib import Path
def patch(path, old, new, count=1):
    p = Path(path); s = p.read_text()
    n = s.count(old)
    assert n == count, (path, n, old[:80])
    p.write_text(s.replace(old, new))
    print("patched", path, old[:50].replace("\n", " "))
