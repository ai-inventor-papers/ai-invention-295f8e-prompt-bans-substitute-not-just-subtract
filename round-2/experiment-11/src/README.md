# Coding-task bench with a baseline pilot (iteration 2)

This repository builds the confirmation bench for an algorithm-choice study. **No ban prompt is rendered anywhere in it.**

Thirteen LeetCode-derived coding tasks get:

- a frozen spec in new wording;
- hidden tests with order-free checkers;
- one verified reference per algorithm mode (54 references);
- a runtime-signature labeller backed by an AST labeller, validated against an adjudicated gold set.

For each task the model **Qwen3-8B** (official FP8 checkpoint, see deviations) produces:

- a 50-sample baseline pilot;
- 20 free-form "standard alternative to X" answers per mode;
- at least 40 forced, name-scrubbed programs per mode, scored by likelihood to give the baseline **forced-ratio latent probability (FRLP)** of every mode.

The tasks are ordered by how much three nomination families disagree (ladder, association, proximity), gated, and **12 tasks are frozen** with sha256 commitments.

Everything below was run in this workspace on 2026-10-20 (one RTX 2000 Ada 16 GB, 6 CPUs); see `reproducibility.md` for the exact steps. OpenRouter judge spend was **$0.142** (1,124 calls). GPU time was about **1.4 h**.

## Main results

| task | K | tests | gate: kappa(runtime, AST) [95% CI] / PABAK / runtime vs adjudicated | Qwen pilot: modal (share, pass) | FRLP L_corr of modal | best alternative (L_corr) | S = Σ exp(L_corr) | association / proximity nomination (modal event) | Llama-3.1-8B modal share | status |
|---|--:|--:|---|---|--:|---|--:|---|---|---|
| T03 k-th smallest | 6 | 60 | 0.95 [0.84, 1.00] / 0.96 / 0.96 | full_sort (1.00, 1.00) | -0.18 | quickselect (-1.5) | 1.05 | quickselect / heapify_pop | heapify_pop 0.34 | frozen |
| T05 two-sum | 4 | 44 | 0.92 [0.75, 1.00] / 0.94 / 0.95 | hash_map (1.00, 1.00) | -0.40 | sort_two_pointers (-15.5) | 0.67 | sort_two_pointers / brute_force | hash_map 0.96 | frozen |
| T06 find duplicate | 5 | 54 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | hash_set (1.00, 1.00) | 0.02 | sort_adjacent (-12.4) | 1.02 | floyd / sort_adjacent | hash_set 0.43 | frozen |
| T14 top-k frequent | 4 | 38 | 0.84 [0.60, 1.00] / 0.88 / 0.91 | sort_by_count (1.00, 0.94) | -0.10 | bucket_sort (-15.4) | 0.91 | heap / heap | heap 0.64 | frozen |
| T10 components | 4 | 57 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | union_find (1.00, 1.00) | -0.15 | dfs (-21.8) | 0.86 | dfs / label_propagation | union_find 0.77 | frozen |
| T08 Fibonacci | 4 | 36 | 0.85 [0.65, 1.00] / 0.89 / 0.91 | iteration (1.00, 1.00) | -0.02 | fast_doubling (-11.4) | 0.98 | matrix_power / fast_doubling | matrix_power 0.79 | frozen |
| T04 substring | 6 | 58 | 0.95 [0.82, 1.00] / 0.96 / 1.00 | naive (1.00, 1.00) | 0.24 | kmp (-14.3) | 1.28 | kmp / bmh | naive 0.53 | frozen |
| T11 LIS | 3 | 57 | 1.00 [1.00, 1.00] / 1.00 / 1.00 | quadratic_dp (1.00, 1.00) | -0.86 | patience_bisect (-14.4) | 0.42 | patience_bisect / patience_bisect | quadratic_dp 0.90 | frozen |
| T13 merge intervals | 3 | 59 | 1.00 [1.00, 1.00] / 1.00 / 0.95 | sort_sweep (1.00, 1.00) | 0.74 | union_find (-35.5) | 2.09 | interval_tree / union_find | sort_sweep 1.00 | frozen |
| R1 non-overlapping | 4 | 53 | 0.89 [0.63, 1.00] / 0.94 / 0.91 | greedy_end (1.00, 1.00) | -0.83 | dp_bisect (-28.1) | 0.44 | dp_bisect / dag_longest_path | greedy_end 0.56 | frozen |
| R2 cycle detection | 4 | 59 | 0.92 [0.73, 1.00] / 0.94 / 0.95 | dfs_parent (1.00, 0.92) | 2.39 | union_find (-14.2) | 10.9 | union_find / union_find | dfs_parent 0.59 | excluded (13th gated; 12-task cap) |
| R3 topological order | 4 | 53 | 1.00 [1.00, 1.00] / 1.00 / 0.95 | kahn (1.00, 1.00) | 2.44 | dfs_postorder (-27.2) | 11.4 | dfs_postorder / source_removal | kahn 0.98 | frozen |
| R6 first/last position | 3 | 56 | 0.90 [0.61, 1.00] / 0.93 / 0.95 | binary_search (0.98, 0.98) | 0.80 | bisect_module (-12.6) | 2.21 | bisect_module / exponential_search | binary_search 1.00 | frozen |

What the numbers say:

- **The Qwen3-8B baseline is fully collapsed on all 13 tasks.** The modal share is 50/50 everywhere except R6 (49/50). The Wilson 95% interval is [0.929, 1.0], and Hill-1 over correct programs is 1.0. No task has a minor mode present at 10% or more.
  - The presence check has low power at N=50: P(at least 5/50 | true share 0.10) ≈ 0.57.
  - The pilot pass rate is at least 0.92 on every task.
  - Collapse is model-specific. **Llama-3.1-8B-Instruct** (FP8, same specs and decoding) is far more diverse. On T03, for example, it splits over heapify_pop, size_k_heap, full_sort and quickselect. It also passes far fewer tests.
- **The labeller gate passes on all 13 tasks.**
  - 11 tasks pass at round 0.
  - T03 and T13 pass after one revision round. The fresh 6-program holdout gave 5/6 and 6/6.
  - Both labellers get all 54 references right.
  - Population agreement between the runtime and AST labellers is 0.91 (3,230 Qwen attempts). The judge was needed on 8.4% of attempts.
- **FRLP behaves sensibly but is noisy.**
  - argmax(π) equals the pilot mode on 13/13 tasks.
  - The mean log score of the pilot labels under π beats uniform on every task (for example −0.06 vs −1.61 on T05).
  - S lands in [0.3, 3] on 11/13 tasks. R2 and R3 overshoot because their default-mode cells exceed 0 nats, an importance-sampling overestimate under low ESS.
  - 34 of the 54 cells have Kish ESS < 5.
  - R3 source_removal and layering stay `insufficient` (M_j = 8 and 3) even after top-ups and the descriptive variant. They remain ban targets but are excluded from S.
  - One notable cell: T03 quickselect has L_corr = −1.5 (≈ 0.21 latent mass) while the pilot shows 0/50.
- **Nominations disagree.**
  - The free-form association answers are near-deterministic (for example "alternative to a full sort" → quickselect, 20/20).
  - Proximity nominates a different mode on 10/13 modal events.
  - Under total collapse the Stage-A ladder is a tie over all survivors.
  - Stage-B order (ladder ties broken by FRLP, proximity from forced programs) vs Stage-A order: Kendall τ = 0.54.
- **Forced adherence is the main limit for exotic modes.** 45/54 modes have adherence ≥ 0.5. The model often writes its default when asked for:
  - R3 layering 0.04 and source removal 0.10;
  - T13 interval tree 0.24;
  - R1 DP variants 0.28;
  - T06 index marking 0.28;
  - T10 label propagation 0.29.

  The full forced-prompt × label confusion matrix is in `method_out.json` → `metadata.forced_adherence`.

## Method in brief (what each step does)

1. **Specs** (`bench/common/catalogue.py`, frozen as `bench/<task>/spec.json`, commitment `spec_v1`).
   - Each spec uses the exp1 scaffold: `[condition segment] + blank line + DESCRIPTION + blank line + FORMAT`.
   - The FORMAT line is exp1's, verbatim.
   - Descriptions are new wording with no complexity hints and no LeetCode follow-ups.
   - Forced templates 0-4 are exp1's paraphrases; 5-9 are frozen but never rendered.
   - The association prompt is `DESCRIPTION + "What is the standard alternative to {X} for this task? Name one algorithm and answer in one sentence."`
2. **GPU job A** (`bench/common/gen_vllm.py`): vLLM with explicit SamplingParams.
   - Decoding: T=1.0, top_p=1.0, top_k=-1, min_p=0, max_tokens 1024, thinking disabled through the Qwen3 chat template. Every rendering ends with an empty think block, and the code asserts this.
   - Seeds: base 20261020 + offsets. Pilot `1000·task_idx + s`; association `10^5 + 100·mode_idx + s`; forced `10^6 + 1000·mode_idx + 10·round + k`.
   - An automatic mini-gate checked code-block extraction (10/10) before scaling.
3. **Build** (`bench/common/build.py`, `testgen.py`, `refs.py`, `checkers.py`, `harness.py`, `runner.py`).
   - Hidden tests are the parsed LeetCodeDataset cases (status ok, converted and filtered to the spec bounds, at most 45 per task), plus generated edge and stress cases with oracle outputs. 684 cases in total.
   - Order-free checkers cover two-sum, top-k, merge intervals and topological order.
   - Each candidate runs in a fresh `python3.12 -I -S` subprocess with forbidden imports blocked, RLIMIT_AS 2 GB, a recursion limit of 10^6, and a thread with a 512 MB stack.
   - Per-case limit = max(1 s, 10 × the fastest reference). Every reference passes at no more than 0.25 × the limit (worst: 0.229, T13 interval tree).
   - All 39 mutants fail, the HumanEval+ smoke test passes 5/5, and the exponential brute forces (LIS subsets, naive Fibonacci) time out.
4. **Labelling.** For every attempt:
   - Extraction, the hidden tests, and the AST labeller (`astrules.py`).
   - The runtime labeller (`tracer.py` + `probes.py` + `rtrules.py`). Its instrumentation includes:
     - heapq/bisect proxy modules;
     - recording deque and queue classes;
     - wrappers on `lru_cache` and `Counter.most_common`, and a patched `sorted`;
     - `sys.setprofile` for self-recursion, C calls and `list.pop(0)` vs `pop()` (decided from the calling bytecode);
     - instrumented inputs: CInt (comparisons, hashes, additions), CList (reads, writes, full passes, probe order) and CStr (method calls, read positions);
     - `settrace` line counts for scaling;
     - a scan of list sizes in returning frames.
   - Combined label: runtime when it agrees with AST or AST says unknown; otherwise the blind judge (gemini-2.5-flash-lite, name-scrubbed code) decides.
5. **Scrubbing** (`scrub.py`, tokenize-based).
   - User identifiers containing any catalogue alias are renamed (`compute_lps` → `compute1`, `tortoise` → `var1`). Comments and docstrings that name an alias are dropped. API names and `solve`'s parameters are never touched.
   - The scrub is checked to be idempotent and to leave 0 residual aliases.
   - A scrubbed program enters an FRLP set only if it gives identical per-case test outcomes and the same runtime label.
6. **Association map** (`order.py`): alias lexicon first, judge for unmapped answers. A_free(X→j) = (count_j + 1) / (n_valid + |S|).
7. **Ordering** (`order.py`).
   - Ladder: argmax of pilot share; ties kept in Stage A and broken by FRLP in Stage B.
   - Association: argmax of A_free.
   - Proximity: argmin of the median normalized token Levenshtein distance on canonical token streams (`canon.py`). Stage A uses references; Stage B uses forced programs.
   - Disagreement = minimum hitting set over the three tie sets, minus 1.
   - Stage A was committed **before** gating; Stage B after FRLP.
8. **Gate** (`gate.py`).
   - Gold set: 10 pilot programs, all references and 2 forced attempts per mode.
   - Judges j1 (gemini-2.5-flash-lite) and j2 (gpt-4.1-mini) label blind; j3 (deepseek-chat-v3.1) breaks ties.
   - Pass criteria: kappa(runtime, AST) ≥ 0.8 (with a 1,000-resample bootstrap CI, PABAK and raw agreement), 100% on references for both labellers, and runtime vs adjudicated ≥ 0.90.
   - The direction's own subset (pilot + references) and population kappa are also reported.
9. **GPU job B** (`score_vllm.py`).
   - Each forced attempt is scored as its scrubbed response, tokenized separately and followed by `<|im_end|>`.
   - Prompts: the baseline, plus every prompt that generated attempts for the mode (the exact mixture proposal, including the descriptive variant where used).
   - 16,040 (program, prompt) pairs.
10. **FRLP** (`frlp.py`).
    - log q(i) = logsumexp_k[log(n_k/N) + l(i|F_j^k)]
    - w_i = l(i|baseline) − log q(i)
    - L_j = logmeanexp over M_j (the first 30 labelled-j, scrub-verified attempts in round-robin order)
    - L_corr = L_j + log a_j
    - Also reported: Kish ESS, halves, a generating-paraphrase-only sensitivity, a correct-only sensitivity, descriptive validity and coverage.
11. **Freeze** (`report.py`): per-task sha256 of the spec, tests, checker, references, labellers, probes, gold set and FRLP set, plus a combined hash. All of these go into the `commitments.log` hash chain.

## Deviations from the plan (all logged in `method_out.json` → `metadata.deviations`)

- **Hardware.** The pod has a 16 GB RTX 2000 Ada, not the 20 GB A4500, and bf16 Qwen3-8B does not fit.
  - Sampling and scoring both use **`Qwen/Qwen3-8B-FP8`** (the official block-FP8 checkpoint).
  - It runs through vLLM's precompiled **FP8 Marlin** kernels (weight-only FP8, bf16 activations).
  - The machine has no C compiler, so Triton is unusable. vLLM runs with `enforce_eager=True`, `TORCH_COMPILE_DISABLE=1` and `VLLM_TEST_FORCE_FP8_MARLIN=1`. The two failed launches are kept in `logs/jobA_failed_*.out`.
- **Scoring engine.** HF transformers cannot hold the bf16 weights on this GPU, and its FP8 path also needs Triton. Scoring therefore uses vLLM prompt logprobs, which forbid prefix caching, so every request is a full prefill. The consistency checks come out as follows:
  - (a) Sampler vs scorer on the generating paraphrase: 20/20 within max(1 nat, 1%), both on the sampled ids and on the re-tokenized text (max |Δ| = 0.76 nat).
  - (b) The planned cache-reuse check has no analogue here; it is replaced by single-request vs batched scoring. **That check fails the 0.1-nat bar on 1 of 5 programs (Δ = 0.62 nat; the others ≤ 0.015).** This is batch-dependent kernel numerics, small next to the 10-100-nat FRLP gaps.
  - (c) Shuffled-token controls score 443-1,388 nats lower.
  - (d) Re-running the same batch is exact (Δ = 0).
- **Forced proposal.** It uses ids 0-4 (exp1's wordings) × 8 rounds = 40 attempts per mode, instead of 10 × 4. The plan's fallback names this mixture, and the full-prefill scoring cost on a slower GPU made the 10-paraphrase mixture unaffordable.
  - Top-ups: 4 more rounds (20 attempts) for modes with M_j < 30.
  - For modes whose 40-attempt adherence was < 0.3, 20 extra attempts with the descriptive variant. The plan triggers that variant at 60 attempts; it was run earlier here to save a GPU round trip.
- **Gold set** extended with forced attempts, as planned. j3 is `deepseek/deepseek-chat-v3.1`. OpenRouter `/key` returned a Cloudflare 403 through the proxy, so spend was tracked from `usage.cost` per call.
- **Revision round 1** for T03 and T13, with a fresh holdout:
  - T03: crashed-probe partial features label the attempted mechanism; hand-written heaps are detected by sift-call counts.
  - T13: a helper called per overlapping pair means union-find.
- **Stress sizes.** T13's widest-interval stress case uses n = 800 (bound 1500) to meet the 0.25× rule. R2 gained shuffled-edge forests after a mutant survived. T14 gained 13 generated cases (now 38).
- **Freeze cap.** All 13 candidates passed the gate. The plan's stop rule freezes the first 12 in Stage-A order, so R2 is `excluded`, but its bench files and gate are in `bench/R2_cycle_detection/`.
- **Not done:**
  - The code-only unscrubbed scoring sensitivity (first in the plan's drop order).
  - Re-checking the canonical suite: not applicable, since there is no T1/T2 task here.
  - The no-ban audit uses a superset ban/novelty lexicon plus `Zorblax`, because the 15 frozen W1-W5 strings are not available to this artifact. Result: 0 hits in 4,310 rendered prompts.
- **Rule snapshots.** `bench/<task>/ast_rules.py` and `runtime_rules.py` are snapshots taken when each task was gated. Only T03 and T13 carry the round-1 revision. For the other tasks the rule functions are byte-identical between the two versions (checked for T05), and the shared `_f` helper behaves the same with its default `allow_error=False`.
- **Tracer determinism.** 52/54 references give identical feature lines on two runs. The two that differ (T03 quickselect, T13 interval tree) call `random` themselves; their labels are stable.
- **Neutral nouns.** All 718 candidates are single Qwen3 tokens, so the token-count match is degenerate. Nouns are frequency-ranked and unique across display names (`bench/<task>/neutral_nouns.json`). They are never rendered.

## Layout

| path | contents |
|---|---|
| `method.py` | CLI: `extract`, `specs`, `gen --job A/C/D`, `build`, `label`, `order --stage A/B`, `gate`, `score`, `frlp`, `freeze`, `report` |
| `bench/common/` | shared code: `catalogue.py` (frozen cards), `prompts.py` (the only 3 prompt builders), `gen_vllm.py`, `score_vllm.py`, `testgen.py`, `checkers.py`, `refs.py`, `harness.py` + `runner.py` (sandbox), `tracer.py` + `probes.py` + `rtrules.py` (runtime labeller), `astrules.py`, `scrub.py`, `canon.py`, `judge.py`, `labeling.py`, `retrace.py`, `combine.py`, `order.py`, `gate.py`, `frlp.py`, `stats.py`, `commit.py`, `report.py`, `finalize.py`, `build.py` |
| `bench/<task_id>/` | per task: `spec.json`, `tests.jsonl` (with per-case limits and reference times), `checker.py`, `references/<mode>.py`, `ast_rules.py` and `runtime_rules.py` (frozen snapshots), `probes.json`, `gold_set.jsonl`, `gate.json`, `forced_programs.jsonl`, `pilot_rows.jsonl`, `association.jsonl`, `frlp_sets.json` (frozen M_j with halves), `frlp_baseline.jsonl`, `neutral_nouns.json`, `build_report.json` |
| `bench/commitment.json` | per-task file hashes and the combined freeze hash |
| `commitments.log` | sha256 hash chain: `spec_v1`, `stageA_order`, `stageB_order`, `bench_freeze` |
| `data/samples_pilot.jsonl`, `data/samples_forced.jsonl`, `data/samples_llama_pilot.jsonl` | per-sample rows in the shared schema `{task, condition, template, paraphrase_id, sample_id, seed, model, decoding, label, labeller_source, passed, code_sha256, code}` plus AST, runtime and judge labels |
| `data/*_raw.jsonl` | raw vLLM outputs: text, token ids, per-token logprobs, finish reason |
| `data/association.jsonl` | 1,080 association answers with mapped label and category |
| `data/labels_*.jsonl`, `data/traces*.jsonl` | per-attempt test results, labels, scrub checks and stored tracer features |
| `data/program_scores.jsonl` | 16,040 l(program \| prompt) scores |
| `data/frlp_cells.jsonl` | FRLP cells: main, halves, generating-paraphrase-only and correct-only variants |
| `data/judge_cache.jsonl` | every judge answer (cached by model, task and code hash) |
| `data/extract/` | the rows of the dependency dataset this bench uses (all 10 datasets; see `extract_summary.json`) |
| `results/` | `gate_summary.json`, `stageA_nominations.json`, `stageB_nominations.json`, `frlp_validity.json`, `pilot_stats.json`, `build_summary.json`, `scoring_consistency.json`, `tracer_unit_tests.json`, `reference_traces.json`, `timings.json`, `frozen_tasks.json` |
| `method_out.json` (+ `full_`/`mini_`/`preview_` variants) | `exp_gen_sol_out`. Dataset `bench_candidates` has one example per candidate, with `predict_ladder` (baseline), `predict_association` and `predict_proximity`. Dataset `frlp_baseline_cells` has one example per (task, mode), with FRLP-implied vs uniform probability |
| `reproducibility.md` | exact, portable reproduction steps: what was run, in order, with failures, fixes, seeds, hardware and runtimes |
| `restore.sh` | recreates `.venv/` from `requirements.txt` and downloads the model weights |
| `pyproject.toml`, `requirements.txt` | all 160 installed packages pinned (Python 3.12.14) |
| `scripts/rederive_headlines.py` | independent re-derivation of every headline number from raw per-sample files, plus placebo checks (`results/rederive_headlines.json`) |
| `scripts/verify_outputs.py` | stdlib-only independent recount, commitment re-hash, hash-chain walk and no-ban audit (result: 0 problems) |
| `scripts/tracer_unit_tests.py` | CLRS binary-search access order (153/153) and probe determinism |
| `scripts/ast_fixture_check.py` | AST rules on TheAlgorithms hand-labelled implementations (26/33) |
| `scripts/chain_*.sh` | the GPU job chaining actually used (one model on the GPU at a time) |
| `logs/` | per-step logs, `prompts_rendered.jsonl` (no-ban audit input), `openrouter_spend.jsonl`, rendered chat examples, effective sampling parameters |

How the dependency datasets were used:

| dataset | use |
|---|---|
| leetcodedataset | test seeds |
| mercury | extracted human solutions, kept as context; not run |
| thealgorithms_python | AST-rule fixture check: the rules recover the hand-labelled mode for 26/33 implementations (library-style human code, often several variants per file; `results/ast_fixture_check.json`) |
| kodcode_algorithmic, xlcost_python | extracted rows that name a bench mode (`data/extract/named_code.json`); kept as context, not scored |
| clrs_text | tracer access-order tests: 153/153 binary-search traces match |
| humanevalplus | harness smoke test (5/5) |
| enamel | extracted; its size-levelled generators target other problems, so this bench's stress cases were written per task instead |
| concreteness_norms | neutral nouns |
| llm_creativity | T02 labels only; reported as an external collapse prior in `metadata.dependency_extract_summary` |

All kept artifacts stay on the run's storage volume at these relative paths. No file here exceeds 100 MB; the largest is `data/traces.jsonl` at 8.4 MB.

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.txt   # vllm 0.11.0, transformers 4.57.1
export TORCH_COMPILE_DISABLE=1                    # no C compiler on the original machine
.venv/bin/python method.py extract                # dependency rows -> data/extract/
.venv/bin/python method.py specs                  # freeze spec v1 (commitment)
.venv/bin/python method.py gen --job A            # pilot 650, association 1,080, forced 2,160 (vLLM, GPU)
.venv/bin/python method.py build                  # tests, references, limits, mutants, smoke tests
.venv/bin/python method.py label                  # tests + AST + runtime trace + scrub check + judge
.venv/bin/python method.py order --stage A        # association map, nominations, committed Stage-A order
.venv/bin/python method.py gate                   # gold sets, adjudication, labeller gate
.venv/bin/python method.py gate --tasks T03,T13 --revise 1
.venv/bin/python method.py score                  # GPU job B: likelihood scores (+ consistency checks)
.venv/bin/python method.py gen --job C            # forced top-ups from data/topup_plan.json
.venv/bin/python method.py label && .venv/bin/python method.py score   # label + score the top-ups
.venv/bin/python method.py gen --job D --model RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8 --tasks T03,T04,...  # optional
.venv/bin/python method.py label --sources samples_llama_pilot_raw.jsonl --llama
.venv/bin/python method.py frlp && .venv/bin/python method.py order --stage B
.venv/bin/python method.py freeze && .venv/bin/python method.py report
.venv/bin/python scripts/verify_outputs.py && .venv/bin/python scripts/tracer_unit_tests.py
```

The judge needs `OPENROUTER_BASE_URL` and `OPENROUTER_API_KEY`, and judge answers are cached in `data/judge_cache.jsonl`. vLLM same-seed outputs are not bit-reproducible across batch compositions, so seeds are logged but determinism is not claimed.

## Restoring removed files

`.aii/manifest.yaml` marks these paths for deletion after the round:

| deleted path | restore command |
|---|---|
| `.venv/` (regenerable, 14 GB) | `bash restore.sh` (or `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r requirements.txt`) |
| `.cache/` (regenerable, vLLM/Triton compile caches) | recreated automatically by the next GPU job, e.g. `.venv/bin/python method.py gen --job A`; `VLLM_CACHE_ROOT`, `TRITON_CACHE_DIR` and `XDG_CACHE_HOME` point under `.cache/` |
| `bench/__pycache__/`, `bench/common/__pycache__/` (regenerable bytecode) | recreated on import: `.venv/bin/python method.py --help` |
| `scripts/__pycache__/` (regenerable bytecode) | recreated when a script module is imported, e.g. `.venv/bin/python -c "import importlib.util as u; s=u.spec_from_file_location('m','scripts/rederive_headlines.py'); u.module_from_spec(s)"` |

Everything else is text or code (data, bench, results, logs) and is kept as is, on the run's volume and in the published repository.

Model weights live in the run's shared Hugging Face cache, not in this folder. To fetch them elsewhere:

```bash
hf download Qwen/Qwen3-8B-FP8
hf download RedHatAI/Meta-Llama-3.1-8B-Instruct-FP8
```

## Upload exclusions

These should not be published: `.venv/`, `.cache/`, `__pycache__/` and the agent session files. The patterns are `(^|/)\.venv/`, `(^|/)\.cache/`, `(^|/)__pycache__/`, `^\.repl_agent\.ptylog$` and `^\.aii_claude_session\.json$`.
