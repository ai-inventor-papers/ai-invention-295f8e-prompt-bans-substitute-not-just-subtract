# Reproducing Claim E (Gemma base-repertoire replication)

This file describes what was **actually run**, in order, including the interruptions. It ran on 2026-10-21 (UTC) on
one GPU server. Every path below is relative to this folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository.

```bash
git clone <URL of the run's repository>
cd <repository>/<this artifact's folder>        # the folder that holds this file
```

**Upstream artifacts** are sibling folders of this one in the repository, each named by its artifact id:

| Short name | Artifact id | What it supplied |
|---|---|---|
| exp23 | `art_k6nzFCDLOjQP` | the iteration-4 Gemma artifact: engine, push and unit code, labellers, rows and forecasts. Also its verified copies of the bench (`art_0ndRfWKBWclR`), suite (`art_8_ULPE8jJQc_`) and templates (`art_6zBfl3kDjeiP`). |
| exp11 | `art_0ndRfWKBWclR` | `bench/commitment.json`, which the bench copy is verified against |
| exp18 | `art_ccAbfJVcv0LO` | the known-solutions index for the novelty audit |
| eval3 | `art_sV0cQ3ef1ZRQ` | the frozen iteration-4 screen (`screen.json`) |
| dependency | `art_j3Rm_lr2nzR6` | the source data (10 datasets): noun bank, known-solution corpus, harness sanity sets |

- **No upstream folder is needed to re-run the experiment.** Everything this artifact read is already copied into
  `inputs/`, and `inputs/SHA256SUMS` hashes every copy.
- **To re-stage from the sibling folders**, run `.venv/bin/python src/stage_inputs.py`. The one environment
  variable `AII_ARTIFACTS_DIR` sets their common parent folder; the default is the parent of this folder.
- **One input has no recorded artifact id.** That is the iteration-4 seed list `inputs/exp22/src/cfg4.py`, copied
  from iteration 4's `gen_art_experiment_22`. The published copy is the one the seed audit read.
- **No user-uploaded input was used.** The run's user-uploads folder was empty.

## 2. System, Python and libraries

- **OS:** the run used Debian GNU/Linux 12 (bookworm) in a container. Any recent Ubuntu works.
- **GPU:** one NVIDIA L4 (23 GB VRAM, compute capability 8.9). The driver was 595.91.07; the CUDA 12.8 runtime
  comes from the torch wheel.
- **CPU and RAM:** 6 vCPU (cgroup quota) and 57 GB RAM.
- **Python 3.12**, plus a system CPython 3.12 on `PATH`. The frozen labellers run candidate programs in fresh
  `python3.12 -I -S` subprocesses. `BENCH_SANDBOX_PYTHON` (bench) and `SANDBOX_PYTHON` (T1/T2 suite) can point
  them at another stdlib-only CPython 3.12.
- **uv** 0.6.14 (no pip inside the venv).

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml
```

`pyproject.toml` pins all 84 installed packages with `==`; it is identical to `uv pip freeze` of the venv used. The
main ones are torch 2.8.0 (cu128 wheels), transformers 4.57.6, safetensors 0.8.0, huggingface-hub 0.36.2,
tokenizers 0.22.2, numpy 2.2.6, scipy 1.18.1, pandas 3.0.6, matplotlib 3.11.2, openai 3.35.1, loguru 0.7.3 and
zss 1.2.0.

## 3. Models, environment variables, keys (names only)

| Name | Needed for |
|---|---|
| `HF_TOKEN` | gated Gemma weights. Accept the Gemma licence for `google/gemma-3-4b-it` and `google/gemma-3-4b-pt` first. |
| `HF_HOME` / `HF_HUB_CACHE` | where the weights go. The run used a shared cache outside this folder. |
| `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` | LLM judges: inline labeller disagreements, re-gate, audits. Total spend USD 0.39. |
| `AII_ARTIFACTS_DIR` (optional) | parent folder of the sibling upstream artifact folders (staging only) |
| `AII_DATA_FIG_GEN` (optional) | path to the aii-data-fig-gen `scripts/` folder, for house-style figures. Without it, plain matplotlib is used. |

Pinned weights:
- `google/gemma-3-4b-it` @ `093f9f388b31de276ce2de164bdc2081324b9767`
- `google/gemma-3-4b-pt` @ `cc012e0a6d0787b4adcc0fa2c4da74402494554d`

`predictions/commit_E1.json` records their LFS sha256 and verifies them against the Hub. Download them with:

```bash
.venv/bin/python src/download_models.py          # ~45 s per model on the run's network
```

## 4. Commands actually run, in order

All commands run from this folder with `.venv/bin/python`. The UTC times are from `logs/` and `commitments.log`.

| # | Command | What happened | Wall time |
|---|---|---|---|
| 1 | `src/download_models.py` | both pinned snapshots | 1.5 min |
| 2 | `src/stage_inputs.py`, then `src/stage_inputs.py --recheck` | inputs staged and hashed; bench verified against the ITER2 commitment; dependency extracted (all 10 datasets); seed audit; labeller re-check (13 bench gates reproduced, suite 22/22) | 3 min |
| 3 | `src/gen.py it_tests` | GPU tests U1–U4 and U9; U5 reference logits | 1 min |
| 4 | `src/commit0.py` | **commit #0** (13:10:30Z): protocol, frozen analysis, input hashes, hardware | <1 min |
| 5 | `src/label_worker.py` (background, whole run) | labels every row of `data/raw_*.jsonl`. Restarted three times: after a regex fix in code extraction (13:24), after dropping the labels of the truncated pt batch (13:35), and after adding the harness-error guard (14:33, deviation D14). | — |
| 6 | `src/gen.py engine_check`, then `src/engine_check_eval.py` | exp23 slot keys, direction 9003, cap 640: **PASS**, 100% per-slot label agreement | 3 min |
| 7 | `src/tests_cpu.py` | CPU tests T1–T8 pass | 2 min |
| 8 | `src/gen.py stage1_it` | it twin (N=50 per task), novelty (N=30 per task), clean it states written to `cache/` | 8 min |
| 9 | `src/gen.py stage1_pt` | **first attempt stopped** after one pt-chat batch at the 1,536 cap (298 s, rambling output) | 5 min |
| 10 | `src/truncate_ptchat.py` | truncated that batch to 640 tokens, which equals a 640-capped run under CRN (deviation D4) | <1 min |
| 11 | `src/gen.py stage1_pt` (with `PT_CHAT_CAP = 640` in `src/gen.py`) | U5 passed; pt-chat N=100 per task; pt plain N=50 per task; pt states written to `cache/` | 55 min |
| 12 | `src/chain_after_pt.sh <pid of step 11>` | waited for labels, then ran the four sub-steps 12a–12d below | 60 min |
| 12a | `src/predictors.py draft` | D_u and r_u for the opening ladder | |
| 12b | `src/gen.py ladder` and `src/regate.py`, in parallel | opening-margin rival; re-gate sample, structural audit, iteration-4 rescoring | |
| 12c | `src/predictors.py commit1` | **commit #1** (14:41:55Z), before any push row | |
| 12d | `src/gen.py stage2_pipelined` | 16 fresh directions × α 1, 2 × N=10 plus plan noise; each task's confirmation top-up runs after the next task's stage 1 | |
| 13 | `src/amend_M.py` (during step 12d) | **commit #1b** (14:45:48Z): massive set M* of 5 channels, before any transplant row (deviation D11) | <1 min |
| 14 | `src/rejudge_disputed.py` | re-judged 104 rate-limited `disputed` rows (sensitivity only, D17) | 1 min |
| 15 | `src/chain_stage3.sh <pid>` | `gen.py stage3_valid`, then `transplant_decide.py` (λ = 1), then `gen.py stage3`. **Stopped before any transplant row was written**, to replace the RND/XT edit by the split edit (D16). | 8 min |
| 16 | `src/chain_stage3.sh 1` | restarted: U6/U7 re-run (all pass), the validity rows reused, λ = 1, full transplant | 21 min |
| 17 | `src/chain_final.sh <pid>` | `novelty_audit.py`, `final_analysis.py`, `bookkeeping.py`, `outputs.py`, `audit/rederive.py`, `outputs.py`, `figures.py`, `report.py`, `tests_cpu.py` | 10 min |
| 18 | aii-json `aii_json_format_mini_preview.py --input method_out.json` | `full_` / `mini_` / `preview_method_out.json` | <1 min |
| 19 | `python3 -I audit/rederive_headlines.py` | second-code-path re-derivation of every headline number, with placebos (all match) | 4 s |

**Single-command equivalent.** `.venv/bin/python method.py` runs the same stages in the same order (see its `STAGES`
list) and starts the label worker. It does not replay the two interruptions (steps 9–10 and 15). Re-running from
scratch uses the final code: the 640-token pt-chat cap and the split RND/XT edit. `method.py --from analysis`
recomputes every result from the stored samples on CPU.

**Seeds and configuration.**
- **Common random numbers:** the uniform stream of slot (task, template, k) is `PCG64(stable_seed('iter5E', task,
  template, k))`. `stable_seed` is the sha256 of the parts joined by `|`.
- **Fresh push directions:** `unit(PCG64(s).standard_normal(2560))` for s = 52001…52016.
- **Plan-noise directions:** `PCG64(stable_seed('iter5E_PN', task, alpha, template, k))`.
- **Matched-random direction g:** `PCG64(stable_seed('iter5E_RND', u, w, k))`, with the M* channels zeroed.
- **Decoding:** temperature 1.0, top-p 1, no top-k, bf16 with sdpa, logits in fp32, CDF in fp64.
- **Caps:** bench 1,024 tokens; T1/T2 1,536; pt-chat 640; pt plain 768.
- **Batches:** the twin and pt-chat arms use multi-prompt batches of B = 50. Push, plan noise and transplant use
  single-prompt batches of B = 42. Confirmation batches keep their natural size.
- **Analysis:** permutation and bootstrap RNG seed 0 (numpy `default_rng`), 200,000 permutations, 10,000
  bootstrap draws.
- **Determinism:** the sampler is deterministic for a fixed GPU type, batch shape and library versions. On another
  GPU, bf16 kernels can change tokens on some slots. The engine check found 100% label agreement between
  iteration 4's RTX 2000 Ada and this L4.

**Runtime and cost.**
- Generation took 2.16 GPU-hours on the L4 (`results/timing_summary.json`).
- The whole pipeline took about 3.5 h of wall clock, because labelling overlapped generation.
- OpenRouter spend was USD 0.39 (`results/costs.json`).

## 5. What a reader should get

| File | Number(s) |
|---|---|
| `results/verdicts.json`, `results/e_a2.json` | **E-A2 PASS:** 5 of 7 landings equal the pt runner-up (exact Poisson-binomial p = 0.0252). Log score base − association = 1.496 nats (exact one-sided Wilcoxon p = 0.0234); base − proximity = 0.510 nats. |
| `results/e_a1.json` | **E-A1 INCONCLUSIVE:** Spearman ρ(β, E_u) = 0.421, one-sided permutation p = 0.0596 (n = 15). Rivals: twin modal share ρ = 0.668, novelty ρ = 0.640. |
| `results/transplant.json` | λ = 1. T04: 40/50 `builtin` under the transplant (twin 6/50). R6: 39/50 binary search (twin 4/50). Both have McNemar T vs XT p < 1e-11. RND pass is 0.16–0.50 and XT pass 0.00–0.22. Support share 2/7. |
| `results/novelty_audit.json` | 56 correct `other` programs; 0 novel (35 catalogue variants, 21 degenerate). |
| `results/rederive.json`, `results/rederive_headlines.json` | 0 mismatches, `all_match: true`; the placebos fail as required. |
| `figures/fig1`–`fig6` (PDF + PNG), `method_out.json` | the README figures; 12,290 examples in exp_gen_sol_out form |

These are the numbers to quote for Claim E (the secondary, second-family replication) in the run's paper. The
README's Results section gives them with their caveats: a replication on seen tasks, raw p before Holm, and
LOW_CORRECT β.
