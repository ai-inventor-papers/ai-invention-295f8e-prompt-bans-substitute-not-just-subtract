#!/usr/bin/env python3
"""F1 GPU driver: prefix resampling on base paths, change points, token-level localisation, S = 20 confirmation,
fork definitions -> predictions/commit1_forks.json (commit #1, before any margin).

usage: python src/forkrun.py [--paths N] [--tasks T2,T10,T03] [--define]
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
import torch  # noqa: E402
from loguru import logger  # noqa: E402

import c7 as common  # noqa: E402
from c7 import (DEFAULTS, FORK_ROWS, PRED, RESULTS, append_jsonl, commit, read_jsonl, setup_logging, stable_seed,  # noqa: E402
                utc_now, write_json)
import engine7 as E  # noqa: E402
import fork7 as F  # noqa: E402
import gen7 as G  # noqa: E402
import prompts7 as PR  # noqa: E402

POS = list(range(0, 64, 4))
EXT = list(range(64, 129, 8))          # pre-declared window extension (every 8th token, 2 paths per class)
EXTENDED: set[str] = set()
S_SCREEN, S_CONF = 8, 20
MAXC = 512
B_FORK = 40


def path_prompt(task: str, p: dict[str, Any]) -> dict[str, Any]:
    return PR.ban(task, p["template"]) if p["cell"] == "BAN" else PR.twin(task, p["template"])


def path_edits(ctx: G.Ctx, task: str, p: dict[str, Any]) -> dict | None:
    """PN paths: exp29 per-sample plan noise (pn_direction(task, arm, w, k), push_spec alpha 2, ban unit)."""
    if p["cell"] != "PN":
        return None
    from ctx4 import ban_unit, push_spec
    from hooks4 import make_edits_v4
    w, k, arm = p["template"], int(p["sample_id"]), p["arm"]
    seed = stable_seed(task, arm, w, k)
    x = np.random.Generator(np.random.PCG64(seed)).standard_normal(4096)
    u = (x / np.linalg.norm(x)).astype(np.float32)
    sp = push_spec(ctx.dev, u, ban_unit(task), 2.0)
    tw = ctx.twin(w)
    return make_edits_v4("TARGET", tw["a"], tw["b"], sp["U"], sp["M"], {l: tw["S"][l] for l in sp["U"]})


def done_rows() -> set[str]:
    return {f"{r['path_id']}|{r['t']}|{r['i']}" for r in read_jsonl(FORK_ROWS)}


def run_entries(model: Any, tok: Any, ctx: G.Ctx, task: str, entries: list[tuple[dict, int, int]], stage: str
                ) -> None:
    """entries: (path, t, S). Rows of equal total length are batched (<= B_FORK rows)."""
    from engine4 import u_stream
    done = done_rows()
    todo = []
    for p, t, S in entries:
        ii = [i for i in range(S) if f"{p['path_id']}|{t}|{i}" not in done]
        if ii:
            todo.append((p, t, ii))
    by_len: dict[int, list] = defaultdict(list)
    for p, t, ii in todo:
        by_len[len(path_prompt(task, p)["ids"]) + t].append((p, t, ii))
    for L, items in sorted(by_len.items()):
        batch, rows_n = [], 0
        for it in items + [None]:
            if it is not None and rows_n + len(it[2]) <= B_FORK:
                batch.append(it)
                rows_n += len(it[2])
                continue
            if batch:
                _run_batch(model, tok, ctx, task, batch, stage, u_stream)
            if it is not None:
                batch, rows_n = [it], len(it[2])
            else:
                batch = []


def _run_batch(model, tok, ctx, task, batch, stage, u_stream) -> None:
    t0 = time.time()
    groups, meta = [], []
    for p, t, ii in batch:
        pr = path_prompt(task, p)
        ids = pr["ids"] + p["ids"][:t]
        pre = E.prefill(model, ids, edits=path_edits(ctx, task, p))
        groups.append({"pre": pre, "us": [u_stream(task, "fork", p["path_id"], t, i, n=MAXC) for i in ii]})
        meta += [(p, t, i) for i in ii]
    prefix_ids = [p["ids"][:t] for p, t, _ in meta]

    def stop(r: int, new: list[int]) -> bool:
        text = tok.decode(prefix_ids[r] + new, skip_special_tokens=True)
        return F.partial_label(task, text) is not None or F.fence_closed(task, text)

    res = E.sample_stop(model, tok, groups, stop, MAXC)
    out = []
    for (p, t, i), r in zip(meta, res):
        text = tok.decode(p["ids"][:t] + r["token_ids"], skip_special_tokens=True)
        lab, how = F.opening_label(task, text)
        out.append({"task": task, "path_id": p["path_id"], "class": p["class"], "cell": p["cell"],
                    "template": p["template"], "t": t, "i": i, "stage": stage,
                    "crn_key": f"{task}|fork|{p['path_id']}|{t}|{i}", "first_tok": r["token_ids"][0]
                    if r["token_ids"] else None, "cont_ids": r["token_ids"][:64], "n_new": r["n_tokens"],
                    "label": lab, "how": how, "finish": r["finish_reason"], "utc": utc_now()})
    append_jsonl(FORK_ROWS, out)
    dt = time.time() - t0
    append_jsonl(RESULTS / "timing.jsonl", [{"stage": f"fork_{stage}", "task": task, "rows": len(out),
                                             "seconds": dt, "steps": res[0]["steps"], "utc": utc_now()}])
    logger.info(f"fork {stage} {task}: {len(batch)} entries / {len(out)} rows in {dt:.1f}s ({res[0]['steps']} steps)")


def series(task: str, p: dict[str, Any], rows: list[dict[str, Any]], positions: list[int]) -> dict[str, Any]:
    """Outcome series k_t / n_t of a base path; positions >= t_dec are determined by the prefix (k = 0)."""
    by_t = defaultdict(list)
    for r in rows:
        by_t[r["t"]].append(r)
    ks, ns, src = [], [], []
    for t in positions:
        if p["t_dec"] is not None and t >= p["t_dec"]:
            ks.append(0)
            ns.append(S_SCREEN)
            src.append("prefix")
            continue
        rr = [r for r in by_t.get(t, []) if r["label"] not in (None, "unknown", "invalid")]
        ks.append(sum(r["label"] != p["class"] for r in rr))
        ns.append(len(rr))
        src.append("sampled")
    return {"t": positions, "k": ks, "n": ns, "src": src}


def screen_positions(p: dict[str, Any]) -> list[int]:
    pos = POS + (EXT if p["path_id"] in EXTENDED else [])
    return [t for t in pos if t < len(p["ids"]) - 1]


def stage_screen(model, tok, task: str, paths: list[dict[str, Any]]) -> None:
    ctx = G.Ctx(model, task, PR.p4())
    entries = []
    for p in paths:
        for t in screen_positions(p):
            if p["t_dec"] is None or t < p["t_dec"]:
                entries.append((p, t, S_SCREEN))
    run_entries(model, tok, ctx, task, entries, "screen")
    ctx.release()


def analyse_paths(task: str, paths: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [r for r in read_jsonl(FORK_ROWS) if r["task"] == task]
    by_path = defaultdict(list)
    for r in rows:
        by_path[r["path_id"]].append(r)
    out = {}
    for p in paths:
        pos = screen_positions(p)
        s = series(task, p, [r for r in by_path[p["path_id"]] if r["t"] in pos], pos)
        cp = F.series_cp(s["k"], s["n"], n_perm=1000, seed=stable_seed(p["path_id"]) % (2 ** 31))
        out[p["path_id"]] = {"series": s, "cp": cp, "class": p["class"], "cell": p["cell"], "t_dec": p["t_dec"]}
    return out


def localise(model, tok, task: str, paths: list[dict[str, Any]], an: dict[str, Any]) -> dict[str, int]:
    """For each significant change between screen positions t1 < t2, sample t1+1..t2-1 (S = 8); f = position before
    the largest one-token drop of the outcome rate over [t1, t2]."""
    ctx = G.Ctx(model, task, PR.p4())
    entries, brackets = [], {}
    for p in paths:
        a = an[p["path_id"]]
        if a["cp"]["p_value"] >= 0.01 or not a["cp"]["cps"]:
            continue
        s = a["series"]
        rates = [k / n if n else np.nan for k, n in zip(s["k"], s["n"])]
        best = None
        for i in a["cp"]["cps"]:
            drop = (rates[i - 1] - rates[i]) if not (np.isnan(rates[i - 1]) or np.isnan(rates[i])) else -1
            if best is None or drop > best[0]:
                best = (drop, i)
        i = best[1]
        t1, t2 = s["t"][i - 1], s["t"][i]
        brackets[p["path_id"]] = (t1, t2)
        for t in range(t1 + 1, t2):
            if p["t_dec"] is None or t < p["t_dec"]:
                entries.append((p, t, S_SCREEN))
    run_entries(model, tok, ctx, task, entries, "local")
    rows = [r for r in read_jsonl(FORK_ROWS) if r["task"] == task]
    forks = {}
    for p in paths:
        if p["path_id"] not in brackets:
            continue
        t1, t2 = brackets[p["path_id"]]
        tt = list(range(t1, t2 + 1))
        s = series(task, p, [r for r in rows if r["path_id"] == p["path_id"] and r["t"] in tt], tt)
        rates = [k / n if n else np.nan for k, n in zip(s["k"], s["n"])]
        drops = [(rates[j] - rates[j + 1], tt[j]) for j in range(len(tt) - 1)
                 if not (np.isnan(rates[j]) or np.isnan(rates[j + 1]))]
        if drops:
            forks[p["path_id"]] = max(drops)[1]
    ctx.release()
    return forks


def confirm(model, tok, task: str, paths: list[dict[str, Any]], fork_pos: list[int], per_path: dict[str, int],
            opening: list[int]) -> None:
    """S = 20 at every fork f_j for all paths sharing the canonical opening up to f_j; f-1 and controls f+-8 for the
    paths whose own fork was localised."""
    ctx = G.Ctx(model, task, PR.p4())
    entries = []
    for p in paths:
        for f in fork_pos:
            if p["ids"][:f] == opening[:f] and len(p["ids"]) > f:
                entries.append((p, f, S_CONF))
        f = per_path.get(p["path_id"])
        if f is not None:
            for t in (f - 1, f - 8, f + 8):
                if 0 <= t < len(p["ids"]) - 1 and (p["t_dec"] is None or t < p["t_dec"]):
                    entries.append((p, t, S_CONF))
    run_entries(model, tok, ctx, task, entries, "confirm")
    ctx.release()


def define(task: str, tok: Any, paths: list[dict[str, Any]], an: dict[str, Any], per_path: dict[str, int]
           ) -> dict[str, Any]:
    """F1.5: canonical default opening o_t; fork set F_t = localised forks of non-default paths whose prefix up to the
    fork equals o_t (the fork lies ON the default path; forks inside non-default space are reported, not used);
    forks within 2 tokens are merged to the earliest; token maps q_j; conditional label entropy."""
    default = DEFAULTS[task]
    twins = [p for p in F.labelled_programs(task) if p["arm"] == "TWIN" and p["label"] == default]
    o_full, _ = F.canonical_opening([p["ids"] for p in twins], 130)
    for L_ in range(129, 0, -1):     # longest modal prefix shared by >= 50% of default twin programs
        pref, share = F.canonical_opening([p["ids"] for p in twins], L_)
        if share >= 0.5:
            o_full = pref
            break
    along, off = defaultdict(list), defaultdict(list)
    for p in paths:
        f = per_path.get(p["path_id"])
        if f is None or p["class"] == default:
            continue
        on = p["ids"][:f] == o_full[:f] and f < len(o_full)
        (along if on else off)[p["class"]].append(f)
    cands = sorted({f for v in along.values() for f in v})
    fset = cands[:3]          # distinct change positions along the default path (no merging; at most 3 forks)
    out: dict[str, Any] = {"task": task, "forks": fset, "forks_along_default_by_class": dict(along),
                           "forks_off_default_by_class": dict(off), "n_paths": len(paths),
                           "n_paths_sig": sum(1 for p in paths if an[p["path_id"]]["cp"]["p_value"] < 0.01),
                           "opening_len_majority": len(o_full)}
    if not fset:
        out["status"] = "no single fork"
        return out
    opening = o_full
    out["opening_ids"] = opening
    out["opening_text"] = tok.decode(opening[:max(fset) + 1])
    out["opening_share_twin"] = F.canonical_opening([p["ids"] for p in twins], max(fset) + 1)[1]
    out["opening_share_paths"] = float(np.mean([p["ids"][:max(fset)] == opening[:max(fset)] for p in paths]))
    rows = [r for r in read_jsonl(FORK_ROWS) if r["task"] == task]
    path_by_id = {p["path_id"]: p for p in paths}
    maps, ent = {}, {}
    out["default_token_at_fork"] = {}
    for f in fset:
        tokc: dict[int, list[int]] = defaultdict(list)
        labc: dict[int, Counter] = defaultdict(Counter)
        for r in rows:
            p = path_by_id.get(r["path_id"])
            if p is None or r["t"] != f or p["ids"][:f] != opening[:f]:
                continue
            if r["label"] in (None, "unknown", "invalid") or r["first_tok"] is None:
                continue
            tokc[r["first_tok"]].append(int(r["label"] != default))
            labc[r["first_tok"]][r["label"]] += 1
        q = {}
        for tk, v in tokc.items():
            q[str(tk)] = {"q": float(np.mean(v)), "n": len(v), "tok": tok.decode([tk]),
                          "mapped": len(v) >= 3, "labels": dict(labc[tk])}
        maps[f] = q
        n_all = sum(len(v) for v in tokc.values())
        h_lab = F.entropy_bits(Counter(l for c in labc.values() for l in c.elements()))
        h_cond = sum(sum(labc[tk].values()) / n_all * F.entropy_bits(labc[tk]) for tk in labc) if n_all else None
        ent[f] = {"H_label_bits": h_lab, "H_label_given_token_bits": h_cond, "n": n_all}
        out["default_token_at_fork"][str(f)] = {"id": opening[f], "tok": tok.decode([opening[f]])}
    out["token_maps"] = {str(k): v for k, v in maps.items()}
    out["entropy"] = {str(k): v for k, v in ent.items()}
    out["status"] = "fork found"
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", type=int, default=6)
    ap.add_argument("--tasks", default="T2,T10,T03")
    ap.add_argument("--define", action="store_true")
    args = ap.parse_args()
    setup_logging("forkrun")
    tasks = args.tasks.split(",")
    tok, model = E.load()
    allp = {}
    for task in tasks:
        paths = F.select_base_paths(task, tok, n_per_class=args.paths)
        allp[task] = paths
        logger.info(f"{task}: {len(paths)} base paths: {Counter((p['class'], p['cell']) for p in paths)}; "
                    f"t_dec {[p['t_dec'] for p in paths]}")
        t0 = time.time()
        stage_screen(model, tok, task, paths)
        logger.info(f"{task}: screen done in {time.time() - t0:.0f}s")
    if not args.define:
        return
    res = {}
    for task in tasks:
        paths = allp[task]
        an = analyse_paths(task, paths)
        if not any(a["cp"]["p_value"] < 0.01 for a in an.values()):
            # pre-declared fallback: extend the window to 128 tokens (every 8th token, 2 paths per class)
            by_c = defaultdict(list)
            for p in paths:
                by_c[p["class"]].append(p)
            for c, ps in by_c.items():
                for p in ps[:2]:
                    EXTENDED.add(p["path_id"])
            logger.info(f"{task}: no change point in 64 tokens -> window extension on {len(EXTENDED)} paths")
            stage_screen(model, tok, task, paths)
            an = analyse_paths(task, paths)
        per_path = localise(model, tok, task, paths, an)
        d0 = define(task, tok, paths, an, per_path)
        if d0.get("forks"):
            confirm(model, tok, task, paths, d0["forks"], per_path, d0["opening_ids"])
        an = analyse_paths(task, paths)
        d = define(task, tok, paths, an, per_path)
        if not d.get("forks"):
            d["fallback"] = "48-token opening LLR is this task's margin (pre-declared); 'no single fork'"
        d["window_extended"] = sorted(p for p in EXTENDED if p.startswith(task + ":"))
        d["per_path"] = {pid: {"class": a["class"], "cell": a["cell"], "t_dec": a["t_dec"], "series": a["series"],
                               "cp": a["cp"], "fork": per_path.get(pid)} for pid, a in an.items()}
        d["base_paths"] = [{k: p[k] for k in ("path_id", "class", "cell", "template", "sample_id", "src", "arm",
                                                "t_dec")} for p in paths]
        res[task] = d
        logger.info(f"{task}: forks {d.get('forks')} along {d.get('forks_along_default_by_class')} off "
                    f"{d.get('forks_off_default_by_class')} status {d.get('status')}")
    first = PRED / "commit1_forks.json"
    name = ("commit1c_forks" if (PRED / "commit1b_forks.json").exists() else "commit1b_forks") if first.exists() \
        else "commit1_forks"
    obj = {"name": name, "utc": utc_now(), "screen_positions": POS, "extension_positions": EXT, "S_screen": S_SCREEN,
           "S_confirm": S_CONF, "max_continuation": MAXC, "tasks": res,
           "amends": {"commit1b_forks": "commit1_forks (written before the pre-declared 128-token extension was run "
                                        "and with a fork-set rule that merged non-default-internal forks)",
                      "commit1c_forks": "commit1b_forks: its 2-token merge of adjacent forks hid T10's second fork "
                                        "(' def' -> ' find' vs ' dfs'); forks are now distinct change positions along "
                                        "the default path, and the multi-fork margin sets q_j(default-path token) = 0 "
                                        "at every fork but the last (staying on the default path is scored by the "
                                        "later forks; no double counting). Written before any margin or predictor."
                      }.get(name),
           "multi_fork_margin_rule": "e_j = sum_tok p(tok) q_j(tok) / sum_mapped p(tok) with q_j(o_t[f_j]) := 0 for "
                                     "j < J; P_esc = 1 - prod_j (1 - e_j)"}
    p = PRED / f"{name}.json"
    write_json(p, obj)
    write_json(RESULTS / "forks.json", obj)
    logger.info(f"{name} -> {commit(name, p)}")


if __name__ == "__main__":
    main()
