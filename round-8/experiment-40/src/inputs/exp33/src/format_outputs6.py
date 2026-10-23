#!/usr/bin/env python3
"""Portable stand-in for the aii-json format/validate scripts: writes full_/mini_/preview_method_out.json (mini = first
3 examples per dataset; preview = mini with every string truncated to 200 characters) and validates all four files
against schemas/exp_gen_sol_out.json with jsonschema."""

import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]


def trunc(o):
    if isinstance(o, str):
        return o[:200]
    if isinstance(o, list):
        return [trunc(x) for x in o]
    if isinstance(o, dict):
        return {k: trunc(v) for k, v in o.items()}
    return o


def main() -> None:
    src = ROOT / (sys.argv[1] if len(sys.argv) > 1 else "method_out.json")
    d = json.loads(src.read_text())
    mini = {**{k: v for k, v in d.items() if k != "datasets"},
            "datasets": [{"dataset": x["dataset"], "examples": x["examples"][:3]} for x in d["datasets"]]}
    out = {"full": d, "mini": mini, "preview": trunc(mini)}
    schema = json.loads((ROOT / "schemas" / "exp_gen_sol_out.json").read_text())
    for name, obj in out.items():
        p = src.with_name(f"{name}_{src.name}")
        p.write_text(json.dumps(obj, indent=1))
        jsonschema.validate(obj, schema)
        print(f"{p.name}: {sum(len(x['examples']) for x in obj['datasets'])} examples, schema OK")
    jsonschema.validate(d, schema)
    print(f"{src.name}: schema OK")


if __name__ == "__main__":
    main()
