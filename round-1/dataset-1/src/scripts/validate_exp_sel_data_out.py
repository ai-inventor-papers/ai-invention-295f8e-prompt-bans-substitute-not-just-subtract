#!/usr/bin/env python3
"""Validate a file against the exp_sel_data_out schema (schemas/exp_sel_data_out.json).

Portable stand-in for the AI Inventor aii-json validation script that was used in this step: the same
JSON Schema (draft-07) check plus the same warnings for empty input/output fields.

    .venv/bin/python scripts/validate_exp_sel_data_out.py full_data_out.json
Exits 1 when the schema check fails.
"""

import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator
from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "exp_sel_data_out.json"

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")


def is_empty(value: object) -> bool:
    return value is None or str(value).strip() == ""


@logger.catch(reraise=True)
def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: validate_exp_sel_data_out.py <file.json>")
    path = Path(sys.argv[1])
    data = json.loads(path.read_text())
    errors = sorted(Draft7Validator(json.loads(SCHEMA.read_text())).iter_errors(data), key=lambda e: list(e.path))
    for e in errors[:20]:
        logger.error(f"{' -> '.join(map(str, e.path))}: {e.message[:200]}")
    warnings = []
    for ds in data.get("datasets", []) if isinstance(data, dict) else []:
        for i, ex in enumerate(ds.get("examples", [])):
            if is_empty(ex.get("input")):
                warnings.append(f"'{ds.get('dataset')}' example {i} has empty 'input' field")
            if is_empty(ex.get("output")):
                warnings.append(f"'{ds.get('dataset')}' example {i} has empty 'output' field")
    for w in warnings[:20]:
        logger.warning(w)
    if errors:
        logger.error(f"Validation FAILED ({len(errors)} errors) for {path.name}")
        sys.exit(1)
    logger.info(f"Validation PASSED for {path.name} ({len(warnings)} warnings)")


if __name__ == "__main__":
    main()
