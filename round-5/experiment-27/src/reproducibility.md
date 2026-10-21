# Reproducing this artifact

This folder is one artifact of a public repository: **plan noise against plan-first prompting (iteration 5)**, plus
the literal thinking-on temperature cell. Everything below is what was actually run, in order, on 2026-10-21.
Paths are relative to this folder.

## 1. Get the artifact

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>      # the folder that holds method.py
```

The run reads its inputs from `inputs/`. These are read-only copies of earlier artifacts of the same research run,
with sha256 values in `inputs/SHA256SUMS`, and all of them are published with this folder:

- `exp6`: semantic-seed paragraphs.
- `exp7`: neutral nouns.
- `exp8`: the T1/T2 path-task suite, its labeller and the frozen prompts.
- `exp11`: the 13-task bench, with specs, hidden tests, labellers, gold sets and `commitment.json`.
- `exp13`: twin prompt ids and the ban unit norms.
- `exp16`, `exp17`: the engine-check directions and norms.
- `exp18`: the known-solutions summary.
- `eval2`, `eval3`: statistics code and the frozen movability screen (sha256 `d6a2ca97…`).
- `exp19`, `exp20`, `exp21`, `exp23`: iteration-4 code, rows and the r_Q depth ratios.
- `exp5`: iteration-1 Qwen3-8B-Base compositions of T1/T2.

The declared dataset dependency `art_j3Rm_lr2nzR6` ("Source data for an algorithm-choice coding bench") is the
sibling folder of that id in the repository. It is used only through the bench copies above. Its known solutions
come from `inputs/exp19/data/known_solutions_dep.jsonl`, already extracted from its `full_data_out.json`.

No user-uploaded files were used.

## 2. System, Python and packages

- **Machine actually used:** Linux (Debian 12 container), 14 CPUs (cgroup quota), 77 GB RAM limit, one NVIDIA
  GeForce RTX 4090 (24 GB, compute capability 8.9), driver 595.91.07, CUDA 12.8 wheels. There is no C compiler,
  so vLLM runs eager with FP8 Marlin kernels.
- **Python and environment manager:** Python 3.12.14, uv 0.6.14.

```bash
# HF engine, analysis and labelling (the versions pinned in pyproject.toml: torch 2.8.0, transformers 4.57.6, ...)
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
# vLLM, for the literal cell only (never imported together with the HF engine)
uv venv .venv_vllm --python=3.12
uv pip install --python .venv_vllm/bin/python -r env/requirements_vllm.txt     # vllm==0.11.0, torch 2.8.0
```

## 3. Models, environment variables and keys

Weights are downloaded with `src/download_models.py`, which writes `predictions/model_revisions.json`:

| Model | Revision | Used for |
|---|---|---|
| `Qwen/Qwen3-8B` | `b968826d9c46dd6066d109eabc6255188de91218` | HF bf16 engine: every Claim-C arm |
| `Qwen/Qwen3-8B-FP8` | `220b46e3b2180893580a4454f21f22d3ebb187d3` | vLLM: the literal cell |
| `Qwen/Qwen3-8B-Base` | `main`, resolved to `49e3418f…` | base-written intents (BINT) |

The full Base sha is in `predictions/model_revisions.json`.

Environment variables, by name only:

- `HF_HOME` / `HF_HUB_CACHE`: the model cache.
- `HF_TOKEN`: optional.
- `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`: the blind judges. A judge runs only when the runtime and AST labels
  disagree, plus in the audits. Judge answers are cached in `data/judge_cache*.jsonl` and `audit/`, so a re-run
  with the caches makes no new calls.

## 4. Commands, in the order they were run

The wall-clock start was 11:35 UTC (`results/t0.json`). The hard generation deadline was 4 h 45 min later.

```bash
.venv/bin/python src/download_models.py                  # 3 checkpoints into HF_HUB_CACHE
.venv/bin/python src/s0.py precision                     # predictions/precision_rule.json -> hf_bf16, vLLM FP8 checkpoint
.venv/bin/python src/s0.py hashes                        # inputs/SHA256SUMS, bench files vs commitment.json, screen sha256
.venv/bin/python src/s0.py seeds                         # results/seed_collisions.json (0 collisions)
.venv/bin/python src/s0.py recheck                       # results/labeller_recheck.json (all references pass)
.venv/bin/python src/prereg5.py commit0F                 # literal-cell spec + analysis_f.py into commitments.log
.venv_vllm/bin/python src/vllm_literal.py all            # S2 literal cell: 100 traces, ~15 min
.venv/bin/python src/label_worker_v4.py --raw data/literal_samples.jsonl --out data/literal_labels.jsonl
.venv/bin/python src/analysis_f.py                       # results/literal_cell.json
.venv/bin/python src/prompts5.py                         # prompts/prompts.jsonl (430 prompts, all assertions)
.venv/bin/python src/gen5.py base,tests,calib,ec,knobs &  # GPU: blocks on commit0C, then commit1 (below)
.venv/bin/python src/label5.py &                         # labels follow data/samples_raw.jsonl
.venv/bin/python src/prereg5.py commit0C                 # after the format pilot passed (see deviations D-pilot, D-parser)
.venv/bin/python src/prereg5.py commit1
.venv/bin/python src/label_worker_v4.py --raw data/engine_check_raw.jsonl --out data/engine_check_labels.jsonl
bash src/after_queue.sh &                                # restore dropped cells if the queue ends early (amendment A2)
.venv/bin/python src/audit5.py all                       # lexicon audit, style re-gate, novelty audit
.venv/bin/python src/analysis_ec.py                      # results/engine_check.json
.venv/bin/python src/analysis_c.py                       # Claim C: results/claim_c.json and the other result files
.venv/bin/python src/tests_cpu.py                        # results/tests_cpu.json
.venv/bin/python src/figures5.py                         # figures/F1-F6
.venv/bin/python src/outputs5.py                         # method_out.json, then the aii-json mini/preview variants
.venv/bin/python audit/rederive.py                       # results/rederive.json
```

In the real run, the post-generation steps were chained by `bash src/finalize.sh`:

1. Wait for the restore stage and the labeller.
2. `audit5.py novelty`.
3. `analysis_f` → `analysis_ec` → `analysis_c --workers 12`.
4. `figures5`, `outputs5`, `rederive`, `outputs5`, `report5`.
5. The aii-json validation and the mini/preview files.

After that, `.venv/bin/python src/posthoc5.py` (post-hoc label-vocabulary harmonisation, A4) and
`.venv/bin/python src/outputs5.py` were run once more.

`method.py` wraps the same stages: `.venv/bin/python method.py <stage>`.

The real run had three restarts of the GPU stage, all resumable:

1. The format pilot failed with the v1 wording. The model obeyed the specification's code-block line.
2. The wording was revised once, as the plan allows.
3. The parser was fixed for the literal `<1>. <Name>:` form.

All three are logged in `results/deviations.jsonl`.

**Seeds.**

- Common random numbers: `u_stream(task, w, k)` = PCG64 uniforms seeded by `stable_seed(task, w, k)`, the sha256 of
  the '|'-joined key (`src/cfg.py`).
- PN directions: `stable_seed(task, 'PN5', w, k)`.
- Calibration: `'PNCAL'` and `'CAL'`.
- Intents: `'IFG:intent'` and `'BINT:intent'`.
- Stage streams: `'PSL:A'`, `'PSL:B'` and `'EAP:A'`.
- Picks: `'EAP_pick'` and `'PSL_pair'`.
- Literal cell: `stable_seed('T2', w, k)` and `stable_seed('T2', w, k, 'answer')`.
- Bootstrap: `BOOT_SEED5 = 20261021`.

**Approximate runtimes on the RTX 4090.**

| Stage | Time |
|---|---|
| Literal cell (vLLM) | 15 min |
| Base intents | 4 min |
| GPU tests | 1 min |
| DMD calibration | 15 min |
| Engine check | 3 min |
| Knob queue | ~2 h |
| Analysis with bootstraps | ~15 min on 12 CPU workers |

## 5. What you should get

| File | Contents |
|---|---|
| `results/literal_cell.json` | Claim F: C_T, Clopper-Pearson bounds, completion per T, noise floor, pairing with exp21 |
| `results/claim_c.json` | Claim C: verdict, per-task H5 of PN and of each text sampler, P(PN >= best text), D_bar, sensitivities |
| `results/pn_vs_dmd.json` | PN vs departure-matched decoding (exact McNemar per task and pooled) |
| `results/plain_vs_twin.json` | PN plain vs PN twin |
| `results/landings.json` | moves, landing sets, EAP lists |
| `results/knob_table.json` | H5 / P15 / P20 with CIs for every knob class and task |
| `results/engine_check.json` | bf16 vs exp19's FP8 rows |
| `predictions/dmd_temperatures.json` | the committed DMD temperatures |
| `method_out.json` | everything above, with per-trace and per-slot datasets |

**Headline numbers you should get** (all in `results/summary.md` and `README.md`):

- **Claim F:**
  - C_T = 0 of 20 seeds, Clopper-Pearson one-sided 95% upper bound 0.139.
  - Completion 100/100; every final label is Dijkstra (heap).
  - Repeat noise floor: 4/20 byte-identical traces, label agreement 1.00.
  - Label agreement with exp21: 1.00 on 100 pairs.
- **Claim C:** DISCONFIRMED. PN wins 1 of 5 decisive tasks (T03).
  - H5 of PN: T03 1.98, T10 1.09, T2 1.18, T05 1.17, T1 1.06.
  - Best text sampler: EAP 1.83, BINT 2.53, BINT 1.45, BINT 1.61, EAP 1.08.
  - D̄ = −0.40 [−0.70, −0.24], from 2,000 replicates.
  - P(PN ≥ best): 0.58, 0.00, 0.06, 0.01, 0.38.
- **PN vs DMD:** at α 2, the pooled discordant counts are 19 vs 3 (exact p = 0.0009); at α 1, 4 vs 3.
- **Run size:** 7,060 knob rows in data/samples_raw.jsonl. The restored P5 cells (ND10 PSL-lite/BINT) were cut by the
  deadline on R3 (stage B incomplete) and R6 (not run). OpenRouter spend: USD 0.12.

Small Monte-Carlo differences in the hull prices (±0.02 in Hill) come from rarefaction draws. These are seeded,
so a re-run on the same rows is exact.

GPU decoding is deterministic for a fixed batch composition (unit test U1). On another GPU model, or with a different
batch size, bf16 kernels can pick different reductions, and individual token paths can then diverge
(`results/engine_check.json` quantifies this against the FP8 engine). The literal cell runs vLLM on Ada without
batch invariance. Its repeat at T 0.7 is byte-identical on 4 of 20 traces, with identical labels on 20 of 20.
