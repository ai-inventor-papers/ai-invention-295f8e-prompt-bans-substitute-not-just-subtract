"""Fallback for the aii-json format script: write full_/mini_/preview_ variants of method_out.json (mini = first 3
examples per dataset; preview = mini with every string truncated to 200 characters)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def trunc(o):
    if isinstance(o, str):
        return o[:200]
    if isinstance(o, list):
        return [trunc(x) for x in o]
    if isinstance(o, dict):
        return {k: trunc(v) for k, v in o.items()}
    return o


d = json.loads((ROOT / "method_out.json").read_text())
(ROOT / "full_method_out.json").write_text(json.dumps(d, indent=2))
mini = {**d, "datasets": [{**ds, "examples": ds["examples"][:3]} for ds in d["datasets"]]}
(ROOT / "mini_method_out.json").write_text(json.dumps(mini, indent=2))
(ROOT / "preview_method_out.json").write_text(json.dumps(trunc(mini), indent=2))
print("wrote full/mini/preview")
