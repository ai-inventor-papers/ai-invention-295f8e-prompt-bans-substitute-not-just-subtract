## How it was run

Every stage is `.venv/bin/python method.py <stage> [args]`; logs go to `logs/`, timings to `results/timing.jsonl`,
OpenRouter spend to `results/costs.json`. Stages in run order:

| Stage | Command | What it does |
|---|---|---|
| -1 | `inputs` | Copies the prior-artifact inputs into `inputs/` (+ `inputs/SHA256SUMS`), vendors the harness and labeller, writes `predictions/hardware.json` |
| 0 | `commit0` | Predictions P1-P8, gates, definitions, named outcomes; hash-committed before any state (`commitments.log`) |
| 1 | `mname 32b` | Qwen3-32B nf4 S-mean states of iteration 8's 300 forced prompts + the reproduction gate |
| 2 | `cpu` | 40 probe grids, expansion tracer on the 15 T1 references (G-tracer), behavioural RDM, lexical measures, descriptions v0, M-lex prompts with token-matched neutral twins, M-code contexts; COMMIT #1a |
| 3a | `naming` | Qwen3-32B (OpenRouter, DeepInfra fp8, thinking off) names each description 20 times; <= 2 rewrites |
| 3b | `topups` | 600 forced Qwen3-32B programs (60 per algorithm) |
| 4 | `pools` | ACCEPT (tier A committed, tier B used), scrub + G-scrub, M-code sets PRIMARY / M32 / M8, placement sets SURV / BASE / DISOBEY, M-desc prompts; COMMIT #1b |
| 5 | `states 32b mlex ban`, `states 8b mname mlex ban`, `states 32b mdesc mcode`, `states 8b mdesc mcode` | S-mean and code-token states |
| 6 | `blocks` | Label-only block selection (iteration 8's layer rule) for every model x manifold; COMMIT #2 |
| 7-10 | `analyse` | Geometry, verdicts, landing, bootstrap, robustness grid, crossnobis / z-scored sensitivities, frozen geodesics, lexical regression, exact-permutation RSA, name evocation, out-of-sample placement |
| 11 | `figures` | PCA / MDS / Isomap figures in activation coordinates, class table, RDM heatmaps, behavioural MDS |
| 12 | `outputs` | `data/points.jsonl`, `data/placements.jsonl`, `results/n4_verdict.json`, `method_out.json` |
| audit | `audit/rederive.py`, `audit/audit_states.py` | Independent re-derivations (stdlib-only from JSON; independent kNN/Dijkstra from raw states) with placebos |

`run_chain.sh` runs stages 5 (mdesc/mcode) to the audit unattended.

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator, one sub-command per stage |
| `src/common.py`, `src/prompts_tp.py`, `src/states.py`, `src/geometry.py`, `src/landing.py`, `src/label_tp.py`, `src/sample_or.py`, `src/judge_tp.py` | Iteration 8's modules (art_R-HSmXq2t97f), byte-identical copies, imported unchanged |
| `src/e44/` | Unedited archive of iteration 8's whole `src/` |
| `src/tpg.py` | This artifact's frozen constants (banned split, model pins, blocks, k, budgets, gates) |
| `src/stage_setup.py` | Stage -1 and commit #0 |
| `src/stage_states.py`, `src/stage_mcode.py` | State extraction (S-mean families; M-code readouts R1 / R1g / R2 / R3) |
| `src/stage_cpu.py`, `src/expansion.py`, `src/expansion_child.py` | Probe grids, expansion tracer (child runs sandboxed, stdlib only), behavioural RDM, lexical measures, descriptions, M-lex twins, M-code contexts |
| `src/stage_or.py` | OpenRouter naming gate and top-ups (pinned provider, cost ledger, 403 stop) |
| `src/programs.py`, `src/stage_pools.py` | ACCEPT, scrubber, G-scrub, program and placement sets |
| `src/stage_analysis.py` | Block selection, geometry, landing, bootstrap, robustness, lexical regression, RSA, placement |
| `src/stage_figures.py`, `src/stage_outputs.py` | Figures and outputs |
| `audit/` | Independent re-derivations |
| `predictions/commit{0,1a,1b,2}.json`, `commitments.log` | Pre-registrations and their sha256 hash chain |
| `inputs/` | Prior-artifact inputs copied at Stage -1 (+ `SHA256SUMS`) |
| `vendor/exp9/`, `vendor/exp2/` | Iteration-2 harness, hidden suites, references and labeller (via iteration 8) |
| `data/` | Probe grids, descriptions, naming calls, top-ups, program sets, M-lex prompts, points and placements rows, sandbox cache |
| `results/` | Every analysis JSON |
| `figures/` | PDF + PNG figures; `figures/coords/` holds the 2-D coordinates they were drawn from |
| `cache/states/` | Activation states and frozen geodesic graphs. **Kept on the run's storage volume, not in the published repository** (files of 100 MB or more are not published; the whole directory is excluded from upload) |

## Restoring removed files

The manifest (`.aii/manifest.yaml`) marks three things for deletion after the round; each is restorable:

```bash
# .venv/ (regenerable)
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.lock.txt
# inputs/e44/states/ (regenerable: copies of the iteration-8 states; needs the art_R-HSmXq2t97f artifact folder,
# located by the TPG_E44 environment variable)
.venv/bin/python method.py inputs
# __pycache__/ (regenerable): created on import
```

Model weights are not stored in this folder. They are downloaded into the Hugging Face cache by
`.venv/bin/python scripts/download_models.py` (`unsloth/Qwen3-32B-bnb-4bit@7f721e74a6a8cc9ee352f7e49303a2c1705f9083`,
`Qwen/Qwen3-8B@b968826d9c46dd6066d109eabc6255188de91218`).
`cache/states/` is kept on the run volume; to rebuild it from scratch run the `mname`, `states` and `analyse` stages
(about 30 GPU-minutes on one RTX 5090).
