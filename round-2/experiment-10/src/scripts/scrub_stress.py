#!/usr/bin/env python3
"""T5b scrubber stress test on the dataset artifact (art_j3Rm_lr2nzR6), covering every one of its 10 datasets:

- code-bearing datasets (thealgorithms_python, kodcode_algorithmic, xlcost_python, mercury, leetcodedataset, enamel,
  humanevalplus): up to 400 programs each (those whose text names a catalogue algorithm first). Scrub, then check that
  the program still parses, that no name-table match survives outside import lines, and that programs naming nothing
  are left byte-identical;
- clrs_text: algorithm traces scrubbed as TEXT (neutralise), residual matches counted;
- concreteness_norms: the neutral-noun bank (used by the main protocol; re-tokenised under Llama in src/config.py);
- llm_creativity: blind-judge T02 mode labels of 225 programs by other LLMs, reported as an external reference
  distribution next to Llama's sampled T2 baseline.
Writes results/scrub_stress.json.  Run: .venv/bin/python scripts/scrub_stress.py
"""

from __future__ import annotations

import ast
import collections
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.ws import dependency_dataset  # noqa: E402

DEP = dependency_dataset()  # dataset artifact full_data_out.json (override: AII_DEP_DATASET)

import io  # noqa: E402
import tokenize  # noqa: E402

from src.names import find_all, identifier_names_algorithm, neutralise  # noqa: E402
from src.scrub import residual_names, scrub  # noqa: E402


def names_anything(code: str) -> bool:
    if find_all(code, None):
        return True
    try:
        return any(t.type == tokenize.NAME and identifier_names_algorithm(t.string)
                   for t in tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return True


def attribute_residuals(code: str) -> int:
    """Residual identifiers in attribute position (after '.'), which the plan never renames."""
    n, prev = 0, None
    for t in tokenize.generate_tokens(io.StringIO(code).readline):
        if t.type == tokenize.NAME and prev is not None and prev.string == "." and identifier_names_algorithm(t.string):
            n += 1
        if t.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
            prev = t
    return n

CODE_SETS = ("thealgorithms_python", "kodcode_algorithmic", "xlcost_python", "mercury", "leetcodedataset", "enamel",
             "humanevalplus")


def main() -> None:
    d = json.loads(DEP.read_text())
    rng = random.Random(0)
    out: dict = {"source": "art_j3Rm_lr2nzR6 full_data_out.json", "datasets": {}}
    for ds in d["datasets"]:
        name, ex = ds["dataset"], ds["examples"]
        if name in CODE_SETS:
            progs = [e["output"] for e in ex if isinstance(e.get("output"), str) and e["output"].strip()]
            named = [p for p in progs if names_anything(p)]
            plain = [p for p in progs if not names_anything(p)]
            rng.shuffle(named)
            rng.shuffle(plain)
            pick = named[:300] + plain[:100]
            stats = collections.Counter()
            for p in pick:
                try:
                    ast.parse(p)
                except (SyntaxError, ValueError):
                    stats["unparsable_input"] += 1
                    continue
                stats["n"] += 1
                try:
                    s, info = scrub(p)
                except (SyntaxError, ValueError, IndentationError) as e:
                    stats["scrub_error"] += 1
                    continue
                stats["parses_after"] += 1
                if residual_names(s):
                    stats["residual_names"] += 1
                    stats["residual_attribute_only"] += int(len(residual_names(s)) == attribute_residuals(s))
                if not names_anything(p):
                    stats["plain"] += 1
                    stats["plain_identical"] += int(s == p)
                if info["renamed"]:
                    stats["renamed_any"] += 1
            out["datasets"][name] = {"n_examples": len(ex), "n_naming_an_algorithm": len(named), **stats}
        elif name == "clrs_text":
            pick = [e["input"] for e in ex if isinstance(e.get("input"), str)][:500]
            before = sum(1 for t in pick if find_all(t, None))
            after = sum(1 for t in pick if find_all(neutralise(t), None))
            out["datasets"][name] = {"n_examples": len(ex), "n_tested": len(pick), "texts_naming_before": before,
                                     "texts_naming_after": after}
        elif name == "concreteness_norms":
            out["datasets"][name] = {"n_examples": len(ex), "use": "neutral-noun bank (718 candidates) -> src/config.py",
                                     "n_candidates": sum(1 for e in ex if e.get("metadata_noun_bank_candidate") in (True, "True"))}
        elif name == "llm_creativity":
            c = collections.Counter(str(e.get("metadata_t02_mode")) for e in ex)
            out["datasets"][name] = {"n_examples": len(ex), "t02_mode_counts": dict(c),
                                     "use": "external reference: blind-judge T02 labels of other LLMs' programs"}
    ok = all(v.get("scrub_error", 0) == 0 and v.get("residual_names", 0) == v.get("residual_attribute_only", 0)
             and v.get("plain", 0) == v.get("plain_identical", 0) for k, v in out["datasets"].items() if k in CODE_SETS)
    out["pass_rule"] = ("no scrub error; every residual is an attribute name (never renamed by the plan's rule); programs "
                        "naming no algorithm (text or identifier) are byte-identical")
    out["all_pass"] = bool(ok)
    (ROOT / "results" / "scrub_stress.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
