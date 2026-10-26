#!/usr/bin/env python3
"""Ablate the whole-multiple-of-item term in the 'novel' bin-packing programs of the first search.

Reviewer check for Section 10.3 (art_k7A5-5vcXY1g). For each program whose multiple-of-item term is a
separable line, remove that line (and the related leftover-equals-item bonus), then re-score:
  * held-out excess on the two primary sets (FunSearch Weibull 5k test set, OR-Library binpack3), with the
    harness's packing loop and FunSearch's family excess (copied from the artifact's src/bp.py);
  * probe agreement on the committed 2,000 probe states against the stored decision vectors of the
    86-program corpus and the 3,843-member ab grid (as in the artifact's src/probes.py).
Before any ablation the script checks that it reproduces best fit and every full program's reported values.

Usage: python checks/ablate_whole_multiple.py --exp-dir <gen_art_experiment_51 dir> --out results/ablation.json
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from loguru import logger

ROOT = Path(__file__).resolve().parent.parent
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "ablate_whole_multiple.log", rotation="30 MB", level="DEBUG")

ERR = 65535  # probe decision for a failed state, as in src/probes.py
HELDOUT = ["H-FSW5k", "H-OR3"]

# Lines removed in order; variant k removes the first k lines. Strings are copied from results/v3_final.json.
ABLATIONS: dict[str, list[tuple[str, str]]] = {
    "cand_22": [("scores[multiples] += 8.0", "pass"), ("scores[closest] += 15.0", "pass")],
    "cand_20": [("scores[multiples] += 15.0", "pass"), ("scores[closest] += 25.0", "pass")],
    "cand_09": [("scores += np.where(available % item < 1e-5, 5, 0)", "pass")],
    "cand_29": [
        ("multiple_bonus = np.where(np.abs(remaining - np.round(remaining / item) * item) < 1e-6, 3, 0)",
         "multiple_bonus = 0"),
        ("match_score = -np.abs(remaining - np.round(remaining / item) * item)",
         "match_score = np.zeros_like(remaining, dtype=float)"),
    ],
}


def pack(items: list[int], cap: int, prio) -> int:
    """FunSearch semantics: one pre-allocated bin per item; the item goes to the first argmax over fitting bins."""
    bins = np.array([cap for _ in range(len(items))])
    for it in items:
        v = np.nonzero(bins >= it)[0]
        p = np.asarray(prio(it, bins[v]))
        bins[v[np.argmax(p)]] -= it
    return int((bins != cap).sum())


def family_excess(prio, insts: list[dict]) -> float:
    """FunSearch's excess in percent: (mean bins - mean L1) / mean L1 over the instance family."""
    nb = [pack(x["items"], x["capacity"], prio) for x in insts]
    mb, ml = float(np.mean(nb)), float(np.mean([x["l1"] for x in insts]))
    return 100.0 * (mb - ml) / ml


def compile_priority(src: str):
    ns: dict = {"np": np}
    exec(src, ns)  # noqa: S102 - the artifact's own generated programs, run as the harness runs them
    return ns["priority"]


def decide(prio, item: int, arr: np.ndarray) -> int:
    try:
        p = np.asarray(prio(item, arr.copy()))
        if p.ndim != 1 or p.shape[0] != arr.shape[0]:
            return ERR
        return int(arr[int(np.argmax(p))])
    except (ValueError, TypeError, IndexError, ZeroDivisionError, FloatingPointError):
        return ERR


def max_agreement(dv: np.ndarray, mats: np.ndarray, names: list[str]) -> tuple[float, str]:
    ag = ((mats == dv) & (dv != ERR)).mean(axis=1)
    j = int(np.argmax(ag))
    return float(ag[j]), names[j]


@logger.catch(reraise=True)
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp-dir", type=Path, required=True, help="path to gen_art_experiment_51")
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "ablation_whole_multiple.json")
    args = ap.parse_args()
    exp = args.exp_dir

    sets = {k: json.loads((exp / "data" / "instances" / f"{k}.json").read_text()) for k in HELDOUT}
    states_raw = json.loads((exp / "data" / "probes" / "P1.json").read_text())["states"]
    states = [(int(it), np.array(list(of) + [int(cap)] * int(ne))) for it, of, ne, cap in states_raw]
    corpus = [e for e in json.loads((exp / "data" / "corpus" / "corpus.json").read_text())["entries"]
              if e.get("decisions")]
    corp_m, corp_n = np.array([e["decisions"] for e in corpus]), [e["name"] for e in corpus]
    grid = [p for p in json.loads((exp / "data" / "corpus" / "ab_grid.json").read_text())["points"]
            if p.get("decisions")]
    grid_m = np.array([p["decisions"] for p in grid])
    grid_n = [f"ab{p['base']}({p['a']},{p['b']})" for p in grid]
    novel = {c["anon_id"]: c for c in json.loads((exp / "results" / "v3_final.json").read_text())["novel"]}
    logger.info(f"Loaded {len(states)} probe states, {len(corpus)} corpus and {len(grid)} ab-grid vectors")

    bf = [family_excess(lambda item, bins: -(bins - item), sets[k]) for k in HELDOUT]
    logger.info(f"Best fit held-out excess {bf[0]:.3f}% / {bf[1]:.3f}% (report: 3.98 / 5.37)")
    if abs(bf[0] - 3.98) > 0.01 or abs(bf[1] - 5.37) > 0.01:
        raise RuntimeError("harness reproduction failed for best fit")

    out = {"heldout_sets": HELDOUT, "best_fit_excess_pct": bf, "bars_pct": [3.19, 4.29], "programs": {}}
    for cid, edits in ABLATIONS.items():
        c = novel[cid]
        src, rows = c["code"], []
        variants = [("full", src)]
        for k, (old, new) in enumerate(edits, start=1):
            if old not in src:
                raise RuntimeError(f"{cid}: ablation line not found: {old}")
            src = src.replace(old, new)
            variants.append((f"minus_{k}", src))
        full_dv = None
        for name, s in variants:
            prio = compile_priority(s)
            exc = [family_excess(prio, sets[k]) for k in HELDOUT]
            dv = np.array([decide(prio, it, a) for it, a in states])
            full_dv = dv if full_dv is None else full_dv
            ca, cn = max_agreement(dv, corp_m, corp_n)
            ga, gn = max_agreement(dv, grid_m, grid_n)
            rows.append({"variant": name, "removed": [e[0] for e in edits[: len(rows)]],
                         "excess_pct": exc, "passes_both_bars": exc[0] < 3.19 and exc[1] < 4.29,
                         "max_corpus_agreement": ca, "nearest_corpus": cn,
                         "max_abgrid_agreement": ga, "nearest_abgrid": gn,
                         "agreement_with_full": float(np.mean((dv == full_dv) & (dv != ERR)))})
            logger.info(f"{cid} {name}: excess {exc[0]:.3f}/{exc[1]:.3f}, corpus {ca:.4f} ({cn}), grid {ga:.4f}")
        full = rows[0]
        if abs(full["excess_pct"][0] - c["exc_FSW5k"]) > 1e-6 or abs(full["excess_pct"][1] - c["exc_OR3"]) > 1e-6:
            raise RuntimeError(f"{cid}: full program does not reproduce the reported held-out excess")
        if abs(full["max_corpus_agreement"] - c["max_corpus_agreement"]) > 1e-9:
            raise RuntimeError(f"{cid}: full program does not reproduce the reported corpus agreement")
        out["programs"][cid] = {"arm": c["arm"], "seed": c["seed"], "pid": c["pid"], "rows": rows}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2))
    logger.info(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
