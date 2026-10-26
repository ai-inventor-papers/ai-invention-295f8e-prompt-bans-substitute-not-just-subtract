#!/usr/bin/env python3
"""Final deviations record (CPU): completes results/deviations.json with every departure from the plan that is not
logged by a stage itself, with the numbers taken from the result files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from k3cfg import RESULTS_DIR, read_json, utc_now, write_json  # noqa: E402


def main() -> None:
    p = RESULTS_DIR / "deviations.json"
    cur = read_json(p) if p.exists() else []
    by = {d["id"]: d for d in cur}
    g = read_json(RESULTS_DIR / "gpu_tests.json")
    c = read_json(RESULTS_DIR / "contrasts.json")

    def put(i: str, sev: str, text: str) -> None:
        by[i] = {"id": i, "severity": sev, "text": text, "utc": by.get(i, {}).get("utc", utc_now())}
    u3, u3b = g["U3"], g.get("U3b_full_vs_full", {})
    put("F5_prefix_cache", "major",
        f"U3 (suffix forward with reused prefix KV vs full recompute) differs by mean {u3['mean_abs_diff']:.3f} / max "
        f"{u3['max_abs_diff']:.3f} nats (> 0.05). The same 20 rows run as full forwards in two batch shapes differ by mean "
        f"{u3b.get('mean_abs_diff', float('nan')):.3f} / max {u3b.get('max_abs_diff', float('nan')):.3f}: the gap is bf16 "
        "path noise, not a cache error, so suffix forwards were kept (amendment 0a rule) instead of F5's full forwards. "
        f"U2 (patch everything -> corrupt) is off by {abs(g['U2']['dm_patch_all'] - g['U2']['target_dm']):.3f} and U8 "
        f"(own-state exchange) by {abs(g['U8']['dm_own_exchange']):.3f} nats for the same reason; every effect is measured "
        "against an unedited base row of its own batch.")
    put("F2_C1forced_primary", "major",
        f"C1-nat set A mean TE {c['C1nat_A']['TE_mean']:.3f} nats < 1.0 -> F2: C1-forced is the primary C1 unit "
        "(amendment 0a, committed before any screen row). art_MZAfDPVhM6Ui has one forced-Prim wording, so 15 wordings were "
        "written here: F1-F10 are the 10 pairs, F11-F15 (and their padding twins) the 10 held-out validation prompts. "
        "C1-nat is screened, validated and reported descriptively.")
    put("F4b_exhaustive_sweep", "major",
        "AtP and IG-AtP both gave Spearman < 0.4 against exact patching on 160 random nodes (those nodes sit at the bf16 "
        "noise floor), so F4's second clause applied: ranking by exact noising over ALL DEC-class nodes plus the screen's "
        "top 120; all 144 MLP nodes were added because AtP is least reliable for early MLPs. This found C1-forced's largest "
        "node, the layer-0 MLP at the condition span (7.7 of 9.9 nats; AtP estimate 0.1), which the screen had missed. "
        "Edges and faithfulness were recomputed for the new top 15; screen-only lists are kept in circuit_*.json.")
    put("IG_AtP_input_interpolation", "minor",
        "IG-AtP interpolates the input difference (embedding at the differing positions; the exchanged states for C2a) "
        "with every activation live, so gradients stay total derivatives; it did not improve the random-node correlation "
        "and plain AtP was kept. The S19 (arXiv 2606.09899) HVP correction was not implemented within the timebox.")
    put("faithfulness_definition", "minor",
        "Faithfulness type 1/2 freeze every non-circuit node to the corrupt run (type 1) or the corrupt-class same-template "
        "mean (type 2) on the clean input with circuit nodes live and the input embedding clean (MIB style). With the "
        "embedding also patched, as the plan wrote, no clean information can enter a frozen network and f(k) = 0 by "
        "construction. Type 1 is ~0 at every k <= 60 (the decision nodes need distributed upstream processing); "
        "completeness (top-k jointly noised) and sufficiency (top-k jointly denoised), both live, carry the faithfulness "
        "result. Type 2 is undefined for C1-forced (one prompt per wording) and C2a's corrupt run is an intervention, so "
        "C2a reports completeness/sufficiency only.")
    put("transcoder_extension_dropped", "minor",
        "F11: the Qwen3-8B transcoders (~96.5 GB) exceed the 23 GB GPU and 57 GB RAM and circuit-tracer is not installed; "
        "dropped at the precheck (results/transcoder_precheck.json). No feature-level account.")
    put("C2b_dropped", "minor", "C2b (ban vs twin on T10) was not run (first droppable item after the transcoders).")
    put("hardware", "minor", "Ran on one NVIDIA L4 (23 GB; plan: RTX A4500 20 GB); the embedding stayed on the GPU.")
    put("generation_alignment_rule", "minor",
        "C1-forced's top-10 includes the layer-0 COND MLP, whose positions (the forced instruction) have no counterpart "
        "in the B3 twin's condition sentence; by the rule committed in amendment 0a the generation TOP5 uses the five "
        "highest-ranked non-COND nodes (all at DEC) and RAND5 matches those.")
    put("FREE_condition_exact", "minor",
        "FREE is implemented exactly without online hooks: the edited opening is teacher-forced and each slot samples "
        "with its own uniforms until the first divergence; rows that reproduce the whole opening continue from the "
        "edited decision position (identical to PREFILL), diverged rows continue from their own prefix with only the "
        "edits at earlier positions.")
    put("engine_check_reference", "minor",
        "The T10 engine-check reference (art_pHL7LWNhpcCS) was generated on an RTX 4090 with the iteration-6 exp29 engine "
        "and different CRN keys, so T10 is compared at the label level only; B3 uses the same keys and engine family.")
    put("sign_flip_exact_to_40", "minor",
        "The sign-flip test is exact up to n = 40 (meet-in-the-middle enumeration of all 2^n sign patterns) instead of "
        "exact to 25 and Monte Carlo beyond.")
    if (RESULTS_DIR.parent / "data" / "validation_sens_rows_C1forced.jsonl").exists():
        put("head_null_sensitivity_posthoc", "minor",
            "POST HOC (labelled, committed before its rows): the top decision heads are write-norm outliers, so their "
            "matched pools fell back to the 50 nearest heads (smaller norms; head draws are not rescaled in the committed "
            "design); a sensitivity re-runs those nulls with each draw rescaled to the target's write norm. The primary "
            "validation is unchanged.")
    if (RESULTS_DIR.parent / "data" / "gen_dose_raw_C1forced.jsonl").exists():
        put("dose_sensitivity_posthoc", "minor",
            "POST HOC (labelled; commit_dose_<contrast> before its rows): at the committed dose 2 the matched random five "
            "also saturates the minority algorithm, so a dose sensitivity was added: logit-level P(minority token) at "
            "doses 0.25-2 and PREFILL generation of TOP5 / RAND5 at doses 0.5 and 1 on the same 30 CRN slots. The "
            "committed K3 verdicts use dose 2 only.")
    put("mcnemar_sidedness", "major",
        "Commit #0's text says 'exact McNemar TOP5 vs RAND5 p < 0.05' without sidedness; the analysis code fixed by "
        "hash at commit #0 used the one-sided test, the plan's power calibration (8:0 -> 0.0078, 7:1 -> 0.07) is "
        "two-sided. The two-sided test is primary (conservative): C1 is PARTIAL (7:1, p = 0.070); with the one-sided "
        "test C1 would be PASS (p = 0.035). Both are reported.")
    put("oom_restarts", "minor",
        "Two CUDA out-of-memory stops (class means cached on the GPU; memory accumulated over many stages in one "
        "process) were fixed (CPU class means, smaller row chunks, one process per stage) and every stage resumed "
        "from its files; no row was recomputed or dropped.")
    put("U5_not_run", "minor", "GPU test U5 (path-patching sanity against direct-logit attribution) was not run.")
    put("stability_screen", "minor",
        "Pair set B (stability) ran the screen, exact patching of the top 60 + 20 calibration nodes, path patching and "
        "the F4b sweep, without the 160-node reliability check or IG; 12 of its 15 pairs have TE > 0.2.")
    out = sorted(by.values(), key=lambda d: d["utc"])
    write_json(p, out)
    print(f"{len(out)} deviations")


if __name__ == "__main__":
    main()
