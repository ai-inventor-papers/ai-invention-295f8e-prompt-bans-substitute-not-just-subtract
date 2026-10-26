#!/usr/bin/env python3
"""full / mini / preview variants of method_out.json (the aii-json formatter needs a top-level array; this object
keeps its datasets): full = identical; mini = the first 3 examples per dataset; preview = mini with every string
truncated to 200 characters (metadata included)."""
import json
import shutil
import sys
from pathlib import Path

src = Path(sys.argv[1] if len(sys.argv) > 1 else "method_out.json")
d = json.loads(src.read_text())
shutil.copyfile(src, src.with_name("full_" + src.name))


def trunc(o):
    if isinstance(o, str):
        return o[:200]
    if isinstance(o, list):
        return [trunc(x) for x in o[:20]]
    if isinstance(o, dict):
        return {k: trunc(v) for k, v in o.items()}
    return o


mini = {"metadata": d.get("metadata", {}), "datasets": [{"dataset": x["dataset"], "examples": x["examples"][:3]}
                                                        for x in d["datasets"]]}
src.with_name("mini_" + src.name).write_text(json.dumps(mini))
prev = {"metadata": trunc(d.get("metadata", {})), "datasets": [{"dataset": x["dataset"],
                                                                "examples": trunc(x["examples"][:3])}
                                                               for x in d["datasets"]]}
src.with_name("preview_" + src.name).write_text(json.dumps(prev, indent=1))
print("ok")
