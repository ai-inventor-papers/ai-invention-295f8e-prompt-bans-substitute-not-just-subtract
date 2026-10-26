#!/usr/bin/env python3
"""Stage implementations for method.py (iteration 9, TP-B). Each `stage_<name>(*args)` is one sub-command."""

from __future__ import annotations

import gc
import re
from collections import Counter, defaultdict
import json
import math
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from loguru import logger

from common import (ADJ_PAIR, CAP_V9_USD, COMMIT_LOG, DATA, INPUTS, LOGS, MODELS_V9, PRED, RESULTS, ROOT, SRC_PATHS,
                    append_jsonl, commit, commit_time, deviation, read_json, read_jsonl, sha256_file, sha256_text,
                    timing, total_cost, utc_now, verify_chain, write_json, write_jsonl)

SRC = ROOT / "src"


# ---------------------------------------------------------------------------------------------- hardware + limits
def _detect_cpus() -> int:
    try:
        q = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_quota_us").read_text())
        p = int(Path("/sys/fs/cgroup/cpu/cpu.cfs_period_us").read_text())
        if q > 0:
            return math.ceil(q / p)
    except (FileNotFoundError, ValueError):
        pass
    try:
        parts = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if parts[0] != "max":
            return math.ceil(int(parts[0]) / int(parts[1]))
    except (FileNotFoundError, ValueError, IndexError):
        pass
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


def _container_ram_gb() -> float | None:
    for p in ["/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"]:
        try:
            v = Path(p).read_text().strip()
            if v != "max" and int(v) < 1_000_000_000_000:
                return int(v) / 1e9
        except (FileNotFoundError, ValueError):
            pass
    return None


NUM_CPUS = _detect_cpus()
RAM_GB = _container_ram_gb() or 16.0
N_WORKERS = max(1, min(6, NUM_CPUS))
# Parent processes stay well under the 28 GB container limit (children set their own 1 GB RLIMIT_AS).
_RAM_BUDGET = int(min(8.0, 0.3 * RAM_GB) * 1e9)
try:
    resource.setrlimit(resource.RLIMIT_AS, (_RAM_BUDGET * 3, _RAM_BUDGET * 3))
except (ValueError, OSError):
    pass


# ---------------------------------------------------------------------------------------------- stage 0
INPUT_COPIES: list[tuple[str, str, str]] = [
    # (source key, path relative to the source artifact, destination relative to inputs/)
    *[("iter8", f"src/{f}", f"iter8/src/{f}") for f in
      ("common.py", "prompts_tp.py", "sample_or.py", "label_tp.py", "judge_tp.py", "adjudicate.py", "novelty.py",
       "screen.py", "stages.py")],
    *[("iter8", f"data/labelled_{c}_{a}.jsonl", f"iter8/data/labelled_{c}_{a}.jsonl")
      for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8") for a in ("baseline", "ban")],
    ("iter8", "data/labelled_C6_confirm.jsonl", "iter8/data/labelled_C6_confirm.jsonl"),
    ("iter8", "data/manual_reads.jsonl", "iter8/data/manual_reads.jsonl"),
    ("iter8", "data/judge_cache.jsonl", "iter8/data/judge_cache.jsonl"),
    *[("iter8", f"results/{f}.json", f"iter8/results/{f}.json") for f in
      ("screen", "adjudication_ban", "carried_rows", "confirmation", "executor_review", "judge_gate",
       "novelty_audit", "selection", "labeller_validation", "renderer_checks", "landing", "geometry_M1")],
    ("iter8", "commitments.log", "iter8/commitments.log"),
    ("iter8", "README.md", "iter8/README.md"),
    # iteration 8's sha256-verified copies of the art_IVZc3TWCeE9f files (preferred, per the plan)
    ("iter8", "inputs/exp9/prompts/frozen_prompts.json", "exp9/prompts/frozen_prompts.json"),
    ("iter8", "inputs/exp9/tasks/t1_grid/spec.txt", "exp9/tasks/t1_grid/spec.txt"),
    ("iter8", "inputs/exp9/data/top5_labelled_rows.jsonl", "exp9/data/top5_labelled_rows.jsonl"),
    ("iter8", "inputs/exp9/labeller_ext/gold_set_v2.jsonl", "exp9/labeller_ext/gold_set_v2.jsonl"),
    ("iter8", "inputs/exp9/labeller_ext/gold_set_iter1.jsonl", "exp9/labeller_ext/gold_set_iter1.jsonl"),
    *[("iter8", f"inputs/exp9/tasks/t1_grid/references/{f}", f"exp9/tasks/t1_grid/references/{f}") for f in
      ("astar_fg.py", "bfs_deque_parent.py", "bfs_listpop_pathcarry.py", "biastar.py", "bibfs_deques.py",
       "bibfs_sets.py", "dfs_recursive.py", "dfs_stack.py", "dijkstra_counter.py", "dijkstra_lazy.py",
       "gbfs_counter.py", "idastar.py", "iddfs_iterative.py", "iddfs_recursive.py", "jps4.py")],
    ("iter8", "inputs/exp34/cache/known_corpus.jsonl", "exp34/cache/known_corpus.jsonl"),
    ("iter8", "inputs/dataset/corpus_rows.jsonl", "dataset/corpus_rows.jsonl"),
    ("iter8", "inputs/exp2/tasks/hidden_tests_t1.json", "exp2/tasks/hidden_tests_t1.json"),
    # art_IVZc3TWCeE9f itself: every T1 condition (C9 core, k-curve, baseline, forced gold pool)
    ("exp9", "data/samples.jsonl", "exp9/data/samples.jsonl"),
    ("exp9", "README.md", "exp9/README.md"),
    # art_zNyBP6zieI5u: gemma-3-4b-it TOP5 rows (C10)
    ("exp31", "data/labels.jsonl", "exp31/data/labels.jsonl"),
    ("exp31", "results/top5.json", "exp31/results/top5.json"),
    # art_D6Z0Snf09sFL: the ITER1 secondary suite at its source (sha256 must equal the iteration-8 copy)
    ("exp2", "tasks/hidden_tests_t1.json", "exp2_src/tasks/hidden_tests_t1.json"),
]


def _count_rows(p: Path) -> int | None:
    if p.suffix == ".jsonl":
        with p.open() as fh:
            return sum(1 for ln in fh if ln.strip())
    return None


def stage_stage0(*_: str) -> None:
    t0 = time.time()
    # 0.1 hardware record
    hw = {"utc": utc_now(), "python": sys.version, "platform": platform.platform(), "num_cpus_cgroup": NUM_CPUS,
          "ram_gb_cgroup": RAM_GB, "n_workers": N_WORKERS, "gpu": None, "parent_rlimit_as_bytes": _RAM_BUDGET * 3}
    try:
        hw["gpu"] = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                                   capture_output=True, text=True, timeout=20).stdout.strip() + " (unused)"
    except (OSError, subprocess.TimeoutExpired):
        hw["gpu"] = "none detected"
    pk = {}
    for mod in ("numpy", "scipy", "pandas", "matplotlib", "loguru", "aiohttp", "zss", "networkx", "yaml"):
        try:
            pk[mod] = __import__(mod).__version__
        except (ImportError, AttributeError):
            pk[mod] = None
    hw["packages"] = pk
    hw["sandbox_python"] = shutil.which("python3.12") or "/usr/local/bin/python3.12"
    write_json(PRED / "hardware.json", hw)
    # 0.2 inputs
    sums: list[str] = []
    manifest: list[dict[str, Any]] = []
    missing = []
    for key, rel, dst in INPUT_COPIES:
        src = SRC_PATHS[key] / rel
        d = INPUTS / dst
        if not src.exists():
            missing.append(f"{key}:{rel}")
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        if not d.exists() or sha256_file(d) != sha256_file(src):
            shutil.copy2(src, d)
        h = sha256_file(d)
        sums.append(f"{h}  {dst}")
        manifest.append({"source_artifact": key, "source_path": str(src), "dest": f"inputs/{dst}", "sha256": h,
                         "rows": _count_rows(d), "bytes": d.stat().st_size})
    (INPUTS / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    ok_exp2 = (INPUTS / "exp2_src/tasks/hidden_tests_t1.json").exists() and sha256_file(
        INPUTS / "exp2_src/tasks/hidden_tests_t1.json") == sha256_file(ROOT / "vendor/exp2/hidden_tests_t1.json")
    write_json(RESULTS / "inputs_manifest.json", {"utc": utc_now(), "files": manifest, "missing": missing,
                                                  "exp2_source_equals_vendored_copy": ok_exp2,
                                                  "vendor_note": "vendor/exp9 and vendor/exp2 are executable copies "
                                                                 "of the iteration-8 vendor folders (harness, "
                                                                 "10-class labeller, ITER1 suite)"})
    if missing:
        deviation("D-input", f"missing inputs at Stage 0: {missing}")
    logger.info(f"inputs: {len(manifest)} copied, {len(missing)} missing; exp2 identical={ok_exp2}")
    # 0.3 OpenRouter key
    key = _get_key()
    write_json(RESULTS / "key_start.json", key)
    rem = float((key.get("data") or {}).get("limit_remaining") or 0.0)
    cap = min(CAP_V9_USD, 0.35 * rem)
    write_json(RESULTS / "budget_plan.json", {"phase_remaining_start": rem, "artifact_cap": cap, "utc": utc_now(),
                                              "rule": "ARTIFACT_CAP = min(3.5, 0.35 * remaining)"})
    if rem < 5.0:
        deviation("D-budget", f"phase remaining {rem:.2f} < 5 at Stage 0: scale check and Qwen3-14B dropped")
    logger.info(f"/key: remaining {rem:.3f} -> artifact cap {cap:.3f}")
    # 0.4 mocked 403
    import sample_v9

    t403 = sample_v9.mock_403_test(LOGS)
    write_json(RESULTS / "mock_403_test.json", t403)
    logger.info(f"mock 403 test: {t403}")
    assert t403["passed"], "mocked budget 403 did not stop the batch"
    timing("stage0", time.time() - t0, 1)


def _get_key() -> dict[str, Any]:
    import urllib.request

    req = urllib.request.Request(os.environ["OPENROUTER_BASE_URL"].rstrip("/") + "/key",
                                 headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
                                          "User-Agent": "aii-tpb/1.0"})   # the proxy refuses urllib's default UA
    try:
        with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 - the run's own proxy
            return json.loads(r.read().decode())
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"/key failed: {type(e).__name__}: {e}")
        return {"error": str(e)}


def key_remaining() -> float:
    k = _get_key()
    return float((k.get("data") or {}).get("limit_remaining") or 0.0)


def artifact_cap() -> float:
    p = RESULTS / "budget_plan.json"
    return float(read_json(p)["artifact_cap"]) if p.exists() else CAP_V9_USD


# ---------------------------------------------------------------------------------------------- smoke (0.5)
def stage_smoke(*_: str) -> None:
    import judge_tp
    import sample_v9
    from prompts_tp import baseline_prompt

    p = baseline_prompt(0)
    items = []
    for mk in ("q32", "q14", "q235", "gptoss"):
        for s in range(2):
            items.append({"cell": f"SMOKE_{mk}", "slot": s, "seed": 900000 + s + 1, "prompt": p["prompt"],
                          "model_key": mk, "arm": "smoke", "template": p["template"]})
    out = DATA / "smoke_v9.jsonl"
    res = sample_v9.run(items, lambda it: out, "smoke", concurrency=8, max_tokens=700, cap=artifact_cap())
    rows = read_jsonl(out)
    summ = []
    for r in rows:
        summ.append({"cell": r["cell"], "provider": r.get("provider"), "finish_reason": r.get("finish_reason"),
                     "reasoning_chars": len(r.get("reasoning") or ""), "reasoning_tokens": r.get("reasoning_tokens"),
                     "completion_tokens": r.get("completion_tokens"), "cost": r.get("cost_usd"),
                     "seconds": r.get("gen_seconds")})
    ref = (INPUTS / "exp9/tasks/t1_grid/references/bfs_deque_parent.py").read_text()
    jres = {}
    for m in ("deepseek/deepseek-chat-v3.1", "moonshotai/kimi-k2", "mistralai/mistral-medium-3.1"):
        r = judge_tp.judge_codes([ref], m, purpose="smoke")[0]
        jres[m] = {"label": (r or {}).get("label"), "cost": (r or {}).get("cost")}
    write_json(RESULTS / "smoke.json", {"utc": utc_now(), "run": res, "rows": summ, "judges": jres,
                                        "spend_after": total_cost()})
    logger.info(f"smoke: {json.dumps(summ)[:1500]}")
    logger.info(f"judges: {jres}")


# ---------------------------------------------------------------------------------------------- commit #1a
MECH_COARSE = {"bfs": ["BFS"], "dfs": ["DFS"], "iddfs": ["ID"], "astar": ["HEUR"], "gbfs": ["HEUR"],
               "bibfs": ["BIDIR"], "biastar": ["BIDIR"], "idastar": ["ID"], "jps": ["HEUR"], "dijkstra_unit": ["BFS"]}
MECH_FINE = {"bfs": ["BFS"], "dfs": ["DFS"], "iddfs": ["ID-depth"], "astar": ["HEUR-f"], "gbfs": ["HEUR-h"],
             "bibfs": ["BIDIR-BFS"], "biastar": ["BIDIR-heuristic"], "idastar": ["ID-f"], "jps": ["HEUR-jump"],
             "dijkstra_unit": ["BFS"]}
EXPECTED_REF_CLASS = {"bfs": ("BFS", "BFS"), "dfs": ("DFS", "DFS"), "iddfs": ("ID", "ID-depth"),
                      "idastar": ("ID", "ID-f"), "astar": ("HEUR", "HEUR-f"), "gbfs": ("HEUR", "HEUR-h"),
                      "jps": ("HEUR", "HEUR-jump"), "bibfs": ("BIDIR", "BIDIR-BFS"),
                      "biastar": ("BIDIR", "BIDIR-heuristic"), "dijkstra_unit": ("BFS", "BFS")}
EST_COST_PER_ROW = {"q32": 0.0030, "q14": 0.0019, "q235": 0.0060, "gptoss": 0.0015}

PREDICTIONS = {
    "R6": "the rename hypothesis: a prompt that bans a model's path-search repertoire by NAME is obeyed on names "
          "(lexically) but not on mechanisms: the banned expansion orders come back under new names",
    "N1": {"claim": "Across the 10 retraced five-name-ban configurations, lexical compliance exceeds mechanistic "
                    "compliance (gap = lex - mech, among traceable programs).",
           "primary": "equal-weight mean of the 10 per-configuration gaps (95% configuration-cluster bootstrap, "
                      "10,000 resamples); program-weighted pooled gap beside it",
           "supported": "pooled gap >= 0.3 AND gap > 0 in >= 7/10 configurations",
           "disconfirmed": "pooled gap < 0.1",
           "tests": "per configuration: 2x2 lex x mech, Newcombe paired interval (method 10), exact McNemar on "
                    "the discordant cells",
           "sensitivities": ["L2 instead of L1", "fine classes", "untraceable counted as compliant (lower bound) "
                             "and as non-compliant (upper bound)"]},
    "N2": {"claim": "Qwen3-32B-thinking's correct NAME-level survivors of the five-name ban mostly run a banned "
                    "coarse order class.",
           "pool": "iteration-8 screen 17 + held-out 21 + new A k=5 (W1-W3) + new A held-out",
           "supported": "share in a banned coarse order class >= 0.6 (Wilson CI reported)",
           "disconfirmed": "share <= 0.3",
           "readings": ["(a) all survivors", "(b) survivors whose name-level identity is not BFS order by "
                        "definition (excluding unit Dijkstra, FIFO SPFA, wavefront/flood fill, uniform-cost search)",
                        "N2-adj: observed share minus the uniform-over-non-banned-catalogue null (0.6 coarse, 0.2 "
                        "fine), Wilson interval shifted; the text states whether the share exceeds the null"],
           "by_source": "iteration-8 rows (cap 9,728) vs new rows (cap 12,288) reported separately"},
    "N3": {"claim": "Under cumulative bans B_k = first k of [BFS, DFS, IDDFS, A*, greedy] on Qwen3-32B thinking, "
                    "mechanistic compliance falls with k while lexical compliance stays high.",
           "criteria": ["k=1: lexical and mechanistic compliance both >= 0.7",
                        "Jonckheere-Terpstra one-sided (decreasing in k) on binary mechanistic compliance over the 5 "
                        "ordered groups: Monte-Carlo exact p (100,000 permutations) < 0.05; Cochran-Armitage beside",
                        "lexical (L1) >= 0.7 at every k", "k=5 gap >= 0.4 (paired Newcombe)",
                        "CONFIRMATION: held-out k=5 (W4/W5/P6/P7) gap >= 0.4 with Newcombe lower bound > 0"],
           "disconfirmed": "|lex - mech| <= 0.1 at every k",
           "denominators": "among completed programs (primary) and over all samples",
           "sensitivities": ["L2", "fine classes (e.g. greedy at k=4 is compliant)", "all-samples denominator"],
           "replication": "Qwen3-14B thinking, same rules"},
    "N3-D": {"claim": "exploratory: a name-free described five-mechanism ban vs the named k=5 cell",
             "direction": "under R6, mechanistic compliance OR violation (banned class) rises relative to the named "
                          "k=5 cell (unpaired Newcombe)",
             "measures": ["mechanistic compliance", "violation (banned coarse class)", "lexical use of any banned "
                          "name", "correct survivors"]},
    "N5": {"claim": "secondary: across the literal set and six rotated five-name sets, name-level survivors sit "
                    "mechanistically CLOSER to the banned set (Dm < 0) and NAME-wise FARTHER from it (Dn > 0) than "
                    "the non-banned catalogue average",
           "supported": ">= 5 of 7 sets (or of the defined sets, with >= 4 defined) with Dm < 0 AND Dn > 0",
           "disconfirmed": "<= 3 of 7",
           "tests": "exact algorithm-level permutation per set; binomial sign test over sets (p0 = 0.25 joint, "
                    "0.5 per component)", "defined": "a set needs >= 3 name-level survivors"},
    "scale": "exploratory/descriptive: Qwen3-235B-A22B-thinking and gpt-oss-120b, baseline 50 -> own top five -> "
             "five-name ban 50, in the C1-C10 table format plus traces",
    "multiple_testing": "raw p for N1-N3 reported here; they enter the iteration's Holm family (N1-N4, N4 in TP-G), "
                        "which this artifact cannot apply itself",
}

TRACER_RULES = {
    "events": "ONE global event stream with a sequence counter: POP(cell, kind, container) from the heapq proxy, "
              "queue.get, and an AST rewrite of method calls named pop/popleft/remove/discard/popitem on any object; "
              "PUSH(cell) from append/appendleft/add/put/insert/extend/extendleft (AST), heappush/heapify (proxy), "
              "deque constructor items, and item assignment of a cell key (dict[cell] = v, a[r][c] = v); "
              "ITER(cell) for items yielded by for-loops/comprehensions over a container that was pushed to or that "
              "holds start/goal; READ(cell) from str-subclass grid rows; CALL(fn, cell) for candidate-frame calls "
              "whose arguments contain an in-grid cell (2-int tuple/list or two consecutive ints)",
    "expansion_record": "a candidate is a POP/ITER or CALL carrying a cell (consecutive candidates on the same cell "
                        "merge); it is CONFIRMED if, before the next candidate, a READ or PUSH touches a 4-neighbour "
                        "of the cell, or the next candidate is a 4-neighbour of it. E = confirmed container "
                        "candidates (POP/ITER) if >= 3 on the probe, else confirmed CALL candidates if >= 3, else "
                        "centres of READ bursts (flagged scan-derived). Restarts are counted on the merged stream.",
    "probe_stats": ["n_restart, per-pass max d_root and max d_root+h", "p_mono", "level_cover", "p_lifo",
                    "rho_h (Spearman of expansion index vs -h)", "c_g, c_f, c_h (next expansion in argmin over the "
                    "open list F of d, d+h, h; ties allowed)", "bidir", "fifo (>= 0.98 of within-level pairs ordered "
                    "as their discovering parents)", "jump share", "revisit share"],
    "decision_list": ["(1) ID if root restarts with a growing pass bound on >= 50% of informative probes (fine: "
                      "ID-depth if the pass max d_root grows by 1, else ID-f)",
                      "(2) BIDIR if bidir on >= 50% (fine BIDIR-BFS / BIDIR-heuristic)",
                      "(3) BFS if pooled p_mono >= 0.98 AND pooled level_cover >= 0.98 AND no restarts",
                      "(4) HEUR if median rho_h >= 0.6 AND max(c_f, c_h) >= 0.9 (fine HEUR-f if c_f >= c_h, "
                      "HEUR-h, HEUR-jump if jump share >= 0.5)",
                      "(5) DFS if pooled p_lifo >= 0.9 (fine DFS-revisit when revisits > 0.1)",
                      "(6) HEUR (weak) if median rho_h >= 0.6", "(7) OTHER (revisit/random-walk, raster-sweep, "
                      "random-priority, unknown)"],
    "informative_probe": "|E| >= 6; >= 10 informative probes per program, else UNTRACEABLE",
    "revisable_in_gate": "at most 2 revision rounds using ONLY references, planted controls and gold: the "
                         "informative-probe minimum (10 down to 6), the c_f/c_h cut-off and the level_cover cut-off; "
                         "the class semantics never change",
    "gate": "references 100% in their expected coarse class; planted controls 9/9; gold agreement >= 0.9; else "
            "N1-N3 DESCRIPTIVE and the fallback label (iteration-8 runtime label mapped through the 1.11 table)",
}


def _src_hashes(files: list[str]) -> dict[str, str]:
    return {f: sha256_file(SRC / f) for f in files if (SRC / f).exists()}


def stage_commit1a(*_: str) -> None:
    import cells_v9
    import lexical
    from prompts_tp import renderer_checks

    assert not (RESULTS / "commit1a.lock").exists(), "commit #1a already made"
    rows = []
    for cid, cell in cells_v9.CELLS.items():
        if cell["group"] in ("A", "E") or cell["kind"] == "baseline":
            rows += cells_v9.prompts_for(cid)
    write_jsonl(PRED / "prompts_v9_1a.jsonl", rows)
    # renderer byte checks: k=5 W1 slot 0 == iteration 8's C6 ban slot 0 prompt == iteration 2's TOP5 W1 prompt
    i8 = [r for r in read_jsonl(INPUTS / "iter8/data/labelled_C6_ban.jsonl") if int(r["slot"]) == 0][0]
    e9 = [r for r in read_jsonl(INPUTS / "exp9/data/samples.jsonl") if r["condition"] == "multi:TOP5"
          and r.get("template") in ("W1", 1, "1")]
    a5 = [r for r in rows if r["cell"] == "A_k5" and r["slot"] == 0][0]
    rc = renderer_checks(e9[0]["prompt"] if e9 else None)
    rc.update({"A_k5_slot0_equals_iter8_C6_ban_slot0": a5["prompt"] == i8["prompt"],
               "A_k5_slot0_sha256": a5["prompt_sha256"], "iter8_C6_ban_slot0_sha256": sha256_text(i8["prompt"]),
               "k_prompts_example": {r["cell"]: r["segment"] for r in rows if r["slot"] == 0 and r["group"] == "A"}})
    write_json(RESULTS / "renderer_checks_v9.json", rc)
    assert rc["A_k5_slot0_equals_iter8_C6_ban_slot0"], "k=5 prompt differs from iteration 8's literal ban"
    lex = lexical.run_unit_tests()
    write_json(RESULTS / "lexical_unit_tests.json", lex)
    assert lex["n_ok"] == lex["n"], "lexical unit tests failed"
    payload = {
        "label": "commit #1a (iteration 9 TP-B): everything that governs the A, E and F-baseline cells",
        "utc": utc_now(),
        "commit_split": "D-commit-split: plan COMMIT #1 is made as two commits, each before the rows it governs. "
                        "#1a (this) precedes every new sample; it fixes the k order, prompts, seeds, N, decoding, "
                        "provider pins, budget plan, lexical rules, mechanism mappings, the tracer's decision-list "
                        "semantics and initial thresholds, and every prediction/disconfirmer. #1b precedes the first "
                        "traced ban row (old or new) and the B/C/D/F-ban samples; it fixes the tracer code, probes, "
                        "planted controls, gate result, rotated sets, N3-D descriptions and the analysis code. New A/E "
                        "rows are only appended to data/raw_*.jsonl by the background sampler and are not opened, "
                        "labelled or traced before #1b (asserted by the label stage).",
        "k_order": ["bfs", "dfs", "iddfs", "astar", "gbfs"],
        "deviation_D_order": "the direction's order (BFS; +DFS; +IDDFS; +A*; +greedy) differs from iteration 8's "
                             "FILL_ORDER (BFS, DFS, greedy, IDDFS, A*) at k = 3 and 4; beyond DFS the frequency order "
                             "is a convention (C6 baseline BFS 91 / invalid 9)",
        "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": "off", "max_tokens": 12288, "thinking": "on",
                     "reasoning_returned": True},
        "deviation_D_cap": "max_tokens 12,288 (direction) vs iteration 8's 9,728; N2 pools by source and reports "
                           "each source separately",
        "models": MODELS_V9,
        "seeds": "1000 * cell_index + slot + 1",
        "cells": {cid: c for cid, c in cells_v9.CELLS.items()},
        "run_order": "A, B, C, D, E, F (drop order F, E, D, C; never A; N per cell may drop to 30 on A before any "
                     "cell is dropped)",
        "staging": "each cell 10 -> full (cells are 50); before every batch GET /key; run only if spent + 1.3 * "
                   "estimate <= ARTIFACT_CAP and phase remaining >= 2 * estimate; F runs only if >= 0.9 of the "
                   "3.5 cap remains after E",
        "est_cost_per_row": EST_COST_PER_ROW,
        "artifact_cap": artifact_cap(),
        "prompts_file": "predictions/prompts_v9_1a.jsonl",
        "prompts_file_sha256": sha256_file(PRED / "prompts_v9_1a.jsonl"),
        "prompt_sha256_by_cell": {cid: sorted({r["prompt_sha256"] for r in rows if r["cell"] == cid})
                                  for cid in sorted({r["cell"] for r in rows})},
        "renderer_checks": rc,
        "lexical": {"L1": "alias_regex(banned keys) of common.py anywhere in the code (primary; the shared-protocol "
                          "field lexical_flag = lexical_L1)",
                    "L2": lexical.__doc__.split("L2 (sensitivity, self-naming):")[1].split("Trace names")[0].strip(),
                    "trace_names": "banned-alias matches in the thinking text",
                    "unit_tests": f"{lex['n_ok']}/{lex['n']}",
                    "L1_note": "the committed regex is substring-based for the short aliases ('BFS', 'DFS', "
                               "'IDDFS', 'JPS'), so 'dfs' inside 'iddfs' counts; r'\\bgbfs\\b' does not match inside "
                               "'gbfs_heap' (L2 splits identifiers)"},
        "mechanism_mapping": {"coarse": MECH_COARSE, "fine": MECH_FINE, "B_c_coarse_banned": ["BFS", "DFS", "ID",
                                                                                              "HEUR"],
                              "heuristic_weak_counts_as": "HEUR",
                              "extended_alias_table_other": ["wavefront / flood fill / Lee algorithm",
                                                             "SPFA / Bellman-Ford / label-correcting",
                                                             "uniform-cost search (Dijkstra aliases)", "random walk",
                                                             "beam search", "random-priority search"]},
        "expected_reference_classes": EXPECTED_REF_CLASS,
        "tracer_rules": TRACER_RULES,
        "survivor_definitions": {"name_level": "passes the 48-case suite AND its adjudicated algorithm (catalogue or "
                                               "named known-outside) is not in B_k",
                                 "mechanism_level": "passes AND its order class is not in the coarse classes of B_k",
                                 "never_mixed": True},
        "name_level_labelling": "iteration-8 pipeline unchanged: last python fence; truncated = finish_reason "
                                "'length' or no closed fence; 48-case hidden suite + ITER1 41-case column; 10-class "
                                "runtime+AST labeller; judge 'a' (deepseek-chat-v3.1) on disagreement; adjudication by "
                                "re-gated deepseek-chat-v3.1 + kimi-k2 (third mistral-medium-3.1) for cells with "
                                "candidate survivors / review classes / 10% audit",
        "predictions": PREDICTIONS,
        "source_hashes": _src_hashes(["common.py", "prompts_tp.py", "cells_v9.py", "sample_v9.py", "lexical.py",
                                      "label_tp.py", "judge_tp.py", "adjudicate.py", "stages_v9.py"]),
        "inputs_sha256sums": sha256_file(INPUTS / "SHA256SUMS"),
    }
    write_json(PRED / "commit1a.json", payload)
    commit(PRED / "commit1a.json", "commit1a", "pre-registration of the A/E/F-baseline cells, predictions, rules")
    ok, problems, _ = verify_chain()
    assert ok, problems
    (RESULTS / "commit1a.lock").write_text(utc_now())
    logger.info("commit #1a made and chain verified")


# ---------------------------------------------------------------------------------------------- sampling (stage 3)
GOVERNING = {"A": "commit1a", "E": "commit1a", "B": "commit1b", "C": "commit1b", "D": "commit1b"}


def _governing_commit(cell: dict[str, Any]) -> str:
    if cell["group"] == "F":
        return "commit1a" if cell["kind"] == "baseline" else "commit2"
    return GOVERNING[cell["group"]]


def _per_row_cost(mkey: str) -> float:
    vals = [float(r.get("cost_usd") or 0) for cid in _cells_of_model(mkey) for r in read_jsonl(DATA / f"raw_{cid}.jsonl")]
    vals = [v for v in vals if v > 0]
    return (sum(vals) / len(vals)) if len(vals) >= 5 else EST_COST_PER_ROW[mkey]


def _cells_of_model(mkey: str) -> list[str]:
    import cells_v9

    return [cid for cid, c in cells_v9.CELLS.items() if c["model_key"] == mkey]


def stage_sample(*cell_args: str) -> None:
    """`sample A E` or `sample A_k1 A_k2`: staged (first 10 per cell, then the rest), budget-gated per batch."""
    import cells_v9
    import sample_v9

    want: list[str] = []
    for a in cell_args:
        if a in cells_v9.RUN_ORDER:
            want += [cid for cid, c in cells_v9.CELLS.items() if c["group"] == a]
        elif a in cells_v9.CELLS:
            want.append(a)
        else:
            raise SystemExit(f"unknown cell/group {a}")
    want = sorted(dict.fromkeys(want), key=lambda c: (cells_v9.RUN_ORDER.index(cells_v9.CELLS[c]["group"]),
                                                       cells_v9.CELLS[c]["cell_index"]))
    for cid in want:
        gc_label = _governing_commit(cells_v9.CELLS[cid])
        assert commit_time(gc_label) is not None, f"{cid}: governing {gc_label} not made yet"
    cap = artifact_cap()
    prompts = {cid: cells_v9.prompts_for(cid) for cid in want}
    for stage_name, lo, hi in (("first10", 0, 10), ("rest", 10, 10 ** 6)):
        items = [p for cid in want for p in prompts[cid][lo:hi]]
        if not items:
            continue
        est = sum(_per_row_cost(it["model_key"]) for it in items)
        rem = key_remaining()
        spent = total_cost()
        logger.info(f"[sample {stage_name}] {len(items)} rows, estimate ${est:.3f}, artifact spent ${spent:.3f}, "
                    f"cap ${cap:.2f}, phase remaining ${rem:.2f}")
        if spent + 1.3 * est > cap or rem < 2 * est:
            # trim to what fits, never below the per-cell floor of 30 for A; otherwise skip
            logger.error(f"[sample {stage_name}] budget gate refuses the batch (spent {spent:.3f} + 1.3*{est:.3f} "
                         f"> {cap:.2f} or remaining {rem:.2f} < 2*{est:.3f})")
            append_jsonl(RESULTS / "budget_gate.jsonl", {"utc": utc_now(), "cells": want, "stage": stage_name,
                                                         "estimate": est, "spent": spent, "remaining": rem,
                                                         "decision": "refused"})
            return
        append_jsonl(RESULTS / "budget_gate.jsonl", {"utc": utc_now(), "cells": want, "stage": stage_name,
                                                     "estimate": est, "spent": spent, "remaining": rem,
                                                     "decision": "run"})
        t0 = time.time()
        s0 = total_cost()
        res = sample_v9.run(items, lambda it: DATA / f"raw_{it['cell']}.jsonl", f"sample:{'+'.join(want)}"[:60],
                            concurrency=56, cap=cap)
        dt, ds = time.time() - t0, total_cost() - s0
        timing(f"sample:{stage_name}:{','.join(want)}"[:120], dt, max(res["n_ok"], 1),
               note=f"usd={ds:.4f} usd_per_row={ds / max(res['n_ok'], 1):.5f}")
        logger.info(f"[sample {stage_name}] {res} in {dt:.0f}s, ${ds:.4f}")
        if res["stopped"]:
            logger.error(f"sampling stopped: {res['reason']} -- the batch is not rerun")
            return


# ---------------------------------------------------------------------------------------------- dataset use (all 10)
def _parse_clrs(e: dict[str, Any]) -> dict[str, Any] | None:
    import re as _re

    txt = e["input"]
    m = _re.search(r"A:\s*(\[\[.*?\]\])", txt, _re.DOTALL)
    if not m:
        return None
    rows = _re.findall(r"\[([0-9.\s]+)\]", m.group(1))
    A = [[int(float(x)) for x in r.split()] for r in rows]
    sm = _re.search(r"\bs:\s*(\d+)", txt)
    arrs = _re.findall(r"\[([0-9\s]+)\]", e["output"])
    if not arrs:
        return None
    pi = [int(x) for x in arrs[-1].split()]
    if len(pi) != len(A):
        return None
    return {"algorithm": e["metadata_algorithm"], "row_index": e.get("metadata_row_index"), "A": A,
            "s": int(sm.group(1)) if sm else 0, "pi_final": pi}


def stage_datasets(*_: str) -> None:
    """Uses every dataset of the declared dependency (art_j3Rm_lr2nzR6, full_data_out.json, 10 datasets): clrs_text
    BFS/DFS traces (order-statistics sanity check), thealgorithms_python / kodcode_algorithmic / xlcost_python /
    mercury / leetcodedataset (known corpus for the novelty audit's nearest-neighbour search + lexical positives),
    humanevalplus / enamel (non-search code: lexical false-positive rate), concreteness_norms (English words matching
    an alias regex: lexical specificity), llm_creativity (the inspiration repository's T02 label distribution)."""
    import lexical
    from common import CANON_ORDER, DS_FILE

    d = json.loads(DS_FILE.read_text())
    by = {ds["dataset"]: ds["examples"] for ds in d["datasets"]}
    del d
    gc.collect()
    out: dict[str, Any] = {"source": str(DS_FILE), "source_sha256": sha256_file(DS_FILE),
                           "datasets": {k: len(v) for k, v in by.items()}, "use": {}}
    # clrs_text
    cl = [x for x in (_parse_clrs(e) for e in by["clrs_text"] if e.get("metadata_algorithm") in ("bfs", "dfs")) if x]
    write_jsonl(INPUTS / "dataset" / "clrs_bfs_dfs.jsonl", cl)
    out["use"]["clrs_text"] = {"parsed_bfs": sum(1 for x in cl if x["algorithm"] == "bfs"),
                               "parsed_dfs": sum(1 for x in cl if x["algorithm"] == "dfs"),
                               "role": "order-statistics sanity check on canonical traces (gate unit tests)"}
    # lexical specificity / sensitivity
    allk = list(CANON_ORDER)

    def rate(codes: list[str]) -> dict[str, Any]:
        h1 = sum(1 for c in codes if lexical.l1_hits(c, allk))
        h2 = sum(1 for c in codes if lexical.l2_hits(c, allk))
        return {"n": len(codes), "L1_any_alias": h1, "L2_self_naming": h2,
                "L1_rate": h1 / len(codes) if codes else None, "L2_rate": h2 / len(codes) if codes else None}

    out["use"]["humanevalplus"] = {"role": "non-search code: lexical false-positive rate",
                                   **rate([e["output"] for e in by["humanevalplus"]])}
    out["use"]["enamel"] = {"role": "non-search code: lexical false-positive rate",
                            **rate([e["output"] for e in by["enamel"]])}
    words = [e["input"] for e in by["concreteness_norms"]]
    rx_hits = [w for w in words if lexical.l1_hits(" " + w + " ", allk)]
    out["use"]["concreteness_norms"] = {"role": "English words matched by an alias regex (lexical specificity)",
                                        "n_words": len(words), "n_matching": len(rx_hits),
                                        "examples": sorted(rx_hits)[:40]}
    lc_graph = [e["output"] for e in by["leetcodedataset"] if re.search(r"Breadth-First|Depth-First|Graph",
                                                                         str(e.get("metadata_tags")))]
    out["use"]["leetcodedataset"] = {"role": "graph-search reference solutions: lexical sensitivity",
                                     **rate(lc_graph)}
    mc = [e["output"] for e in by["mercury"] if re.search(r"Breadth-First|Depth-First",
                                                          str(e.get("metadata_topic_tags")))]
    out["use"]["mercury"] = {"role": "human BFS/DFS solutions: lexical sensitivity", **rate(mc)}
    for name in ("thealgorithms_python", "kodcode_algorithmic", "xlcost_python"):
        ex = by[name]
        named = [e for e in ex if re.search(r"bfs|dfs|breadth|depth.first|dijkstra|a\*|astar|a_star|greedy|"
                                            r"iterative.deepening|bidirectional|jump.point", e.get("output", "")
                                            + " " + str(e.get("metadata_named_algorithms", "")), re.IGNORECASE)]
        out["use"][name] = {"n_rows": len(ex), "n_naming_search": len(named),
                            "role": "known corpus for the novelty audit (iteration-8 corpus_rows.jsonl subset) + "
                                    "lexical sensitivity", **{k: v for k, v in rate([e["output"] for e in named
                                                                                      ][:500]).items()}}
    lcre = Counter(e["output"] for e in by["llm_creativity"])
    out["use"]["llm_creativity"] = {"role": "the inspiration repository's blind-judge T02 label distribution "
                                            "(context for positioning; no program text, licence)",
                                    "labels": dict(lcre)}
    write_json(RESULTS / "dataset_use.json", out)
    logger.info(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items()
                                                                       if kk != "examples"}) for k, v in
                            out["use"].items()})[:3000])


# ---------------------------------------------------------------------------------------------- tracer gate (stage 1)
def stage_tracer_gate(round_label: str = "round0", *_: str) -> None:
    """Gate run: references, planted controls, gold (non-ban), blind order judges, unit tests. No ban row is read."""
    import gate_v9
    import orderclass

    assert commit_time("commit1b") is None, "the gate runs before commit #1b"
    t0 = time.time()
    refs = sorted(gate_v9.REF_DIR.glob("*.py"))
    ctrls = sorted((ROOT / "controls").glob("*.py"))
    gold = gate_v9.gold_rows()
    logger.info(f"gate: {len(refs)} references, {len(ctrls)} controls, {len(gold)} gold programs")
    items = [(f"ref|{p.stem}", p.read_text(), True) for p in refs] + \
            [(f"ctl|{p.stem}", p.read_text(), True) for p in ctrls] + \
            [(f"gold|{g['gid']}", g["code"], False) for g in gold]
    res = gate_v9.trace_many(items, workers=N_WORKERS - 1)
    # references
    ref_rows = []
    for p in refs:
        alg = gate_v9.ref_alg(p.stem)
        exp_c, exp_f = EXPECTED_REF_CLASS[alg]
        r = res[f"ref|{p.stem}"]
        ref_rows.append({"reference": p.stem, "algorithm": alg, "expected": exp_c, "expected_fine": exp_f,
                         "class": r.get("order_class"), "fine": r.get("order_class_fine"),
                         "ok": r.get("order_class") == exp_c, "ok_fine": r.get("order_class_fine") == exp_f,
                         "fifo_flag": r.get("fifo_flag"), "ds_signature": r.get("ds_signature"),
                         "stats": {k: r.get(k) for k in ("id_share", "bidir_share", "p_mono", "level_cover",
                                                         "rho_h_median", "c_f", "c_h", "p_lifo", "fifo",
                                                         "jump_share", "revisit_share", "n_informative")}})
    ctl_rows = []
    for p in ctrls:
        exp_c, exp_f = gate_v9.CONTROLS[p.stem]
        r = res[f"ctl|{p.stem}"]
        ctl_rows.append({"control": p.stem, "expected": exp_c, "expected_fine": exp_f, "class": r.get("order_class"),
                         "fine": r.get("order_class_fine"), "ok": r.get("order_class") == exp_c and (
                             exp_c != "OTHER" or r.get("order_class_fine") == exp_f),
                         "fifo_flag": r.get("fifo_flag"), "ds_signature": r.get("ds_signature")})
    # controls must pass the 48-case suite
    import label_tp

    ev = label_tp.evaluate_unique([p.read_text() for p in ctrls])
    for row, p in zip(ctl_rows, ctrls):
        e = ev[sha256_text(p.read_text())]
        row["passes_48"] = bool(e.get("passed"))
        row["passes_41"] = bool(e.get("passed_exp2"))
    # gold
    gold_rows = []
    for g in gold:
        r = res[f"gold|{g['gid']}"]
        exp_c, exp_f = EXPECTED_REF_CLASS[g["label"]]
        gold_rows.append({**{k: g[k] for k in ("gid", "source", "condition", "label", "labeller_source",
                                               "code_sha256", "passed")}, "expected": exp_c, "expected_fine": exp_f,
                          "class": r.get("order_class"), "fine": r.get("order_class_fine"),
                          "reason": r.get("reason"), "fifo_flag": r.get("fifo_flag")})
    unverified = sorted({row["expected_fine"] for row in ref_rows if not row["ok"]})
    traceable = [g for g in gold_rows if g["class"] != "UNTRACEABLE"]
    in_scope = [g for g in traceable if g["expected_fine"] not in unverified]
    agree = sum(1 for g in in_scope if g["class"] == g["expected"])
    per_class = {}
    for lab in sorted({g["label"] for g in gold_rows}):
        sub = [g for g in gold_rows if g["label"] == lab]
        tr = [g for g in sub if g["class"] != "UNTRACEABLE"]
        per_class[lab] = {"n": len(sub), "traceable": len(tr), "agree": sum(1 for g in tr if g["class"] == g["expected"]),
                          "agree_rate": (sum(1 for g in tr if g["class"] == g["expected"]) / len(tr)) if tr else None,
                          "classes": dict(Counter(g["class"] for g in sub))}
    conf = defaultdict(Counter)
    for g in gold_rows:
        conf[g["expected"]][g["class"]] += 1
    gate = {"round": round_label, "utc": utc_now(), "thresholds": dict(orderclass.TH),
            "references": ref_rows, "references_ok": sum(r["ok"] for r in ref_rows), "references_n": len(ref_rows),
            "controls": ctl_rows, "controls_ok": sum(r["ok"] for r in ctl_rows), "controls_n": len(ctl_rows),
            "gold_n": len(gold_rows), "gold_traceable": len(traceable), "gold_in_scope": len(in_scope),
            "gold_agree": agree, "gold_agreement": agree / len(in_scope) if in_scope else None,
            "gold_per_label": per_class, "gold_confusion": {k: dict(v) for k, v in conf.items()},
            "unverified_classes": unverified}
    gate["passed_references"] = all(r["ok"] for r in ref_rows if r["expected_fine"] not in unverified)
    gate["passed_controls"] = all(r["ok"] and r["passes_48"] for r in ctl_rows)
    gate["passed_gold"] = (gate["gold_agreement"] or 0) >= 0.9
    gate["one_class_fallback"] = len(unverified) == 1
    gate["passed"] = bool(gate["passed_references"] and gate["passed_controls"] and gate["passed_gold"]
                          and len(unverified) <= 1)
    write_jsonl(RESULTS / f"tracer_gate_gold_{round_label}.jsonl", gold_rows)
    write_json(RESULTS / f"tracer_gate_{round_label}.json", gate)
    logger.info(f"GATE {round_label}: refs {gate['references_ok']}/{gate['references_n']} (unverified {unverified}), "
                f"controls {gate['controls_ok']}/{gate['controls_n']}, gold {agree}/{len(in_scope)} = "
                f"{gate['gold_agreement']}, passed={gate['passed']}")
    timing(f"tracer_gate:{round_label}", time.time() - t0, len(items))


def stage_gold_judges(*_: str) -> None:
    """Blind order-discipline adjudication of a stratified 100 gold programs by two gated judges (10 controls each,
    >= 9/10 to pass)."""
    import random as _r

    import gate_v9
    from judge_tp import rename_identifiers

    gold = {g["gid"]: g for g in gate_v9.gold_rows()}
    rows = read_jsonl(RESULTS / "tracer_gate_gold_round0.jsonl")
    ctrl_refs = {"bfs_deque_parent": "FIFO levels", "dfs_stack": "LIFO depth-first",
                 "gbfs_counter": "global priority on estimate", "astar_fg": "global priority on cost+estimate",
                 "iddfs_iterative": "restarts with growing bound", "idastar": "restarts with growing bound",
                 "bibfs_deques": "two frontiers", "biastar": "two frontiers",
                 "dijkstra_counter": "global priority on cost so far", "jps4": "global priority on cost+estimate"}
    ctrl_codes = [rename_identifiers((gate_v9.REF_DIR / f"{k}.py").read_text()) for k in ctrl_refs]
    by_lab = defaultdict(list)
    for r in rows:
        by_lab[r["label"]].append(r)
    rng = _r.Random(0)
    labs = sorted(by_lab)
    pick: list[dict[str, Any]] = []
    per = max(1, 100 // len(labs))
    for lab in labs:
        sub = sorted(by_lab[lab], key=lambda x: x["gid"])
        pick += rng.sample(sub, min(per, len(sub)))
    rest = [r for r in rows if r not in pick]
    pick += rng.sample(rest, max(0, min(100 - len(pick), len(rest))))
    out: dict[str, Any] = {"judges": {}, "n": len(pick)}
    for m in ADJ_PAIR:
        cres = gate_v9.judge_disciplines(ctrl_codes, m)
        score = sum(1 for (k, want), c in zip(ctrl_refs.items(), cres) if c and c["discipline"] == want)
        out["judges"][m] = {"control_score": score, "passed": score >= 9,
                            "controls": [{"ref": k, "want": w, "got": (c or {}).get("discipline")}
                                         for (k, w), c in zip(ctrl_refs.items(), cres)]}
        logger.info(f"order judge {m}: {score}/10")
    gated = [m for m, v in out["judges"].items() if v["passed"]]
    items = []
    if gated:
        codes = [gold[r["gid"]]["code"] for r in pick]
        answers = {m: gate_v9.judge_disciplines(codes, m) for m in gated}
        for j, r in enumerate(pick):
            votes = {m: (answers[m][j] or {}).get("discipline") for m in gated}
            cls = [gate_v9.DISC_TO_CLASS.get(v) for v in votes.values() if v]
            judged = cls[0] if cls and all(c == cls[0] for c in cls) else None
            items.append({"gid": r["gid"], "label": r["label"], "expected": r["expected"], "tracer": r["class"],
                          "votes": votes, "judged_class": judged})
        dec = [x for x in items if x["judged_class"]]
        out["n_judges_agree"] = len(dec)
        out["tracer_vs_judges"] = sum(1 for x in dec if x["judged_class"] == x["tracer"]) / len(dec) if dec else None
        out["prior_label_vs_judges"] = sum(1 for x in dec if x["judged_class"] == x["expected"]) / len(dec) if dec \
            else None
        pcl = defaultdict(lambda: [0, 0])
        for x in dec:
            pcl[x["label"]][0] += int(x["judged_class"] == x["tracer"])
            pcl[x["label"]][1] += 1
        out["tracer_vs_judges_per_label"] = {k: {"agree": a, "n": n} for k, (a, n) in pcl.items()}
    out["gated"] = gated
    out["items"] = items
    out["spend_total"] = total_cost()
    write_json(RESULTS / "gold_order_judges.json", out)
    logger.info(f"gold order judges: gated {gated}, tracer-vs-judges {out.get('tracer_vs_judges')}, "
                f"prior-vs-judges {out.get('prior_label_vs_judges')}")


def stage_tracer_tests(*_: str) -> None:
    import gate_v9

    out: dict[str, Any] = {"utc": utc_now()}
    progs = gate_v9.unit_test_programs()
    res = gate_v9.trace_many([(k, c, False) for k, (c, _) in progs.items()], workers=N_WORKERS - 1)
    import orderclass

    rows = []
    for k, (c, want) in progs.items():
        r = res[k]
        if want is None and k.startswith("renamed_"):
            stem = k[len("renamed_"):]
            want = EXPECTED_REF_CLASS[gate_v9.ref_alg(stem)][0]
        rows.append({"test": k, "expected": want, "class": r.get("order_class"), "fine": r.get("order_class_fine"),
                     "reason": r.get("reason"), "ok": r.get("order_class") == want})
    out["programs"] = rows
    out["no_double_count"] = gate_v9.no_double_count_test()
    out["determinism"] = gate_v9.determinism_test()
    out["clrs_order_stats"] = gate_v9.clrs_check()
    out["n_ok"] = sum(r["ok"] for r in rows)
    out["n"] = len(rows)
    out["all_passed"] = bool(out["n_ok"] == out["n"] and out["no_double_count"]["passed"] and
                             out["determinism"]["passed"] and out["clrs_order_stats"]["passed"])
    write_json(RESULTS / "tracer_unit_tests.json", out)
    logger.info(f"tracer unit tests: {out['n_ok']}/{out['n']} programs; double-count {out['no_double_count']}; "
                f"determinism {out['determinism']}; clrs {out['clrs_order_stats']}")
    for r in rows:
        if not r["ok"]:
            logger.warning(f"unit test FAILED: {r}")


# ---------------------------------------------------------------------------------------------- N5 sets (1.12)
def stage_n5sets(*_: str) -> None:
    import gate_v9
    import mechdist

    assert commit_time("commit1b") is None
    refs = sorted(gate_v9.REF_DIR.glob("*.py"))
    res = gate_v9.trace_many([(p.stem, p.read_text(), True) for p in refs], workers=N_WORKERS - 1)
    write_json(RESULTS / "reference_traces.json", res, indent=None)
    Dm = mechdist.mech_matrix(res)
    Dn = mechdist.name_matrix()
    sel = mechdist.select_sets(Dm, Dn, seed=0)
    out = {"utc": utc_now(), "D_mech": Dm, "D_name": Dn, **sel,
           "refs_of": mechdist.REFS_OF, "ext_aliases": mechdist.EXT_ALIASES, "ext_short": mechdist.EXT_SHORT}
    write_json(PRED / "n5_sets.json", out)
    logger.info(f"N5 rule {sel['rule']}: M-only {sel['n_M_only']}, L-only {sel['n_L_only']}")
    for k, v in sel["sets"].items():
        logger.info(f"{k} ({v['type']}): {v['set']} M={v['type_M']} L={v['type_L']}")


# ---------------------------------------------------------------------------------------------- N3-D (1.13)
N3D_DESCRIPTIONS = {
    "bfs": "a search that explores cells in rings of increasing step count from the start, keeping discovered cells "
           "in a first-in-first-out line",
    "dfs": "a search that follows one branch as far as it can go before backing up to the last fork, keeping "
           "discovered cells in a last-in-first-out pile",
    "iddfs": "a search that repeats a branch-following search from the start with a step limit that grows by one "
             "each round",
    "astar": "a search that always expands the open cell with the smallest sum of steps taken so far plus an "
             "estimate of the steps remaining to the goal",
    "gbfs": "a search that always expands the open cell with the smallest estimate of the steps remaining to the "
            "goal, ignoring the steps taken so far",
}


def stage_describe(*_: str) -> None:
    import lexical
    import sample_v9

    assert commit_time("commit1b") is None
    desc = dict(N3D_DESCRIPTIONS)
    checks: dict[str, Any] = {}
    for k, d in desc.items():
        checks[k] = {"text": d, "alias_hits_any_of_10": lexical.all_alias_hits(d)}
        assert not checks[k]["alias_hits_any_of_10"], (k, checks[k])
    items = []
    q = ("Which standard grid path-search algorithm does the following describe? Answer with the algorithm's name "
         "only.\n\n{d} /no_think")
    for k, d in desc.items():
        for s in range(20):
            items.append({"cell": f"N3D_NAME_{k}", "slot": s, "seed": 700000 + 100 * CANON_INDEX(k) + s + 1,
                          "prompt": q.format(d=d[0].upper() + d[1:] + "."), "model_key": "q32", "arm": "naming"})
    out = DATA / "n3d_naming.jsonl"
    sample_v9.run(items, lambda it: out, "n3d_naming", concurrency=32, max_tokens=64, cap=artifact_cap())
    rows = read_jsonl(out)
    for k in desc:
        rs = [r for r in rows if r["cell"] == f"N3D_NAME_{k}"]
        ok = [bool(lexical.l1_hits((r.get("content") or "") + " " + (r.get("reasoning") or "")[-200:], [k]))
              for r in rs]
        ok_c = [bool(lexical.l1_hits(r.get("content") or "", [k])) for r in rs]
        checks[k].update({"n": len(rs), "named_correctly_content": sum(ok_c), "rate": sum(ok_c) / len(rs) if rs
                          else None, "answers": [trunc_s(r.get("content")) for r in rs[:6]]})
    passed = {k: (v["rate"] or 0) >= 0.8 for k, v in checks.items()}
    write_json(PRED / "n3d_descriptions.json", {"utc": utc_now(), "descriptions": desc, "checks": checks,
                                                 "passed": passed, "rewrites": 0,
                                                 "rule": "zero L1 matches against all ten algorithms' aliases AND "
                                                         "Qwen3-32B (/no_think, max_tokens 64, 20 queries) names it "
                                                         "correctly >= 0.8 (L1 regex of the intended algorithm on the "
                                                         "answer)"})
    logger.info({k: (v["rate"], v["answers"][:2]) for k, v in checks.items()})


def CANON_INDEX(k: str) -> int:
    from common import CANON_ORDER

    return CANON_ORDER.index(k)


def trunc_s(s: Any, n: int = 120) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[:n] + "..."


# ---------------------------------------------------------------------------------------------- stage 2: retrace
def _truncated_iter8(r: dict[str, Any]) -> bool:
    return r.get("finish_reason") == "length" or r.get("extract_method") in ("no_fence", "no_content") or \
        (r.get("content") is not None and r.get("content").count("```") % 2 == 1)


def retrace_rows(include_extras: bool = False) -> list[dict[str, Any]]:
    """P_ret: C1-C8 ban rows, C6 held-out confirm, C9 = art_IVZc3TWCeE9f multi:TOP5, C10 = art_zNyBP6zieI5u TOP5;
    (descriptive extras: art_IVZc3TWCeE9f single:bfs and multi:TOP/ARC/SCATTER)."""
    from common import LITERAL5

    rows: list[dict[str, Any]] = []
    for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"):
        for arm in (("ban", "confirm") if c == "C6" else ("ban",)):
            for r in read_jsonl(INPUTS / f"iter8/data/labelled_{c}_{arm}.jsonl"):
                rows.append({"uid": r["uid"], "config": c, "source": "iter8", "arm": arm, "template": r.get("template"),
                             "slot": r.get("slot"), "banned_set": list(LITERAL5), "code": r.get("code"),
                             "content": r.get("content"), "reasoning": r.get("reasoning"),
                             "passed": bool(r.get("passed")), "passed_exp2": bool(r.get("passed_exp2")),
                             "label": r.get("adj_label") or r.get("label_raw"), "label_other_name": r.get("adj_other_name"),
                             "truncated": _truncated_iter8(r), "cap": 9728 if c in ("C1", "C4", "C6") else 1536,
                             "provider": r.get("provider"), "model": r.get("model"),
                             "reasoning_tokens": r.get("reasoning_tokens"), "runtime_label": r.get("runtime_label"),
                             "ast_label": r.get("ast_label")})
    conds = ["multi:TOP5"] + (["single:bfs", "multi:TOP", "multi:ARC", "multi:SCATTER"] if include_extras else [])
    for r in read_jsonl(INPUTS / "exp9/data/samples.jsonl"):
        if r.get("task") != "t1" or r.get("condition") not in conds:
            continue
        cfg = "C9" if r["condition"] == "multi:TOP5" else f"EXP9:{r['condition']}"
        banned = r.get("banned") if isinstance(r.get("banned"), list) else list(LITERAL5)
        rows.append({"uid": f"exp9|{r['condition']}|{r.get('sample_id')}|{r.get('template')}", "config": cfg,
                     "source": "exp9", "arm": r["condition"], "template": r.get("template"), "slot": r.get("sample_id"),
                     "banned_set": banned, "code": r.get("code"), "content": r.get("text"), "reasoning": None,
                     "passed": bool(r.get("passed")), "label": r.get("label"), "label_other_name": None,
                     "truncated": bool(r.get("truncated")), "cap": 1024, "model": r.get("model"),
                     "runtime_label": r.get("runtime_label"), "ast_label": r.get("ast_label")})
    for r in read_jsonl(INPUTS / "exp31/data/labels.jsonl"):
        if r.get("arm") != "top5" or r.get("stage") != "contrast":
            continue
        rows.append({"uid": f"exp31|{r['row_id']}", "config": "C10", "source": "exp31", "arm": "top5",
                     "template": r.get("template"), "slot": r.get("slot"), "banned_set": list(LITERAL5),
                     "code": r.get("code"), "content": None, "reasoning": None, "passed": bool(r.get("passed")),
                     "label": r.get("label"), "label_other_name": None,
                     "truncated": r.get("finish_reason") == "length", "cap": None, "model": r.get("model"),
                     "runtime_label": r.get("runtime_label"), "ast_label": r.get("ast_label")})
    seen: set[tuple[str, str]] = set()
    out = []
    for r in rows:
        k = (r["config"], r["uid"])
        if k in seen:
            continue
        seen.add(k)
        r["has_code"] = bool(r.get("code"))
        r["code_sha256"] = sha256_text(r["code"]) if r.get("code") else None
        out.append(r)
    return out


def _add_lex(r: dict[str, Any]) -> None:
    import lexical

    f = lexical.flags(r.get("code"), r.get("reasoning"), r.get("banned_set") or [])
    r.update({k: f[k] for k in ("lexical_L1", "lexical_L2", "lexical_flag", "lexical_L1_hits", "lexical_L2_hits",
                                "trace_alias_hits", "bidirectional_matches")})


def _add_trace(r: dict[str, Any], t: dict[str, Any]) -> None:
    r.update({"order_class": t.get("order_class"), "order_class_fine": t.get("order_class_fine"),
              "fifo_flag": t.get("fifo_flag"), "ds_signature": t.get("ds_signature"),
              "trace_reason": t.get("reason"), "trace_rule": t.get("rule"),
              "trace_stats": {k: t.get(k) for k in ("n_informative", "id_share", "bidir_share", "p_mono",
                                                     "level_cover", "rho_h_median", "c_f", "c_h", "p_lifo", "fifo",
                                                     "jump_share", "revisit_share", "raster_share_median")}})
    if not r.get("has_code"):
        r.update({"order_class": "UNTRACEABLE", "order_class_fine": "UNTRACEABLE", "trace_reason": "no code"})


def stage_retrace(extras: str = "", *_: str) -> None:
    import gate_v9

    assert commit_time("commit1b") is not None, "Stage 2 runs after commit #1b"
    t0 = time.time()
    rows = retrace_rows(include_extras=(extras == "extras"))
    logger.info(f"retrace: {len(rows)} rows, {Counter(r['config'] for r in rows)}")
    items = [(f"{r['config']}|{r['uid']}", r.get("code"), r["config"] == "C6") for r in rows if r.get("has_code")]
    res = gate_v9.trace_many(items, workers=N_WORKERS - 1)
    for r in rows:
        _add_lex(r)
        _add_trace(r, res.get(f"{r['config']}|{r['uid']}", {}))
    name = "retrace_extras" if extras == "extras" else "retrace"
    slim = [{k: v for k, v in r.items() if k not in ("content", "reasoning")} for r in rows]
    write_jsonl(RESULTS / f"{name}.jsonl", slim)
    timing(f"retrace:{name}", time.time() - t0, len(items))
    logger.info(f"retrace done: {Counter((r['config'], r['order_class']) for r in rows)}")


# ---------------------------------------------------------------------------------------------- stage 4: label new
def stage_judge_gate(*_: str) -> None:
    """Re-gate the three adjudication judges on the 10 renamed reference controls (>= 8/10 as in iteration 8)."""
    import judge_tp
    from common import ADJ_PAIR, ADJ_THIRD, CANON_ORDER

    refs = sorted((INPUTS / "exp9" / "tasks" / "t1_grid" / "references").glob("*.py"))
    import gate_v9

    by_cls: dict[str, str] = {}
    for p in refs:
        cls = gate_v9.ref_alg(p.stem)
        by_cls.setdefault(cls, p.read_text())
    controls = [(cls, judge_tp.rename_identifiers(by_cls[cls])) for cls in CANON_ORDER]
    out = {"utc": utc_now(), "threshold": 8, "judges": {}}
    for m in list(ADJ_PAIR) + [ADJ_THIRD]:
        res = judge_tp.judge_codes([c for _, c in controls], m, purpose="gate_v9")
        per = [{"class": cls, "label": (r or {}).get("label"), "ok": (r or {}).get("label") == cls}
               for (cls, _), r in zip(controls, res)]
        sc = sum(p["ok"] for p in per)
        out["judges"][m] = {"score": sc, "passed": sc >= 8, "per_control": per}
        logger.info(f"judge gate v9 {m}: {sc}/10")
    write_json(RESULTS / "judge_gate_v9.json", out)


def stage_label(*cell_args: str) -> None:
    """Name-level labelling (iteration-8 pipeline) + lexical flags + tracing of the named cells' new rows."""
    import adjudicate
    import cells_v9
    import gate_v9
    import label_tp

    t1b = commit_time("commit1b")
    assert t1b is not None, "new rows are labelled and traced only after commit #1b"
    want = []
    for a in cell_args:
        want += [cid for cid, c in cells_v9.CELLS.items() if c["group"] == a] if a in cells_v9.RUN_ORDER else [a]
    for cid in want:
        raw = read_jsonl(DATA / f"raw_{cid}.jsonl")
        if not raw:
            logger.warning(f"{cid}: no raw rows")
            continue
        cell = cells_v9.CELLS[cid]
        banned = cells_v9.banned_for(cell) or []
        gov = _governing_commit(cell)
        first_utc = min(r["utc"] for r in raw)
        assert commit_time(gov) < first_utc, f"{cid}: governing {gov} does not precede the first row"
        rows = []
        for r in sorted(raw, key=lambda x: int(x["slot"])):
            rr = dict(r)
            rr["uid"] = f"{cid}|{int(r['slot'])}"
            rows.append(rr)
        lab = label_tp.label_rows(rows, use_judge=True)
        stats = adjudicate.apply_adjudication(lab, banned if cell["kind"] != "baseline" else None, purpose=cid)
        n_other = sum(1 for r in lab if r.get("label_raw") == "other")
        if lab and n_other / len(lab) > 0.2:
            rest = [r for r in lab if r.get("code") and r.get("adj_source") == "labeller"]
            res2 = adjudicate.adjudicate_codes([r["code"] for r in rest], cid + ":other>20%")
            for r in rest:
                a = res2.get(r["code_sha256"])
                if a:
                    r.update({"adj_label": a["adj_label"], "adj_source": a["adj_source"],
                              "adj_reason": "cell_other_gt_20pct", "judge_labels": a["votes"],
                              "adj_other_name": a.get("adj_other_name"), "needs_manual": a.get("needs_manual")})
            stats["other_gt_20pct_extended"] = len(rest)
        out_rows = []
        for r in lab:
            content = r.get("content") or ""
            trunc_flag = (r.get("finish_reason") == "length") or (content.count("```") % 2 == 1) or \
                r.get("extract_method") in ("no_fence", "no_content")
            row = {"uid": r["uid"], "cell": cid, "config": cid, "group": cell["group"], "model": r.get("model"),
                   "model_key": cell["model_key"], "engine": "OpenRouter", "provider": r.get("provider"),
                   "task": "T1", "arm": r.get("arm"), "condition": cell["kind"], "k": r.get("k"),
                   "banned_set": banned, "template": r.get("template"), "slot": int(r["slot"]), "seed": r.get("seed"),
                   "prompt_sha256": r.get("prompt_sha256"), "label": r.get("adj_label"),
                   "label_source": r.get("adj_source"), "label_raw": r.get("label_raw"),
                   "label_other_name": r.get("adj_other_name"), "passed": bool(r.get("passed")),
                   "passed_exp2": bool(r.get("passed_exp2")), "truncated": bool(trunc_flag),
                   "finish_reason": r.get("finish_reason"), "n_tokens": r.get("completion_tokens"),
                   "reasoning_tokens": r.get("reasoning_tokens"), "cost": r.get("cost_usd"),
                   "code_sha256": r.get("code_sha256"), "code": r.get("code"), "has_code": bool(r.get("code")),
                   "reasoning": r.get("reasoning"), "content": r.get("content"), "source": "new", "cap": r.get("max_tokens"),
                   "needs_manual": r.get("needs_manual"), "judge_labels": r.get("judge_labels"), "utc": r.get("utc"),
                   "runtime_label": r.get("runtime_label"), "ast_label": r.get("ast_label")}
            _add_lex(row)
            out_rows.append(row)
        keep = {r["uid"] for r in out_rows if r["has_code"] and (r["k"] == 5 or r["passed"])}
        res = gate_v9.trace_many([(r["uid"], r["code"], r["uid"] in keep) for r in out_rows if r["has_code"]],
                                 workers=N_WORKERS - 1)
        for r in out_rows:
            _add_trace(r, res.get(r["uid"], {}))
        write_jsonl(DATA / f"labelled_v9_{cid}.jsonl", out_rows)
        write_json(RESULTS / f"adjudication_{cid}.json", stats)
        logger.info(f"{cid}: {len(out_rows)} rows; labels {Counter(r['label'] for r in out_rows)}; classes "
                    f"{Counter(r['order_class'] for r in out_rows)}; adjudication {stats}")


# ---------------------------------------------------------------------------------------------- commit #1b
def stage_commit1b(gate_round: str = "round0", *_: str) -> None:
    import cells_v9
    import orderclass

    assert commit_time("commit1a") is not None and commit_time("commit1b") is None
    gate = read_json(RESULTS / f"tracer_gate_{gate_round}.json")
    rows = []
    for cid, cell in cells_v9.CELLS.items():
        if cell["group"] in ("B", "C", "D"):
            rows += cells_v9.prompts_for(cid)
    write_jsonl(PRED / "prompts_v9_1b.jsonl", rows)
    ctrl = {p.name: sha256_file(p) for p in sorted((ROOT / "controls").glob("*.py"))}
    payload = {
        "label": "commit #1b (iteration 9 TP-B): tracer, probes, gate, rotated sets, descriptions, analysis code",
        "utc": utc_now(),
        "governs": "the first traced ban row (Stage 2 retrace and Stage 4 tracing of new rows) and the B, C, D "
                   "samples; F-ban is governed by commit #2 (each scale model's own top five)",
        "source_hashes": _src_hashes(["tracer_v9.py", "orderclass.py", "lexical.py", "analysis_v9.py", "stats_v9.py",
                                      "mechdist.py", "gate_v9.py", "probes_v9.py", "cells_v9.py", "stages_v9.py",
                                      "label_tp.py", "adjudicate.py", "judge_tp.py"]),
        "probes_sha256": sha256_file(ROOT / "probes" / "probes_v9.json"),
        "planted_controls_sha256": ctrl,
        "thresholds": dict(orderclass.TH), "confirm_first_k": orderclass.CONFIRM_FIRST_K,
        "decision_list": TRACER_RULES["decision_list"], "expected_reference_classes": EXPECTED_REF_CLASS,
        "mechanism_mapping": {"coarse": MECH_COARSE, "fine": MECH_FINE},
        "gate": {k: gate[k] for k in ("round", "references_ok", "references_n", "controls_ok", "controls_n",
                                      "gold_n", "gold_traceable", "gold_in_scope", "gold_agree", "gold_agreement",
                                      "unverified_classes", "passed", "passed_references", "passed_controls",
                                      "passed_gold", "one_class_fallback")},
        "gate_file_sha256": sha256_file(RESULTS / f"tracer_gate_{gate_round}.json"),
        "tracer_dev_log_sha256": sha256_file(RESULTS / "tracer_dev_log.json"),
        "gate_outcome": "FAILED after 2 revision rounds -> committed fallback: N1-N3 DESCRIPTIVE; primary mechanism "
                        "label = runtime_class (iteration-8 10-class runtime label mapped through the 1.11 coarse "
                        "table); the tracer v9 order class is the second column; N5 keeps tracer distances (flagged)",
        "primary_mechanism_label": "runtime_class",
        "gate_rounds": {r: {k: read_json(RESULTS / f"tracer_gate_{r}.json")[k] for k in ("gold_agree", "gold_in_scope",
                                                                                        "gold_agreement")}
                        for r in ("round0", "round1", "round2")},
        "unverified_class_rule": "BIDIR-heuristic (bidirectional A*) failed its reference; per the fallback it is "
                                 "excluded from the gate and every program whose name-level label is biastar is "
                                 "reported as 'unverified class'; the analysis stays inferential for the rest",
        "n5_sets_file_sha256": sha256_file(PRED / "n5_sets.json"),
        "n5_sets": read_json(PRED / "n5_sets.json")["sets"],
        "n3d_descriptions_file_sha256": sha256_file(PRED / "n3d_descriptions.json"),
        "n3d_descriptions": read_json(PRED / "n3d_descriptions.json")["descriptions"],
        "prompts_file": "predictions/prompts_v9_1b.jsonl", "prompts_file_sha256": sha256_file(PRED / "prompts_v9_1b.jsonl"),
        "prompt_sha256_by_cell": {cid: sorted({r["prompt_sha256"] for r in rows if r["cell"] == cid})
                                  for cid in sorted({r["cell"] for r in rows})},
        "cells": {cid: c for cid, c in cells_v9.CELLS.items() if c["group"] in ("B", "C", "D", "F")},
        "analysis_plan": {"N1": "analysis_v9.n1", "N2": "analysis_v9.n2", "N3": "analysis_v9.n3 (JT 100,000 "
                          "permutations, seed 0; Cochran-Armitage beside)", "N3-D": "analysis_v9.n3d",
                          "N5": "analysis_v9.n5 (exact algorithm-level permutation; binomial sign test)",
                          "survivors": "name-level vs mechanism-level, never mixed",
                          "manual_reads": "every k=5 and held-out survivor (Qwen3-32B, Qwen3-14B); every survivor "
                                          "whose name-level label and order class disagree beyond the 1.11 mapping; "
                                          "a 10% random sample (seed 0) of the other survivors"},
        "predictions_ref": "predictions/commit1a.json -> predictions (unchanged)",
        "stats_self_test": __import__("stats_v9").self_test(),
    }
    write_json(PRED / "commit1b.json", payload)
    commit(PRED / "commit1b.json", "commit1b", "tracer v9 + gate + N5 sets + N3-D descriptions + analysis code")
    ok, problems, _ = verify_chain()
    assert ok, problems
    logger.info(f"commit #1b made; chain ok; gate passed={gate['passed']} unverified={gate['unverified_classes']}")


# ---------------------------------------------------------------------------------------------- commit #2 (scale)
def stage_commit2(*_: str) -> None:
    """Each scale model's own top five from its labelled baseline (filled from iteration 8's FILL_ORDER), rendered
    ban prompts hashed, before any F-ban sample."""
    import cells_v9
    from common import FILL_ORDER

    out: dict[str, Any] = {"utc": utc_now(), "rule": "top five by implemented (adjudicated) count, ties and gaps "
                                                      "filled from FILL_ORDER (iteration 8)", "scale_top5": {},
                           "baseline_composition": {}}
    for cid in [c for c, v in cells_v9.CELLS.items() if v["kind"] == "baseline"]:
        rows = read_jsonl(DATA / f"labelled_v9_{cid}.jsonl")
        cnt = Counter(r["label"] for r in rows if r.get("label") not in (None, "invalid", "other"))
        top = [a for a, _ in sorted(cnt.items(), key=lambda kv: (-kv[1], FILL_ORDER.index(kv[0])
                                                                 if kv[0] in FILL_ORDER else 99))][:5]
        for a in FILL_ORDER:
            if len(top) >= 5:
                break
            if a not in top:
                top.append(a)
        out["scale_top5"][cid] = top
        out["baseline_composition"][cid] = dict(Counter(r["label"] for r in rows))
    write_json(PRED / "commit2.json", out)
    rows = []
    for cid, cell in cells_v9.CELLS.items():
        if cell["kind"] == "ban_top5":
            rows += cells_v9.prompts_for(cid)
    write_jsonl(PRED / "prompts_v9_2.jsonl", rows)
    out["prompt_sha256_by_cell"] = {cid: sorted({r["prompt_sha256"] for r in rows if r["cell"] == cid})
                                    for cid in sorted({r["cell"] for r in rows})}
    write_json(PRED / "commit2.json", out)
    commit(PRED / "commit2.json", "commit2", "scale models: own top five from the labelled baselines")
    ok, problems, _ = verify_chain()
    assert ok, problems


# ---------------------------------------------------------------------------------------------- stage 5: analyses
def _new_rows(cid: str) -> list[dict[str, Any]]:
    return read_jsonl(DATA / f"labelled_v9_{cid}.jsonl")


def stage_analyse(*_: str) -> None:
    import analysis_v9 as A
    import mechdist
    from common import LITERAL5

    out: dict[str, Any] = {"utc": utc_now()}
    gate = read_json(RESULTS / "tracer_gate_final.json")
    primary = "order_class" if gate.get("passed") else "runtime_class"
    out["gate_passed"] = bool(gate.get("passed"))
    out["primary_mechanism_label"] = primary
    out["status_N1_N3"] = "inferential" if gate.get("passed") else "DESCRIPTIVE (tracer gate failed; fallback label)"
    for mf in [primary] + [m for m in ("runtime_class", "order_class") if m != primary]:
        A.MECH_FIELD = mf
        suffix = "" if mf == primary else ("_tracer" if mf == "order_class" else "_runtime")
        out[f"mech_field{suffix or '_primary'}"] = mf
        _analyse_mech(A, out, suffix)
    A.MECH_FIELD = primary
    _analyse_n5_scale(A, out)
    _k_curve_qwen8b(A, out)
    write_json(RESULTS / "headlines.json", out)
    logger.info(json.dumps(out, default=str)[:4000])


def _analyse_mech(A: Any, out: dict[str, Any], suffix: str) -> None:
    from common import LITERAL5

    # ---- N1 (retrace)
    ret = read_jsonl(RESULTS / "retrace.jsonl")
    order = ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"]
    by_cfg = {c: [r for r in ret if r["config"] == c] for c in order if any(r["config"] == c for r in ret)}
    n1 = A.n1(by_cfg)
    n1["mech_field"] = A.MECH_FIELD
    n1["C6_split"] = {arm: A.table2x2([r for r in by_cfg.get("C6", []) if r["arm"] == arm], list(LITERAL5))
                      for arm in ("ban", "confirm")}
    write_json(RESULTS / f"n1{suffix}.json", n1)
    out[f"N1{suffix}"] = {k: n1[k] for k in ("pooled_equal_weight", "pooled_bootstrap95", "pooled_program_weighted",
                                             "n_positive", "n_configs", "verdict")}
    # ---- N2
    surv = []
    for r in by_cfg.get("C6", []):
        if A.named_survivor(r, LITERAL5):
            surv.append({**r, "source": f"iter8:{r['arm']}"})
    for cid in ("A_k5", "A_k5_ho"):
        for r in _new_rows(cid):
            if A.named_survivor(r, LITERAL5):
                surv.append({**r, "source": f"new:{cid}"})
    n2 = A.n2(surv)
    write_json(RESULTS / f"n2{suffix}.json", n2)
    out[f"N2{suffix}"] = {k: n2[k] for k in ("n_survivors", "n_traceable", "a_all", "b_not_bfs_by_definition",
                                             "adj_coarse", "adj_fine", "verdict", "exceeds_null")}
    # ---- N3 (both models)
    n3 = {}
    for mk, pre in (("q32", "A"), ("q14", "E")):
        cells = {k: _new_rows(f"{pre}_k{k}") for k in range(1, 6)}
        if not any(cells.values()):
            continue
        ho = _new_rows(f"{pre}_k5_ho")
        n3[mk] = A.n3(cells, ho or None)
    write_json(RESULTS / f"n3{suffix}.json", n3)
    out[f"N3{suffix}"] = {mk: {"verdict": v["verdict"], "criteria": v["criteria"],
                               "jt_p": v["jt_mech_coarse"].get("p_mc"), "ca_p": v["ca_mech_coarse"].get("p_one_sided")}
                          for mk, v in n3.items()}
    # ---- N3-D
    if _new_rows("C_desc"):
        n3d = A.n3d(_new_rows("C_desc"), _new_rows("A_k5"))
        write_json(RESULTS / f"n3d{suffix}.json", n3d)
        out[f"N3-D{suffix}"] = {k: n3d[k] for k in ("mech_rises", "violation_rises", "diffs")}


def _analyse_n5_scale(A: Any, out: dict[str, Any]) -> None:
    from common import LITERAL5
    import mechdist  # noqa: F401

    # ---- N5
    sets = read_json(PRED / "n5_sets.json")
    ref_traces = read_json(RESULTS / "reference_traces.json")
    set_rows = {"literal": (list(LITERAL5), _new_rows("A_k5"))}
    for R, cid in (("R1", "B_R1"), ("R2", "B_R2"), ("R3", "B_R3"), ("R4", "B_R4"), ("R5", "D_R5"), ("R6", "D_R6")):
        rows = _new_rows(cid)
        if rows:
            set_rows[R] = (sets["sets"][R]["set"], rows)
    # program traces (with expansion sequences) of every name-level survivor
    import gate_v9

    need = {}
    for R, (Sset, rows) in set_rows.items():
        for r in rows:
            if A.named_survivor(r, Sset) and r.get("code"):
                need[r["code_sha256"]] = r["code"]
    tr = gate_v9.trace_many([(k, c, True) for k, c in need.items()], workers=N_WORKERS - 1)
    n5 = A.n5(set_rows, sets["D_mech"], ref_traces, tr)
    write_json(RESULTS / "n5.json", n5)
    out["N5"] = {k: n5[k] for k in ("n_defined", "n_joint", "binom_p_joint", "n_dm_neg", "n_dn_pos", "verdict")}
    # ---- scale
    sc = {}
    for base, ban in (("F_gptoss_base", "F_gptoss_ban"),):
        b, n = _new_rows(base), _new_rows(ban)
        if not b:
            continue
        top = read_json(PRED / "commit2.json")["scale_top5"].get(base) if (PRED / "commit2.json").exists() else None
        sc[base] = {"baseline_composition": dict(Counter(r.get("label") for r in b)),
                    "baseline_order_classes": dict(Counter(r.get("order_class") for r in b)),
                    "baseline_pass_rate": sum(r["passed"] for r in b) / len(b), "top5": top}
        if n and top:
            cs = A.cell_summary(n, top)
            sc[base]["ban"] = cs
    write_json(RESULTS / "scale.json", sc)
    out["scale"] = {k: {kk: (vv if kk != "ban" else {x: vv[x] for x in ("n", "lex_L1_completed",
                                                                          "mech_coarse_traceable", "named_survivors",
                                                                          "mech_survivors", "pass_rate")})
                        for kk, vv in v.items()} for k, v in sc.items()}


# ---------------------------------------------------------------------------------------------- novelty, figures, outputs
def stage_novelty(*_: str) -> None:
    import cells_v9
    import novelty

    reads = {r["uid"]: r for r in read_jsonl(DATA / "manual_reads_v9.jsonl")}
    rows_by = {}
    for cid in cells_v9.CELLS:
        rows = _new_rows(cid)
        for r in rows:
            r["adj_label"] = r.get("label")
            r["adj_other_name"] = r.get("label_other_name")
            r["manual_flag"] = bool(reads.get(r["uid"], {}).get("flag_novelty"))
        if rows:
            rows_by[cid] = rows
    out = novelty.audit(rows_by)
    logger.info(f"novelty: {out['n_candidates']} candidates, {out['n_novel']} novel; {out['claim']}")


def stage_figures(*_: str) -> None:
    import figures_v9 as F
    import orderclass

    for fn in (F.f1_forest, F.f2_mosaics, F.f3_k_curves, F.f4_n2, F.f5_n5, F.f8_reads):
        try:
            fn()
        except (FileNotFoundError, KeyError, ValueError, TypeError) as e:
            logger.error(f"{fn.__name__} failed: {type(e).__name__}: {e}")
    for g in ("tracer_gate_round0.json", "tracer_gate_round2.json"):
        try:
            F.f7_gate(g)
        except (FileNotFoundError, KeyError, ValueError) as e:
            logger.error(f"f7 {g} failed: {e}")
    # F6: actual traced expansion orders for references and survivors
    ref = read_json(RESULTS / "reference_traces.json")
    ex = [("BFS reference", ref["bfs_deque_parent"]), ("unit Dijkstra ref.", ref["dijkstra_lazy"]),
          ("DFS reference", ref["dfs_stack"]), ("A* reference", ref["astar_fg"])]
    import gate_v9

    surv = read_json(RESULTS / "n2.json")["per_survivor"] if (RESULTS / "n2.json").exists() else []
    picks = []
    for want in ("BFS", "OTHER"):
        for s in surv:
            if s.get("tracer_class") == want and s["uid"] not in [p[0] for p in picks]:
                picks.append((s["uid"], f"survivor: {s.get('other_name') or s.get('label')}"[:24]))
                break
    if picks:
        allrows = {r["uid"]: r for r in read_jsonl(RESULTS / "retrace.jsonl")}
        for cid in ("A_k5", "A_k5_ho"):
            for r in _new_rows(cid):
                allrows[r["uid"]] = r
        items = [(u, (allrows.get(u) or {}).get("code") or _code_of(u), True) for u, _ in picks]
        tr = gate_v9.trace_many([i for i in items if i[1]], workers=2)
        for u, title in picks:
            if u in tr:
                ex.append((title, tr[u]))
    pid = {p["name"]: p["i"] for p in [{"name": q["name"], "i": i} for i, q in enumerate(orderclass.probes())]}
    F.f6_traces(ex, [pid["P39"], pid["P09"], pid["P17"]])


def _code_of(uid: str) -> str | None:
    for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"):
        for arm in ("ban", "confirm"):
            for r in read_jsonl(INPUTS / f"iter8/data/labelled_{c}_{arm}.jsonl"):
                if r["uid"] == uid:
                    return r.get("code")
    return None


def stage_outputs(*_: str) -> None:
    import outputs_v9

    outputs_v9.write()
    logger.info("method_out.json written")


# ---------------------------------------------------------------------------------------------- post-hoc bounds
def stage_bounds(*_: str) -> None:
    """POST-HOC (not pre-registered) instrument-agreement bounds: a program is mechanistically compliant under BOTH
    labels (lower bound of mechanistic compliance) or under EITHER label (upper bound). Neither instrument passed the
    full committed gate (tracer: gold 0.70; fallback runtime label: planted controls 6/9), so the bounds show how far
    each headline depends on the instrument."""
    import analysis_v9 as A
    from common import K_ORDER, LITERAL5

    def comp(r: dict[str, Any], banned: list[str]) -> tuple[bool | None, bool | None]:
        if not r.get("has_code"):
            return None, None
        A.MECH_FIELD = "runtime_class"
        a = A.mech_ok(r, banned) if A.traceable(r) else None
        A.MECH_FIELD = "order_class"
        b = A.mech_ok(r, banned) if A.traceable(r) else None
        A.MECH_FIELD = "runtime_class"
        return a, b

    def bounds(rows: list[dict[str, Any]], banned: list[str], completed_only: bool = False) -> dict[str, Any]:
        lo = hi = n = lex = agree = 0
        for r in rows:
            if not r.get("has_code") or (completed_only and r.get("truncated")):
                continue
            a, b = comp(r, banned)
            if a is None or b is None:
                continue
            n += 1
            lex += int(bool(r.get("lexical_L1")))
            lo += int(a and b)
            hi += int(a or b)
            agree += int(a == b)
        return {"n_both_traceable": n, "lex": lex / n if n else None, "mech_lower_both": lo / n if n else None,
                "mech_upper_either": hi / n if n else None, "instrument_agreement": agree / n if n else None,
                "gap_upper": (lex - lo) / n if n else None, "gap_lower": (lex - hi) / n if n else None}

    out: dict[str, Any] = {"note": stage_bounds.__doc__}
    ret = read_jsonl(RESULTS / "retrace.jsonl")
    out["N1"] = {c: bounds([r for r in ret if r["config"] == c], list(LITERAL5))
                 for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10")}
    g = [v["gap_lower"] for v in out["N1"].values() if v["gap_lower"] is not None]
    gu = [v["gap_upper"] for v in out["N1"].values() if v["gap_upper"] is not None]
    out["N1_pooled_gap_lower"] = sum(g) / len(g) if g else None
    out["N1_pooled_gap_upper"] = sum(gu) / len(gu) if gu else None
    for pre, mk in (("A", "q32"), ("E", "q14")):
        out[f"N3_{mk}"] = {k: bounds(_new_rows(f"{pre}_k{k}"), sorted(K_ORDER[:k], key=lambda x: K_ORDER.index(x)),
                                     completed_only=True) for k in range(1, 6)}
        out[f"N3_{mk}"]["5ho"] = bounds(_new_rows(f"{pre}_k5_ho"), list(LITERAL5), completed_only=True)
    # N2: survivors banned under both / either
    n2 = read_json(RESULTS / "n2.json")
    per = n2["per_survivor"]
    cb = {"BFS", "DFS", "ID", "HEUR"}
    both = sum(1 for p in per if p["runtime_class"] in cb and p["tracer_class"] in cb)
    either = sum(1 for p in per if p["runtime_class"] in cb or p["tracer_class"] in cb)
    nn = sum(1 for p in per if p["runtime_class"] != "UNTRACEABLE" and p["tracer_class"] not in (None, "UNTRACEABLE"))
    out["N2"] = {"n": nn, "banned_under_both": both, "banned_under_either": either,
                 "share_lower": both / nn if nn else None, "share_upper": either / nn if nn else None,
                 "disagreements": [p for p in per if (p["runtime_class"] in cb) != (p["tracer_class"] in cb)]}
    write_json(RESULTS / "instrument_bounds.json", out)
    logger.info(json.dumps({k: v for k, v in out.items() if k in ("N1_pooled_gap_lower", "N1_pooled_gap_upper")}))
    logger.info(json.dumps({k: v for k, v in out["N2"].items() if k != "disagreements"}))


def stage_reads_summary(*_: str) -> None:
    """Summary of the executor's manual reads; each read family is mapped to a coarse expansion class and compared
    with the name-level label, the fallback runtime label and the tracer (descriptive, post-hoc)."""
    import analysis_v9 as A

    fam_class = {"UD": "BFS", "BF": "OTHER", "FL": "OTHER", "RP": "OTHER", "RC": "OTHER", "SP": "OTHER", "CK": "OTHER",
                 "MX": "OTHER", "DFS": "DFS", "BFS": "BFS", "AS": "HEUR", "GB": "HEUR", "ID": "ID"}
    reads = read_jsonl(DATA / "manual_reads_v9.jsonl")
    rows = {}
    for cid in ("A_k5", "A_k5_ho", "E_k5", "E_k5_ho"):
        for r in _new_rows(cid):
            rows[r["uid"]] = r
    items = []
    for rd in reads:
        r = rows.get(rd["uid"])
        if not r:
            continue
        A.MECH_FIELD = "runtime_class"
        rt = A.runtime_class(r)
        items.append({"uid": rd["uid"], "family": rd.get("family"), "read_class": fam_class.get(rd.get("family"), "OTHER"),
                      "name_label": r.get("label"), "runtime_class": rt, "tracer_class": r.get("order_class"),
                      "named_survivor": A.named_survivor(r, r["banned_set"]),
                      "mech_survivor_runtime": A.mech_survivor(r, r["banned_set"])})
    cb = {"BFS", "DFS", "ID", "HEUR"}
    n = len(items)
    out = {"n": n, "by_reason": "every Qwen3-32B and Qwen3-14B k=5 and held-out survivor (name- or mechanism-level)",
           "families": dict(Counter(i["family"] for i in items)),
           "read_banned_share": sum(1 for i in items if i["read_class"] in cb) / n if n else None,
           "agreement_read_vs_runtime_class": sum(1 for i in items if (i["read_class"] in cb) == (i["runtime_class"] in cb)) / n if n else None,
           "agreement_read_vs_tracer_class": sum(1 for i in items if (i["read_class"] in cb) == (i["tracer_class"] in cb)) / n if n else None,
           "name_label_vs_read_family": dict(Counter(f"{i['name_label']}->{i['family']}" for i in items)),
           "named_survivors_read": sum(1 for i in items if i["named_survivor"]),
           "named_survivors_read_banned": sum(1 for i in items if i["named_survivor"] and i["read_class"] in cb),
           "items": items}
    write_json(RESULTS / "manual_reads_summary.json", out)
    logger.info({k: v for k, v in out.items() if k != "items"})


def stage_commit3(*_: str) -> None:
    """Amendment commit before the FINAL analysis run: records every source file changed after commit #1b, why, and
    which analyses are post-hoc (instrument bounds, manual-read summary)."""
    c1b = read_json(PRED / "commit1b.json")
    now = _src_hashes(sorted(c1b["source_hashes"]) + ["figures_v9.py", "outputs_v9.py", "manual_reads.py", "novelty.py"])
    changed = {f: {"commit1b": c1b["source_hashes"].get(f), "now": h} for f, h in now.items()
               if c1b["source_hashes"].get(f) != h}
    payload = {"label": "commit #3 (amendment, before the final analysis run)", "utc": utc_now(),
               "changed_after_commit1b": changed,
               "reasons": {"stages_v9.py": "new orchestration stages only (novelty, figures, outputs, commit3, bounds, "
                                           "reads_summary), the ADJ_PAIR import fix of the gold-judge stage, and the "
                                           "README-facing label of the read summary; no change to sampling, labelling, "
                                           "tracing or the committed analyses",
                           "gate_v9.py": "order-judge response parsing (the first run lost every answer to a 200-token "
                                         "truncation of the JSON); informational check only, the gate had already failed",
                           "figures_v9.py": "presentation only"},
               "unchanged_rule_files": [f for f in ("tracer_v9.py", "orderclass.py", "lexical.py", "analysis_v9.py",
                                                    "stats_v9.py", "mechdist.py", "cells_v9.py", "label_tp.py",
                                                    "adjudicate.py", "judge_tp.py") if f not in changed],
               "post_hoc_analyses": ["results/instrument_bounds.json (compliance under both / either mechanism label)",
                                     "results/manual_reads_summary.json (executor reads mapped to coarse classes)",
                                     "results/fallback_label_validation.json (fallback label on the gate sets)"],
               "primary_unchanged": "the committed fallback (runtime_class primary, tracer second column, N1-N3 "
                                    "descriptive) stays the primary reading"}
    write_json(PRED / "commit3.json", payload)
    commit(PRED / "commit3.json", "commit3", "amendment: post-#1b source changes + post-hoc analyses declared")
    ok, problems, _ = verify_chain()
    assert ok, problems
    logger.info(f"commit #3: {sorted(changed)}")


def stage_export(*_: str) -> None:
    """data/samples_v9.jsonl (one row per new sample, plan 4.6 fields) and data/survivors_for_tpg.jsonl (every new
    name- or mechanism-level survivor program, for placement on TP-G's frozen manifolds next round)."""
    import analysis_v9 as A
    import cells_v9

    keys = ["model", "engine", "provider", "task", "arm", "condition", "k", "banned_set", "template", "slot", "seed",
            "label", "label_source", "order_class", "order_class_fine", "fifo_flag", "ds_signature", "lexical_flag",
            "lexical_L1", "lexical_L2", "trace_alias_hits", "passed", "passed_exp2", "truncated", "n_tokens",
            "reasoning_tokens", "cost", "code_sha256", "code"]
    rows, surv = [], []
    for cid, cell in cells_v9.CELLS.items():
        for r in _new_rows(cid):
            A.MECH_FIELD = "runtime_class"
            row = {"uid": r["uid"], "cell": cid, **{k: r.get(k) for k in keys}, "runtime_label": r.get("runtime_label"),
                   "runtime_class": A.runtime_class(r), "label_other_name": r.get("label_other_name")}
            rows.append(row)
            b = r.get("banned_set") or []
            if cell["kind"] != "baseline" and (A.named_survivor(r, b) or A.mech_survivor(r, b)):
                A.MECH_FIELD = "order_class"
                surv.append({**row, "named_survivor": A.named_survivor(r, b),
                             "mech_survivor_runtime": (lambda: (setattr(A, "MECH_FIELD", "runtime_class"),
                                                                A.mech_survivor(r, b))[1])(),
                             "mech_survivor_tracer": (lambda: (setattr(A, "MECH_FIELD", "order_class"),
                                                               A.mech_survivor(r, b))[1])(),
                             "prompt_sha256": r.get("prompt_sha256")})
    A.MECH_FIELD = "runtime_class"
    write_jsonl(DATA / "samples_v9.jsonl", rows)
    write_jsonl(DATA / "survivors_for_tpg.jsonl", surv)
    logger.info(f"export: {len(rows)} samples, {len(surv)} survivors")


def _k_curve_qwen8b(A: Any, out: dict[str, Any]) -> None:
    """Plan 2.4 (descriptive): Qwen3-8B (iteration 2, thinking off) under single:bfs (k=1), multi:TOP/ARC/SCATTER
    (k=4, three different sets) and TOP5 (k=5): lexical vs mechanistic compliance under both mechanism labels."""
    p = RESULTS / "retrace_extras.jsonl"
    if not p.exists():
        return
    rows = read_jsonl(p)
    res = {}
    for cfg in ("EXP9:single:bfs", "EXP9:multi:TOP", "EXP9:multi:ARC", "EXP9:multi:SCATTER", "C9"):
        sub = [r for r in rows if r["config"] == cfg]
        if not sub:
            continue
        banned = sub[0]["banned_set"]
        ent = {"banned": banned, "k": len(banned), "n": len(sub)}
        for mf in ("runtime_class", "order_class"):
            A.MECH_FIELD = mf
            t = A.table2x2(sub, banned)
            ent[mf] = {"lex": t["lex"], "mech": t["mech"], "gap": t["gap"], "gap_newcombe95": t["gap_newcombe95"],
                       "n": t["n"]}
        res[cfg] = ent
    A.MECH_FIELD = "runtime_class"
    write_json(RESULTS / "k_curve_qwen3_8b.json", res)
    out["k_curve_qwen3_8b"] = {k: {"k": v["k"], "lex": v["runtime_class"]["lex"], "mech_runtime": v["runtime_class"]["mech"],
                                   "mech_tracer": v["order_class"]["mech"]} for k, v in res.items()}


def _heap_key_kind(code: str) -> str | None:
    """Classify the priority key of a program's heap pushes from the pushed expression (post-hoc audit; reads
    expressions, not algorithm names): goal-distance (abs(...goal...)), path cost (d + 1 / g + 1), random,
    coordinate (r + c, r*cols + c, (r, c), r**2 + c**2, r - c), counter-only, or unknown."""
    import re as _re

    pushes = [ln for ln in code.splitlines() if "heappush" in ln or "heapify" in ln or ".put(" in ln]
    if not pushes:
        return None
    body = code
    if _re.search(r"random\.(random|randint|uniform|choice)\(", " ".join(pushes)) or (
            "random" in body and _re.search(r"heappush\([^,]+,\s*\(\s*(rand|r_?key|rnd)", body)):
        return "random"
    if _re.search(r"abs\(", body) and _re.search(r"goal|target|end|gr\b|gc\b|g_r|g_c|tr\b|tc\b", body):
        return "goal-distance (heuristic)"
    joined = " ".join(pushes)
    if _re.search(r"\(\s*\w*(dist|cost|steps|d|g|curr_dist|current_dist|new_dist|nd|ng|priority|cnt|level)\w*\s*\+\s*1\b", joined) \
            or _re.search(r"new_dist|new_cost|nd\b|ng\b|dist\s*\+\s*1|cost\s*\+\s*1|steps\s*\+\s*1", joined):
        return "path cost (distance)"
    if _re.search(r"\b(nr|new_r|new_row|r|row|i|x|nx|next_r|next_row)\s*(\*\s*cols|\*\*\s*2|[+-]\s*(2\s*\*\s*)?(nc|new_c|new_col|c|col|j|y|ny|next_c|next_col))", joined) \
            or _re.search(r"heappush\(\w+,\s*\(\s*(nr|new_r|new_row|r|row|start\[0\]|start_r|start_row|x|nx)\s*,", joined) \
            or _re.search(r"priority\s*=\s*\w+\s*(\*\s*cols|[+-])", body) or _re.search(r"\(\s*\(nr, nc\)\s*,", joined):
        return "coordinate (goal-independent)"
    return "unknown"


def stage_heap_keys(*_: str) -> None:
    import cells_v9

    out: dict[str, Any] = {"note": "POST-HOC audit of heap priority keys by regex on the pushed expressions "
                                   "(_heap_key_kind); spot-checked by the executor's reads", "cells": {}}
    tot = Counter()
    for cid, cell in cells_v9.CELLS.items():
        rows = _new_rows(cid)
        c = Counter()
        for r in rows:
            if not r.get("code"):
                continue
            kk = _heap_key_kind(r["code"])
            if kk:
                c[(r.get("label"), kk)] += 1
        out["cells"][cid] = {f"{a} | {b}": v for (a, b), v in sorted(c.items())}
        tot.update(c)
    out["total"] = {f"{a} | {b}": v for (a, b), v in sorted(tot.items(), key=lambda x: -x[1])}
    lab_h = {lab: {kind: v for (l2, kind), v in tot.items() if l2 == lab} for lab in ("gbfs", "astar", "dijkstra_unit")}
    out["name_label_vs_key"] = lab_h
    write_json(RESULTS / "heap_key_audit.json", out)
    logger.info(json.dumps(lab_h))
