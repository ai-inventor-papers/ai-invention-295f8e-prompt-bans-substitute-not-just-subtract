# Predicting where coding bans send a model (iteration 3)

This repository tests whether ban-free signals can forecast where a named "do not use X" ban sends a collapsed code
model. The model is **Qwen3-8B** (bf16, Hub revision `b968826d`, thinking off), run on the 12 frozen bench tasks from
iteration 2. The bench had never seen a ban prompt before this run.

The run has three steps:

1. **Forecast without the ban text.** For each task's modal ban, four forecast families are built:
   - **SUBTRACT**: token vetoes of the default's distinctive n-gram (one-shot, persistent, up to 3 iterated rounds),
     coupled to the neutral-twin samples.
   - **LADDER**: generic pushes (nonce ban, novelty instruction, and 3 matched-norm random directions patched into the
     task-spec states at layers 12-23).
   - **ASSOCIATE**: free-form association answers (frozen in iteration 2).
   - **PROXIMITY**: AST tree-edit distance to the default's programs.

   All forecasts, n-grams, seeds, norms and the analysis code were **hash-chained and sealed** (`commitments.log`,
   `SEAL_BEFORE_BANS`) before the first ban sample.
2. **Sample the modal ban.** 5 templates × 20 samples per task, labelled with the gated bench labellers.
3. **Score.** Each family gets a mean log score under one frozen smoothing. The frozen advance rule (C1) and the C2b
   test (does the one-shot veto reproduce the ban's landing?) are then applied.

Everything ran on 2026-10-20 on one RTX 4090 (24 GB) and 14 CPUs. GPU wall-clock was about 45 min, including smoke
runs. Judge spend (OpenRouter) was **$0.024** over 344 calls.

## Main results

### Verdicts

| claim | frozen (committed) result | what drives it |
|---|---|---|
| **C1**: which forecast family predicts the ban's landing | **"SUBTRACTION/LADDER (LADDER)"**. Five gated events, all disagreeing. Wins: LADDER 3 (T03, T06, T10), PROXIMITY 2 (T05, T13), SUBTRACT 0, ASSOCIATE 0. Camp contest: BAN-FREE 3, PROXIMITY 2. | Two of LADDER's three wins (T06, T10) come from LADDER being **undefined and therefore scored as uniform**, while every defined forecast named the wrong survivor. Post-hoc, counting only wins by defined forecasts gives LADDER 1 and PROXIMITY 2, so **no family advances**. No family beats the uniform reference on average over gated events (mean log score minus uniform: LADDER +0.06, SUBTRACT −0.69, PROXIMITY −1.53, ASSOCIATE −1.78). On 3 of the 5 gated events no family's top-1 equals the realised landing. The data are therefore closer to "X-specific but unaimed" than to a ban-free win. |
| **C2b**: does the one-shot veto reproduce the ban's modal survivor | **UNDETERMINED** (0 eligible events) | The one-shot veto never reaches the required 0.5 avoidance on a gated task (T03 0.38, T10 0.33, others 0). Descriptively, the last iterated veto round is eligible on T06 and T10, and **both land elsewhere**: T06 lands on sort_adjacent vs the ban's index_marking (JS 0.77 vs null p95 0.09); T10 lands on dfs vs the ban's bfs (JS 0.58 vs 0.09). |
| template effect | strong | The banned share differs by wording: likelihood ratio 374 (df 4, p ≈ 1e-79). Mixed GLM SDs: template ≈ 2.0 logits [1.1, 3.5], template×task ≈ 1.25. The shuffled-template placebo is null (p 0.44). Under W4 ("X is not allowed here.") the default keeps ≥ 70% of samples on 10 of 12 tasks. |

### Forecasts committed before any ban sample (top-1 survivor; "–" = undefined, scored as uniform)

| task | D (default) | distinctive n-gram (source) | SUBTRACT | LADDER | ASSOCIATE | PROXIMITY | disagree |
|---|---|---|---|---|---|---|---|
| T03 | full_sort | `'    nums'` (FP8 pilot) | – | quickselect | quickselect | heapify_pop | yes |
| T04 | naive | `' needle:\n           '` (FP8 pilot) | – | – | kmp | builtin | yes |
| T06 | hash_set | `' set'` (FP8 pilot) | sort_adjacent | – | floyd | sort_adjacent | yes |
| T05 | hash_map | `' if complement'` (FP8 pilot) | – | – | sort_two_pointers | brute_force | yes |
| T10 | union_find | `' find'` (FP8 pilot) | dfs | – | dfs | label_propagation | yes |
| R1 | greedy_end | `' if start'` (bf16 re-derived) | – | – | dp_bisect | dag_longest_path | yes |
| T08 | iteration | `'('` (FP8 pilot) | – | matrix_power | matrix_power | memo_recursion | yes |
| R3 | kahn | `'.p'` (FP8 pilot) | – | – | dfs_postorder | – | no |
| T13 | sort_sweep | `' last'` (FP8 pilot) | – | – | interval_tree | union_find | yes |
| R6 | binary_search | `'_last'` (FP8 pilot) | – | – | bisect_module | bisect_module | no |
| T14 | sort_by_count | `'_counts'` (bf16 re-derived) | – | – | heap | heap | no |
| T11 | quadratic_dp | `' j'` (FP8 pilot) | – | patience_bisect | patience_bisect | patience_bisect | no |

SUBTRACT is undefined on 7 tasks because D keeps at least 0.5 of attempts in every veto round, so the default is
**not carried by a small set of surface tokens**. It is undefined on 3 more tasks because no round produced 20
non-default attempts.

### What the named ban did (100 samples per task; landing = attempted non-default programs)

| task | ban avoidance [Wilson 95%] | gate | ban landing | twin D share | one-shot veto avoid. | best ban-free push | band-patch avoid. | frozen-rule winner |
|---|---|---|---|---|---|---|---|---|
| T03 | 0.97 [0.92, 0.99] | pass | quickselect 59, size_k_heap 38 | 0.96 | 0.38 | novelty 1.00 | 1.00 | LADDER |
| T04 | 0.40 [0.31, 0.50] | fail | kmp 21, builtin 16, rabin_karp 2, z 1 | 1.00 | 0.00 | novelty 0.26 | 0.00 | – |
| T06 | 0.79 [0.70, 0.86] | pass | index_marking 73, floyd 5, sort_adjacent 1 | 1.00 | 0.00 | novelty 0.02 | 0.04 | LADDER (uniform) |
| T05 | 0.86 [0.78, 0.91] | pass | brute_force 86 | 1.00 | 0.00 | novelty 0.08 | 0.22 | PROXIMITY |
| T10 | 1.00 [0.96, 1.00] | pass | bfs 83, dfs 17 | 1.00 | 0.33 | rand3 0.26 | 1.00 | LADDER (uniform) |
| R1 | 0.00 [0.00, 0.04] | fail | – | 1.00 | 0.00 | none (0.00) | 0.00 | – |
| T08 | 0.34 [0.25, 0.44] | fail | other 33, fast_doubling 1 | 1.00 | 0.00 | novelty 0.40 | 0.00 | – |
| R3 | 0.08 [0.04, 0.15] | fail | dfs_postorder 8 | 1.00 | 0.00 | none (0.00) | 0.00 | – |
| T13 | 0.58 [0.48, 0.67] | pass | other 44, union_find 14 | 1.00 | 0.00 | none (0.00) | 0.14 | PROXIMITY |
| R6 | 0.03 [0.01, 0.08] | fail | other 2, bisect_module 1 | 0.80 | 0.42 | nonce 0.36 | 0.00 | – |
| T14 | 0.48 [0.38, 0.58] | fail | heap 32, quickselect_counts 15, other 1 | 0.96 | 0.04 | nonce 0.04 | 0.00 | – |
| T11 | 0.02 [0.01, 0.07] | fail | patience_bisect 2 | 1.00 | 0.00 | novelty 0.68 | 0.00 | – |

### What the numbers say

**Bans often fail on this model.**
- Only 5 of 12 modal bans pass the gate (avoidance ≥ 0.5 and ≥ 20 non-banned attempts).
- R1, R3, R6 and T11 keep their default on almost every sample, whatever the wording.
- Programs that keep the banned mechanism almost never name it. 88-100% of them contain no alias or display name of
  D (`descriptives.disguise`).

**Where gated bans land is mostly unforeseen by any ban-free signal.**
- T06 goes to **index_marking**, a mode the model rarely wrote even when explicitly forced (exp11 adherence 0.28;
  1 of 40 template-forced programs), and that no family nominated.
- T10 goes to **bfs**, while SUBTRACT and ASSOCIATE both said dfs.
- T13 goes mostly to "other".
- Spot checks of the labels:
  - T06's index_marking programs place each value at index value−1 (cyclic placement); 67 of 73 pass.
  - T13's "other" is a merge sweep **without sorting**, which fails every time (0 of 44 pass).
  - T08's "other" is Binet's closed form, which also fails (0 of 33 pass).
  - T10's bfs and T05's nested-loop brute force are genuine.
- Only T03 (quickselect: LADDER, ASSOCIATE and FRLP_FP8) and T05 (brute_force: PROXIMITY) were hit by a top-1.

**Token vetoes do not move the algorithm; they move the surface.**
- The distinctive n-gram fires in 95% of twin samples, and the redraw always avoids it (asserted).
- D survives every persistent/iterated round on 9 of 12 tasks.
- The model re-spells the same mechanism. Examples:
  - T03: `nums.sort()` becomes `return sorted(nums)[k-1]`.
  - T05: the next round's distinctive token is `' compliment'`, a misspelling that dodges `' complement'`.
  - Later rounds often veto comment words (`' through'`, `' Over'`).
- The vetoed n-gram's text reappears under another token split in 23% of one-shot samples (54% by round 2).
- Where vetoes do move off D, the outputs are mostly invalid (no parseable `solve`).
- The **sham veto** of a shared token (e.g. the indentation token after `def solve(...):`) breaks programs without
  moving the algorithm. For example, the model indents with non-breaking spaces, so the program fails to parse.

**Generic pushes rarely move this collapsed model.**
- Nonce bans move nothing except R6's already-noisy twin.
- Novelty moves T03 (all 50 off D; 45 quickselect), T11, T08, T04 and T10.
- Isotropic random directions at matched norm move T03 under one of three directions (rand3: 0.82 avoidance, mostly
  quickselect) and T10 a little (0.26, to dfs). This is not an engine artefact: the HF twin control keeps D at 0.98
  on T03 and 1.00 on T10.

**Positive control.** Patching the ban's own task-spec states into the twin at layers 12-23 reproduces the ban's
avoidance only on T03 and T10 (1.00 each), partly on T05 (0.22) and T13 (0.14), and nowhere else. On the other tasks,
the ban's effect is not carried by the task-spec states in this band alone.

**FRLP (descriptive).**
- Rescoring the frozen FRLP sets on the fp32-activation path moves L_corr by a median of 0.88 nats (max 9.0). Every
  shift larger than 2 nats sits in a cell with Kish ESS < 5.
- The argmax mode is unchanged on 12 of 12 tasks.
- The rescoring scorer first reproduced 5 stored exp7 program scores to within 0.021 nats.
- FRLP_FP8 is defined only on T03, where it named quickselect.

**Integrity.**
- The independent re-derivation (`audit/rederive.py`) has 0 mismatches.
- The task-shuffled placebo collapses the family wins (mean LADDER wins 0.52 vs 3 observed).
- The template permutation test gives p = 0.002 on real data and p = 0.42 on shuffled data.
- A second audit (`audit/rederive_raw.py`) reads only the raw label files and reproduces every headline number
  through new code. Its hand-written logistic likelihood-ratio test gives LR 374.1 on real data and LR 4.1 (p 0.39) on
  shuffled templates.
- The hash chain verifies, and the first ban request (18:55:16Z) postdates the seal (18:50:57Z).
- Every committed file is unchanged except `src/common.py`. After the bans, its absolute input paths were replaced by
  relative constants for portability; no logic changed. This is a documented `post_ban_revision` in
  `commitments.log`, with the diff and the byte-preserved sealed copy in `audit/sealed_files/`, which the guard
  verifies.

## Method in brief

1. **S0 inputs.**
   - The 12 frozen task directories, `bench/common` and `bench/commitment.json` are copied from the iteration-2 bench
     into `inputs/bench/`.
   - All 146 committed file hashes are verified. The non-committed bench files (pilot, forced, association, neutral
     nouns, FRLP sets) are hashed as the first `commitments.log` entry.
   - All 528 dependency-derived test ids are checked against the iteration-1 dataset with identical expected outputs
     (`results/dependency_provenance.json`). That dataset is used for provenance only.
2. **Labeller re-check.** The labeller re-check on every gold-set program and reference matches `gate.json` exactly
   on all 12 tasks, with references 100% (`results/labeller_recheck.json`).
3. **Prompts** (`src/prompts.py`).
   - Each prompt is `cap_first(segment) + blank line + frozen spec`, using templates W1-W5.
   - The twin uses noun N plus `' .'` fillers until the chat-formatted token count equals the ban's.
   - Ids from `Task` onward are asserted identical between ban and twin. The spec span is recorded.
   - No alias of D appears in any pre-commit segment.
4. **N-grams** (`src/ngrams.py`).
   - The rule: the minimum max-collateral n-gram (n ≤ 6) with coverage ≥ 0.8 on the default's pilot programs.
   - Collateral is measured on forced programs of the other modes.
   - Sham n-gram: the same n, maximum minimum collateral.
   - The n-gram is re-derived on bf16 twin outputs when its token-level coverage is below 0.8 (R1, T14).
5. **Veto engine** (`src/veto.py`).
   - Exact rejection plus masked redraw (`logit_bias −100`), coupled to the twin samples by seed.
   - Unit tests pass: the first completion is removed; persistent runs leave zero completions; a never-firing mask
     reproduces the base exactly; redraws avoid the mask (`results/veto_unit_tests.json`).
6. **Process A** (`src/vllm_stage.py A`).
   - twin 600; one-shot, sham and persistent 600 each; nonce 600; novelty 600.
   - Iterated rounds 600 / 500 / 450, each triggered when the default share is ≥ 0.20.
7. **Process B** (`src/hf_stage.py B`).
   - Norms: template-mean ‖h(ban) − h(twin)‖ per band layer and spec position.
   - 3 seeded isotropic directions × 50 samples per task, with the displacement patched exactly at layers 12-23 and
     spec positions.
   - HF twin control, 50 per task.
   - Hook tests pass (`results/hook_unit_tests.json`): zero patch exact, layers below the band untouched,
     displacement norm within 0.23%, batch equals single 20/20.
8. **S1d forecasts and seal** (`src/forecasts.py`). The 17 files are listed in `commitments.log`.
9. **Process C.** The guard runs, then the bans (1,200), then labels.
10. **Process D.** The band-patch control (600).
11. **Process D2.** FRLP fp32 rescoring (`src/frlp_rescore.py`).
12. **S3.** The committed analysis (`src/analyze.py`, `score.py`, `c2b.py`, `template_effect.py`), then post-hoc
    sensitivity (`src/posthoc.py`, not pre-registered), sanity checks, outputs and the audit.

## Deviations (all in `results/deviations.jsonl` and `method_out.json → metadata.deviations`)

- **Hardware.**
  - An RTX 4090 (24 GB) replaces the planned A4500 (20 GB), so bf16 fits and no fallback was needed.
  - vLLM runs with `max_num_seqs` 64 and `max_num_batched_tokens` 4096. This affects scheduling only.
  - There is no C compiler, so vLLM runs with `enforce_eager=True` and `TORCH_COMPILE_DISABLE=1`.
- **Weights.** The weights live in the run's shared Hugging Face cache, not in a workspace `hf_cache/`. This follows
  the run's storage rule.
- **Twin padding.** Fillers are appended to the end of the neutral segment, which is exp7's frozen implementation.
- **N-gram re-derivation.** The pre-declared re-derivation rule fired for R1 (FP8 n-gram coverage on bf16 twin
  programs was 0.64) and T14 (0.79).
- **Greedy cover.** The greedy cover was operationalised as a pace rule, declared before any veto sampling. It never
  fired.
- **HF twin control.** It was run for every task instead of only on trigger. This is a superset of the plan.
- **Judge.**
  - Gemini-2.5-flash-lite 429s are retried with backoff.
  - exp11's judge cache was reused (same judge, prompt and code hash).
  - Labels are reused for identical code within the run.
- **Open verdict branches.** These are named explicitly in the committed code:
  - C2b `INCONCLUSIVE`;
  - C1 `NO FAMILY ADVANCES`;
  - LADDER_EXISTS counts survivors only.
- **Hook test (c).** It is judged against the bf16 rounding bound. The measured error is 0.23%.
- **Scale-up.** Smoke runs (process A on T03 and T05 at 2 samples per template; process B on T03) went straight to
  the full runs instead of 10 → 100 → full. The full stages took minutes (A 6, B 8, C 4), so extrapolation was moot
  (`results/timing.jsonl`).
- **FRLP rescoring scope.** It covers the 50 cells of the 12 frozen tasks; the plan's 54 counted the excluded R2.
  The scorer re-implements exp7's fp32-activation numerics and passed exp7's 5-program reproduction gate.
- **Post-hoc analyses.** These are kept apart from the committed analysis (`src/posthoc.py` →
  `results/posthoc_sensitivity.json`).
- **Post-ban portability revision.** After the bans, the committed `src/common.py` had its absolute input-artifact
  paths replaced by relative constants with environment-variable overrides (`AII_EXP11_DIR`, `AII_EXP7_DIR`,
  `AII_EXP8_DIR`, `AII_DEP_DATASET_DIR`). Nothing else changed, and the CPU re-analysis is byte-identical. The change
  is appended as `post_ban_revision`/`post_ban_note`; the sealed bytes and the diff are in `audit/sealed_files/`.
- **Not run or changed.**
  - FRLP fp32 rescoring ran (it was optional).
  - The C2b figure for the one-shot arm is absent because no event was eligible.
  - The committed log-score figure draws its shading over the points. `figures/logscores_by_family_v2.png` redraws it
    from the same numbers.

## Layout

| path | contents |
|---|---|
| `method.py` | CLI: `.venv/bin/python method.py all` or individual stages (`setup … audit`) |
| `src/common.py` | constants, task table, W1-W5 templates, seeds, paths (committed) |
| `src/setup_inputs.py`, `src/labelpool.py` | S0 copy/verify/provenance; labelling pool (exp11 labellers + judge) and the labeller re-check |
| `src/prompts.py`, `src/ngrams.py`, `src/proximity.py` | prompts and token alignment; distinctive/sham n-grams; AST-TED PROXIMITY |
| `src/veto.py`, `src/vllm_stage.py` | coupled token-veto engine; GPU processes A (ban-free) and C (bans, guarded) |
| `src/hf_stage.py` | GPU processes B (norms, random directions, HF twin) and D (band-patch) |
| `src/forecasts.py` | ASSOCIATE/FRLP nominees, forecasts, commitment + seal, tamper test |
| `src/score.py`, `src/c2b.py`, `src/template_effect.py`, `src/analyze.py` | committed analysis code (hash-chained before bans) |
| `src/posthoc.py`, `src/sanity.py`, `src/figures_extra.py`, `src/outputs.py`, `src/frlp_rescore.py` | post-hoc sensitivity, sanity checks, extra figures, outputs, FRLP rescoring |
| `audit/rederive.py` | independent re-derivation from `data/samples.jsonl` + placebos → `results/rederive.json` |
| `audit/rederive_raw.py` | second independent audit from the raw label files (own logistic LR test, own FRLP cells) + placebos → `results/rederive_raw.json` |
| `audit/sealed_files/` | byte-preserved sealed copy of `src/common.py` (`.sealed`, never executed) and the post-ban portability diff |
| `reproducibility.md` | exact steps, versions, seeds, hardware, runtimes and expected numbers |
| `tests/dryrun_full.py` | pre-seal dry run of the analysis with the novelty arm standing in for the ban |
| `inputs/` | copied frozen bench (`bench/`), exp7 template/padding file, exp8 engine sources, exp11 FRLP cells, provenance manifest |
| `prompts/` | `prompts.jsonl` (every prompt with token hash and spec span), `prompt_ids.json`, rendered T03 examples |
| `predictions/` | committed forecasts, n-grams (FP8 and final), iterated chain, proximity, associate, FRLP_FP8, seeds, constants, norms manifest |
| `commitments.log` | sha256 hash chain: provenance → 17 forecast commitments → `SEAL_BEFORE_BANS` |
| `data/raw/<arm>.jsonl` | raw generations with token ids (vetoes: positions, banned tokens, redraws, text leaks) |
| `data/labels/<arm>.jsonl` | labels (runtime, AST, judge, combined, pass) per sample |
| `data/samples.jsonl` | one protocol row per sample (9,350 rows) with veto metadata |
| `results/c1_events.jsonl`, `results/analysis.json` | committed analysis outputs (C1 events, verdicts, C2b, descriptives, template effect) |
| `results/posthoc_sensitivity.json` | post-hoc: defined-only wins, vs-uniform, closest arm per ban landing |
| `results/frlp_rescore.json`, `results/frlp_program_scores_fp32.json` | FRLP fp32 rescoring (validation, 50 cells, rank changes) and program scores |
| `results/tensors/norms_<task>.npz` | per-position displacement norms and per-layer mean displacement vectors (layers 12-23) |
| `results/*unit_tests*.json`, `labeller_recheck.json`, `sanity.json`, `rederive.json`, `tamper_test.json`, `env.json`, `timing.jsonl`, `deviations.jsonl` | checks, environment, timing |
| `figures/` | composition per task, log scores (committed and v2), forecast table, avoidance by arm, template × task heatmap (PNG + PDF) |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out`. Dataset `modal_ban_samples` has 1,200 examples: output = `label\|pass`, and `predict_subtract/ladder/associate/proximity` = the committed top-1s. Dataset `ban_free_arm_samples` has 8,150 examples. Every analysis is in `metadata` |
| `scratch/`, `results/dryrun_*/` | pre-seal dry runs: commitment log, tampered copy (tamper test), dry-run forecasts, figures and analyses with the nonce/novelty arm standing in for the ban (no ban sampled before the seal) |
| `logs/` | per-stage logs and `openrouter_spend.jsonl` |
| `pyproject.toml`, `requirements.txt`, `restore.sh` | all 178 installed packages pinned (Python 3.12.14); venv + model restore script |

Kept artifacts are named by relative path and stay on the run's storage volume. No file here reaches 100 MB; the
largest is `full_method_out.json` at 19 MB, so everything is also in the published repository. Model weights are not
in this folder.

## How to run

See `reproducibility.md` for the complete record. In short:


```bash
bash restore.sh                                # .venv from requirements.txt + model weights
export TORCH_COMPILE_DISABLE=1                 # no C compiler on the original machine
.venv/bin/python method.py all                 # every stage in order (about 45 min of GPU on an RTX 4090)
.venv/bin/python method.py analyze posthoc sanity figures outputs audit   # re-analysis only, CPU
.venv/bin/python src/vllm_stage.py A --smoke   # smoke test of process A (T03 + T05, tiny N) into data/smoke/
.venv/bin/python src/hf_stage.py B --smoke     # hook unit tests + tiny B run into data/smoke/
```

- The judge needs `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`. Its answers are cached in
  `data/judge_cache.jsonl`, with a personal cap of USD 0.6.
- vLLM and HF same-seed outputs are not bit-reproducible across batch compositions. Seeds are logged, but exact
  determinism is not claimed.
- `method.py commit` refuses to re-seal an already sealed log.

## Restoring removed files

`.aii/manifest.yaml` marks these paths for deletion after the round:

| deleted path | why | restore command |
|---|---|---|
| `.venv/` (15 GB) | regenerable | `bash restore.sh` or `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.txt` |
| `src/__pycache__/` | regenerable bytecode | `.venv/bin/python -m compileall -q src` (or simply re-import) |
| `inputs/bench/__pycache__/`, `inputs/bench/common/__pycache__/` | regenerable bytecode | `.venv/bin/python -m compileall -q inputs/bench` |

The model weights are in the shared Hugging Face cache, not in this folder. To fetch them elsewhere, run
`hf download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.

## Upload exclusions

Do not publish:

- `.venv/`
- `__pycache__/`
- the agent session files

The patterns are `(^|/)\.venv/`, `(^|/)__pycache__/`, `^\.repl_agent\.ptylog$` and `^\.aii_claude_session\.json$`.
