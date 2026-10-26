#!/usr/bin/env python3
"""STEPs 6-7: pilot + default rule + commit #1, and the ban-free stage (Phase A twin / escape stage 1 / plan noise /
T 1.3; Phase B confirmation top-up; Phase C novelty; Phase D 'can' + association; opening ladder).

Usage: python src/banfree.py {pilot|commit1|phaseA|phaseB|phaseC|phaseD|ladder} [--tasks T03,T2]
"""

from __future__ import annotations

import collections
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, ALPHAS, BENCH_TASKS, CAP_FLOOR, DATA_DIR, ESCAPE_SEEDS, MAX_NEW_ASSOC, MAX_NEW_BENCH,
                 MAX_NEW_PATH, MODEL_ID, MODEL_REVISION, N_PN_PER_T, N_STAGE1_PER_T, N_T13_PER_T, N_TWIN_PER_T,
                 PATH_TASKS, PRED_DIR, QWEN_DEFAULT, RESULTS_DIR, ROOT, STAGE2_SLOTS, T_HOT, TEMPLATE_IDS,
                 add_deviation, model_path, read_json, read_jsonl, setup_logging, write_json)
import prompts_gemma as PG

RAW_PILOT = DATA_DIR / "raw_pilot.jsonl"
RAW_A = DATA_DIR / "raw_phaseA.jsonl"
RAW_B = DATA_DIR / "raw_phaseB.jsonl"
RAW_C = DATA_DIR / "raw_novelty.jsonl"
RAW_CAN = DATA_DIR / "raw_can.jsonl"
ASSOC_RAW = DATA_DIR / "assoc_answers.jsonl"   # not raw_*: association answers are mapped, not program-labelled
LADDER = RESULTS_DIR / "opening_ladder.json"
C1 = PRED_DIR / "commit1.json"
TASK_ORDER_RUN = ("T03", "T2", "T05", "T06", "T04", "T1", "T10", "R1", "T08", "R3", "T13", "R6", "T14", "T11", "R2")


def labels_by_id() -> dict[str, dict[str, Any]]:
    return {r["row_id"]: r for r in read_jsonl(DATA_DIR / "labels.jsonl")}


def lab_of(r: dict[str, Any]) -> str:
    return r["label"]


# ------------------------------------------------------------------------------------------------ pilot (STEP 6)
def pilot_rows() -> list[dict[str, Any]]:
    rows = []
    for t in ALL_TASKS:
        X = QWEN_DEFAULT[t]
        for w in TEMPLATE_IDS:
            tw = PG.p_twin(t, X, w)
            for k in (0, 1):
                rows.append({"row_id": f"pilot|{t}|{w}|twin_pilot|{k}", "task": t, "arm": "twin_pilot", "prompt": tw,
                             "ukey": (t, "pilot", w, k), "temperature": 1.0, "mode": X, "template": w, "slot": k})
    return rows


def run_pilot(R: Any) -> None:
    rows = pilot_rows()
    done = R.done_ids(RAW_PILOT)
    rows = [r for r in rows if r["row_id"] not in done]
    bench = [r for r in rows if r["task"] not in PATH_TASKS]
    path = [r for r in rows if r["task"] in PATH_TASKS]
    for i in range(0, len(bench), 36):
        R.run_multi(bench[i:i + 36], MAX_NEW_BENCH, "pilot", RAW_PILOT, f"pilot:bench:{i // 36}")
    if path:
        R.run_multi(path, MAX_NEW_PATH, "pilot", RAW_PILOT, "pilot:path:0")


def weight_hashes() -> dict[str, Any]:
    """Local safetensors = HF blobs named by their sha256 (LFS); compared with the repo's LFS metadata."""
    snap = Path(model_path(MODEL_ID, MODEL_REVISION))
    meta = read_json(ROOT / "logs" / "gemma_repo_meta.json")
    out = {}
    for f in sorted(snap.glob("*.safetensors")):
        blob = os.path.realpath(f)
        local = Path(blob).name
        exp = meta["files"].get(f.name, {}).get("lfs_sha256")
        out[f.name] = {"blob_sha256": local, "repo_lfs_sha256": exp, "match": local == exp}
    return {"repo": MODEL_ID, "revision": MODEL_REVISION, "files": out, "all_match": all(v["match"] for v in out.values())}


def commit1() -> dict[str, Any]:
    """Pilot rule, default rule, cap rule, batch size; commit #1 (before any CRN batch)."""
    from commit import commit

    rows = read_jsonl(RAW_PILOT)
    labs = labels_by_id()
    per: dict[str, Any] = {}
    lens = {"bench": [], "path": []}
    for t in ALL_TASKS:
        rr = [r for r in rows if r["task"] == t]
        ll = [labs[r["row_id"]] for r in rr if r["row_id"] in labs]
        n = len(ll)
        passed = [l for l in ll if l.get("passed")]
        cnt_any = collections.Counter(l["label"] for l in passed if l["label"] not in ("invalid", "disputed"))
        cat = set(PG.modes(t))
        # a ban must name D with its catalogue display name: D_g is the modal correct CATALOGUE label (>= 3 correct)
        cnt = collections.Counter({m: c for m, c in cnt_any.items() if m in cat})
        X = QWEN_DEFAULT[t]
        modal_any = cnt_any.most_common(1)[0][0] if cnt_any else None
        if modal_any is not None and modal_any not in cat and (not cnt or max(cnt.values()) < 3):
            D_g, flag = X, f"offcatalogue_modal_default:{modal_any}"
        elif sum(cnt.values()) < 3 or not cnt:
            D_g, flag = X, "lt3_correct"
        else:
            top = max(cnt.values())
            tops = sorted(m for m, c in cnt.items() if c == top)
            D_g, flag = (X, "tie_to_Xq") if (len(tops) > 1 and X in tops) else (tops[0], None)
        per[t] = {"n": n, "pass_rate": len(passed) / max(n, 1), "correct_labels": dict(cnt_any), "D_g": D_g, "X_q": X,
                  "modal_correct_any": modal_any,
                  "flag": flag, "rebuild_twin": D_g != X,
                  "labels_all": dict(collections.Counter(l["label"] for l in ll))}
        lens["path" if t in PATH_TASKS else "bench"] += [r["n_new_tokens"] for r in rr]
    n_low = sum(1 for v in per.values() if v["pass_rate"] < 0.6)
    pilot_rule = {"n_tasks_pass_lt_0.6": n_low, "switch_to_fallback": n_low > 7,
                  "rule": "fallback model iff pass < 0.6 on > 7 of 15 tasks"}
    caps = {}
    for cls, default in (("bench", MAX_NEW_BENCH), ("path", MAX_NEW_PATH)):
        p99 = float(np.percentile(lens[cls], 99)) if lens[cls] else default
        caps[cls] = {"p99": p99, "cap": int(min(default, max(CAP_FLOOR, p99 + 64))), "default": default}
    twins = {}
    for t in ALL_TASKS:
        for w in TEMPLATE_IDS:
            tw = PG.p_twin(t, per[t]["D_g"], w)
            twins[f"{t}|{w}"] = {"noun": tw["noun"], "pad": tw["pad"], "P": tw["P"], "spec_start": tw["spec_start"],
                                 "spec_end": tw["spec_end"], "noun_source": tw["noun_source"],
                                 "prompt_sha256": tw["prompt_sha256"]}
    Bs = {}
    for t in ALL_TASKS:
        cap = caps["path" if t in PATH_TASKS else "bench"]["cap"]
        Pmax = max(twins[f"{t}|{w}"]["P"] for w in TEMPLATE_IDS)
        Bs[t] = 36 if Pmax + cap <= 1250 else 24
    rec = {"model": MODEL_ID, "revision": MODEL_REVISION, "weights": weight_hashes(), "precision": "bf16 sdpa",
           "pilot": per, "pilot_rule": pilot_rule, "caps": caps, "B": Bs, "twins": twins,
           "default_rule": "D_g = modal correct label in the pilot (ties -> X_q; < 3 correct -> X_q, flagged); if "
                           "D_g != X_q the task's twin is rebuilt for ban_len(D_g); after the twin N=50, D = its modal "
                           "correct label (used for all analyses and the ban if it differs; logged)",
           "unit": "outlier-excluded ban-free unit (src/units.py; deviation D3)",
           "qwen_ratio_sha256": __import__("cfg").sha256_file(RESULTS_DIR / "qwen_ratio.json")}
    write_json(C1, rec)
    write_json(RESULTS_DIR / "pilot.json", {"per_task": per, "pilot_rule": pilot_rule, "caps": caps})
    c = commit("commit1_model_pilot_default", [C1, RESULTS_DIR / "qwen_ratio.json", ROOT / "src" / "units.py"])
    logger.info(f"commit #1: {c['hash'][:12]}; caps {caps}; B {Bs}; low-pass tasks {n_low}; "
                f"D_g {({t: v['D_g'] for t, v in per.items()})}")
    return rec


def c1() -> dict[str, Any]:
    return read_json(C1)


def D_of(t: str) -> str:
    return c1()["pilot"][t]["D_g"]


def cap_of(t: str) -> int:
    return c1()["caps"]["path" if t in PATH_TASKS else "bench"]["cap"]


def B_of(t: str) -> int:
    return int(c1()["B"][t])


# ------------------------------------------------------------------------------------------------ Phase A
def phaseA_rows(t: str, w: str) -> list[dict[str, Any]]:
    rows = [{"arm": "twin", "slot": k, "alpha": 0.0, "dir_kind": None} for k in range(N_TWIN_PER_T)]
    for s in ESCAPE_SEEDS:
        for a in ALPHAS:
            for k in range(N_STAGE1_PER_T):
                rows.append({"arm": f"esc{s}_a{int(a)}", "slot": k, "alpha": a, "dir_kind": "escape",
                             "direction_seed": s})
    rows += [{"arm": "pn_a1", "slot": k, "alpha": 1.0, "dir_kind": "PN", "direction_seed": "PN"}
             for k in range(N_PN_PER_T)]
    rows += [{"arm": "t13", "slot": k, "alpha": 0.0, "dir_kind": None, "temperature": T_HOT}
             for k in range(N_T13_PER_T)]
    rows += [{"arm": "pn_a2", "slot": k, "alpha": 2.0, "dir_kind": "PN", "direction_seed": "PN"}
             for k in range(N_PN_PER_T)]
    return rows


def pack(rows: list[dict[str, Any]], B: int, pad_fn) -> list[list[dict[str, Any]]]:
    out = [rows[i:i + B] for i in range(0, len(rows), B)]
    if out and len(out[-1]) < B:
        need = B - len(out[-1])
        out[-1] = out[-1] + pad_fn(need)
    return out


def twin_pad(n: int, start: int = 10) -> list[dict[str, Any]]:
    return [{"arm": "twin_pad", "slot": start + i, "alpha": 0.0, "dir_kind": None, "pad": True} for i in range(n)]


def run_phaseA(R: Any, tasks: list[str]) -> None:
    done = R.done_ids(RAW_A)
    t_start = time.time()
    for ti, t in enumerate(tasks):
        D = D_of(t)
        B, cap = B_of(t), cap_of(t)
        for w in TEMPLATE_IDS:
            batches = pack(phaseA_rows(t, w), B, twin_pad)
            for bi, rows in enumerate(batches):
                ids = {f"A|{t}|{w}|{r['arm']}|{r['slot']}" for r in rows}
                if ids <= done:
                    continue
                R.run_crn(t, D, w, rows, B, cap, "A", RAW_A, f"A:{t}:{w}:b{bi}")
        el = time.time() - t_start
        logger.info(f"Phase A {t} done; {ti + 1}/{len(tasks)} tasks in {el / 60:.1f} min; "
                    f"extrapolated remaining {el / (ti + 1) * (len(tasks) - ti - 1) / 60:.1f} min")


# ------------------------------------------------------------------------------------------------ Phase B
def run_phaseB(R: Any, tasks: list[str]) -> None:
    import predictors as PR

    done = R.done_ids(RAW_B)
    for t in tasks:
        st1 = PR.stage1(t)
        passing = [(int(s), float(a)) for s, a in st1["passing"]]
        if not passing:
            logger.info(f"Phase B {t}: no direction-alpha passes stage 1")
            continue
        D, B, cap = D_of(t), B_of(t), cap_of(t)
        for w in TEMPLATE_IDS:
            rows = [{"arm": f"esc{s}_a{int(a)}", "slot": k, "alpha": a, "dir_kind": "escape", "direction_seed": s}
                    for (s, a) in passing for k in STAGE2_SLOTS]

            def pn_pad(n: int) -> list[dict[str, Any]]:
                return [{"arm": "pn_a1_pad", "slot": 10 + i, "alpha": 1.0, "dir_kind": "PN", "direction_seed": "PN",
                         "pad": True} for i in range(n)]
            for bi, rr in enumerate(pack(rows, B, pn_pad)):
                ids = {f"B|{t}|{w}|{r['arm']}|{r['slot']}" for r in rr}
                if ids <= done:
                    continue
                R.run_crn(t, D, w, rr, B, cap, "B", RAW_B, f"B:{t}:{w}:b{bi}")
        logger.info(f"Phase B {t}: {len(passing)} passing direction-alphas topped up")


# ------------------------------------------------------------------------------------------------ Phase C / D
def run_novelty(R: Any, tasks: list[str], n: int = 50) -> None:
    done = R.done_ids(RAW_C)
    for t in tasks:
        p = PG.p_novelty(t)
        rows = [{"row_id": f"C|{t}|novelty|{k}", "task": t, "arm": "novelty", "prompt": p, "ukey": (t, "novelty", k),
                 "temperature": 1.0, "slot": k, "mode": None} for k in range(n)]
        rows = [r for r in rows if r["row_id"] not in done]
        half = (len(rows) + 1) // 2
        for bi, rr in enumerate([rows[:half], rows[half:]]):
            if rr:
                R.run_multi(rr, cap_of(t), "C", RAW_C, f"C:{t}:b{bi}")


def run_can(R: Any, tasks: list[str], per_mode: int = 10) -> None:
    done = R.done_ids(RAW_CAN)
    for t in tasks:
        D = D_of(t)
        rows = []
        for m in PG.modes(t):
            if m == D:
                continue
            for k in range(5):
                for att in range(per_mode // 5):
                    rows.append({"row_id": f"D|{t}|can:{m}|k{k}|{att}", "task": t, "arm": "can", "mode": m,
                                 "prompt": PG.p_forced(t, m, k), "ukey": (t, "can", m, k, att), "temperature": 1.0,
                                 "template": f"k{k}", "slot": att})
        rows = [r for r in rows if r["row_id"] not in done]
        for bi in range(0, len(rows), 36):
            R.run_multi(rows[bi:bi + 36], cap_of(t), "D", RAW_CAN, f"D:can:{t}:{bi // 36}")


def run_assoc(R: Any, tasks: list[str], n: int = 20) -> None:
    done = R.done_ids(ASSOC_RAW)
    rows = []
    for t in tasks:
        D = D_of(t)
        p = PG.p_assoc(t, D)
        rows += [{"row_id": f"D|{t}|assoc|{k}", "task": t, "arm": "association", "mode": D, "prompt": p,
                  "ukey": (t, "assoc", D, k), "temperature": 1.0, "slot": k} for k in range(n)]
    rows = [r for r in rows if r["row_id"] not in done]
    for bi in range(0, len(rows), 40):
        R.run_multi(rows[bi:bi + 40], MAX_NEW_ASSOC, "D", ASSOC_RAW, f"D:assoc:{bi // 40}", fence_stop=False)


def run_t16(R: Any, tasks: list[str], per_t: int = 5) -> None:
    """Optional T 1.6 cell (plan: N = 25 on this model's movable tasks, run only with >= 20 min of slack): twin
    prompts, slots 0-4 per template with the twin's uniforms; multi-prompt batches (uncoupled batch shape)."""
    raw = DATA_DIR / "raw_t16.jsonl"
    done = R.done_ids(raw)
    for t in tasks:
        D = D_of(t)
        rows = [{"row_id": f"T16|{t}|{w}|t16|{k}", "task": t, "arm": "t16", "prompt": PG.p_twin(t, D, w),
                 "ukey": (t, w, k), "temperature": 1.6, "template": w, "slot": k, "mode": D}
                for w in TEMPLATE_IDS for k in range(per_t)]
        rows = [r for r in rows if r["row_id"] not in done]
        if rows:
            R.run_multi(rows, cap_of(t), "T16", raw, f"T16:{t}")


# ------------------------------------------------------------------------------------------------ opening ladder
def openings(t: str) -> dict[str, list[str]]:
    """Mode -> candidate first body lines (comments/docstrings stripped) of correct adherent forced programs
    (bench forced_programs.jsonl; T1/T2: the exp8 suite references)."""
    import ast as _ast

    from cfg import BENCH, SUITE

    def first_body_line(code: str) -> str | None:
        try:
            tree = _ast.parse(code)
        except SyntaxError:
            return None
        fn = next((n for n in _ast.walk(tree) if isinstance(n, _ast.FunctionDef) and n.name == "solve"), None)
        if fn is None:
            return None
        body = [n for n in fn.body if not (isinstance(n, _ast.Expr) and isinstance(getattr(n, "value", None),
                                                                                   _ast.Constant)
                                           and isinstance(n.value.value, str))]
        if not body:
            return None
        lines = code.splitlines()
        ln = lines[body[0].lineno - 1]
        s = ln.split("#")[0].rstrip() if "#" in ln and "'" not in ln and '"' not in ln else ln.rstrip()
        return s.strip() or None
    out: dict[str, list[str]] = collections.defaultdict(list)
    if t in PATH_TASKS:
        sub = {"T1": "t1_grid", "T2": "t2_wsp"}[t]
        pref = {"T1": [("bfs", "bfs"), ("bibfs", "bibfs"), ("dfs", "dfs"), ("iddfs", "iddfs"), ("astar", "astar_gbfs"),
                       ("gbfs", "astar_gbfs"), ("dijkstra", "dijkstra")],
                "T2": [("bellman", "bf_spfa"), ("spfa", "bf_spfa"), ("bidijkstra", "bidijkstra"), ("dial", "dial"),
                       ("dijkstra", "dijkstra"), ("floyd", "floyd")]}[t]
        for f in sorted((SUITE / "tasks" / sub / "references").glob("*.py")):
            m = next((mode for p, mode in pref if f.stem.startswith(p)), None)
            fl = first_body_line(f.read_text()) if m else None
            if fl:
                out[m].append(fl)
    else:
        from bench.common.catalogue import TASKS

        for r in read_jsonl(BENCH / TASKS[t]["task_id"] / "forced_programs.jsonl"):
            if str(r.get("passed")) == "True" and r.get("label") == r.get("forced_mode") and r.get("code"):
                fl = first_body_line(r["code"])
                if fl:
                    out[r["forced_mode"]].append(fl)
    return dict(out)


def PR_Dg(t: str) -> str:
    return D_of(t)


def run_ladder(R: Any, tasks: list[str]) -> None:
    import re

    tok = R.tok
    labs = labels_by_id()
    res = read_json(LADDER) if LADDER.exists() else {}
    rawA = [r for r in read_jsonl(RAW_A) if r["arm"] == "twin"]
    import predictors as PRm

    for t in tasks:
        if t in res:
            continue
        D = PRm.D_final(t)["D"]
        ops = openings(t)
        O = {m: collections.Counter(v).most_common(1)[0][0] for m, v in ops.items() if v}
        # model's own opening for D (sensitivity): modal first body line of its correct D twin programs
        own = []
        for r in rawA:
            if r["task"] == t and labs.get(r["row_id"], {}).get("label") == D and labs[r["row_id"]].get("passed"):
                m = re.search(r"def solve\(.*?\):\n((?:[ \t]*\n)*)([ \t]+)(\S[^\n]*)", r["text"])
                if m:
                    own.append(m.group(3).split("#")[0].rstrip())
        own_D = collections.Counter(own).most_common(1)[0][0] if own else None
        ctxs = []
        for w in TEMPLATE_IDS:
            got = 0
            for r in sorted((x for x in rawA if x["task"] == t and x["template"] == w), key=lambda x: x["slot"]):
                m = re.search(r"```python\n(.*?def solve\([^\n]*\):\n)", r["text"], re.S)
                if not m:
                    continue
                body = r["text"][m.end():]
                ind = re.match(r"((?:[ \t]*\n)*)([ \t]*)", body)
                indent = ind.group(2) if ind and ind.group(2) else "    "
                tw = PG.p_twin(t, PR_Dg(t), w)
                rendered = PG.CHAT_HEAD + tw["text"] + PG.CHAT_TAIL
                ctxs.append((rendered + r["text"][:m.end()], indent))
                got += 1
                if got >= 2:
                    break
        if not ctxs or not O:
            res[t] = {"defined": False, "reason": "no contexts or no openings", "openings": O}
            continue
        toks_len = {m: len(tok(o, add_special_tokens=False)["input_ids"]) for m, o in O.items()}
        K = int(min(16, min(toks_len.values())))
        lp: dict[str, list[float]] = collections.defaultdict(list)
        lp_tok: dict[str, list[float]] = collections.defaultdict(list)
        variants = dict(O)
        if own_D:
            variants["__own_D__"] = own_D
        for ctx, indent in ctxs:
            for m, o in variants.items():
                full = ctx + indent + o
                enc = tok(full, add_special_tokens=False, return_offsets_mapping=True)
                ids = enc["input_ids"]
                tgt = [i for i, (a, b) in enumerate(enc["offset_mapping"]) if b > len(ctx)][:K]
                if not tgt:
                    continue
                v = R.tf(ids, tgt)
                lp[m].append(float(np.sum(v)))
                lp_tok[m].append(float(np.mean(v)))

        def lme(x: list[float]) -> float:
            x = np.array(x)
            return float(np.log(np.mean(np.exp(x - x.max()))) + x.max())
        logp = {m: lme(v) for m, v in lp.items() if v and m != "__own_D__"}
        surv = [m for m in logp if m != D]
        dist = {}
        if surv:
            z = np.array([logp[m] for m in surv])
            p = np.exp(z - z.max())
            p /= p.sum()
            dist = {m: float(x) for m, x in zip(surv, p)}
        margin = (logp[D] - max(logp[m] for m in surv)) if (D in logp and surv) else None
        margin_own = (lme(lp["__own_D__"]) - max(logp[m] for m in surv)) if (lp.get("__own_D__") and surv) else None
        tokmean = {m: float(np.mean(v)) for m, v in lp_tok.items() if v}
        res[t] = {"defined": bool(dist), "D": D, "K": K, "n_contexts": len(ctxs), "openings": O, "own_D": own_D,
                  "logp": logp, "distribution": dist, "top1": max(dist, key=dist.get) if dist else None,
                  "margin": margin, "margin_ownD_sensitivity": margin_own, "per_token_mean_logp": tokmean,
                  "missing_modes": [m for m in PG.modes(t) if m not in O]}
        write_json(LADDER, res)
        logger.info(f"ladder {t}: K={K} margin={margin} top1={res[t]['top1']}")
    write_json(LADDER, res)


# ------------------------------------------------------------------------------------------------ main
def main() -> None:
    cmd = sys.argv[1]
    tasks = list(TASK_ORDER_RUN)
    if "--tasks" in sys.argv:
        tasks = sys.argv[sys.argv.index("--tasks") + 1].split(",")
    setup_logging(f"banfree_{cmd}")
    if cmd == "commit1":
        commit1()
        return
    from runner import Runner

    R = Runner()
    if cmd == "pilot":
        run_pilot(R)
    elif cmd == "phaseA":
        run_phaseA(R, tasks)
    elif cmd == "phaseB":
        run_phaseB(R, tasks)
    elif cmd == "phaseC":
        run_novelty(R, tasks)
    elif cmd == "phaseD":
        run_assoc(R, tasks)
        run_can(R, tasks, per_mode=int(os.environ.get("CAN_PER_MODE", "10")))
    elif cmd == "ladder":
        run_ladder(R, tasks)
    elif cmd == "t16":
        run_t16(R, tasks)
    elif cmd == "all_after_A":
        run_phaseB(R, tasks)
        run_assoc(R, tasks)
        run_ladder(R, tasks)
        if os.environ.get("SKIP_NOVELTY") != "1":
            run_novelty(R, tasks)
        run_can(R, tasks, per_mode=int(os.environ.get("CAN_PER_MODE", "10")))
    logger.info(f"{cmd} finished")


if __name__ == "__main__":
    main()
