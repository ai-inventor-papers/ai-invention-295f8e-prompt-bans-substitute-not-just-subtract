## What was run

Everything runs in one bf16 Hugging Face engine (`src/engine8.py`) with the iteration-6 sampler transform: float64
softmax(logits / T), an optional top-k mask, then the inverse CDF over the full vocabulary in token-id order. Each
program slot owns one PCG64 uniform stream, so a slot keeps its stream across every temperature and sampler (common
random numbers). Fit twins and sweeps use one fixed batch composition per (unit, template) at every temperature.
Prefix-resampling continuations are independent samples, so finished rows are dropped from the cache.

| stage | what | design |
|---|---|---|
| S0 | setup | prompts rebuilt from the source artifacts and checked (Gemma ids sha256 = exp31; Llama prompt lengths = exp10); seed disjointness; CPU tests U5/U8/U9/U10/U11, change-point rule, scoring dry run on iteration-7 data, labeller references; **COMMIT #0** (protocol + code hashes) |
| S1 | per family: load, GPU tests, fit twin | CRN determinism, batch-size sensitivity, teacher-forced vs incremental logits; fit twin N = 100 (20 slots x W1-W5, T 1) at the source keys (Qwen = iteration-7 twin keys, Gemma = exp31 keys) so it doubles as an engine check; Llama bench candidates re-measured in the committed order until two have a second algorithm >= 0.10 (**COMMIT #1a**); Llama label re-gate with two blind judges + tiebreak (**COMMIT #1b**) |
| S3 | blind decision-token locator | token-trie clusters, 6 stratified base paths, 8 continuations per prefix length k in {0, 2, ..., 62} + {64, 68, ..., W_u}, Bayesian single change point (P >= 0.9, TV >= 0.25), 16-continuation single-token refinement; forced-token confirmation (top 20 tokens of the template-averaged T-1 distribution x 10 continuations); second decisions inside impure branches (resampling every token d+1..d+24, forced top-10 at d2); entropy-located rival BH; **COMMIT #1-family** |
| S4 | predictions | teacher-forced fp32 logits per template along every opening, at d and at d2; the law L, B0 (flat), B1 (algorithm-level tempering), B2 (single decision), BH; per-slot replay of every sweep slot; internal-consistency gate; **COMMIT #2-family** (with the scoring code's sha256) |
| S5 | same-stream sweep | per unit 100 fresh streams ('iter8L-sweep', disjoint from every earlier key) x T in {0.3, 0.7, 1.0, 1.3} at top-p 1; top-k 10 cells by exact shadow sampling on the same uniforms (validated on 20 directly sampled slots per family) |
| S6 | base sub-arm | Qwen3-8B and Qwen3-8B-Base teacher-forced on identical chat-templated ids at the decision positions (T1, T10, T2 forks from art_MZAfDPVhM6Ui; B3, A3 from COMMIT #1-qwen) and at 64 phrasing positions of 20 programs per task; URIAL rank categories; JS divergence with entropy-matched and random-position controls; template-free sensitivity |
| S7 | scoring | `src/analysis_L.py` (frozen; hash in COMMIT #2 + one pre-sweep amendment): MAE, McNemar drops, replay accuracy and gaps, H, verdict, placebos, diversity and phrasing clusters |
| S8 | judges | Llama re-gate, adjudication of cells with > 20% 'other', novelty audit of every correct off-catalogue program against the 18k-solution corpus built from the dependency art_j3Rm_lr2nzR6 |

## Layout

| path | content |
|---|---|
| `method.py` | entry point: runs every stage in order (`.venv/bin/python method.py all`) or a comma list |
| `src/cfg8.py` | constants: units, families, keys, thresholds, paths to the prior artifacts (with fallback to `inputs/src_*`) |
| `src/prompts8.py` | prompt ids per (unit, template) -> `prompts/prompts8.jsonl`, `results/prompt_checks.json` |
| `src/engine8.py` | the bf16 engine: loaders (Gemma text-only, Qwen/Llama with CPU embedding when < 18 GiB free), CRN decoder (coupled / free), top-k shadow, teacher forcing |
| `src/oc8.py`, `src/opening_cls.py` | opening classifiers (iteration-7 rules for B3/A3/B6, new keyword rules for the other units) and their gate |
| `src/label8.py`, `src/label7.py` | label worker (frozen labellers of iterations 5-6; persistent `--serve` mode) |
| `src/locate8.py`, `src/forks.py` | locator functions (clusters, base paths, grid, change points, classes, H) |
| `src/predict8.py`, `src/predict.py`, `src/replay.py` | the law (two-level composition), baselines, unit tests U5-U11; iteration-7 law and replay reused unchanged |
| `src/gpu8.py` | per-family GPU driver (tests, fit, select, locate, commit1, predict, commit2, sweep) |
| `src/commit0.py`, `src/commit8.py` | COMMIT #0 and the sha256 hash chain (`commitments.log`, `predictions/*.json`) |
| `src/analysis_L.py` | committed scoring -> `results/analysis_L.json`, `results/verdict.json` |
| `src/base_arm.py` | base sub-arm (GPU teacher forcing for both models; analysis -> `results/base_subarm.json`) |
| `src/novelty8.py` | judges: re-gate, adjudication, novelty audit -> `results/regate.json`, `results/adjudication.json`, `results/novelty_audit.json` |
| `src/tests_cpu.py`, `src/vendor_inputs.py` | CPU tests -> `results/tests_cpu.json`; input copies + `inputs/SHA256SUMS` |
| `src/figures8.py`, `src/report8.py`, `src/outputs8.py` | figures F1-F6, `results/summary.md`, `method_out.json` |
| `audit/rederive.py` | standard-library re-derivation of every headline with placebos -> `results/rederive.json` |
| `protocol8L.json`, `commitments.log`, `predictions/` | the committed protocol, hash chain and commit payloads |
| `data/samples_raw.jsonl`, `data/labels.jsonl` | every program (fit twins, sweeps, top-k cells, top-k validation) with ids, text, slot, cell, seed; labels |
| `data/continuations.jsonl` | every locator / refinement / forced-token / second-decision continuation with its label |
| `data/judge_cache.jsonl`, `data/adjudicated_labels.jsonl` | judge calls (cached) and adjudicated labels |
| `results/` | per-unit `fit_*`, `locate_*`, `predict_*`, `sweep_*` JSON; analysis, verdict, engine checks, GPU tests, timing, deviations, costs, positioning, summary.md |
| `figures/` | F1-F6 (PDF + PNG) |
| `inputs/` | sha256-checked copies of the prior artifacts this pipeline reads (`inputs/SHA256SUMS`) |
| `method_out.json` (+ `full_`, `mini_`, `preview_`) | exp_gen_sol_out output (datasets law_sweep, fit_twins, locator, forced_tokens, base_subarm) |
| `run_chain.sh`, `finalize.sh`, `restore.sh` | the GPU chain as run (Llama -> Qwen -> base sub-arm), the CPU finalisation (judges, scoring, figures, outputs, re-derivation, schema check) and the restore script |
| `results/positioning.json`, `results/novelty_manual.json` | dated literature positioning with quotes and verdicts; the manual read of every correct off-catalogue program |
| `docs/` | the README's source parts (assembled by `src/assemble_readme.py`) |
| `data/continuations_superseded.jsonl` | 984 L-T1 forced/second-decision continuations sampled before amendment 3 (index-tagged ids), kept for transparency and never read by the pipeline |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
.venv/bin/python src/download_models.py            # the four model revisions into the HF cache
.venv/bin/python method.py all                     # or a comma list of stages, see method.py
```

The GPU stages need one CUDA GPU with at least 20 GB (this run: RTX A4500). The judges need `OPENROUTER_BASE_URL` and
`OPENROUTER_API_KEY`. Every stage resumes from its result file; the commit stages refuse to overwrite a commit.
