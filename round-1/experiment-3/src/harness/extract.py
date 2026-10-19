"""Code-block extraction shared by the parent process and the sandboxed child."""

from __future__ import annotations

import hashlib
import re

_FENCE = re.compile(r"```[ \t]*(?:python3?|py|Python)[ \t]*\r?\n(.*?)(?:\r?\n[ \t]*```|\Z)", re.S)


def extract_code(text: str) -> str | None:
    """First ```python block (closing fence optional: the closing-fence stop string strips it)."""
    m = _FENCE.search(text or "")
    if not m:
        return None
    code = m.group(1)
    return code if code.strip() else None


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()
