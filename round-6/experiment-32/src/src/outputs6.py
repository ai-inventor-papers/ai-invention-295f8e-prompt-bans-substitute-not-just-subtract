#!/usr/bin/env python3
"""Final CPU stage: assemble units.json / landing_events.json (src/events6.py), run the FROZEN analysis code
(analysis/pool_l1.py, l2l3.py, m_k.py, hash-committed before the first nudge), write every results/*.json, the
figures, data/samples.jsonl (the per-program table) and method_out.json (exp_gen_sol_out)."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

import numpy as np  # noqa: E402
from loguru import logger  # noqa: E402

from cfg5 import (COSTS, DATA_DIR, DEVIATIONS, FIG_DIR, LABELS, PRED_DIR, RAW, REALISED, RESULTS_DIR, ROOT,  # noqa: E402
                  TIMING, VENDOR, read_json, read_jsonl, setup_logging, utc_now, write_json, write_jsonl)

PY = sys.executable


def run_frozen() -> dict[str, Any]:
    out = {}
    subprocess.run([PY, str(ROOT / "analysis" / "pool_l1.py"), "--events", str(ROOT / "landing_events.json"),
                    "--units", str(ROOT / "units.json"), "--out", str(RESULTS_DIR / "l1.json")], check=True,
                   capture_output=True, text=True)
    out["l1"] = read_json(RESULTS_DIR / "l1.json")
    subprocess.run([PY, str(ROOT / "analysis" / "l2l3.py"), "--events", str(ROOT / "landing_events.json"),
                    "--units", str(ROOT / "units.json"), "--programs",
                    str(RESULTS_DIR / "nudged_correct_S_programs.json"), "--out", str(RESULTS_DIR / "l2l3.json")],
                   check=True, capture_output=True, text=True)
    l23 = read_json(RESULTS_DIR / "l2l3.json")
    import l2l3 as _l23
    un = {u["unit_id"]: u for u in read_json(ROOT / "units.json")["units"]}
    scr_l2 = _l23.l2(read_json(RESULTS_DIR / "nudged_correct_S_programs_screen.json"), un)
    write_json(RESULTS_DIR / "l2.json", {**l23["L2"], "SCREEN (never primary)": scr_l2})
    write_json(RESULTS_DIR / "l3.json", {"L3": l23["L3"], "kendall_base_vs_tail": l23["kendall_base_vs_tail"],
                                         "kendall_base_vs_tail_screen": l23["kendall_base_vs_tail_screen"]})
    out["l2l3"] = l23
    settings = k_settings()
    write_json(RESULTS_DIR / "k_settings.json", settings)
    subprocess.run([PY, str(ROOT / "analysis" / "m_k.py"), "--units", str(ROOT / "units.json"), "--signs",
                    str(PRED_DIR / "m_signs.json"), "--settings", str(RESULTS_DIR / "k_settings.json"),
                    "--hull-dir", str(VENDOR / "exp27" / "src"), "--out", str(RESULTS_DIR / "m_k.json")],
                   check=True, capture_output=True, text=True)
    mk = read_json(RESULTS_DIR / "m_k.json")
    write_json(RESULTS_DIR / "m.json", mk["M"])
    write_json(RESULTS_DIR / "k.json", mk["K"])
    out["mk"] = mk
    return out


def k_settings() -> dict[str, Any]:
    from labels6 import all_final
    units = read_json(ROOT / "units.json")["units"]
    out = {}
    for u in units:
        if u["unit_kind"] != "new_unit" or u["status"] != "enrolled":
            continue
        rows = all_final({u["unit_id"]})
        st = {}
        tw = [r for r in rows if r["arm"] == "TWIN" and r["model_tag"] == "instruct"]
        st["TWIN"] = {"pass": sum(r["passed"] for r in tw) / len(tw), "n": len(tw),
                      "correct_labels": [r["label"] for r in tw if r["passed"]]}
        for arm in ("BINT", "PN_a2.0", "PN_a4.0"):
            rr = [r for r in rows if r["arm"] == arm]
            if rr:
                st[arm] = {"pass": sum(r["passed"] for r in rr) / len(rr), "n": len(rr),
                           "correct_labels": [r["label"] for r in rr if r["passed"]]}
        out[u["unit_id"]] = st
    return out


def samples_table() -> int:
    """data/samples.jsonl: one row per program with the plan's row schema (code included)."""
    from labels6 import all_final
    rawm = {}
    for r in read_jsonl(RAW):
        k = f"{r['unit']}|{r['template']}|{r['arm']}|{r['slot']}|{r['model_tag']}"
        rawm[k] = r
    rows = []
    for f in all_final():
        r = rawm.get(f["key"], {})
        rows.append({"key": f["key"], "model": r.get("model"), "model_tag": f["model_tag"], "unit": f["unit"],
                     "unit_kind": "new_unit" if f["unit"].startswith("II") else "iter5_screen", "arm": f["arm"],
                     "family": f.get("family"), "site": r.get("site"), "precision": r.get("precision"),
                     "lambda": None, "alpha": f.get("alpha"), "direction_seed": f.get("direction_seed"),
                     "template": f["template"], "slot": f["slot"], "temperature": f.get("temperature"),
                     "thinking": False, "prompt_sha256": f.get("prompt_sha256"), "label": f.get("label"),
                     "labeller_source": f.get("label_source"), "passed": f.get("passed"),
                     "finish_reason": f.get("finish_reason"), "n_new_tokens": f.get("n_tokens"),
                     "realised_disp": r.get("rel_err_max"), "code_sha256": f.get("code_sha256"),
                     "code": f.get("code"), "engine": r.get("engine"), "kernel": r.get("kernel"),
                     "hook_sha256": r.get("hook_sha256"), "stage": f.get("stage"), "utc": f.get("utc"),
                     "assoc_answer": f.get("assoc_answer"), "intent_text": f.get("intent_text")})
    write_jsonl(DATA_DIR / "samples.jsonl", rows)
    return len(rows)


def engine_and_dose() -> tuple[dict, dict]:
    units = read_json(ROOT / "units.json")["units"]
    eng = {u["unit_id"]: {"twin_hf_vs_vllm": u.get("engine_check_twin"), "base_iter5_vs_new": u.get("base_engine_check")}
           for u in units}
    # iteration-5 B twin slots re-drawn on HF (same streams): per-slot label agreement
    try:
        old = {}
        for r in read_jsonl(VENDOR / "exp26" / "samples_B_nocode.jsonl"):
            if r["arm"] == "TWIN" and r["model_tag"] == "instruct" and r["slot"] < 10:
                old[(r["unit"], r["template"], r["slot"])] = r.get("label")
        from labels6 import all_final
        agree = defaultdict(list)
        for f in all_final({u for u, _, _ in old}):
            if f["arm"] == "TWIN" and f.get("engine") == "hf" and f["slot"] < 10:
                k = (f["unit"], f["template"], f["slot"])
                if k in old:
                    agree[f["unit"]].append(old[k] == f["label"])
        for u, v in agree.items():
            eng.setdefault(u, {})["iter5_twin_per_slot_agreement"] = {"n": len(v), "agreement": sum(v) / len(v)}
    except FileNotFoundError:
        pass
    rd = read_jsonl(REALISED)
    dose: dict[str, Any] = {}
    by = defaultdict(list)
    for r in rd:
        fam = r["arm"].split("_")[0]
        a = r["arm"].rsplit("_a", 1)[-1]
        by[(r["unit"], fam, a)].append(r)
    for (u, fam, a), rr in sorted(by.items()):
        rel = [x.get("rel_err_max") for x in rr if x.get("rel_err_max") is not None]
        tgt = [x.get("target_mean") for x in rr if x.get("target_mean") is not None]
        dR = [x.get("disp_R_norm", {}).get("23") or x.get("disp_R_norm", {}).get(23) for x in rr if x.get("disp_R_norm")]
        dpos = [x.get("disp_pos_norm_35") for x in rr if x.get("disp_pos_norm_35") is not None]
        dmean = [x.get("disp_mean") for x in rr if x.get("disp_mean") is not None]
        dose[f"{u}|{fam}|a{a}"] = {"n_prefills_or_batches": len(rr),
                                   "rel_err_max_median": float(np.median(rel)) if rel else None,
                                   "rel_err_max_max": float(np.max(rel)) if rel else None,
                                   "target_norm_mean": float(np.mean(tgt)) if tgt else None,
                                   "disp_read_position_block23_mean": float(np.mean([x for x in dR if x])) if dR else None,
                                   "disp_task_spec_block35_mean": float(np.mean(dpos)) if dpos else None,
                                   "gtn_disp_mean": float(np.mean(dmean)) if dmean else None}
    return eng, dose


def screen_report(l1: dict[str, Any]) -> dict[str, Any]:
    ev = read_json(ROOT / "landing_events.json")["events"]
    rows = [e for e in ev if e["set"] == "SCREEN" and e["is_event"] and e["content_free"]]
    named = []
    for e in rows:
        m = e["modal_landing"]
        named.append({"event_id": e["event_id"], "iter5_origin": e["iter5_origin"], "default": e["default"],
                      "landing": m, "counts": e["counts"], "r_u": e["r_u"], "qlik_top1": e["qlik_top1"],
                      "t_u": e["t_u"], "tail_empty": e["tail_empty"], "hit_r_u": m == e["r_u"],
                      "hit_qlik_top1": m == e["qlik_top1"], "hit_t_u": m == e["t_u"]})
    a25 = read_json(VENDOR / "exp25" / "pooled_inputs.json")["units"]
    a_rows = []
    for u in a25:
        if u["unit_id"] not in ("A1", "A2", "A3", "A4", "A5", "A7", "A8", "A9"):
            continue
        land = Counter()
        for c in u["escape"]["cells"]:
            if c.get("confirmed"):
                land.update(c.get("landing_counts") or {})
        a_rows.append({"unit": u["unit_id"], "default": u["default"], "r_u_iter5": u["base"].get("r"),
                       "iter5_confirmed_landing_counts": dict(land),
                       "twin_minority_iter5": {k: v for k, v in u["twin"]["comp_correct"].items() if k != u["default"]},
                       "note": "A units: not topped up in iteration 6 (no fresh q_tail / q_lik; logged deviation)"})
    return {"label": "SCREEN (iteration-5 units; never primary)", "events": named, "screen_only_analysis":
            l1.get("screen_only"), "screen_included_analysis": l1.get("screen_included"), "A_units_iter5": a_rows}


def figures(l1: dict[str, Any], mk: dict[str, Any]) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})
    FIG_DIR.mkdir(exist_ok=True)
    ev = [e for e in read_json(ROOT / "landing_events.json")["events"] if e["is_event"] and e["content_free"]]
    # F1: per-event landing vs forecasts
    fig, ax = plt.subplots(figsize=(7.5, 0.35 * len(ev) + 1.2))
    for i, e in enumerate(ev):
        S = [a for a in e["catalogue"] if a != e["default"]]
        tot = max(sum(e["counts"].get(a, 0) for a in S), 1)
        left = 0.0
        for j, a in enumerate(S):
            w = e["counts"].get(a, 0) / tot
            ax.barh(i, w, left=left, color=plt.cm.tab10(j % 10), edgecolor="white", height=0.7)
            if w > 0.12:
                ax.text(left + w / 2, i, a[:14], ha="center", va="center", fontsize=6, color="white")
            left += w
        marks = []
        for nm, key in (("r", "r_u"), ("q", "qlik_top1"), ("t", "t_u")):
            marks.append(f"{nm}:{'+' if e[key] and e[key] == e['modal_landing'] else '-'}")
        tag = ("TE " if e["tail_empty"] else "") + ("DC " if e["discordant"] else "")
        ax.text(1.02, i, f"{tag}{' '.join(marks)}", va="center", fontsize=6)
    ax.set_yticks(range(len(ev)))
    ax.set_yticklabels([e["event_id"] for e in ev], fontsize=6)
    ax.set_xlim(0, 1.35)
    ax.set_xlabel("share of correct off-default programs (pooled qualifying cells)")
    ax.set_title("F1. Landing composition per event; r/q/t = r_u / qlik_top1 / t_u hit (+) or miss (-); "
                 "TE tail-empty, DC discordant", fontsize=7)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"F1_landings.{ext}", dpi=200)
    plt.close(fig)
    # F2: forest plot of D_lik and D_tail
    fig, ax = plt.subplots(figsize=(6, 2.6))
    ys, labs = [], []
    k = 0
    for sub in ("E", "Ea", "Eb"):
        for riv in ("lik", "tail", "assoc", "uniform"):
            b = l1["log_scores"][sub].get(f"D_{riv}", {}).get("event", {})
            if b.get("mean") is None:
                continue
            ax.errorbar(b["mean"], k, xerr=[[b["mean"] - b["ci95"][0]], [b["ci95"][1] - b["mean"]]], fmt="o",
                        color="C0" if riv in ("lik", "tail") else "C7", ms=4, capsize=2)
            labs.append(f"{sub}: base - {riv} (n={b['n']})")
            ys.append(k)
            k += 1
    ax.axvline(0, color="k", lw=0.8)
    ax.axvline(-0.10, color="r", lw=0.8, ls="--")
    ax.set_yticks(ys)
    ax.set_yticklabels(labs, fontsize=6)
    ax.set_xlabel("mean log-score difference (nats per program), 95% bootstrap CI")
    ax.set_title("F2. Base forecast vs rivals on matched events (red: non-inferiority margin)", fontsize=7)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"F2_logscore_forest.{ext}", dpi=200)
    plt.close(fig)
    # F3: per-direction escape heatmap
    esc = read_json(RESULTS_DIR / "escape_table.json")
    units = sorted({r["unit"] for r in esc}, key=lambda x: (x[0] != "I", x))
    cols = []
    for a in (1.0, 2.0, 4.0):
        for kk in range(8):
            cols.append((a, kk))
    M = np.full((len(units), len(cols)), np.nan)
    for i, u in enumerate(units):
        cells = [r for r in esc if r["unit"] == u]
        seeds = {}
        for r in cells:
            seeds.setdefault(r["alpha"], [])
            if r["dir_seed"] not in seeds[r["alpha"]]:
                seeds[r["alpha"]].append(r["dir_seed"])
        for r in cells:
            if r["n"]:
                j = cols.index((r["alpha"], seeds[r["alpha"]].index(r["dir_seed"])))
                M[i, j] = (r["share"] or 0) - (r["twin_off"] or 0)
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(units) + 1.2))
    im = ax.imshow(M, aspect="auto", cmap="viridis", vmin=-0.1, vmax=1.0)
    for i, u in enumerate(units):
        for r in [r for r in esc if r["unit"] == u and r["confirmed"]]:
            pass
    ax.set_yticks(range(len(units)))
    ax.set_yticklabels(units, fontsize=7)
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([f"a{int(a)}d{kk}" for a, kk in cols], fontsize=5, rotation=90)
    fig.colorbar(im, ax=ax, label="correct off-default share - twin")
    ax.set_title("F3. Escape excess per direction x alpha (CONFIRMATION units; SCREEN units alpha 4)", fontsize=7)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"F3_escape_heatmap.{ext}", dpi=200)
    plt.close(fig)
    # F4: q_base vs q_tail per unit
    un = [u for u in read_json(ROOT / "units.json")["units"] if u.get("q_base")]
    fig, axes = plt.subplots(1, len(un), figsize=(1.6 * len(un) + 1, 2.4), squeeze=False)
    tau = (read_json(RESULTS_DIR / "l3.json")["kendall_base_vs_tail"]["per_unit"] |
           read_json(RESULTS_DIR / "l3.json")["kendall_base_vs_tail_screen"]["per_unit"])
    for ax, u in zip(axes[0], un):
        S = list(u["q_base"])
        x = np.arange(len(S))
        ax.bar(x - 0.2, [u["q_base"][a] for a in S], 0.4, label="q_base")
        ax.bar(x + 0.2, [u["q_tail"][a] for a in S], 0.4, label="q_tail")
        ax.set_xticks(x)
        ax.set_xticklabels([a[:8] for a in S], rotation=90, fontsize=5)
        t = tau.get(u["unit_id"])
        ax.set_title(f"{u['unit_id']} tau={t:.2f}" if t is not None else u["unit_id"], fontsize=6)
        ax.tick_params(axis="y", labelsize=5)
    axes[0][0].legend(fontsize=5)
    fig.suptitle("F4. Base vs twin-tail composition over S (Kendall tau-b)", fontsize=7)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"F4_base_vs_tail.{ext}", dpi=200)
    plt.close(fig)
    # F5: M candidates vs E_u
    M5 = mk["M"]
    cands = list(M5["candidates"])
    fig, axes = plt.subplots(1, len(cands), figsize=(2.0 * len(cands), 2.2), squeeze=False)
    for ax, c in zip(axes[0], cands):
        vals = M5["candidates"][c]["values"]
        xs = [vals[u] for u in vals if vals[u] is not None]
        ys = [M5["E_u"][u] for u in vals if vals[u] is not None]
        ax.scatter(xs, ys, s=12)
        for u in vals:
            if vals[u] is not None:
                ax.annotate(u, (vals[u], M5["E_u"][u]), fontsize=5)
        r = M5["candidates"][c]["rho"]
        ax.set_title(f"{c}\nrho={r:.2f}" if r is not None else c, fontsize=6)
        ax.tick_params(labelsize=5)
    axes[0][0].set_ylabel("E_u", fontsize=6)
    fig.suptitle("F5. M candidates vs escape fraction (new units)", fontsize=7)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"F5_m_candidates.{ext}", dpi=200)
    plt.close(fig)
    # F6: K prices (pass cost vs correct-only Hill-1)
    K = mk["K"]
    fig, ax = plt.subplots(figsize=(4.5, 3))
    for i, (u, rec) in enumerate(K.items()):
        for arm, mkr in (("BINT", "s"), ("PN_a2.0", "o"), ("PN_a4.0", "^")):
            if arm in rec:
                h = rec[arm]["hill1_correct"]["hill1"]
                ax.scatter(rec[arm]["pass_cost"], h, marker=mkr, color=plt.cm.tab10(i % 10), s=18,
                           label=f"{u} {arm}" if True else None)
        t = rec.get("TWIN_hill1_correct", {}).get("hill1")
        if t is not None:
            ax.scatter(0, t, marker="*", color=plt.cm.tab10(i % 10), s=30)
    ax.set_xlabel("pass-rate cost vs twin")
    ax.set_ylabel("correct-only Hill-1 (depth 25)")
    ax.legend(fontsize=4, ncol=2)
    ax.set_title("F6. Knob prices (star = twin)", fontsize=7)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(FIG_DIR / f"F6_k_prices.{ext}", dpi=200)
    plt.close(fig)


def method_out(res: dict[str, Any], eng: dict, dose: dict, scr: dict) -> dict[str, Any]:
    from units_spec import UNITS, spec_text
    units = read_json(ROOT / "units.json")["units"]
    events = read_json(ROOT / "landing_events.json")["events"]
    esc = read_json(RESULTS_DIR / "escape_table.json")
    ds_units = []
    for u in units:
        lands = {e["nudge"]: e["modal_landing"] for e in events if e["unit_id"] == u["unit_id"]
                 and not e["iter5_origin"]}
        ds_units.append({
            "input": spec_text(u["unit_id"]),
            "output": json.dumps({"default": u["default"], "modal_landings": lands}),
            "predict_base": str(u.get("r_u")), "predict_qlik": str(u.get("qlik_top1")),
            "predict_tail": str(u.get("t_u")), "predict_assoc": str(max(u["assoc"], key=u["assoc"].get))
            if u.get("assoc") else "None",
            "metadata_unit_id": u["unit_id"], "metadata_unit_kind": u["unit_kind"], "metadata_status": u["status"],
            "metadata_catalogue": u["catalogue"], "metadata_default_share": u.get("default_share"),
            "metadata_tail_empty": u.get("tail_empty"), "metadata_discordant": u.get("discordant"),
            "metadata_E_u": u.get("E_u"), "metadata_E_u_by_alpha": u.get("E_u_by_alpha"),
            "metadata_flags": u.get("flags"), "metadata_q_base": u.get("q_base"), "metadata_q_lik": u.get("q_lik_softmax"),
            "metadata_q_tail": u.get("q_tail"), "metadata_beta": u.get("beta"),
            "metadata_m_candidates": u.get("m_candidates"), "metadata_commit_sha256": u["commit"]["sha256"]})
    ds_events = []
    for e in events:
        ds_events.append({
            "input": f"{e['unit_id']} nudge={e['nudge']} set={e['set']} (pooled qualifying cells: "
                     f"{e['n_qualifying_cells']}/{e['n_cells']})",
            "output": json.dumps({"modal_landing": e["modal_landing"], "counts": e["counts"],
                                  "is_event": e["is_event"]}),
            "predict_base": str(e["r_u"]), "predict_qlik": str(e["qlik_top1"]), "predict_tail": str(e["t_u"]),
            "metadata_event_id": e["event_id"], "metadata_set": e["set"], "metadata_content_free": e["content_free"],
            "metadata_tail_empty": e["tail_empty"], "metadata_discordant": e["discordant"],
            "metadata_margin_pts": e["margin_pts"], "metadata_iter5_origin": e["iter5_origin"],
            "metadata_other_correct": e["other_correct"]})
    ds_cells = []
    for c in esc:
        ds_cells.append({"input": f"{c['unit']} {c['cell']}", "output": json.dumps(
            {"share": c["share"], "pass_rate": c["pass_rate"], "stage1": c["stage1"], "confirmed": c["confirmed"]}),
            "predict_escape_confirmed": str(c["confirmed"]), "metadata_n": c["n"], "metadata_alpha": c["alpha"],
            "metadata_dir_seed": c["dir_seed"], "metadata_p": c["p"], "metadata_twin_off": c["twin_off"],
            "metadata_set": c["set"]})
    if not ds_cells:
        ds_cells = [{"input": "none", "output": "none"}]
    meta = {"method_name": "Panel II landing test (iteration 6): base runner-up vs the tuned model's own tail and "
                           "likelihood ranking", "panel": "II", "utc": utc_now(),
            "models": {"instruct": "Qwen/Qwen3-8B@b968826d", "base": "Qwen/Qwen3-8B-Base@49e3418f"},
            "engine": "HF transformers 4.57.6 bf16 (hooked arms, CRN sampler B = 20) + vLLM 0.11.0 bf16 (unhooked)",
            "gpu": "NVIDIA L4 23 GB", "verdict_L1_panel_II": res["l1"]["verdict"], "L1a": res["l1"]["L1a"],
            "L1b": res["l1"]["L1b"], "tail_rival": res["l1"]["tail_rival"],
            "log_scores": {k: {kk: {kkk: vvv for kkk, vvv in vv.items() if kkk != "per_event"}
                               if isinstance(vv, dict) else vv for kk, vv in v.items()}
                           for k, v in res["l1"]["log_scores"].items()},
            "unit_level": res["l1"]["unit_level"], "priority_subset": {k: res["l1"]["priority_subset"][k]
                                                                       for k in ("L1a", "L1b")},
            "L2": res["l2l3"]["L2"], "L3": res["l2l3"]["L3"]["base_vs"],
            "kendall": res["l2l3"]["kendall_base_vs_tail"], "M": {c: {k: v for k, v in r.items() if k != "values"}
                                                                  for c, r in res["mk"]["M"]["candidates"].items()},
            "K": res["mk"]["K"], "engine_checks": eng, "dose_summary_keys": len(dose),
            "screen": {"n_events": len(scr["events"]), "events": scr["events"]},
            "deviations": read_jsonl(DEVIATIONS), "costs_usd": sum(float(r.get("cost") or 0) for r in read_jsonl(COSTS))}
    return {"metadata": meta, "datasets": [{"dataset": "panelII_units", "examples": ds_units},
                                           {"dataset": "panelII_events", "examples": ds_events},
                                           {"dataset": "panelII_cells", "examples": ds_cells}]}


def posthoc(l1: dict[str, Any]) -> dict[str, Any]:
    """Summaries of the frozen sensitivities plus two post-hoc ones (marked): dropping AUDIT_WEAK units (plan F7) and
    restricting to ESC events (one event per unit and nudge family is already the unit; ESC is the decisive arm)."""
    import pool_l1 as P
    units = {u["unit_id"]: u for u in read_json(ROOT / "units.json")["units"]}
    ba = read_json(RESULTS_DIR / "base_audit.json") if (RESULTS_DIR / "base_audit.json").exists() else {}
    ev = P.select(read_json(ROOT / "landing_events.json")["events"], units)

    def brief(r: dict[str, Any]) -> str:
        return (f"L1a {r['L1a']['hits_r_u']}/{r['L1a']['n_events']} (p {r['L1a']['p']}, {r['L1a']['status']}); "
                f"L1b b {r['L1b']['b_r_u_only']} c {r['L1b']['c_qlik_only']} ties {r['L1b']['ties']} "
                f"(p {r['L1b']['p']}, {r['L1b']['status']}); mean D_lik "
                f"{(r['log_scores']['E'].get('D_lik') or {}).get('event', {}).get('mean')}; mean D_tail "
                f"{(r['log_scores']['E'].get('D_tail') or {}).get('event', {}).get('mean')}")
    out = {k: brief(v) for k, v in l1["sensitivities"].items()}
    out["priority_subset"] = brief(l1["priority_subset"])
    out["SCREEN_included (never primary)"] = brief(l1["screen_included"])
    out["SCREEN_only (never primary)"] = brief(l1["screen_only"])
    weak = {u for u, v in ba.items() if v.get("flag_AUDIT_WEAK")}
    out[f"POST-HOC drop AUDIT_WEAK units {sorted(weak)}"] = brief(P.analyse([e for e in ev if e["unit_id"] not in weak],
                                                                           units))
    out["POST-HOC ESC events only"] = brief(P.analyse([e for e in ev if e["nudge"] == "ESC"], units))
    return out


@logger.catch(reraise=True)
def main() -> None:
    setup_logging("outputs6")
    import events6
    events6.main()
    res = run_frozen()
    eng, dose = engine_and_dose()
    write_json(RESULTS_DIR / "engine_checks.json", eng)
    write_json(RESULTS_DIR / "dose.json", dose)
    write_json(RESULTS_DIR / "posthoc_sensitivities.json", posthoc(res["l1"]))
    scr = screen_report(res["l1"])
    write_json(RESULTS_DIR / "screen.json", scr)
    write_json(RESULTS_DIR / "deviations.json", read_jsonl(DEVIATIONS))
    write_json(RESULTS_DIR / "timing.json", {"hf_batches": len(read_jsonl(TIMING)),
                                             "hf_seconds": sum(r["seconds"] for r in read_jsonl(TIMING)),
                                             "gpu_tasks": read_jsonl(RESULTS_DIR / "gpu_tasks.jsonl")})
    cs = read_jsonl(COSTS)
    write_json(RESULTS_DIR / "costs.json", {"total_usd": sum(float(r.get("cost") or 0) for r in cs), "n_calls": len(cs),
                                            "by_purpose": dict(Counter(r.get("purpose", "?").split(":")[0] for r in cs))})
    enr = sorted((PRED_DIR / "enrolment").glob("*.json"))
    write_json(RESULTS_DIR / "enrolment.json", [read_json(p) for p in enr])
    n = samples_table()
    figures(res["l1"], res["mk"])
    mo = method_out(res, eng, dose, scr)
    write_json(ROOT / "method_out.json", mo)
    logger.info(f"outputs written: {n} sample rows; verdict {res['l1']['verdict']}")


if __name__ == "__main__":
    main()
