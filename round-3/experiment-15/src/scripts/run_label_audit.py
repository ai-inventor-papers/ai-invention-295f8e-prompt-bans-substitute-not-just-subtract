#!/usr/bin/env python3
"""C3: Llama label audit -- 5 bf16 baseline programs per task, second blind judge (j2), agreement with the combined label."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import label as L  # noqa: E402
from src.jobs import raw_rows  # noqa: E402
from src.ws import RESULTS, read_jsonl, setup_logging, write_json  # noqa: E402

setup_logging("label_audit")
raw_by = {r["row_id"]: r for r in L.pilot_rows() + raw_rows()}
labels = read_jsonl(L.LABELS)
au = L.label_audit(raw_by, labels)
write_json(RESULTS / "llama_label_audit.json", au)
print({k: v for k, v in au.items() if k != "rows"})
