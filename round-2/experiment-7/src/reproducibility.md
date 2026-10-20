# Reproducing the FRLP ban screen (substitute vs ladder)

Everything below is what was actually run for this artifact, in order, on one machine. All paths are relative to
this folder.

## 1. Get the artifact

This folder is published as one folder of a public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-folder>          # the folder that contains method.py and this file
```

The folder already contains every input copied in step 0.1: `suite/` (the iteration-1 task suite, hidden tests,
references, sandbox harness, labeller, gold set and judge cache), `data_in/` (iteration-1 samples and labels, the
exp4 random directions, the 718-noun bank). From step 0.2 on, nothing outside this folder is needed except the model
weights and, for the judge, an OpenRouter key.

Only step 0.1 (`src/copy_inputs.py`) reads other artifacts. It takes their folders from environment variables
(or from a `paths.local.json` that is not published):

| variable | artifact id | what is read |
|---|---|---|
| `FRLP_EXP1` | `art__skdlFp_o3e9` (iteration-1 gen_art_experiment_1) | canonical suite, labeller, exp1 samples/labels, prompts |
| `FRLP_EXP4` | `art_U5UKkFrOgSsE` (iteration-1 gen_art_experiment_4) | `directions/rand{1,2}_T{1,2}_L18.npy` |
| `FRLP_DS` | `art_j3Rm_lr2nzR6` (iteration-1 gen_art_dataset_1, declared dependency) | `full_data_out.json` -> concreteness_norms noun bank |

When the repository publishes those artifacts as sibling folders, point the variables at them, e.g.
`export FRLP_EXP1=../<folder of art__skdlFp_o3e9>`. No user-uploaded files were used (the run's upload folder was
empty).

## 2. System, Python and libraries

- Ubuntu (Linux x86_64), Python 3.12 (CPython 3.12 at `/usr/local/bin/python3.12` doubles as the stdlib-only sandbox
  for candidate programs; set `SANDBOX_PYTHON` if yours lives elsewhere). No C compiler was available, so vLLM ran
  with `enforce_eager=True`.
- `uv` 0.6.14. Environment: `uv sync --python 3.12` creates `.venv/` from `pyproject.toml`, where all 169 installed
  packages are pinned exactly (from `uv pip freeze`; the uv venv has no pip binary). Key pins: `vllm==0.11.0`,
  `torch==2.8.0` (CUDA 12.8 wheels), `transformers==4.57.6`, `tokenizers==0.22.2`, `numpy==2.2.6`,
  `pandas==3.0.6`, `scipy==1.18.1`, `pyarrow==26.0.0`, `rapidfuzz==3.14.6`, `loguru==0.7.3`, `openai==3.35.1`.
- Hardware actually used: 1x NVIDIA L4 (23 GB VRAM, 72 W power cap; clocks throttle to about 1 GHz under load),
  48 CPU cores, 503 GB RAM.

## 3. Model, data and keys

- Model: `Qwen/Qwen3-8B`, revision `b968826d9c46dd6066d109eabc6255188de91218`, bf16 weights, thinking off. If not
  cached: `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`
  (`FRLP_MODEL_SNAPSHOT` may point at a local snapshot folder instead). `HF_TOKEN` is optional.
- OpenRouter (only for the strategy-blind judge on runtime/AST disagreements, model `openai/gpt-4.1-mini`, cap USD
  0.5): `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`. This run spent USD 0.30 (671 calls; `results/openrouter_cost.json`).
  Re-running hits the judge cache (`suite/labeller/judge_cache.jsonl`) for every program seen here.

## 4. Commands, in the order they were run

All stage scripts live in `src/` and are run from there (`method.py <stage>` wraps them; seeds are fixed in
`src/config.py`).

```bash
uv sync --python 3.12
cd src
../.venv/bin/python copy_inputs.py            # step 0.1: 61 files + noun bank, sha256 -> results/inputs_manifest.json
../.venv/bin/python labelling.py              # step 0.2: labeller re-check (gold 0.965, references 22/22), ~1 min
../.venv/bin/python gate_events.py            # step 0.3: 19 gate events, hash-committed
../.venv/bin/python prompts_v2.py             # step 0.4: 604 conditions, filler ' .', 0/190 alignment failures, hash-committed
../.venv/bin/python gen_vllm.py --smoke       # 10 forced generations: format / finish_reason / no thinking text
../.venv/bin/python gen_vllm.py --max-num-seqs 48   # step 1: 3 adaptive rounds (440 + 370 + 360) + 220 free-form, ~16 min incl. labelling
../.venv/bin/python select_programs.py        # step 2: scrub, verify, select (seed 7), halves (seed 11), association profiles, ~3 min
../.venv/bin/python frlp_score.py --deadline 05:35 --precision tf32   # step 3 (see notes below), ~3.3 GPU-hours
../.venv/bin/python gate.py                   # step 5, run as soon as Q1+Q2 had finished
cd .. && bash audit/final_steps.sh            # analysis_misc, gate, c1 (2,000 bootstrap reps, seed 13; 200,000-draw nulls),
                                              # freeze, outputs, report, audit/rederive.py, outputs (~5 min CPU)
.venv/bin/python audit/synthetic_c1_test.py   # T0-5 synthetic tests of the C1 code
.venv/bin/python audit/synthetic_pipeline_test.py
.venv/bin/python audit/inject_readme.py       # README result tables from results/summary.md
```

Notes on what actually happened in step 3 (all logged in `logs/` and `results/deviations.json`):

1. The first two scorer validations failed: bf16 activations gave cached-vs-full differences up to 2.1 nats per
   program (`logs/scorer_validation_bf16_logits_FAILED.json`), and an fp32 lm_head on bf16 activations still gave 1.6
   (`logs/scorer_validation_fp32logits_bf16acts_FAILED.json`). Production scoring therefore keeps bf16 weights but
   runs fp32 activations with TF32 matmuls and an fp32 log-softmax (`--precision tf32`): 0.074 per program, 0.119
   per contrast (narrowly over the 0.10 target), 0.045 for B=1 vs B=8 (`logs/scorer_validation.json`).
2. Measured throughput was about 1,000 tokens/s, so the pre-registered cut rule set M = 20 programs per algorithm
   and 3 gate paraphrases (`logs/throughput.json`).
3. The queue was restarted twice from `scores/units_done.jsonl` (no unit is re-scored): once to reallocate Q7 to the
   unscrubbed denominators + gate set, once to put t1's Q7 first. `logs/deadline.txt` moved the GPU cutoff to 05:45;
   Q7 was partly scored and Q8 (shams) and Q9 (variant ii) were not run (`logs/queue_final.json`).
4. A loader bug (unit ids unique only within a task) was fixed before any C1 output was read; the gate was
   recomputed and re-committed (`commitments.log`).

Determinism: vLLM sampling uses per-request seeds (`int(sha256(task|forced:j|family|k|i|v2)[:8], 16)`); vLLM is
reproducible in distribution, not bit for bit. Teacher-forced scoring is deterministic given the same GPU type and
batch composition.

## 5. What you should get

| output | content |
|---|---|
| `results/labeller_recheck.json` | combined vs adjudicated 0.965 (eval split 0.966), references 22/22 |
| `results/yields.json`, `data/forced_selected.jsonl` | 11/11 algorithms measurable; bidirectional Dijkstra 14 labelled (descriptive family), comment-only scrub |
| `results/gate.json` | FRLP gate FAIL on (a) calibration; (b) and (c) pass; see README |
| `results/c1.json`, `results/summary.md` | C1 SHARE per task and pooled with bootstrap CIs, AIM and nulls, branches (descriptive) |
| `results/sensitivity.json`, `results/secondary.json` | variant and u-variant SHAREs, two-step landing, iteration-1 sham checks |
| `results/independent_rederivation.json` | independent recomputation of headline numbers (match to 1e-9) + placebo |
| `frozen/` | profiles and code hashes for the confirmation bench |
| `figures/F1-F6` | gate, gain heatmaps, ladder vs X-specific sums of squares, generic cosines, prime/veto, ESS |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out` output: 19 gate events + 11 C1 rows |

The README's "Results" section quotes every headline number with its source file. No paper is part of this
artifact; a paper built on it should cite these files.
