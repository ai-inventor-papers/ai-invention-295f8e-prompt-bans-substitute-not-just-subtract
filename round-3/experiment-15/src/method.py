#!/usr/bin/env python3
"""Where Llama goes when an algorithm is banned: second-family (Llama-3.1-8B-Instruct, bf16) replication of Claim 1
on the frozen 12-task bench.  One sub-command per stage (see README.md for the order):

  setup      Step A: provenance, sha256 checks, model record, X0 freeze, dependency inventory
  gen1       vLLM session 1: sampler test (T2) + label-independent generations B1-B5
  label      Step C: label every raw generation not yet labelled (bench labellers; judge on disagreements)
  freeze     C4/C5/C6: default D, present-minor events, association map (predictions/events.json, ...)
  hf         Step E1 + T4: HF prompt-only ban-displacement norms, random directions, hook tests
  push       vLLM session 2: E3 random-direction pushes (prefill hooks; prefix caching off)
  veto       vLLM session 3a: forced round 2, n-grams (D1), vetoes D2-D4, screen B6
  commit     Step F: forecasts, smoothing, hash-chained commitment, grep audit
  ban        vLLM session 3b: G1/G2 bans (+ G3 exposure if budget remains)
  analyse    Step H: C1 scoring, sensitivities, descriptive analyses, method_out.json
  assoc      C6/C7: association map (lexicon + judge) and the forced summary (round-2 trigger)
  proximity  PROXIMITY nominations (Zhang-Shasha on identifier-normalised ASTs)
  screen     B6/D4/H6 path-task screen (descriptive, never pooled)
(H9 audit: audit/rederive.py)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from loguru import logger  # noqa: E402

from src.ws import DATA as DATA_DIR, RESULTS, set_ram_limit, setup_logging, write_json  # noqa: E402


def cmd_setup(args) -> None:
    from src.setup_inputs import run
    run()


def _sampler_test(llm) -> dict:
    """T2: explicit params logged; T=1.0 vs a deliberate T=0.6 run at identical seeds must differ."""
    from src import prompts_llama as P
    from src.engine_vllm import effective_params, generate, sampling
    from src.jobs import x0

    p = P.p_twin("T04", x0()["T04"], 1, 0)
    reqs = [{"prompt_ids": p["ids"], "max_tokens": 48, "seed": 1000 + i} for i in range(20)]
    a = generate(llm, reqs)
    b = generate(llm, reqs)
    from vllm import SamplingParams
    from vllm.inputs import TokensPrompt
    sps = [SamplingParams(n=1, temperature=0.6, top_p=0.9, top_k=-1, max_tokens=48, seed=1000 + i,
                          stop_token_ids=[128001, 128008, 128009]) for i in range(20)]
    c = llm.generate([TokensPrompt(prompt_token_ids=p["ids"]) for _ in range(20)], sps, use_tqdm=False)
    c_ids = [list(o.outputs[0].token_ids) for o in c]
    same_rerun = sum(x["out_ids"] == y["out_ids"] for x, y in zip(a, b))
    same_t06 = sum(x["out_ids"] == y for x, y in zip(a, c_ids))
    eff = effective_params(sampling(1024, 1))
    res = {"effective_params": eff, "n": 20, "identical_on_rerun_same_seed": same_rerun,
           "identical_T1_vs_T0.6_same_seed": same_t06,
           "passed": eff["temperature"] == 1.0 and eff["top_p"] == 1.0 and eff["top_k"] in (-1, 0) and same_t06 < 20}
    write_json(RESULTS / "tests_sampler.json", res)
    logger.info(f"T2 sampler test: {res}")
    return res


def cmd_gen1(args) -> None:
    from src.engine_vllm import make_llm
    from src import jobs as J

    llm = make_llm(prefix_caching=True)
    try:
        cc = llm.llm_engine.vllm_config.cache_config
        kv = {"num_gpu_blocks": cc.num_gpu_blocks, "block_size": cc.block_size,
              "kv_tokens": (cc.num_gpu_blocks or 0) * cc.block_size}
    except AttributeError as e:
        kv = {"error": str(e)}
    write_json(RESULTS / "kv_cache_session1.json", kv)
    logger.info(f"KV cache: {kv}")
    _sampler_test(llm)
    only = set(args.phases.split(",")) if args.phases else None
    plan = [("B1", lambda: J.reqs_twin_family("B1", "neutral_baseline")),
            ("B4", lambda: J.reqs_twin_family("B4", "vetofree")),
            ("B3r1", lambda: J.reqs_forced(list(range(10)), 2, "r1")),
            ("B2", lambda: J.reqs_association()),
            ("B5", lambda: J.reqs_nonce_novelty())]
    for name, fn in plan:
        if only and name not in only:
            continue
        t0 = time.time()
        J.run_staged(llm, fn(), name)
        logger.info(f"{name} done in {time.time() - t0:.0f}s")


def cmd_label(args) -> None:
    """Label every raw generation (and the exp11 FP8 pilot) not yet labelled; then combine with the judge."""
    from src import label as L
    from src.jobs import raw_rows

    phases = set(args.phases.split(",")) if args.phases else None
    rows = L.pilot_rows() + raw_rows()
    rows = [r for r in rows if phases is None or r["phase"] in phases]
    if args.limit:
        rows = rows[: args.limit]
    L.label_rows(rows, workers=args.workers)
    if not args.no_judge:
        raw_by_id = {r["row_id"]: r for r in L.pilot_rows() + raw_rows()}
        L.combine(raw_by_id)
        logger.info(f"judge spend total ${L.judge_spend():.4f}")


def _labels_now(judge: bool = True) -> list[dict]:
    from src import label as L
    from src.jobs import raw_rows

    raw_by_id = {r["row_id"]: r for r in L.pilot_rows() + raw_rows()}
    return L.combine(raw_by_id, judge_ok=judge)


def cmd_freeze(args) -> None:
    """C4/C5: decision set, D, present-minor events (needs labels of pilot, B1, B4); association later (commit)."""
    from src import freeze as F

    labels = _labels_now()
    F.run(labels, assoc=[])


def cmd_hf(args) -> None:
    """E1/E2 + T4 (HF part): ban-displacement norms for D (prompt-only), random directions, hook tests."""
    from src.engine_hf import run
    from src.ws import PRED, read_json

    ev = read_json(PRED / "events.json")
    D = {t: v["D"] for t, v in ev["tasks"].items()}
    x0 = read_json(PRED / "x0.json")["x0"]
    run(D, x0)


def cmd_push(args) -> None:
    """E3: random-direction pushes at the spec positions of layers 11-21 (prefill only), X0-family twin prompts."""
    import numpy as np
    import torch
    from src import jobs as J
    from src import prompts_llama as P
    from src.engine_hf import directions
    from src.engine_vllm import PushHooks, generate, make_llm
    from src.ws import PRED, PUSH_LAYERS, RANDDIR_SEEDS, read_json, request_seed

    norms = read_json(RESULTS / "ban_norms.json")
    x0 = read_json(PRED / "x0.json")["x0"]
    seeds = RANDDIR_SEEDS[: (args.limit or len(RANDDIR_SEEDS))]
    llm = make_llm(prefix_caching=False)
    # C7 forced round 2 (hooks not yet installed): modes with < 5 correct-and-adherent round-1 programs
    fs = read_json(RESULTS / "forced_summary.json")
    need: dict = {}
    for v in fs.values():
        if v["needs_round2"]:
            need.setdefault(v["task"], []).append(v["mode"])
    if need and not args.phases:
        r2 = J.reqs_forced([-1], 10, "r2", modes_only=need) + J.reqs_forced(list(range(10)), 1, "r2", modes_only=need,
                                                                               start=2)
        J.run_staged(llm, r2, "B3r2")
    hooks = PushHooks(llm, PUSH_LAYERS)
    tasks = list(norms["tasks"].keys())

    def registry(scale: float) -> dict:
        reg = {}
        for t in tasks:
            nt = torch.tensor(np.array(norms["tasks"][t]["norms"]) * scale, dtype=torch.float32, device="cuda")
            for w in range(1, 6):
                for h in (0, 1):
                    p = P.p_twin(t, x0[t], w, h)
                    S = p["spec_end"] - p["spec_start"] + 1
                    assert S == nt.shape[1], (t, w, h, S, nt.shape)
                    reg[tuple(p["ids"])] = {"spec_start": p["spec_start"], "norms": nt, "norms_dev": nt, "task": t}
        return reg

    # T4 (vLLM part): zero-norm direction == hook-free run at the same seeds; perturbed-token accounting
    p = P.p_twin("T04", x0["T04"], 1, 0)
    reqs = [{"prompt_ids": p["ids"], "max_tokens": 64, "seed": 777 + i} for i in range(10)]
    hooks.set({}, None)
    a = generate(llm, reqs)
    hooks.set(registry(0.0), directions(seeds[0]).to("cuda"))
    hooks.stats.update(steps=0, perturbed_tokens=0)
    b = generate(llm, reqs)
    S = p["spec_end"] - p["spec_start"] + 1
    t4 = {"zero_norm_identical": sum(x["out_ids"] == y["out_ids"] for x, y in zip(a, b)), "n": 10,
          "perturbed_tokens": hooks.stats["perturbed_tokens"], "expected_perturbed_tokens": 10 * S * 1}
    hooks.set(registry(1.0), directions(seeds[0]).to("cuda"))
    hooks.stats.update(steps=0, perturbed_tokens=0, added_norm_sum=0.0, target_norm_sum=0.0)
    c = generate(llm, reqs)
    t4["perturbed_tokens_real"] = hooks.stats["perturbed_tokens"]
    t4["added_over_target_l21"] = hooks.stats["added_norm_sum"] / max(hooks.stats["target_norm_sum"], 1e-9)
    t4["differs_from_unperturbed"] = sum(x["out_ids"] != y["out_ids"] for x, y in zip(a, c))
    t4["passed"] = (t4["zero_norm_identical"] >= 9 and t4["perturbed_tokens"] == t4["expected_perturbed_tokens"]
                    and abs(t4["added_over_target_l21"] - 1) < 0.02)
    write_json(RESULTS / "tests_hooks_vllm.json", t4)
    logger.info(f"T4 vLLM hook test: {t4}")
    for k, sd in enumerate(seeds):
        hooks.set(registry(1.0), directions(sd).to("cuda"))
        hooks.stats.update(steps=0, perturbed_tokens=0, added_norm_sum=0.0, target_norm_sum=0.0)
        reqs = []
        for t in tasks:
            for w in range(1, 6):
                for s in range(10):
                    h = 0 if s < 5 else 1
                    pp = P.p_twin(t, x0[t], w, h)
                    reqs.append(J._req(pp, phase="E3", condition=f"randdir:s{k}", task=t, template=w, sample_id=s,
                                       h=h, mode=x0[t], extra={"randdir_seed": sd}))
        J.run_staged(llm, reqs, f"E3_s{k}")
        st = dict(hooks.stats)
        st["added_over_target_l21"] = st["added_norm_sum"] / max(st["target_norm_sum"], 1e-9)
        logger.info(f"push s{k} hook stats: {st}")
        allst = read_json(RESULTS / "push_hook_stats.json") if (RESULTS / "push_hook_stats.json").exists() else {}
        allst[f"s{k}"] = st
        write_json(RESULTS / "push_hook_stats.json", allst)
    hooks.remove()


def forced_summary(labels: list[dict]) -> dict:
    """C7: adherence and correctness per mode from forced rows (label == requested mode = adherent)."""
    import collections
    from src import prompts_llama as P
    from src.ws import FROZEN_TASKS

    out = {}
    for t in FROZEN_TASKS:
        for m in P.modes(t):
            rs = [r for r in labels if r["task"] == t and (r.get("condition") or "").startswith(f"forced:{m}:")]
            att = [r for r in rs if r["label"] != "invalid"]
            adh = [r for r in att if r["label"] == m]
            ca = [r for r in adh if r.get("passed")]
            scr = [r for r in ca if (r.get("scrub") or {}).get("verified")]
            out[f"{t}|{m}"] = {"task": t, "mode": m, "n": len(rs), "n_valid": len(att), "n_adherent": len(adh),
                               "n_correct_adherent": len(ca), "n_correct_adherent_scrub_verified": len(scr),
                               "adherence": len(adh) / max(len(att), 1),
                               "label_counts": dict(collections.Counter(r["label"] for r in rs)),
                               "can_write": len(ca) >= 1, "needs_round2": len(ca) < 5,
                               "rounds": sorted({r["phase"] for r in rs})}
    write_json(RESULTS / "forced_summary.json", out)
    return out


def cmd_assoc(args) -> None:
    """C6: map association answers (lexicon, judge for unmapped) + forced summary (C7 trigger)."""
    from src import label as L
    from src.jobs import raw_rows

    labels = _labels_now()
    fs = forced_summary(labels)
    logger.info(f"forced: {sum(1 for v in fs.values() if v['needs_round2'])} modes need round 2: "
                f"{[k for k, v in fs.items() if v['needs_round2']]}")
    rows = raw_rows({"B2"})
    if rows:
        am = L.map_association(rows)
        import collections
        logger.info(f"association: {len(am)} answers; categories {dict(collections.Counter(a['category'] for a in am))}")
    logger.info(f"judge spend total ${L.judge_spend():.4f}")


def cmd_veto(args) -> None:
    """D1-D3: n-grams and exact vetoes (vLLM session 3a, prefix caching on), labelled between rounds."""
    from src.engine_vllm import make_llm
    from src import veto_job as V

    _labels_now()  # combined labels incl. forced round 2 before n-gram selection
    llm = make_llm(prefix_caching=True)
    V.run(llm, args)


def cmd_proximity(args) -> None:
    """PROXIMITY nominations (ZS on identifier-normalised ASTs; canon token Levenshtein sensitivity)."""
    import collections
    from src import label as L
    from src import prompts_llama as P
    from src.jobs import raw_rows
    from src.ngrams import reference_code
    from src.proximity import nominate
    from src.ws import PRED, read_json, read_jsonl

    ev = read_json(PRED / "events.json")
    dec = read_json(RESULTS / "decision_sets.json")
    labels = read_jsonl(L.LABELS)
    lab_by = {r["row_id"]: r for r in labels}
    raw_by = {r["row_id"]: r for r in L.pilot_rows() + raw_rows()}
    forced = collections.defaultdict(list)
    for r in labels:
        c = r.get("condition") or ""
        if c.startswith("forced:") and r["label"] == c.split(":")[1]:
            code, _ = L.extract(raw_by[r["row_id"]]["text"])
            if code:
                forced[(r["task"], r["label"])].append(code)
    jobs = []
    for e in ev["events"]:
        t, X = e["task"], e["banned"]
        xs = []
        for rid in dec[t]["decision_row_ids"]:
            if lab_by.get(rid, {}).get("label") == X:
                code, _ = L.extract(raw_by[rid]["text"])
                if code:
                    xs.append(code)
        surv, src = {}, {}
        for j in P.modes(t):
            if j == X:
                continue
            js = forced.get((t, j), [])
            if not js:
                rc = reference_code(t, j)
                js = [rc] if rc else []
                src[j] = "bench_reference(no adherent forced program)"
            else:
                src[j] = f"forced_adherent(n={len(js)})"
            surv[j] = js
        jobs.append({"event_id": e["event_id"], "X": X, "xs": xs, "survivors": surv, "sources": src})
    res = nominate(jobs, workers=args.workers)
    write_json(PRED / "proximity.json", res)
    logger.info(f"proximity: k_used={res['k_used']} agreement={res['nomination_agreement']:.2f} "
                f"{ {k: v['nominee_zs'] for k, v in res['events'].items()} }")


def _forecast_ctx() -> dict:
    """Everything the forecasts read: decision-set labels, veto rounds, push labels, association, proximity."""
    import collections
    from src import label as L
    from src.forecasts import push_label_index
    from src.freeze import associate_targets
    from src.jobs import raw_rows
    from src.ws import PRED, read_json, read_jsonl

    labels = read_jsonl(L.LABELS)
    lab_by = {r["row_id"]: r for r in labels}
    dec = read_json(RESULTS / "decision_sets.json")
    ev = read_json(PRED / "events.json")
    ctx = {"decision_labels": {t: [lab_by[r]["label"] for r in v["decision_row_ids"] if r in lab_by]
                               for t, v in dec.items()},
           "push_labels": push_label_index(labels)}
    import os
    atf = PRED / "association_targets.json"
    if atf.exists() and not os.access(atf, os.W_OK):  # committed (read-only): never recompute after the commit
        at = read_json(atf)
    else:
        at = associate_targets(read_jsonl(L.ASSOC))
        write_json(atf, at)
    ctx["assoc_targets"] = at
    prox = read_json(PRED / "proximity.json") if (PRED / "proximity.json").exists() else {"events": {}}
    ctx["proximity"] = prox["events"]
    vs = read_json(DATA_DIR / "veto_summary.json") if (DATA_DIR / "veto_summary.json").exists() else {}
    raw_v = [r for r in raw_rows({"D2", "D3"})]
    veto = {}
    for e in ev["events"]:
        eid, X = e["event_id"], e["banned"]
        ent = {"ngrams": vs.get(eid, {}).get("ngrams"), "undefined_reason": vs.get(eid, {}).get("undefined_reason")}
        rr = [r for r in raw_v if r["event_id"] == eid]
        p1 = {}
        if e["event_type"] == "present_minor":
            p1 = {r: lab_by[r]["label"] for r in dec[e["task"]]["decision_row_ids"]}  # placeholder, replaced below
            p1 = {}
            for r in raw_rows({"B1", "B4"}):
                if r["task"] == e["task"] and r["row_id"] in lab_by:
                    p1[r["row_id"]] = lab_by[r["row_id"]]["label"]
        rounds = sorted({r["round"] for r in rr if r["arm"] == "persistent"})
        pr = []
        for k in rounds:
            sel = [r for r in rr if r["arm"] == "persistent" and r["round"] == k]
            labs = [lab_by.get(r["row_id"], {}).get("label") for r in sel]
            wts = [r["weight"] for r in sel]
            hit = [bool(r["hit"]) for r in sel]
            if e["event_type"] == "present_minor":
                hit_ids = {r["pass1_row_id"] for r in sel}
                for rid, lab in p1.items():
                    if rid not in hit_ids:
                        labs.append(lab)
                        wts.append(1.0)
                        hit.append(False)
            pr.append({"round": k, "labels": labs, "weights": wts, "hit": hit})
        ent["persistent_rounds"] = pr
        sel = [r for r in rr if r["arm"] == "oneshot" and r["round"] == 1]
        if sel:
            labs = [lab_by.get(r["row_id"], {}).get("label") for r in sel]
            wts = [r["weight"] for r in sel]
            # moved share: among pass-1 X attempts, the (weighted) fraction whose one-shot output is not X
            p1lab = {r["pass1_row_id"]: lab_by.get(r["pass1_row_id"], {}).get("label") for r in sel}
            num = sum(r["weight"] for r, l in zip(sel, labs) if p1lab.get(r["pass1_row_id"]) == X and l not in (X, None))
            den = sum(r["weight"] for r in sel if p1lab.get(r["pass1_row_id"]) == X)
            if e["event_type"] == "present_minor":
                hit_ids = {r["pass1_row_id"] for r in sel}
                for rid, lab in p1.items():
                    if rid not in hit_ids:
                        labs.append(lab)
                        wts.append(1.0)
                        if lab == X:
                            den += 1.0
            ent["oneshot"] = {"labels": labs, "weights": wts, "moved_share": (num / den if den else None)}
        veto[eid] = ent
    ctx["veto"] = veto
    return ctx


def cmd_commit(args) -> None:
    """Step F: forecasts for every event, hash-chained commitment, grep audit, predictions/ read-only."""
    import os
    import shutil
    from src import prompts_llama as P
    from src.commit import commit, utc_now
    from src.forecasts import build_event
    from src.jobs import raw_rows
    from src.ws import PRED, WS, read_json, read_jsonl

    _labels_now()
    ctx = _forecast_ctx()
    ev = read_json(PRED / "events.json")
    fcs = {e["event_id"]: build_event(e, ctx) for e in ev["events"]}
    write_json(PRED / "forecasts.json", {"utc": utc_now(), "events": fcs,
                                        "smoothing": {"f": 0.93, "uniform_S": 0.05, "other": 0.02}})
    vs = read_json(DATA_DIR / "veto_summary.json") if (DATA_DIR / "veto_summary.json").exists() else {}
    write_json(PRED / "ngrams.json", {eid: {"ngrams": v.get("ngrams"), "rounds": [
        {k: r[k] for k in ("round", "decoded", "grams", "A_share_weighted", "n_hit_rows", "surfaces", "hit_in_code_share")}
        for r in v.get("rounds", [])], "share_in_D_programs": v.get("share_in_D_programs"),
        "veto_removes_D_too": v.get("veto_removes_D_too"), "not_carried_by_surface_tokens": v.get("not_carried_by_surface_tokens"),
        "pooled_forced": v.get("pooled_forced")} for eid, v in vs.items()})
    bn = read_json(RESULTS / "ban_norms.json")
    write_json(PRED / "random_dirs.json", {"seeds": [20261020, 20261021, 20261022], "directions": bn["directions"],
                                          "layers": bn["layers"], "norm_rule": "n_{l,i} = mean_w ||h(ban_w(D)) - h(twin_w(D))||",
                                          "per_task_layer_mean": {t: v["per_layer_mean"] for t, v in bn["tasks"].items()}})
    for f in ("scoring.py", "forecasts.py"):
        shutil.copy(WS / "src" / f, PRED / f)
    # grep audit: no ban prompt of any event target was rendered before the commit
    shas = set()
    for e in ev["events"]:
        for w in range(1, 6):
            shas.add(P.p_ban(e["task"], e["banned"], w)["sha"])
    raw = raw_rows()
    hits = [r["row_id"] for r in raw if r.get("prompt_sha256") in shas or str(r.get("condition", "")).startswith("ban:")]
    audit = {"utc": utc_now(), "n_ban_prompts_checked": len(shas), "n_rows_checked": len(raw),
             "ban_prompt_rows_before_commit": len(hits), "examples": hits[:5]}
    write_json(PRED / "grep_audit_precommit.json", audit)
    assert not hits, f"ban prompt rendered before commit: {hits[:3]}"
    for f in ("association_targets.json", "proximity.json", "ngrams.json", "random_dirs.json", "forecasts.json",
              "scoring.py", "forecasts.py", "grep_audit_precommit.json"):
        if (PRED / f).exists():
            commit(PRED / f, "F3 commit before the first ban sample")
    for f in PRED.iterdir():
        os.chmod(f, 0o444)
    logger.info(f"committed {len(fcs)} event forecasts; audit {audit}")


def cmd_ban(args) -> None:
    """G1/G2 ban sampling (vLLM session 3b) after the commit."""
    from src.commit import verify
    from src import jobs as J
    from src.engine_vllm import make_llm
    from src.ws import PRED, read_json

    v = verify()
    ents = (Path(__file__).resolve().parent / "commitments.log").read_text()
    assert v["chain_ok"] and "predictions/forecasts.json" in ents, "forecasts must be committed before any ban"
    ev = read_json(PRED / "events.json")
    llm = make_llm(prefix_caching=True)
    reqs = []
    for e in ev["events"]:
        reqs += J.reqs_bans(e["task"], e["banned"], 20, phase="G1" if e["event_type"] == "modal" else "G2")
    for r in reqs:
        r["event_id"] = next(e["event_id"] for e in ev["events"] if e["task"] == r["task"] and e["banned"] == r["mode"])
    J.run_staged(llm, reqs, "G")


def cmd_analyse(args) -> None:
    """Step H: scoring, sensitivities, descriptive analyses, label audit, outputs."""
    from src import label as L
    from src import analysis as A
    from src import outputs as O
    from src.jobs import raw_rows
    from src.ws import read_json, read_jsonl

    labels = _labels_now()
    raw_by = {r["row_id"]: r for r in L.pilot_rows() + raw_rows()}
    if not (RESULTS / "llama_label_audit.json").exists():
        au = L.label_audit(raw_by, labels)
        write_json(RESULTS / "llama_label_audit.json", au)
        logger.info(f"label audit: {au['overall_agreement']:.2f} flagged {au['flagged_tasks_below_0.85']}")
    if not (RESULTS / "other_reaudit.json").exists():
        ora = L.other_reaudit(raw_by, labels)
        write_json(RESULTS / "other_reaudit.json", ora)
        logger.info(f"'other' re-audit: {ora['n']} programs; per event {ora['per_event']}")
    ctx = _forecast_ctx()
    res = A.run(labels, raw_by, ctx)
    logger.info(f"C1: {res['c1']['branch']} wins={res['c1']['wins']} gated={res['c1']['n_gated']} "
                f"disagreeing_gated={res['c1']['n_disagreeing_gated']}")
    O.shared_rows(labels, raw_by)
    meta = build_metadata(res, labels)
    O.method_out(res, labels, raw_by, meta)


def build_metadata(res: dict, labels: list[dict]) -> dict:
    import collections
    from src import label as L
    from src.commit import verify
    from src.ws import PRED, read_json

    tm = read_json(RESULTS / "timings.json") if (RESULTS / "timings.json").exists() else {}
    gpu_s = {k: round(sum(x["seconds"] for x in v), 1) for k, v in tm.items()}
    dev = read_json(RESULTS / "deviations.json") if (RESULTS / "deviations.json").exists() else {}
    return {"method_name": "Llama-3.1-8B-Instruct ban-landing replication of Claim 1 (frozen bench, 12 tasks)",
            "description": "Ban-free forecasts (SUBTRACT via exact signature vetoes, LADDER via generic pushes incl. "
                           "matched-norm random directions, ASSOCIATE, PROXIMITY) committed before sampling the bans; "
                           "scored by the frozen C1 rule.",
            "model_record": read_json(RESULTS / "model_record.json"),
            "events": read_json(PRED / "events.json"), "c1": res["c1"], "c1_point_mass": res["c1_pm"],
            "sensitivities": res["sensitivities"], "c2b_descriptive": res["c2b_descriptive"],
            "present_minor_gain": res["present_minor_gain"], "knob_view": res["knob_view"],
            "per_event": {k: {"table": v["table"], "scored": v["scored"]} for k, v in res["events"].items()},
            "label_sources": dict(collections.Counter(r.get("labeller_source") for r in labels)),
            "llama_label_audit": {k: v for k, v in read_json(RESULTS / "llama_label_audit.json").items() if k != "rows"}
            if (RESULTS / "llama_label_audit.json").exists() else None,
            "openrouter_cost_usd": L.judge_spend(), "gpu_seconds_logged_generation": gpu_s,
            "gpu_hours_logged_generation_total": round(sum(gpu_s.values()) / 3600, 3),
            "commitment_chain": verify(), "deviations": dev.get("deviations", []), "drops": dev.get("drops", []),
            "tests": {f.stem: read_json(f) for f in sorted(RESULTS.glob("tests_*.json"))},
            "veto_rounds_corrected": res.get("veto_rounds_corrected"),
            "other_reaudit": {k: v for k, v in read_json(RESULTS / "other_reaudit.json").items() if k != "rows"}
            if (RESULTS / "other_reaudit.json").exists() else None,
            "screen": read_json(RESULTS / "screen.json") if (RESULTS / "screen.json").exists() else None,
            "screen_veto": read_json(DATA_DIR / "screen_veto_summary.json")
            if (DATA_DIR / "screen_veto_summary.json").exists() else None,
            "independent_rederivation": read_json(RESULTS / "independent_rederivation.json")
            if (RESULTS / "independent_rederivation.json").exists() else None}


def cmd_screen(args) -> None:
    """B6 / D4 / H6 path-task screen (descriptive, never pooled)."""
    from src import jobs as J
    from src import screen as SCR
    from src.commit import commit
    from src.engine_vllm import make_llm
    from src.ws import PRED, read_jsonl

    K = SCR.setup()
    # T1 (screen): our copy of exp10's renderer must reproduce exp10's sampled ban prompts byte-for-byte
    ex_sha = {r.get("prompt_sha") for r in SCR.exp10_rows() if r.get("kind") == "ban"}
    chk = {f"{t}:{x}:w{w}": K.p_ban(t, x, w)["sha"] in ex_sha for t, x in SCR.EVENTS.items() for w in range(1, 6)}
    write_json(RESULTS / "tests_screen_prompts.json", {"ban_prompt_sha_matches_exp10": chk, "passed": all(chk.values())})
    logger.info(f"screen prompt identity: {sum(chk.values())}/{len(chk)}")
    llm = make_llm(prefix_caching=True)
    J.run_staged(llm, SCR.b6_requests(K), "S6", path=SCR.RAW)
    raw = read_jsonl(SCR.RAW)
    labels = SCR.label([r for r in raw if r["condition"] in ("nonce", "novelty", "screen_vetofree")])
    SCR.veto_rounds(llm, K, labels)
    labels = read_jsonl(SCR.LAB)
    fcs = SCR.forecasts(K, labels)
    commit(PRED / "screen_forecasts.json", "screen forecasts (descriptive; exp10 landings sampled in iteration 2)")
    SCR.score(fcs)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup")
    g = sub.add_parser("gen1")
    g.add_argument("--phases", default="")
    for name in ("label", "freeze", "assoc", "hf", "push", "veto", "proximity", "commit", "ban", "analyse", "audit", "screen"):
        s = sub.add_parser(name)
        s.add_argument("--phases", default="")
        s.add_argument("--workers", type=int, default=4)
        s.add_argument("--limit", type=int, default=0)
        s.add_argument("--no_judge", action="store_true")
    args = ap.parse_args()
    setup_logging(f"method_{args.cmd}")
    if args.cmd not in ("gen1", "hf", "push", "veto", "ban", "screen"):
        set_ram_limit(24)  # CPU stages only: RLIMIT_AS breaks CUDA/UVM reservations and safetensors mmap
    fn = globals().get(f"cmd_{args.cmd}")
    if fn is None:
        raise SystemExit(f"unknown command {args.cmd}")
    logger.catch(reraise=True)(fn)(args)


if __name__ == "__main__":
    main()
