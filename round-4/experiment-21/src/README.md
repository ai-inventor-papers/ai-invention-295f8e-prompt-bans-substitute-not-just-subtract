# Same seed: temperature vs plan nudges (iteration 4, C1-seed, Qwen3-8B)

Does turning up the **temperature** change *what algorithm* a code model writes, or only *how it phrases* it? And does
a small **plan nudge** (a random push on the residual stream at the task-specification tokens) change the algorithm
under the *same* token noise? This repository answers both with a seed-coupled 2x2 design on Qwen3-8B (thinking off),
plus a thinking-on arm in vLLM. Every token seed keeps one noise stream across every condition, so a seed's programs
differ only by the condition (common random numbers, CRN).

Tasks:
- **T2**: weighted shortest path; the default is Dijkstra.
- **T1**: grid path; the default is BFS.
- **T03**: k-th smallest; the default is a full sort.

Seeds: 20 per task, one per slot (task, template W1-W5, k 0-3).

## Bottom line

**Verdict: PARTIAL.** H-T, H-PHR and H-CON hold. H-PN fails on one task only: T03, where C_PN = 4.55 against the
committed 5. All rules were hash-committed before the first decisive sample (`predictions/prereg_c1seed.json`,
`commitments.log`).

Under one fixed noise stream per seed:
- **Temperature never changed the algorithm.** T was moved through 0.3, 0.7, 1.0 and 1.3, plus top-k 10 at 0.7.
  - The idea stayed the same in **20/20 seeds** on T2, T1 and T03 with thinking off.
  - It also stayed the same in **20/20 seeds on T2 with thinking on** (vLLM, 100/100 traces completed).
  - Each of these counts is C_T = 0; the exact 95% upper bound on the per-seed change rate is 0.168.
- **The plan nudge changed it in many seeds.** One random isotropic direction was added at blocks 12-23, task-spec
  positions, prefill only, at 1 ban unit (alpha 1), T 1.0. Averaged over all 20 three-direction subsets of 6
  directions, C_PN was:
  - **17.25 of 20** seeds on T2 (subset range 12-20);
  - **4.55** on T03 (range 0-7);
  - 2.5 on T1 (descriptive).
- **The paired seed-level contrast is decisive.** x_s = PN change minus T change, pooled over T2 and T03 (40 seeds):
  mean 0.545, 95% bootstrap CI [0.41, 0.67], one-sided sign-flip **p = 1.0e-5** (100,000 draws). This is the
  artifact's single entry to the iteration's secondary Holm family (C1-seed). The condition-shuffle placebo gives p
  < 0.05 in 2% of 200 runs (median p 0.55). The independent re-derivation's placebo (own RNG, 200 runs) gives
  10.5%; pooled over 1,440 placebo runs the rejection rate is about 6%. Two further checks:
  - an assumption-light within-seed condition-permutation test puts the observed mean 0.545 above all 200 placebo
    means (max 0.155), p = 0.005, the minimum at that draw count;
  - **novelty audit (A9):** the only correct off-catalogue ('other') program is a naive Dijkstra (two blind judges
    disagreed, deepseek resolved it as LABELLER MISS), so NOVEL = 0.
- **Temperature changes phrasings, not ideas.** Phrasings per idea (PPI, from AST 4-gram clusters) grow with T: the
  pooled slope of log PPI on T is 0.64, 0.70 and 0.81 at theta 0.7, 0.8 and 0.9, and every 95% CI excludes 0. The
  growth is almost all on T1 (3 to 11-17 clusters). T2 is flat-ish (1 to 2-3) and T03 does not move (2 at every T).
- **Why H-PN fails on T03.** The plan prescribes the protocol-v4 unit (exp13) for T03. That unit is about 0.77x the
  unit the screen used (deviation D4), so alpha 1 here is a weaker push than the screen's alpha 1. Three readings
  point the same way:
  - At alpha 2, T03 reaches C_PN 10.6.
  - Under the Gumbel-max coupling (arm iii), T03 reaches C_PN 5.8.
  - The committed power expectation for T03 was 11.4 (9.2 after unit adjustment); the observed value is 4.55.

| task | C_T off (4 T) | C_T on (4 T) | C_PN a1 T0.7 | C_PN a1 T1.0 | C_PN a2 T0.7 | C_PN a2 T1.0 | correct-only C_PN a1 T1.0 |
|---|---|---|---|---|---|---|---|
| T2 | 0/20 | 0/20 | 17.70 | **17.25** | 18.45 | 19.05 | 10.25 |
| T03 | 0/20 | - | 4.40 | **4.55** | 10.30 | 10.60 | 4.05 |
| T1 | 0/20 | see arm (i) | 1.50 | 2.50 | 8.95 | 8.70 | 1.45 |

C_PN is the mean over the 20 three-direction subsets of the number of seeds whose idea changes across {no PN, 3 PN
draws}. Sensitivities on C_T:
- correct-only and invalid-as-label C_T are 0 on every task;
- with TOPK10 as a 5th condition, C_T stays 0;
- with the min-p T 2.0 cell as a 5th condition, C_T is 1 on T2 and T03 (one BF/SPFA and one quickselect program out
  of 20) and 0 on T1.

### What the nudge costs and where it lands

- **Landings.** At alpha 1 and T 1.0, T2 PN programs land on Bellman-Ford/SPFA (52 of 60 off-default programs; 8
  'other'), T03 on quickselect (11/11) and T1 on DFS (5).
- **Correctness cost.** Plan noise costs correctness on T2:
  - the pass rate is 0.63 at alpha 1, T 1.0 and 0.42 at alpha 2, against 1.00 without PN;
  - restricted to correct programs, the T2 count drops to 10.25 (still at least 5).
- **Diversity.** Rarefied Hill-1 of correct ideas at alpha 1, T 0.7 is 1.87 on T2, 1.31 on T03 and 1.15 on T1. Top-k
  10 gives 1.00 on all three, as predicted (at most 1.10).
- **Interaction.** Under the escaping direction, T 0.7 vs T 1.0 changes the label in 5/20 (T2) and 2/20 (T03) seeds,
  against 0/20 without PN. Temperature only acts on the idea once the plan has been nudged off the default.

### Independent re-derivation

`audit/rederive.py` shares no code with `analysis/`. It reads `data/samples.jsonl` alone, using its own AST
normaliser, BFS components, `numpy.polyfit` and Python's `random`. It recomputes:
- every C_T;
- every C_PN (4 per task);
- the pooled x_s mean and its sign-flip p;
- the PPI slopes at 3 thetas per task;
- the thinking completion rates and the T2 thinking-on C_T;
- the FP8 JS.

Result: **0 mismatches in 33 checks** (`results/rederive.json`). It also verifies the hash chain (0 breaks) and
that commit #0 (05:02:05Z) precedes the first decisive row (05:11:10Z).

### Controls

- **Positive control.** The engine check re-ran the screen's T03 rand9002 and T2 rand9004 cells with their twins
  (N = 50 each). It reproduces exp17 **byte for byte**:
  - 200/200 token-identical programs;
  - T03 rand9002: size-k heap 19, quickselect 16, full sort 15;
  - T2 rand9004: Dijkstra 26, BF/SPFA 24;
  - verdict REPRODUCED.
- **CRN exactness.**
  - The filler repeats (same slot, different batch-mates) are byte-identical in 60/60.
  - The engine-check slots k 0-3 match the 2x2's NO-PN T1.0 rows in 40/40.
  - GPU unit tests U1-U5 pass (`results/unit_tests_gpu.json`).
- **vLLM noise floor.** The T 0.7 thinking-on repeat diverged byte-wise in all 20 traces (first divergence at token
  34-653). Ada has no batch invariance (CC 8.9 < 9.0). Yet the final label agreed in 20/20 and the first approach
  named in 20/20, so the repeat change count is 0. The temperature count of 0 is read against a floor of 0.
- **Coupling check.** U6 recomputed the first sampled token in the parent process as argmax(probs / q), with q from an
  identically seeded CUDA generator. It matched 32/32 requests, which confirms that vLLM 0.11 couples by an
  exponential race (Gumbel-max) with step-indexed noise.

### Thinking on (T2, vLLM, 16k cap, two-pass early exit)

| T | completed | median thinking tokens (max) | final label | first approach named |
|---|---|---|---|---|
| 0.3 | 20/20 | 4,097 (7,381) | Dijkstra 20 | Dijkstra 20 |
| 0.7 | 20/20 | 3,952 (6,327) | Dijkstra 20 | Dijkstra 20 |
| 1.0 | 20/20 | 4,320 (8,808) | Dijkstra 20 | Dijkstra 20 |
| 1.3 | 20/20 | 4,020 (12,612) | Dijkstra 20 | Dijkstra 20 |
| 0.7 repeat | 20/20 | 4,001 (7,427) | Dijkstra 20 | Dijkstra 20 |

- Every program passed the hidden tests.
- **First-approach lexicon audit.** gpt-4.1-mini named the first approach of 20 traces and agreed with the lexicon on
  20/20. Kappa is undefined because every trace names Dijkstra.
- **FP8 cross-check** (thinking off, T2 twins, N = 50 each):
  - vLLM FP8 (weight-only Marlin): Dijkstra 50/50, mean 188.4 tokens.
  - HF FP8 W8A8: Dijkstra 50/50, mean 188.5 tokens.
  - JS = 0 bits. This is a weak check by construction, since the cell is all-Dijkstra.

### Optional arms

- **(iii) Gumbel-max replicate (HF exponential race, T2 + T03).** The coupling does not change the conclusion.
  - C_T = 0 on both tasks.
  - C_PN(alpha 1, T 1.0) = 16.05 on T2 and **5.8 on T03**.
  - Pooled x_s mean 0.546, p = 1.0e-5.
- **(iv) Min-p extended dial (T 2.0, min-p 0.1).**
  - T2: Dijkstra 19, BF/SPFA 1, all passing.
  - T03: full sort 19, quickselect 1, all passing.
  - T1: BFS 20, pass 0.90.
  - Even T 2.0 moves at most 1 seed in 20.
- **(ii) Thinking on with PN** (T2, alpha 2, T 0.7, 2,048-token cap, the 3 directions with the highest thinking-off
  alpha-2 off-default share: D46003, D46002, D46005). The first approach named moved in 1/10, 0/10 and 0/10 seeds.
  The committed expectation (at least 3 of 10 for some direction) is **not met**. Once the model thinks, the prefill
  nudge no longer redirects the first idea it names.
- **(i) T1 thinking on (reduced to 10 seeds)**: all 40 traces completed within the cap (median 5.2k-6.2k thinking tokens, max 9.0k). Every final program and every first approach named is BFS, so C_T = 0 of 10 seeds (CP 95% upper rate 0.31). Coupling: vLLM exponential race.

## Design

| block | conditions | per seed |
|---|---|---|
| NO-PN (temperature) | T 0.3 / 0.7 / 1.0 / 1.3, top-p 1; top-k 10 at T 0.7 | 5 programs |
| PN (plan noise) | 6 fixed isotropic unit directions (PCG64 seeds 46001-46006) x alpha {1, 2} ban units x T {0.7, 1.0} | 24 programs |
| filler repeats | NO-PN T 1.0 again, different batch-mates | 1 program |

- **PN edit.** exp17's displacement-targeted hook: h <- h + (alpha n[l,p] - (h - h_twin_clean).u) u, on the block
  outputs 12-23 at positions S = [p1, spec_end), fp32, prefill only. The realised component along u matches
  alpha * n within 2e-4 (U3).
- **Units.**
  - T1 and T2 use exp17's norms.
  - T03 uses exp13's protocol-v4 unit.
  - The engine check uses exp17's T03 unit, to match the screen.
- **Coupling.**
  - Thinking off: inverse-CDF in vocabulary order. One PCG64 uniform per row and step is drawn from
    u_stream(task, w, k), with float64 CDFs, prune=False and a fixed batch shape of B = 20 rows of one template.
  - Thinking on: vLLM per-request seeds (exponential race).
  - Arm (iii): an HF exponential race.
  - Because thinking-off and thinking-on counts use different couplings, every count above carries its coupling
    (`results/c1seed.json -> couplings`).
- **Labels.**
  - Mechanism-level labels come from the exp8 suite (T1/T2) and the exp11 bench labeller (T03): hidden tests and a
    runtime tracer first, AST rules second, and a blind judge only on disagreement (222 of 3,150 programs).
  - 'invalid' and 'unresolved' are excluded from change counting.
  - The labellers were re-checked first: 22/22 path references, 6/6 T03 references, T03 gold agreement 0.964 = gate.

## Deviations (full list: `results/deviations.json`)

| id | deviation | effect |
|---|---|---|
| D1 | 16 GB RTX 2000 Ada (CC 8.9), so the HF engine is exp17's FP8 W8A8 (the screen's precision and card), as the plan's S0/F2 branch prescribes | no bf16 claims |
| D2 | vLLM runs the official FP8 checkpoint with weight-only Marlin kernels, eager, torch.compile off: there is no C compiler (as in exp18) | A8 compares the two FP8 paths |
| D3 | The screen's escape rule is not defined anywhere on the run volume. It is reconstructed as excess >= 0.20 and pass ratio >= 0.85 on k 0-9 | descriptive only |
| D4 | The T03 protocol-v4 unit (exp13) is 1/1.30 of exp17's unit. This engine reproduces exp17's unit (ratio 0.997), so the gap is a property of exp13's unit, not of FP8 | alpha 1 on T03 is a weaker push than the screen's; the committed T03 power was optimistic |
| D5 | The unit sensitivity was recomputed in FP8 rather than bf16 (bf16 does not fit): T1 1.002, T2 0.992, T03 1.304 | none |
| D6 | The RAM watchdog counted page cache and stopped two launches before any decisive sample. It was replaced by an RSS-based watchdog (`src/memwatch.py`) | engine load time only |
| D7 | OpenRouter /key returns 403 through the proxy, so spend is read from usage.cost | none |
| U7 | The worst case (T1, B = 20, forced to 1,536 tokens) peaked at 94% of VRAM, above the 92% criterion, but ran without OOM. Memory is deterministic per shape, so B = 20 was kept | none |
| D13 | Arm (ii)'s causal-mask identity is exact on 4 of 5 templates. W3 differs by up to 192 (an FP8 GEMM-shape effect) | PN is anchored to the thinking-on clean prefill |

## Layout

| path | what it holds |
|---|---|
| `method.py` | orchestrator: `--stage setup / screen / tests / commit / hf_chain / smoke / engine_check / grid / optional / label / analyse / export / rederive` |
| `src/vllm_think.py` | G1: U6 vLLM tests, thinking-on T2 (two-pass), FP8 cross-check (run with `.venv_vllm/bin/python`) |
| `src/vllm_t1.py` | optional arm (i) wrapper (T1 thinking on, 10 seeds) |
| `src/grid.py` | HF stages: smoke tests U1-U5 and U7, unit sensitivity, engine check, the 2x2 layout and runner, optional arms (ii)-(iv) |
| `src/engine4.py` | exp17 sampler extended with per-row T, top-k, min-p and the coupling (`invcdf` / `gumbel`) |
| `src/engine.py`, `hooks.py`, `prompts.py`, `cfg.py`, `label_worker.py`, ... | exp17 source, byte-identical (verified in `results/input_hashes.json`) |
| `src/cfg4.py`, `screen.py`, `prereg.py`, `s0_setup.py`, `label4.py`, `lexicon.py`, `memwatch.py` | constants, S1/S2, commit #0 and the hash chain, S0 checks, label worker, first-approach lexicon, RAM watchdog |
| `analysis/core.py` | committed analysis core: change counts, subset-averaged C_PN, x_s and the sign-flip test, AST shingles, PPI, Hill numbers |
| `analysis/report.py`, `figures.py`, `llm_audits.py`, `export.py` | A1-A10, figures, the A7/A9 LLM audits, `method_out.json` |
| `audit/rederive.py` | independent re-derivation from `data/samples.jsonl` (no shared code) |
| `tests/test_analysis.py` | synthetic tests of the analysis code (all pass, `results/tests_cpu.json`) |
| `predictions/` | `prereg_c1seed.json` (commit #0) and `screen.sha256` |
| `commitments.log` | sha256 hash chain. Commit #0 at 05:02:05Z, before the first decisive row at 05:11:10Z, holds the rules, analysis core, screen and power. Commit #0b at 08:46Z chains the code written after registration (HF sampler, reporting, audit) and the final results |
| `env/` | pinned requirements and `uv pip freeze` outputs of both venvs (`pyproject.toml` holds the same pins) |
| `run_gpu_chain.sh`, `run_t1_chain.sh`, `run_final.sh` | PID-chained launchers of the GPU stages and the final CPU pipeline |
| `data/samples.jsonl` | one merged row per program: protocol fields, label, pass, code, token ids, thinking fields |
| `data/samples_raw.jsonl`, `labels.jsonl`, `raw_thinking.jsonl`, `realised_norms.jsonl` | raw generations, labels, full thinking traces and token ids, and the realised edit displacements of every PN prefill |
| `results/` | `c1seed.json` (every count, test, CI and verdict), `phrasing.json`, `thinking.json`, `engine_check.json`, `determinism.json`, `fp8_crosscheck.json`, `table_1ac.json`, `screen.json`, `expectations.json`, `unit_tests_gpu.json`, `u6_vllm.json`, `unit_sensitivity.json`, `novelty_audit.json`, `first_approach_judge_audit.json`, `dependency_usage.json`, `costs*.json`, `timing*`, `deviations.json`, `rederive.json` |
| `figures/` | F1 coupling map, F2 Hill-1 vs PPI, F3 changed-seed counts, F4 thinking on, F5 theta sweep (PDF + PNG) |
| `inputs/` | read-only copies of the iteration-2/3 inputs (exp8 suite, exp11 bench, exp13 units and samples, exp17 labels, prompts, directions and screen rows, exp18 known-solution index, dependency previews) |
| `method_out.json` (+ `full_` / `mini_` / `preview_`) | exp_gen_sol_out: datasets `seed_coupled_off`, `seed_coupled_on`, `engine_check`, `fp8_crosscheck`; metadata holds every analysis |

## How to run

```bash
uv venv .venv_hf --python=3.12 && uv pip install --python .venv_hf/bin/python -r env/requirements_hf.txt
uv venv .venv_vllm --python=3.12 && uv pip install --python .venv_vllm/bin/python -r env/requirements_vllm.txt
export PYTHONDONTWRITEBYTECODE=1
.venv_hf/bin/python method.py --stage setup        # S0 (CPU): inputs, hashes, hardware, labeller re-check
.venv_hf/bin/python method.py --stage screen       # S1 screen file + S2 power expectation
.venv_hf/bin/python method.py --stage tests        # synthetic tests of the analysis code
.venv_hf/bin/python method.py --stage commit       # commit #0 (hash chain)
.venv_hf/bin/python method.py --stage label --follow --minutes 300 &   # label worker (CPU)
.venv_vllm/bin/python src/vllm_think.py all        # G1: U6, thinking-on T2, FP8 cross-check (GPU)
.venv_hf/bin/python method.py --stage hf_chain     # smoke, unit sensitivity, engine check, 2x2, optional arms (GPU)
.venv_vllm/bin/python src/vllm_t1.py               # optional arm (i) (GPU)
.venv_hf/bin/python analysis/llm_audits.py         # A7 judge audit + A9 novelty audit (OpenRouter)
.venv_hf/bin/python method.py --stage analyse && .venv_hf/bin/python method.py --stage export
.venv_hf/bin/python audit/rederive.py
```

- `run_gpu_chain.sh` and `run_t1_chain.sh` sequence the GPU stages, waiting on PIDs.
- Every sampling stage is resumable: done slots are skipped.
- Hardware used: one 16 GB RTX 2000 Ada, 5 CPUs, 31 GB RAM.
- GPU time: HF sampling took 0.92 h, and vLLM generation about 1.7 h. That is about 2.6 h of GPU wall clock
  including model loads (`results/gpu_hours.json`, whose vLLM total counts the T2 stage-10 batch twice).
- OpenRouter spend was under USD 0.10 (`results/costs_summary.json`).
- The model weights live in the run's shared Hugging Face cache (`HF_HUB_CACHE`), not in this folder.

## Restoring removed files

| removed path | restore with |
|---|---|
| `.venv_hf/` | `uv venv .venv_hf --python=3.12 && uv pip install --python .venv_hf/bin/python -r env/requirements_hf.txt` |
| `.venv_vllm/` | `uv venv .venv_vllm --python=3.12 && uv pip install --python .venv_vllm/bin/python -r env/requirements_vllm.txt` |
| `src/__pycache__/` | `python -m compileall src` (also regenerated automatically on import) |
| `analysis/__pycache__/` | `python -m compileall analysis` |
| `audit/__pycache__/` | `python -m compileall audit` |
| `inputs/exp8/suite/tasks/__pycache__/` | `python -m compileall inputs/exp8/suite/tasks` |
| `inputs/exp11/bench/common/__pycache__/` | `python -m compileall inputs/exp11/bench/common` |
| Qwen3-8B, bf16 (shared cache, not in this folder) | `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` |
| Qwen3-8B-FP8 (shared cache) | `huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3` |

Everything else is kept where it is: `data/`, `results/`, `predictions/`, `figures/` and `inputs/` are text or
small files. `.aii/manifest.yaml` lists only the delete entries above. No activation tensors were saved; only
per-row displacement scalars are stored, as text.
