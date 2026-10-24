#!/usr/bin/env python3
"""S10 held-out scoring. Every best program (seed-best and artifact-best per arm, chosen by selection F only) is scored
ONCE on every held-out set under the validity rule (120 s per set): H-FSW5k and H-OR3 (primary), then H-W5k, H-W10k,
H-SHIFT, H-OR1, H-OR2, H-OR4. BF is scored in-process on the same sets; per-instance paired bins vs BF are reported.
V3 candidates are scored once on the two primary sets; those passing the 0.8 rule on both get the other six sets and
the corpus-novelty filter (max agreement < 0.9 with every priority-form corpus entry, incl. all 3,843 ab members).

Usage: python src/heldout.py best | candidates"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import bp  # noqa: E402
import clusters as CL  # noqa: E402
import common as C  # noqa: E402
import corpus as CO  # noqa: E402
import sandbox  # noqa: E402

HELDOUT = CO.HELDOUT
PRIMARY = CO.PRIMARY
N_WORKERS = 11
BF_EXC = {"H-FSW5k": 0.039843042559613666, "H-OR3": 0.05367793240556666}


def bf_reference() -> dict:
    p = C.RESULTS / "heldout_bf.json"
    if p.exists():
        return json.loads(p.read_text())
    out = {}
    for s in HELDOUT:
        insts = bp.load_set(s)
        b = [bp.pack(x["items"], x["capacity"], bp.prio_bf) for x in insts]
        out[s] = {"bins": b, "excess": CO.excess(s, b), "l1": [x["l1"] for x in insts]}
    assert abs(out["H-FSW5k"]["excess"] - BF_EXC["H-FSW5k"]) < 1e-12 and abs(out["H-OR3"]["excess"] - BF_EXC["H-OR3"]) < 1e-12
    C.write_json(p, out)
    return out


def score(pool, programs: dict[str, str], sets: list[str]) -> dict[str, dict]:
    """programs: id -> code. One strict task per (program, set); per-set 120 s."""
    futs = {(pid, s): pool.submit(sandbox.heldout_task(code, [s])) for pid, code in programs.items() for s in sets}
    out: dict[str, dict] = {pid: {"bins": {}, "errors": {}} for pid in programs}
    for (pid, s), f in futs.items():
        r = f.result()
        if r["error_type"] == "ok":
            out[pid]["bins"][s] = r["bins"][s]
        else:
            out[pid]["errors"][s] = f"{r['error_type']}: {r.get('msg', '')[:150]}"
    return out


def summarise(rec: dict, bf: dict) -> dict:
    exc, rel, paired = {}, {}, {}
    for s, b in rec["bins"].items():
        exc[s] = CO.excess(s, b)
        rel[s] = exc[s] / bf[s]["excess"] if bf[s]["excess"] else None
        d = np.array(b) - np.array(bf[s]["bins"])
        paired[s] = {"wins": int((d < 0).sum()), "ties": int((d == 0).sum()), "losses": int((d > 0).sum()),
                     "mean_bin_diff": float(d.mean())}
    return {"excess": exc, "excess_over_bf": rel, "paired_vs_bf": paired, "errors": rec["errors"], "bins": rec["bins"]}


def stage_best() -> None:
    best = json.loads((C.RESULTS / "best_programs.json").read_text())
    bf = bf_reference()
    progs = {}
    for k, r in best["seed_best"].items():
        progs[k] = r["code"]
    pool = sandbox.EvalPool(N_WORKERS, C.ROOT)
    try:
        res = score(pool, progs, HELDOUT)
    finally:
        pool.close()
    out = {"bf": {s: bf[s]["excess"] for s in HELDOUT}, "seed_best": {}, "artifact_best": {}}
    for k, r in best["seed_best"].items():
        out["seed_best"][k] = dict(summarise(res[k], bf), F=r["F"], call=r["call"], seed=r["seed"], arm=r["arm"],
                                   code=r["code"])
    for arm, r in best["artifact_best"].items():
        k = f"S{r['seed']}-{arm}"
        out["artifact_best"][arm] = dict(out["seed_best"][k], from_seed=r["seed"])
    # comparison rows: tuned ab member (matched to C*), published ab members, c12 (vec), c14, corpus, stateful
    abh = json.loads((C.RESULTS / "corpus_ab_heldout.json").read_text())
    tuned = json.loads((C.RESULTS / "tuned_ab.json").read_text())["tuned"]
    cstar = str(json.loads((C.RESULTS / "search_config.json").read_text())["C_star"])
    tname = tuned[cstar]["name"]
    comp = {f"tuned_ab@C*={cstar} ({tname})": {"F": abh[tname]["F"], "excess": abh[tname]["heldout_excess"]}}
    for nm in ("ab-FF(5,24)", "ab-WF(1,21)"):
        comp[f"{nm} published"] = {"F": abh[nm]["F"], "excess": abh[nm]["heldout_excess"]}
    corpus = json.loads((C.RESULTS / "corpus.json").read_text())["entries"]
    for e in corpus:
        comp[e["name"]] = {"F": e["F"], "excess": e["heldout_excess"], "family": e["family"],
                           "flag_nonfinite": e["flag_nonfinite"]}
    st = json.loads((C.RESULTS / "corpus_stateful.json").read_text())
    for nm, d in st.items():
        if nm.startswith("_"):
            continue
        comp[f"{nm} (stateful)"] = {"F": d["F"], "excess": d["heldout_excess"]}
    out["comparison"] = comp
    out["tuned_ab_name"] = tname
    C.write_json(C.RESULTS / "heldout_best.json", out)
    for arm, r in out["artifact_best"].items():
        logger.info(f"{arm}: F={r['F']:.4f} FSW5k={100 * r['excess'].get('H-FSW5k', float('nan')):.3f}% "
                    f"OR3={100 * r['excess'].get('H-OR3', float('nan')):.3f}% errors={r['errors']}")


def corpus_vectors() -> tuple[np.ndarray, list[str]]:
    d = json.loads((C.RESULTS / "corpus.json").read_text())
    dec = np.load(C.DATA / "corpus_decisions.npy")
    keep = [i for i, e in enumerate(d["entries"]) if e["priority_form"] and e.get("p10_sha256")]
    names = [d["entries"][i]["name"] for i in keep]
    ab = np.load(C.DATA / "ab_decisions.npy")
    grid = CO.ab_grid()
    return np.concatenate([dec[keep], ab]), names + [CO.ab_name(*g) for g in grid]


def stage_candidates() -> None:
    cands = json.loads((C.RESULTS / "v3_candidates.json").read_text())
    bf = bf_reference()
    for i, c in enumerate(cands):
        c["cid"] = f"cand{i:03d}"
    pool = sandbox.EvalPool(N_WORKERS, C.ROOT)
    try:
        r1 = score(pool, {c["cid"]: c["code"] for c in cands}, PRIMARY)
        lim = {s: 0.8 * BF_EXC[s] for s in PRIMARY}
        passing = []
        for c in cands:
            rec = r1[c["cid"]]
            c["primary_errors"] = rec["errors"]
            c["excess"] = {s: CO.excess(s, b) for s, b in rec["bins"].items()}
            c["pass_08"] = all(s in c["excess"] and c["excess"][s] <= lim[s] for s in PRIMARY)
            if c["pass_08"]:
                passing.append(c)
        rest = [s for s in HELDOUT if s not in PRIMARY]
        r2 = score(pool, {c["cid"]: c["code"] for c in passing}, rest) if passing else {}
    finally:
        pool.close()
    for c in passing:
        rec = r2[c["cid"]]
        c["excess"].update({s: CO.excess(s, b) for s, b in rec["bins"].items()})
        c["other_errors"] = rec["errors"]
    # novelty filter against every priority-form corpus entry (incl. the full ab grid)
    dec = np.fromfile(C.DATA / "decisions.bin", dtype=np.uint16).reshape(-1, 2000)
    cv, cnames = corpus_vectors()
    inf = np.array([len(s[1]) >= 1 for s in json.loads((C.DATA / "probes" / "P10.json").read_text())["states"]])
    V = np.stack([dec[c["probe_row"]] for c in cands])
    A = CL.agreement_matrix(V, cv)
    Ai = CL.agreement_matrix(V, cv, inf)
    for i, c in enumerate(cands):
        order = np.argsort(-A[i])[:3]
        c["max_corpus_agreement"] = float(A[i].max())
        c["nearest_corpus"] = [{"name": cnames[j], "agreement": float(A[i, j]),
                                "agreement_informative": float(Ai[i, j])} for j in order]
        ab_part = A[i, len(cnames) - CO.N_AB:]
        jab = int(np.argmax(ab_part))
        c["nearest_ab"] = {"name": cnames[len(cnames) - CO.N_AB + jab], "agreement": float(ab_part[jab])}
        c["max_corpus_agreement_informative"] = float(Ai[i].max())
        c["pass_novelty_filter"] = bool(c["pass_08"] and c["max_corpus_agreement"] < 0.9)
    # joint clustering of the candidates (for reporting novel-and-better clusters per arm)
    lab = CL.complete_linkage(V, 0.95)
    for c, l in zip(cands, lab):
        c["joint_cluster"] = int(l)
    C.write_json(C.RESULTS / "v3_filtered.json", cands)
    n08 = sum(c["pass_08"] for c in cands)
    nnov = sum(c["pass_novelty_filter"] for c in cands)
    logger.info(f"V3: {len(cands)} candidates, {n08} pass the 0.8 rule, {nnov} pass both filters")


def stage_novelty() -> None:
    """Recompute the novelty filter of the scored candidates against the CURRENT corpus (after S3b/S3c additions)."""
    cands = json.loads((C.RESULTS / "v3_filtered.json").read_text())
    dec = np.fromfile(C.DATA / "decisions.bin", dtype=np.uint16).reshape(-1, 2000)
    cv, cnames = corpus_vectors()
    inf = np.array([len(s[1]) >= 1 for s in json.loads((C.DATA / "probes" / "P10.json").read_text())["states"]])
    V = np.stack([dec[c["probe_row"]] for c in cands])
    A = CL.agreement_matrix(V, cv)
    Ai = CL.agreement_matrix(V, cv, inf)
    for i, c in enumerate(cands):
        order = np.argsort(-A[i])[:3]
        c["max_corpus_agreement"] = float(A[i].max())
        c["nearest_corpus"] = [{"name": cnames[j], "agreement": float(A[i, j]),
                                "agreement_informative": float(Ai[i, j])} for j in order]
        c["max_corpus_agreement_informative"] = float(Ai[i].max())
        c["pass_novelty_filter"] = bool(c["pass_08"] and c["max_corpus_agreement"] < 0.9)
    C.write_json(C.RESULTS / "v3_filtered.json", cands)
    logger.info(f"novelty refreshed against {len(cnames)} priority-form corpus vectors: "
                f"{sum(c['pass_novelty_filter'] for c in cands)} pass both filters")


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("heldout")
    {"best": stage_best, "candidates": stage_candidates, "novelty": stage_novelty}[sys.argv[1]]()


if __name__ == "__main__":
    main()
