#!/usr/bin/env python3
"""S4 corpus: published online-bin-packing heuristics adapted to priority(item, bins), the ab family of
Herrmann & Pallez (arXiv 2510.27353) with a coarse tuned grid, their decision vectors on the committed probes, and
the agreement matrix. Also the batch runner used by the instrument gate and the evaluator."""
from __future__ import annotations

import ast
import inspect
import json
import re
import time
from concurrent.futures import Future
from typing import Any

import numpy as np
from loguru import logger

import bp
import instr
import refs
import sandbox
from common import DATA, ROOT, RESULTS, read_json, sha256_file, sha256_text, write_json

EXT = ROOT / "ext"
AB_A = [0, 1, 2, 3, 5, 8, 12, 16, 20]
AB_B = list(range(0, 61, 5))
AB_BASES = ["FF", "WF", "BF"]
BASE_ORDER = {"FF": 0, "BF": 1, "WF": 2}
PUBLISHED_AB = [("FF", 5, 24), ("WF", 1, 21)]


# ---------------------------------------------------------------------------------------------- batch runner
def probe_batch(pool: sandbox.EvalPool, codes: dict[str, str], probe: str = "P10", seeds=(0, 1),
                force_seeds: list[int] | None = None, sets: list[str] | None = None,
                limits: dict[str, float] | None = None, priority: int = 3,
                extend_stochastic: bool = True) -> dict[str, dict[str, Any]]:
    """Probe every code string under harness seeds (0, 1); programs whose two vectors differ on >= 1% of states are
    STOCHASTIC and are also probed under seeds 2 and 3. `force_seeds` probes those seeds for every program."""
    first = list(force_seeds) if force_seeds else list(seeds)
    futs: dict[str, Future] = {}
    for name, code in codes.items():
        futs[name] = pool.submit({"code": code, "sets": sets or [], "limits": limits or {}, "probes": [probe],
                                  "probe_seeds": first, "probe_even_if_failed": True}, priority=priority)
    out: dict[str, dict[str, Any]] = {}
    for name, f in futs.items():
        r = f.result()
        vecs = {int(k.split("@")[1]): sandbox.decode(v) for k, v in r.get("probes", {}).items()}
        out[name] = {"vecs": vecs, "error_type": r["error_type"], "msg": r.get("msg", ""), "bins": r.get("bins", {}),
                     "probe_error": r.get("probe_error", {}), "set_s": r.get("set_s", {}),
                     "probe_s": r.get("probe_s", {})}
    if extend_stochastic and not force_seeds:
        ext = {n: c for n, c in codes.items() if instr.is_stochastic(out[n]["vecs"])}
        if ext:
            futs2 = {n: pool.submit({"code": c, "sets": [], "probes": [probe], "probe_seeds": [2, 3],
                                     "probe_even_if_failed": True}, priority=priority) for n, c in ext.items()}
            for n, f in futs2.items():
                r = f.result()
                for k, v in r.get("probes", {}).items():
                    out[n]["vecs"][int(k.split("@")[1])] = sandbox.decode(v)
    for n in out:
        out[n]["stochastic"] = instr.is_stochastic(out[n]["vecs"])
        v0 = out[n]["vecs"].get(0)
        out[n]["err_share"] = float(np.mean(v0 == instr.ERR)) if v0 is not None else 1.0
    return out


# ---------------------------------------------------------------------------------------------- adapters
def rename_to_priority(src: str, old: str) -> str:
    return re.sub(rf"def\s+{re.escape(old)}\s*\(", "def priority(", src, count=1)


def strip_imports(src: str, mods: set[str]) -> tuple[str, list[str]]:
    keep, dropped = [], []
    for ln in src.splitlines():
        m = re.match(r"\s*(?:import|from)\s+([A-Za-z_][\w.]*)", ln)
        if m and m.group(1).split(".")[0] in mods:
            dropped.append(ln.strip())
            continue
        keep.append(ln)
    return "\n".join(keep) + "\n", dropped


def ab_name(base: str, a: int, b: int) -> str:
    return f"ab-{base}({a},{b})"


def published_members() -> list[dict[str, Any]]:
    """Every corpus member except the ab grid: name, source, url/commit, adapter note, code."""
    srcs = {r["local"]: r for r in read_json(ROOT / "inputs" / "bp9" / "ext_sources.json")}
    M: list[dict[str, Any]] = []

    def add(name: str, code: str, local: str | None, note: str, family: str, **kw: Any) -> None:
        meta = srcs.get(local, {}) if local else {}
        M.append({"name": name, "family": family, "code": code, "local": local, "url": meta.get("url"),
                  "commit": meta.get("commit"), "file_sha256": sha256_file(ROOT / local) if local else None,
                  "adapter_note": note, "code_sha256": sha256_text(code), **kw})

    for r in refs.DETERMINISTIC:
        add(f"textbook:{r}", refs.SRC[r], None, "textbook rule in the priority interface (refs.py)", "textbook")
    _, _, or_src, w_src = bp.funsearch_notebook()
    nb = "ext/funsearch/bin_packing.ipynb"
    add("funsearch:c12", or_src, nb, "notebook cell 8 source verbatim (FunSearch OR heuristic)", "funsearch")
    add("funsearch:c14", w_src, nb, "notebook cell 9 source verbatim (FunSearch Weibull heuristic)", "funsearch")
    vec = inspect.getsource(bp.prio_c12_vec)
    add("funsearch:c12_vec", rename_to_priority(vec, "prio_c12_vec"), None,
        "vectorised exact equivalent of c12 (bp.prio_c12_vec), renamed to priority", "funsearch")
    for run in (1, 2, 3):
        loc = f"ext/eoh/docs__Results__Prob1_OnlineBinPacking__run{run}__population_generation_20.json"
        pop = json.loads((ROOT / loc).read_text())
        best = min(range(len(pop)), key=lambda i: (pop[i]["objective"], i))
        for i, p in enumerate(pop):
            code = rename_to_priority(p["code"], "score")
            add(f"eoh:run{run}:{i}", code, loc, "EoH population_generation_20 program; function 'score' renamed "
                "to 'priority'", "eoh", objective=p["objective"], best_of_run=(i == best),
                algorithm=p["algorithm"][:400])
    loc = "ext/reevo/prompts__bpp_online__seed_func.txt"
    add("reevo:seed_func", rename_to_priority((ROOT / loc).read_text(), "priority_v1"), loc,
        "ReEvo seed function; 'priority_v1' renamed to 'priority' (it is FunSearch c14)", "reevo")
    loc = "ext/hsevo/problems__bpp_online__gpt.py"
    code, dropped = strip_imports((ROOT / loc).read_text(), {"random", "scipy", "torch"})
    add("hsevo:gpt", rename_to_priority(code, "priority_v2"), loc,
        f"HSEvo problems/bpp_online/gpt.py; dropped unused imports {dropped}; 'priority_v2' renamed", "hsevo")
    loc = "ext/hsevo/baselines__reevo__prompts__bpp_online__seed_func.txt"
    add("hsevo:reevo_seed", rename_to_priority((ROOT / loc).read_text(), "priority_v1"), loc,
        "HSEvo's ReEvo-baseline seed function; 'priority_v1' renamed", "hsevo")
    loc = "ext/mctsahd/problems__bpp_online__gpt.py"
    add("mctsahd:gpt", (ROOT / loc).read_text(), loc, "MCTS-AHD problems/bpp_online/gpt.py verbatim (returns a "
        "list; the harness applies np.asarray)", "mctsahd")
    loc = "ext/llm4ad/llm4ad__task__optimization__online_bin_packing__template.py"
    tree = ast.parse((ROOT / loc).read_text())
    tmpl = next(n.value.value for n in tree.body if isinstance(n, ast.Assign) and
                getattr(n.targets[0], "id", "") == "template_program")
    add("llm4ad:template", tmpl, loc, "LLM4AD template_program string (return item - bins)", "llm4ad")
    loc = "ext/llm4ad/example__tasks__online_bin_packing__online_bin_packing_tutorial.ipynb"
    nbj = json.loads((ROOT / loc).read_text())
    tut = None
    for c in nbj["cells"]:
        s = "".join(c["source"])
        if "template_program = '''" in s:
            tut = s.split("'''")[1]
            break
    if tut:
        add("llm4ad:tutorial_template", tut, loc, "LLM4AD tutorial template/test program (return bins - item); the "
            "tutorial prints no best heuristic", "llm4ad")
    for base, a, b in PUBLISHED_AB:
        add(f"published:{ab_name(base, a, b)}", bp.ab_source(a, b, base), "ext/arxiv_2510.27353/text.txt",
            f"ab-{base} with the published (a, b) = ({a}, {b}) of arXiv 2510.27353 Fig. 9 (bp.ab_source)", "ab")
    return M


def ab_grid() -> list[dict[str, Any]]:
    out = []
    for base in AB_BASES:
        for a in AB_A:
            for b in AB_B:
                code = bp.ab_source(a, b, base)
                out.append({"name": f"grid:{ab_name(base, a, b)}", "family": "ab", "base": base, "a": a, "b": b,
                            "code": code, "code_sha256": sha256_text(code),
                            "adapter_note": "coarse ab grid member (bp.ab_source)"})
    return out


# ---------------------------------------------------------------------------------------------- build
def build(pool: sandbox.EvalPool, hg: dict[str, Any]) -> dict[str, Any]:
    t0 = time.time()
    fit = bp.Fitness(bp.load_set("SEL-OR"), bp.load_set("SEL-W"), hg["sel_bf"]["or_excess"],
                     hg["sel_bf"]["w_excess"])
    members = published_members()
    grid = ab_grid()
    # ab grid: selection fitness F and decision vectors in one task per member
    logger.info(f"corpus: {len(members)} published members, {len(grid)} ab grid members")
    lim = {"SEL-OR": 30.0, "SEL-W": 150.0}
    gres = probe_batch(pool, {g["name"]: g["code"] for g in grid}, sets=["SEL-OR", "SEL-W"], limits=lim)
    for g in grid:
        r = gres[g["name"]]
        g["error_type"] = r["error_type"]
        if r["error_type"] == "ok":
            b25 = r["bins"]["SEL-OR"] + r["bins"]["SEL-W"]
            g["F"] = fit.F(b25)
            g["F_parts"] = list(fit.parts(b25))
        else:
            g["F"] = None
    ok = [g for g in grid if g.get("F") is not None]
    tuned = min(ok, key=lambda g: (round(g["F"], 12), g["a"], g["b"], BASE_ORDER[g["base"]]))
    logger.info(f"tuned ab member: {tuned['name']} F={tuned['F']:.4f} ({len(ok)}/{len(grid)} grid members ok)")
    pres = probe_batch(pool, {m["name"]: m["code"] for m in members}, sets=["SEL-OR", "SEL-W"], limits=lim)
    for m in members:
        r = pres[m["name"]]
        m["error_type"] = r["error_type"]
        m["msg"] = r["msg"]
        if r["error_type"] == "ok":
            b25 = r["bins"]["SEL-OR"] + r["bins"]["SEL-W"]
            m["F"] = fit.F(b25)
            m["F_parts"] = list(fit.parts(b25))
    allm = members + grid
    vecs = {**{m["name"]: pres[m["name"]] for m in members}, **{g["name"]: gres[g["name"]] for g in grid}}
    for m in allm:
        v = vecs[m["name"]]
        m["stochastic"] = bool(v["stochastic"])
        m["probe_err_share"] = v["err_share"]
        m["tuned"] = m["name"] == tuned["name"]
    # store decision vectors (seed-keyed integer lists) separately
    dec = {m["name"]: {str(s): (vv.tolist() if vv is not None else None) for s, vv in vecs[m["name"]]["vecs"].items()}
           for m in allm}
    write_json(DATA / "corpus_decisions.json", dec, indent=None)
    corpus = {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "n_members": len(allm),
              "n_published": len(members), "n_ab_grid": len(grid), "tuned_ab": tuned["name"],
              "tuned_ab_F": tuned["F"], "ab_grid_spec": {"a": AB_A, "b": AB_B, "bases": AB_BASES,
                                                          "tie_rule": "smallest a, then smallest b, then FF, BF, WF"},
              "not_expressible": refs.NOT_EXPRESSIBLE,
              "members": [{k: v for k, v in m.items()} for m in allm],
              "decisions_file": "data/corpus_decisions.json",
              "decisions_sha256": sha256_file(DATA / "corpus_decisions.json"), "seconds": round(time.time() - t0, 1)}
    write_json(RESULTS / "corpus.json", corpus)
    return corpus


def load_vectors() -> dict[str, dict[int, np.ndarray]]:
    d = read_json(DATA / "corpus_decisions.json")
    return {n: {int(s): (np.array(v, dtype=np.uint16) if v is not None else None) for s, v in sv.items()}
            for n, sv in d.items()}


def agreement_matrix(names: list[str], vecs: dict[str, dict[int, np.ndarray]], stoch: dict[str, bool],
                     mask: np.ndarray | None = None) -> list[list[float]]:
    M = []
    for a in names:
        row = []
        for b in names:
            row.append(round(instr.A(vecs[a], vecs[b], stoch.get(b, False), mask), 4))
        M.append(row)
    return M
