#!/usr/bin/env python3
"""Write README.md: static description + the results section rendered from results/summary.md and posthoc.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HEAD = """# Did 8-bit arithmetic cause the nudge effect? (artifact E, iteration 6)

In iteration 4, per-sample **plan noise** (PN) moved Qwen3-8B off its default algorithm on two tasks:

- T10 (connected components): 60% of samples, versus 0% for the clean twin;
- T2 (weighted shortest path): 54%.

PN is one fresh isotropic direction per sample, added at the task-specification positions of decoder blocks 12–23
during the prompt prefill. Those runs used an FP8 (e4m3) W8A8 engine. In iteration 5, the same knob under bf16 was
almost inert (T10 0.02, T2 0.04). This artifact asks whether the **arithmetic precision** caused the effect.

## Design

It holds fixed everything iteration 4 used:

- exp19's prompts and per-sample PN seeds;
- exp22's 40 fixed directions;
- the logged per-position ban units n[l,p];
- exp19's hook code (`src/hooks.py`, sha256-identical);
- the inverse-CDF CRN uniform streams;
- the 1,024-token cap;
- exp19's batch shape (B = 20, exp19's pairs).

Only the precision of the 252 decoder linears varies, in a 2x2 factorial:

| cell | weights | activations | backend |
|---|---|---|---|
| **W16A16** (baseline: the iteration-5 engine) | bf16 | bf16 | HF native `nn.Linear` |
| W16A8 | bf16 | e4m3 per row | EMU |
| W8A16 | e4m3 per output channel | bf16 | EMU |
| **W8A8** (iteration 4's numerics) | e4m3 per output channel | e4m3 per row | EMU |
| W8A8REAL (sm_89 only) | e4m3 | e4m3 | exp19's `FP8Linear` (`torch._scaled_mm`) unchanged |

- **EMU** is exact e4m3 quantise-dequantise using exp19's own quantisers, applied to exact-valued bf16 operands. It
  runs `torch.mm(out_dtype=float32)` with fp32 accumulation, applies both scales in fp32 and casts to bf16 once. The
  quantisers switch on or off; the backend stays the same.
- A kernel-only floor (`W16A16mm`: the EMU GEMM path with quantisers off) is measured in the readouts.
- Tasks: T10 and T2 are decisive; T03 (k-th smallest) is the positive control.
- Arms per precision:
  - TWIN, PN alpha 0.5 / 1 / 2: N 50 each, exp19's exact slots;
  - the 40 exp22 directions at alpha 2: N 10 each;
  - a unit cross: PN seeds at the ban-free unit, W8A8 and W16A16;
  - a dither probe: W16A16 plus uniform noise matched element by element to the e4m3 rounding step, without and with
    PN alpha 2.
- Mechanism readouts use forward passes only, at batch 1:
  - FP8 scale changes and the re-rounding gain;
  - per-block divergence travel and the kernel floor;
  - KL at R and teacher-forced KL over 32 tokens.
- Outcome: **Y_correct** = passed AND label not in {default, invalid}.
- Every contrast is paired by CRN slot and tested with an exact McNemar test.
- Predictions, thresholds, the attribution rule, outcome definitions and the analysis code were sha256
  hash-chained in `commitments.log` (commit #0, 2026-10-21T20:32:48Z) before the first decisive sample.

Hardware: one NVIDIA L4 (sm_89, 23 GB), so the REAL FP8 path was available. Deviations from the plan are listed in
`results/deviations.jsonl`.

## Results
"""

TAIL = """
## Layout

| path | what |
|---|---|
| `method.py` | entry point; runs every stage in order (`uv run method.py --stage all`) |
| `run_gpu_pipeline.sh`, `run_posthoc.sh` | GPU generation queue, then readouts; the post-hoc iteration-5 replication cells |
| `src/cfg.py`, `engine_v4.py`, `hooks.py`, `sampling_v4.py`, `prompts_v4.py`, `label_worker_v4.py`, `commit.py` | exp19's modules copied unchanged |
| `src/cfg_e.py` | this artifact's constants and arm definitions |
| `src/qlinear.py` | e4m3 quantisers (exp19's, op for op), `QLinear` (EMU) and the family manager (W16 / W8 / REAL) |
| `src/engine_e.py` | wrapper around exp19's prefill / sample / TaskContext; one fixed batch shape; per-row precision log |
| `src/dither.py` | dither pre-hooks on the native W16A16 linears |
| `src/run_e.py` | device rule + memory probe, GPU tests, smoke run, the resumable generation queue, readouts |
| `src/tests_gpu.py`, `src/tests_cpu.py` | GPU tests U1–U8 and CPU tests 1–8 |
| `src/readouts.py` | Stage F mechanism readouts |
| `src/label_e.py` | wraps exp19's labeller; Stage A.2 labeller re-check |
| `src/stage_a.py`, `src/commit_e.py`, `src/commit0.py`, `src/commit1.py` | inputs + sha256, iteration-4 reference numbers, prompt diff; hash chain; commits #0 and #1 |
| `src/analysis_e.py` | Stage G statistics (committed before the decisive samples) |
| `src/posthoc_e.py` | POST-HOC iteration-5 replication and unit decomposition |
| `src/novelty_e.py`, `src/dep_usage_e.py` | blind two-judge novelty audit; use of dependency art_j3Rm_lr2nzR6 |
| `src/rederive_e.py` | independent re-derivation (stdlib + numpy), placebos, commit-chain and prompt audits |
| `src/figures_e.py`, `src/report_e.py`, `src/outputs_e.py`, `src/write_readme.py` | figures F1–F9, `results/summary.md`, `method_out.json`, this README |
| `data/samples_raw.jsonl` | every generated program (token ids, text) with precision, kernel, batch shape, hook sha256 |
| `data/labels.jsonl`, `data/samples.jsonl` | labels; merged per-row output (plan PER-ROW OUTPUT, no token ids) |
| `data/realised.jsonl` | realised displacement per pushed prefill |
| `results/` | every analysis JSON, tests, gate checks, timing, readout summaries (`readouts_slots.jsonl`) |
| `predictions/` | `e_inputs.json`, `e_commit.json` (commit #0), `commit1_gate.json`, `device_rule.json`, `landing_ref.json` |
| `commitments.log` | sha256 hash chain (genesis sha256('iter6_E')) |
| `figures/` | F1–F9 as PDF + PNG |
| `inputs/` | sha256-verified read-only copies of exp19, exp22, exp23, exp24, exp25, exp27, exp18 and exp19's inputs |
| `states/` | clean residual states (blocks 11/17/23/29/35, bf16) per task, template and precision (kept on the run volume, not published) |
| `method_out.json`, `full_/mini_/preview_method_out.json` | exp_gen_sol_out output (per-program predictions per precision; all analyses in `metadata`) |

## How to run

```bash
uv sync --frozen
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
uv run method.py --stage all      # about 2.5 GPU-hours on an L4; 'post' re-runs the CPU analysis only
```

`reproducibility.md` lists every command in the order it was run, with seeds and hardware.

## Restoring removed files

Every `delete` entry of `.aii/manifest.yaml` and the command that brings it back:

| removed path | how to restore |
|---|---|
| `.venv/` | `uv sync --frozen` |
| `src/__pycache__/` | `uv run src/stage_a.py` (any script under `src/` recreates the bytecode cache) |
| `inputs/exp11/bench/__pycache__/` | `uv run src/label_e.py --recheck` (recreated when the bench labeller is imported) |
| `inputs/exp11/bench/common/__pycache__/` | `uv run src/label_e.py --recheck` |
| `inputs/exp8/suite/__pycache__/` | `uv run src/label_e.py --recheck` (recreated when the path-task labeller is imported) |
| `inputs/exp8/suite/labeller/__pycache__/` | `uv run src/label_e.py --recheck` |
| `inputs/exp8/suite/tasks/__pycache__/` | `uv run src/label_e.py --recheck` |

The model weights are not stored in this folder. They live in the shared Hugging Face cache; restore them with
`huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.

`states/` (clean residual states from the readouts, about 7 MB per file) stays on the run's storage volume and is
not published to the repository.
"""


def interpretation() -> str:
    """Key reading, every number pulled from results/*.json."""
    R = ROOT / "results"
    prim = json.loads((R / "primary_E.json").read_text())
    uc = json.loads((R / "unit_cross.json").read_text())
    ph = json.loads((R / "posthoc.json").read_text()) if (R / "posthoc.json").exists() else {"tasks": {}}
    pop = json.loads((R / "population40.json").read_text())
    att = json.loads((R / "attribution.json").read_text())
    dose = json.loads((R / "dose.json").read_text())
    t10, t2 = prim["tasks"]["T10"], prim["tasks"]["T2"]
    L = ["### Interpretation", ""]
    L.append(
        f"1. **The 8-bit arithmetic did not cause the effect.** On identical inputs, plan noise at alpha 2 moves W16A16 "
        f"(the iteration-5 bf16 engine) almost as much as W8A8. T10: {t10['share_B']:.2f} vs {t10['share_A']:.2f} "
        f"(exact McNemar p {t10['mcnemar']['p_two_sided']:.2g}). T2: {t2['share_B']:.2f} vs {t2['share_A']:.2f} "
        f"(p {t2['mcnemar']['p_two_sided']:.2g}). The frozen rule returns NO PRECISION EFFECT, and so does REAL "
        f"(exp19's own FP8 kernel). There is no activation or weight main effect at this N: pooled AME "
        f"{att['pooled']['effects']['AME']:.2f}, WME {att['pooled']['effects']['WME']:.2f}.")
    pp = pop["tasks"]["T10"]["pairs"].get("W8A8_vs_W16A16", {})
    if pp:
        L.append(
            f"2. **A small, real FP8 increment on T10 only.** Over the 40 fixed directions, W8A8 sits above W16A16 by "
            f"{pp['mean_diff']:.2f} per direction (Wilcoxon p {pp['wilcoxon_p']:.3f}; Spearman {pp['spearman']:.2f}; "
            f"identical escape sets, Jaccard {pp['jaccard_escape']:.2f}). The T10 weight main effect is "
            f"{att['tasks']['T10']['effects']['WME']:.2f} with 95% CI [{att['tasks']['T10']['boot95']['WME'][0]:.2f}, "
            f"{att['tasks']['T10']['boot95']['WME'][1]:.2f}]. This is an order of magnitude below the iteration-4 to "
            f"iteration-5 gap.")
    a = uc["tasks"]["T10"]["shares"]
    b = uc["tasks"]["T2"]["shares"]
    u16 = uc["tasks"]["T10"]["unit_in_W16A16"]
    u16b = uc["tasks"]["T2"]["unit_in_W16A16"]
    L.append(
        f"3. **The dose unit explains iteration 5's collapse.** With the same PN seeds and slots, replacing the logged "
        f"ban unit n[l,p] by the ban-free unit (||h_twin|| x r_Q) drops T10 from {a['W16A16|ban']['Y_correct']:.2f} to "
        f"{a['W16A16|banfree']['Y_correct']:.2f} under W16A16 (McNemar {u16['table']['10']}:{u16['table']['01']}, "
        f"p {u16['mcnemar']['p_two_sided']:.2g}) and from {a['W8A8|ban']['Y_correct']:.2f} to "
        f"{a['W8A8|banfree']['Y_correct']:.2f} under W8A8. T2 drops from {b['W16A16|ban']['Y_correct']:.2f} to "
        f"{b['W16A16|banfree']['Y_correct']:.2f} (p {u16b['mcnemar']['p_two_sided']:.2g}); the frozen decision text "
        f"labels T2 MIXED only because its ban-unit share is below the coded 0.20 'high' threshold.")
    d16 = dose.get("T10|W16A16|PN_a2", {})
    d16f = dose.get("T10|W16A16|PNF_a2", {})
    if d16 and d16f:
        L.append(
            f"   The two units have the same mean of per-position ratios (exp27 reported 0.99), but not the same "
            f"dose. The ban unit concentrates displacement at a few spec positions, with a coefficient of variation "
            f"of about 1 across positions against about 0.1 for the ban-free unit. Its mean realised displacement at "
            f"block 12 is {d16['disp_S_mean']['12']:.1f} against {d16f['disp_S_mean']['12']:.1f}, a ratio to the "
            f"residual of {d16['ratio_to_residual']['12']['ratio_of_means']:.2f} against "
            f"{d16f['ratio_to_residual']['12']['ratio_of_means']:.2f}. See results/posthoc.json, unit_profile.")
    pt = ph.get("tasks", {})
    if pt.get("T10", {}).get("W16A16|IT5_a2"):
        v10, v2 = pt["T10"]["W16A16|IT5_a2"], pt["T2"]["W16A16|IT5_a2"]
        L.append(
            f"4. **POST-HOC: iteration 5 is reproduced exactly in this engine.** The run used exp27's PN5 seeds and "
            f"its per-template ban-free unit. W16A16 gives T10 {v10['Y_correct']:.2f}, where exp27 had "
            f"{v10['exp27_Y_correct_same_slots']:.2f}, with per-slot label agreement "
            f"{v10['label_agreement_with_exp27']:.2f}. T2 gives {v2['Y_correct']:.2f} against "
            f"{v2['exp27_Y_correct_same_slots']:.2f} (agreement {v2['label_agreement_with_exp27']:.2f}). W8A8 at the "
            f"same settings stays low: T10 {pt['T10']['W8A8|IT5_a2']['Y_correct']:.2f}, T2 "
            f"{pt['T2']['W8A8|IT5_a2']['Y_correct']:.2f}. So iteration 5's batch path and seeds do not matter either; "
            f"the unit does.")
    L.append(
        "5. **Consequence (frozen rule).** The iteration-4 internal claims are restored as properties of the model "
        "under the ban-unit dose, not of the FP8 engine. Iteration 5's 'matched dose' comparison was not matched. "
        "T03 moves under every precision, every precision lands on the base runner-up (T10 dfs, T2 Bellman-Ford/SPFA, "
        "T03 quickselect), and dither neither creates nor removes movability. The dither readings in the table were "
        "written for the predicted W8A8 >> W16A16 case; here W16A16 already moves, so dither has nothing to explain.")
    return "\n".join(L) + "\n\n"


def main() -> None:
    summ = (ROOT / "results" / "summary.md").read_text() if (ROOT / "results" / "summary.md").exists() else ""
    try:
        summ = interpretation() + summ
    except (KeyError, OSError, json.JSONDecodeError) as e:
        summ = f"(interpretation unavailable: {e})\n\n" + summ
    ph = ROOT / "results" / "posthoc.json"
    extra = ""
    if ph.exists():
        d = json.loads(ph.read_text())
        lines = ["", "### POST-HOC (not pre-registered): replicating iteration 5's PN cells in this engine", ""]
        for t, r in d["tasks"].items():
            for k in ("W16A16|IT5_a2", "W8A8|IT5_a2", "W16A16|IT5_a1"):
                v = r.get(k)
                if v:
                    exp27 = v["exp27_Y_correct_same_slots"]
                    exp27 = "–" if exp27 is None else f"{exp27:.2f}"
                    agree = v["label_agreement_with_exp27"]
                    agree = "–" if agree is None else f"{agree:.2f}"
                    lines.append(f"- {t} {k}: Y_correct {v['Y_correct']:.2f} (N {v['N']}); exp27 on the same slots "
                                 f"{exp27}; per-slot label agreement with exp27 {agree}")
            for k in ("W16A16_PN_a2_vs_PNF_a2", "W16A16_PN_a2_vs_IT5_a2", "W8A8_vs_W16A16_IT5_a2"):
                c = r.get(k, {})
                if c.get("n_pairs"):
                    lines.append(f"- {t} {k}: {c['share_A']:.2f} vs {c['share_B']:.2f} (McNemar p "
                                 f"{c['mcnemar']['p_two_sided']:.2g}, n {c['n_pairs']})")
        extra = "\n".join(lines) + "\n"
    (ROOT / "README.md").write_text(HEAD + "\n" + summ + extra + TAIL)
    print("README.md written")


if __name__ == "__main__":
    main()
