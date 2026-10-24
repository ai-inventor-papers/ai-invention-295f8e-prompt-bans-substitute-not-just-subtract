#!/usr/bin/env python3
"""S3: the known corpus. Priority-form heuristics (textbook, FunSearch c12/c14, EoH runs 1-3, HSEvo, MCTS-AHD, ReEvo,
LLM4AD, the FULL 3,843-member ab grid of arXiv 2510.27353, dependency-scan and dated-search additions), stateful
baselines (next fit, harmonic-k), the tuned ab member (random search over a fixed permutation of the grid), selection F
and held-out scores, P10 decision vectors and the corpus agreement matrix.

Usage: python src/corpus.py build        (scores everything; resumable per stage via results/corpus_*.json)
       python src/corpus.py add <json>    (score and append extra priority-form entries, e.g. S3b/S3c additions)"""
from __future__ import annotations

import json
import multiprocessing as mp
import re
import sys
import textwrap
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

import bp  # noqa: E402
import common as C  # noqa: E402

HELDOUT = ["H-FSW5k", "H-OR3", "H-W5k", "H-W10k", "H-SHIFT", "H-OR1", "H-OR2", "H-OR4"]
PRIMARY = ["H-FSW5k", "H-OR3"]
SEL = ["SEL-OR", "SEL-W"]
AB_BASES = ["FF", "BF", "WF"]
AB_A = list(range(0, 21))
AB_B = list(range(0, 61))
N_AB = len(AB_BASES) * len(AB_A) * len(AB_B)  # 3,843
TUNE_SEED = 20261024
TUNE_EVALS = 2000
CORPUS_JSON = C.RESULTS / "corpus.json"
DEC_NPY = C.DATA / "corpus_decisions.npy"
AB_DEC_NPY = C.DATA / "ab_decisions.npy"
EXT_SRC = C.ROOT / "inputs" / "bp9_ext_sources.json"


def ab_grid() -> list[tuple[str, int, int]]:
    """Enumeration order (base FF, BF, WF) x (a 0..20) x (b 0..60)."""
    return [(base, a, b) for base in AB_BASES for a in AB_A for b in AB_B]


def ab_name(base: str, a: int, b: int) -> str:
    return f"ab-{base}({a},{b})"


def fitness() -> bp.Fitness:
    g = json.loads((C.RESULTS / "harness_gate.json").read_text())
    return bp.Fitness(bp.load_set("SEL-OR"), bp.load_set("SEL-W"), g["sel_bf"]["or_excess"], g["sel_bf"]["w_excess"])


def l1s(name: str) -> list[int]:
    return [x["l1"] for x in bp.load_set(name)]


def excess(name: str, bins: list[int]) -> float:
    return bp.family_excess(bins, l1s(name))


# ------------------------------------------------------------------------------------------- source adapters
def _prov() -> dict:
    out = {}
    for e in json.loads(EXT_SRC.read_text()):
        if e.get("status") == "ok":
            out[e["local"]] = e
    return out


def _entry(name, family, code, src_local, note, url=None, commit=None, utc=None, src_sha=None, priority_form=True):
    return dict(name=name, family=family, code=code, source_local=src_local, source_url=url, commit=commit,
                access_utc=utc, source_sha256=src_sha, program_sha256=C.sha256_text(code), adapter_note=note,
                priority_form=priority_form)


def _strip_imports(code: str) -> str:
    keep = []
    for ln in code.splitlines():
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            mods = s.replace("import", " ").replace("from", " ").replace(",", " ").split()
            if not any(m.split(".")[0] in ("numpy", "np", "math", "as") for m in mods[:1]):
                continue
        keep.append(ln)
    return "\n".join(keep) + "\n"


def priority_form_entries() -> list[dict]:
    pv = _prov()
    E: list[dict] = []
    E.append(_entry("FF", "textbook", bp.SRC_FF, None, "first fit, priority form (bp.SRC_FF)"))
    E.append(_entry("BF", "textbook", bp.SRC_BF, None, "best fit, priority form (bp.SRC_BF)"))
    E.append(_entry("WF", "textbook", bp.SRC_WF, None, "worst fit among opened bins, priority form"))
    E.append(_entry("AWF", "textbook", bp.SRC_AWF, None, "almost-worst fit, priority form (S1)"))
    nbk = "ext/funsearch/bin_packing__bin_packing.ipynb"
    nb = pv[nbk]
    _, _, or_src, w_src = bp.funsearch_notebook()
    E.append(_entry("FunSearch-c12", "funsearch", or_src, nbk, "notebook cell 8 (text before '# Test performance')",
                    nb["url"], nb["commit"], nb["utc"], nb["sha256"]))
    E.append(_entry("FunSearch-c14", "funsearch", w_src, nbk, "notebook cell 9 (text before '# Test performance')",
                    nb["url"], nb["commit"], nb["utc"], nb["sha256"]))
    import probes
    E.append(_entry("FunSearch-c12-vec", "funsearch", probes.SRC_C12VEC, nbk,
                    "vectorised exact equivalent of c12 (bins equal per instance on OR3, gate check); held-out proxy for c12",
                    nb["url"], nb["commit"], nb["utc"], nb["sha256"]))
    for r in (1, 2, 3):
        k = f"ext/eoh/docs__Results__Prob1_OnlineBinPacking__run{r}__population_generation_20.json"
        meta = pv[k]
        pop = json.loads((C.ROOT / k).read_text())
        for i, p in enumerate(pop):
            raw = p["code"]
            fixed = re.sub(r"^[ \t]+(def\s+score\s*\()", r"\1", raw, flags=re.M)  # mangled indent (run3-03)
            code = re.sub(r"def\s+score\s*\(", "def priority(", fixed)
            note = "'code' field; def score -> def priority" + ("; def line dedented" if fixed != raw else "")
            e = _entry(f"EoH-run{r}-{i:02d}", "eoh", code, k, note,
                       meta["url"], meta["commit"], meta["utc"], meta["sha256"])
            e["eoh_objective"] = p.get("objective")
            e["eoh_algorithm"] = (p.get("algorithm") or "")[:400]
            E.append(e)
    for key, fam, nm, note in [
        ("ext/hsevo/problems__bpp_online__gpt.py", "hsevo", "HSEvo-gpt",
         "imports other than numpy/math removed; priority_v2 -> priority"),
        ("ext/hsevo/baselines__reevo__prompts__bpp_online__seed_func.txt", "hsevo", "HSEvo-reevo-seed",
         "priority_v1 -> priority"),
        ("ext/mctsahd/problems__bpp_online__gpt.py", "mctsahd", "MCTS-AHD-gpt", "as published (returns a list)"),
        ("ext/reevo/prompts__bpp_online__seed_func.txt", "reevo", "ReEvo-seed", "priority_v1 -> priority"),
    ]:
        meta = pv[key]
        code = _strip_imports((C.ROOT / key).read_text())
        code = re.sub(r"def\s+priority_v\d\s*\(", "def priority(", code)
        E.append(_entry(nm, fam, code, key, note, meta["url"], meta["commit"], meta["utc"], meta["sha256"]))
    k = "ext/llm4ad/llm4ad__task__optimization__online_bin_packing__template.py"
    meta = pv[k]
    txt = (C.ROOT / k).read_text()
    code = txt.split("'''")[1].strip() + "\n"
    E.append(_entry("LLM4AD-template", "llm4ad", code, k, "template_program string (item - bins)",
                    meta["url"], meta["commit"], meta["utc"], meta["sha256"]))
    k = "ext/llm4ad/example__tasks__online_bin_packing__online_bin_packing_tutorial.ipynb"
    meta = pv[k]
    nbt = json.loads((C.ROOT / k).read_text())
    seen = set()
    for ci, cell in enumerate(nbt["cells"]):
        s = "".join(cell["source"])
        for m in re.finditer(r"'''\s*\n(import numpy as np\s*\n\s*def priority.*?)'''", s, flags=re.S):
            body = m.group(1)
            if "while True" in body or body in seen:
                continue  # the tutorial's deliberately invalid infinite-loop example is not a heuristic
            seen.add(body)
            E.append(_entry(f"LLM4AD-tutorial-cell{ci}", "llm4ad", body.strip() + "\n", k,
                            "priority program string in the tutorial notebook (parsed as data)",
                            meta["url"], meta["commit"], meta["utc"], meta["sha256"]))
    pa = C.ROOT / "ext" / "arxiv_2510.27353" / "2510.27353.html"
    for base, a, b in [("FF", 5, 24), ("WF", 1, 21)]:
        E.append(_entry(f"{ab_name(base, a, b)}-published", "ab_published", bp.ab_source(a, b, base),
                        "ext/arxiv_2510.27353/2510.27353.html",
                        f"published member (text.txt: 'Minimum for a = {a} and b = {b}'); bp.ab_source",
                        "https://arxiv.org/html/2510.27353", None, "2026-10-23T09:39:18Z", C.sha256_file(pa)))
    extra = C.RESULTS / "corpus_additions.json"
    if extra.exists():
        for e in json.loads(extra.read_text()):
            E.append(_entry(e["name"], e["family"], e["code"], e.get("source_local"), e.get("adapter_note", ""),
                            e.get("source_url"), e.get("commit"), e.get("access_utc"), e.get("source_sha256")))
    return E


# ------------------------------------------------------------------------------------------- in-process scoring
def _ab_probe_worker(chunk: list[tuple[str, int, int]]) -> np.ndarray:
    import warnings
    warnings.simplefilter("ignore")
    np.seterr(all="ignore")
    sys.path.insert(0, str(C.SRC))
    import probes
    states = json.loads(probes.P10_PATH.read_text())["states"]
    out = np.zeros((len(chunk), len(states)), dtype=np.uint16)
    for i, (base, a, b) in enumerate(chunk):
        out[i] = probes.local_decisions(bp.make_ab(a, b, base), states)
    return out


def _ab_sel_worker(chunk: list[tuple[int, str, int, int]]) -> list[tuple[int, list[int]]]:
    import warnings
    warnings.simplefilter("ignore")
    np.seterr(all="ignore")
    insts = bp.load_set("SEL-OR") + bp.load_set("SEL-W")
    res = []
    for idx, base, a, b in chunk:
        fn = bp.make_ab(a, b, base)
        res.append((idx, [bp.pack(x["items"], x["capacity"], fn) for x in insts]))
    return res


def _stateful_worker(spec: tuple[str, int | None, str]) -> tuple[str, int | None, str, list[int]]:
    name, k, set_name = spec
    insts = bp.load_set(set_name)
    if name == "NF":
        return name, k, set_name, [bp.next_fit(x["items"], x["capacity"]) for x in insts]
    return name, k, set_name, [bp.harmonic_k(x["items"], x["capacity"], k) for x in insts]


def n_workers() -> int:
    import os
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        n = max(1, int(q / p))
    except (FileNotFoundError, ValueError):
        n = len(os.sched_getaffinity(0))
    return n


def score_ab_grid(nw: int) -> None:
    grid = ab_grid()
    if not AB_DEC_NPY.exists():
        chunks = [grid[i:i + 40] for i in range(0, len(grid), 40)]
        with ProcessPoolExecutor(max_workers=nw, mp_context=mp.get_context("spawn")) as ex:
            parts = list(ex.map(_ab_probe_worker, chunks))
        np.save(AB_DEC_NPY, np.concatenate(parts, axis=0))
        logger.info(f"ab grid: {len(grid)} P10 decision vectors saved")
    tp = C.RESULTS / "tuned_ab.json"
    if not tp.exists():
        perm = np.random.default_rng(TUNE_SEED).permutation(N_AB)
        F = fitness()
        todo = [(int(i), *grid[int(i)]) for i in perm[:TUNE_EVALS]]
        chunks = [todo[i:i + 25] for i in range(0, len(todo), 25)]
        bins = {}
        with ProcessPoolExecutor(max_workers=nw, mp_context=mp.get_context("spawn")) as ex:
            for part in ex.map(_ab_sel_worker, chunks):
                for idx, b25 in part:
                    bins[idx] = b25
        order = [int(i) for i in perm[:TUNE_EVALS]]
        Fs = [F.F(bins[i]) for i in order]
        tuned = {}
        for Cb in (1000, 1500, 2000):
            j = int(np.argmin(Fs[:Cb]))  # ties: earliest in the permutation
            base, a, b = grid[order[j]]
            tuned[str(Cb)] = dict(grid_index=order[j], perm_rank=j, base=base, a=a, b=b, name=ab_name(base, a, b),
                                  F=Fs[j])
        C.write_json(tp, {"seed": TUNE_SEED, "perm_sha256": C.sha256_text(json.dumps(perm.tolist())),
                          "perm_first_20": perm[:20].tolist(), "n_evaluated": TUNE_EVALS, "tuned": tuned,
                          "evaluated": [dict(grid_index=i, F=f, bins=bins[i]) for i, f in zip(order, Fs)]})
        logger.info(f"tuned ab members: { {k: (v['name'], round(v['F'], 4)) for k, v in tuned.items()} }")


def score_stateful(nw: int) -> dict:
    sp = C.RESULTS / "corpus_stateful.json"
    if sp.exists():
        return json.loads(sp.read_text())
    specs = [("NF", None, s) for s in SEL + HELDOUT] + [("HK", k, s) for k in range(3, 11) for s in SEL + HELDOUT]
    with ProcessPoolExecutor(max_workers=nw, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(_stateful_worker, specs))
    F = fitness()
    out: dict = {}
    for name, k, s, b in res:
        nm = "next_fit" if name == "NF" else f"harmonic_{k}"
        out.setdefault(nm, {"bins": {}})["bins"][s] = b
    for nm, d in out.items():
        d["F"] = F.F(d["bins"]["SEL-OR"] + d["bins"]["SEL-W"])
        d["heldout_excess"] = {s: excess(s, d["bins"][s]) for s in HELDOUT}
    hk = {nm: d["F"] for nm, d in out.items() if nm.startswith("harmonic_")}
    kstar = min(hk, key=lambda n: (hk[n], int(n.split("_")[1])))
    out["_k_star"] = kstar
    C.write_json(sp, out)
    logger.info(f"stateful baselines scored; harmonic k* = {kstar} (F={hk[kstar]:.4f}); NF F={out['next_fit']['F']:.4f}")
    return out


# ------------------------------------------------------------------------------------------- sandboxed scoring
def score_entries(entries: list[dict], nw: int, label: str) -> list[dict]:
    """FunSearch semantics (strict=False), one task per set (independent), per-set 120 s, plus the P10 pass."""
    import sandbox
    pool = sandbox.EvalPool(nw, C.ROOT)
    F = fitness()
    try:
        futs = {}
        for i, e in enumerate(entries):
            for s in SEL + HELDOUT:
                futs[(i, s)] = pool.submit({"code": e["code"], "sets": [s], "budget": "per_set", "limit": 120.0,
                                            "strict": False, "probes": []})
            futs[(i, "P10")] = pool.submit({"code": e["code"], "sets": [], "budget": "cumulative", "limit": 20.0,
                                            "strict": False, "probes": ["P10"], "probe_limit": 60.0})
        for i, e in enumerate(entries):
            e["bins"], e["set_errors"], nfc = {}, {}, 0
            for s in SEL + HELDOUT:
                r = futs[(i, s)].result()
                if r["error_type"] == "ok":
                    e["bins"][s] = r["bins"][s]
                    nfc += int(r.get("fs_nonfinite_calls") or 0)
                else:
                    e["set_errors"][s] = f"{r['error_type']}: {r.get('msg', '')[:120]}"
            e["nonfinite_calls_funsearch"] = nfc
            e["flag_nonfinite"] = nfc > 0
            rp = futs[(i, "P10")].result()
            dv = rp.get("probes", {}).get("P10")
            e["p10"] = np.frombuffer(dv, dtype=np.uint16).copy() if dv is not None else None
            e["probe_error"] = rp.get("probe_error") or (rp["error_type"] if rp["error_type"] != "ok" else None)
            if "SEL-OR" in e["bins"] and "SEL-W" in e["bins"]:
                b25 = e["bins"]["SEL-OR"] + e["bins"]["SEL-W"]
                e["F"] = F.F(b25)
                e["sel_parts"] = list(F.parts(b25))
            else:
                e["F"] = None
            e["heldout_excess"] = {s: excess(s, e["bins"][s]) for s in HELDOUT if s in e["bins"]}
        logger.info(f"{label}: scored {len(entries)} entries ({sum(e['F'] is not None for e in entries)} with F)")
    finally:
        pool.close()
    return entries


def save_corpus(entries: list[dict]) -> None:
    dec = np.stack([e["p10"] if e["p10"] is not None else np.full(2000, 65535, dtype=np.uint16) for e in entries])
    np.save(DEC_NPY, dec)
    rows = []
    for e in entries:
        r = {k: v for k, v in e.items() if k != "p10"}
        r["p10_sha256"] = C.sha256_bytes(e["p10"].tobytes()) if e["p10"] is not None else None
        rows.append(r)
    C.write_json(CORPUS_JSON, {"utc": C.utc(), "n_entries": len(rows), "entries": rows,
                               "decisions_file": DEC_NPY.relative_to(C.ROOT).as_posix(),
                               "ab_decisions_file": AB_DEC_NPY.relative_to(C.ROOT).as_posix(),
                               "ab_grid_order": "(base FF, BF, WF) x (a 0..20) x (b 0..60)"})


def corpus_hashes() -> dict:
    d = json.loads(CORPUS_JSON.read_text())
    return {"corpus_code_sha256": C.sha256_text(json.dumps([[e["name"], e["program_sha256"]] for e in d["entries"]])),
            "corpus_decisions_sha256": C.sha256_file(DEC_NPY), "ab_decisions_sha256": C.sha256_file(AB_DEC_NPY),
            "n_entries": d["n_entries"], "n_ab_grid": N_AB}


def heldout_tuned_and_published(nw: int) -> None:
    """Held-out scores of the tuned members (C in 1000/1500/2000) and the published members, in-process."""
    hp = C.RESULTS / "corpus_ab_heldout.json"
    if hp.exists():
        return
    t = json.loads((C.RESULTS / "tuned_ab.json").read_text())["tuned"]
    members = {v["name"]: (v["base"], v["a"], v["b"]) for v in t.values()}
    members |= {"ab-FF(5,24)": ("FF", 5, 24), "ab-WF(1,21)": ("WF", 1, 21)}
    specs = [(nm, base, a, b, s) for nm, (base, a, b) in members.items() for s in SEL + HELDOUT]
    with ProcessPoolExecutor(max_workers=nw, mp_context=mp.get_context("spawn")) as ex:
        res = list(ex.map(_ab_set_worker, specs))
    F = fitness()
    out: dict = {}
    for nm, s, b in res:
        out.setdefault(nm, {"bins": {}, "spec": members[nm]})["bins"][s] = b
    for nm, d in out.items():
        d["F"] = F.F(d["bins"]["SEL-OR"] + d["bins"]["SEL-W"])
        d["heldout_excess"] = {s: excess(s, d["bins"][s]) for s in HELDOUT}
    C.write_json(hp, out)
    logger.info("held-out scores of tuned/published ab members: " +
                ", ".join(f"{k}: F={v['F']:.4f} FSW5k={100 * v['heldout_excess']['H-FSW5k']:.2f}% "
                          f"OR3={100 * v['heldout_excess']['H-OR3']:.2f}%" for k, v in out.items()))


def _ab_set_worker(spec):
    import warnings
    warnings.simplefilter("ignore")
    np.seterr(all="ignore")
    nm, base, a, b, s = spec
    fn = bp.make_ab(a, b, base)
    return nm, s, [bp.pack(x["items"], x["capacity"], fn) for x in bp.load_set(s)]


def agreement_matrix() -> None:
    """Agreement among non-ab corpus entries, and max agreement of each with the ab grid (descriptive)."""
    sys.path.insert(0, str(C.SRC))
    import clusters
    d = json.loads(CORPUS_JSON.read_text())
    dec = np.load(DEC_NPY)
    ab = np.load(AB_DEC_NPY)
    A = clusters.agreement_matrix(dec, dec)
    Aab = clusters.agreement_matrix(dec, ab)
    names = [e["name"] for e in d["entries"]]
    grid = ab_grid()
    best_ab = [(ab_name(*grid[int(j)]), float(Aab[i, j])) for i, j in enumerate(np.argmax(Aab, axis=1))]
    idx = {n: i for i, n in enumerate(names)}
    calib = {"c14_vs_ab-WF(1,21)": float(A[idx["FunSearch-c14"], idx["ab-WF(1,21)-published"]]),
             "c12_vs_ab-FF(5,24)": float(A[idx["FunSearch-c12"], idx["ab-FF(5,24)-published"]])}
    C.write_json(C.RESULTS / "corpus_agreement.json", {"names": names, "agreement": np.round(A, 4).tolist(),
                                                       "nearest_ab": best_ab, "calibration_pairs": calib})
    logger.info(f"corpus agreement matrix {A.shape}; calibration pairs {calib}")


@logger.catch(reraise=True)
def main() -> None:
    C.setup_logging("corpus")
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    nw = max(2, n_workers() - 2)
    if cmd == "build":
        score_ab_grid(nw)
        heldout_tuned_and_published(nw)
        score_stateful(nw)
        if not CORPUS_JSON.exists():
            entries = priority_form_entries()
            logger.info(f"{len(entries)} priority-form entries (plus {N_AB} ab grid members)")
            entries = score_entries(entries, nw, "corpus")
            save_corpus(entries)
        agreement_matrix()
        C.write_json(C.RESULTS / "corpus_hashes.json", corpus_hashes())
        C.ledger("S3 corpus scored", planned_h=1.58)
    elif cmd == "add":
        new = json.loads(Path(sys.argv[2]).read_text())
        d = json.loads(CORPUS_JSON.read_text())
        old = d["entries"]
        dec = np.load(DEC_NPY)
        for e, v in zip(old, dec):
            e["p10"] = v
        have = {e["name"] for e in old}
        add = [_entry(e["name"], e["family"], e["code"], e.get("source_local"), e.get("adapter_note", ""),
                      e.get("source_url"), e.get("commit"), e.get("access_utc"), e.get("source_sha256"))
               for e in new if e["name"] not in have]
        if add:
            add = score_entries(add, nw, "corpus additions")
            save_corpus(old + add)
            agreement_matrix()
            C.write_json(C.RESULTS / "corpus_hashes.json", corpus_hashes())
        logger.info(f"added {len(add)} corpus entries")


if __name__ == "__main__":
    main()
