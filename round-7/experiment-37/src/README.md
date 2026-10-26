# Evolving programs to find new algorithms (iteration 7, claim N)

Does an evolutionary program search — FunSearch-style islands over a MAP-Elites archive, with an executable
evaluator and a novelty critic built from 18,237 known solutions — make an 8B model write correct
**out-of-catalogue** algorithms far more often per call than the best single-sample prompting knobs?

**Pre-registered prediction:** S ≥ 10× K on ≥ 2 tasks, at level a (distinct out-of-catalogue programs that pass a
screen). Here S is the search and K is the better of the two iteration-5 text knobs EAP and BINT on each task.
**Verdict: NOT MET** on all three tasks at level a. At level b (programs adjudicated as out-of-catalogue), only T03
produces any such program, so level b is NOT MET overall too. **No correct novel algorithm** was found among 1,870
out-of-catalogue-screen programs in 244 adjudicated candidates. Because the judge gate failed (see below), the
novelty claim is "manually audited", not "judge-verified".

## What was done

* **Mutator.** Qwen/Qwen3-8B @ `b968826d…` (bf16, thinking off) on vLLM 0.11.0, one RTX A4500. Decoding: T 1.0,
  top-p 1, no top-k, held constant across arms. vLLM ran in eager mode because the container has no C compiler for
  `torch.compile`.
* **Tasks.** Each task is the frozen bench of an earlier iteration, vendored read-only with sha256s:
  * T2 — weighted shortest path, `solve(n, edges, s, t)`, 5 catalogue modes.
  * T03 — k-th smallest, `solve(nums, k)`, 6 modes.
  * A3 — trapping rain water, `solve(height)`, 4 modes.
* **Evaluator** (`src/sandbox*.py`). Each program first passes an AST pre-screen (banned imports and calls; literals
  over 64 elements). It then runs in a fresh `python3.12 -I -S` subprocess with RLIMIT_AS 2 GiB, RLIMIT_NOFILE 32,
  RLIMIT_CPU, per-case alarms and stubbed network/process modules, through three stages:
  1. 8 quick cases;
  2. the full hidden suite;
  3. 10 seeded maximum-size stress inputs, checked against the fastest reference.

  "Correct" means all three stages pass. A program that hard-codes the hidden answers passes stage 2 and fails stage 3
  (unit test U1).
* **Labeller.** The frozen labellers of each bench: the runtime tracer first, then the AST label, plus the T2
  array-Dijkstra re-gate. Disputes go to a blind gemini-2.5-flash-lite judge.
* **Novelty critic** (`src/critic.py`). The corpus is rebuilt from the declared dependency `art_j3Rm_lr2nzR6` with
  iteration 6's rule: **n_corpus = 18,237, exactly as expected**. Programs are tokenised (identifiers → ID), cut into
  4-gram shingles hashed to 2^22 buckets, and compared by exact sparse Jaccard. Novelty is ν = 1 − s, where s is the
  nearest-known similarity.
* **OOC screen.** A program passes the screen if it is correct AND (its label is `other` OR s < s\*). The variant band
  s\* is the 5th percentile of s over forced catalogue programs plus the references:

  | Task | s\* |
  |---|---|
  | T2 | 0.359 |
  | T03 | 0.303 |
  | A3 | 0.608 |

* **Arms.** The same evaluator, labeller and critic score every arm.

  | Arm | What it is |
  |---|---|
  | S | Full search: 4 islands × 3 prompts × 4 children per round; 2 parents per prompt, drawn with a Boltzmann choice over cells (τ periodic over 500 calls); the worst island is reset every 500 calls; cell = (runtime label, DS-signature). |
  | NE | AlphaEvolve-style no-evolution ablation: the same prompt, but the parents are frozen seed references. |
  | I0 | The same novelty instruction with no parents. |
  | EAP | Iteration-5 enumerate-and-pick knob. |
  | BINT | Iteration-5 knob: the Qwen3-8B-Base model writes an intent. |
  | B0 | Neutral twin prompt. |
  | L | Optional: a larger mutator, qwen3-235b via OpenRouter, 500 children. |

* **Statistics** (`src/analysis.py`, hash-committed before any GPU sample):
  * the exact conditional binomial test of two Poisson rates, with a one-sided Clopper–Pearson LB95 and Holm
    adjustment;
  * rule-of-three bounds for zero counts;
  * Chao-1 rarefaction and extrapolation of idea-cluster richness;
  * an island bootstrap;
  * an arm-shuffle placebo.
* **Pre-registration.** `commitments.log` is a sha256 hash chain:
  * commit #0 — before any GPU sample;
  * commit #1 — s\* and N, before the first decisive sample;
  * amendments 1–3 — BINT-intent headroom, a critic bug fix, and Level 2 on T03;
  * commit #2 — the frozen candidates and controls, before any judge call.

## Results

Counts per task × arm. N = calls. Correct = passes stages 1–3. X_a = distinct OOC-screen programs. X_b = distinct
adjudicated KNOWN-OUTSIDE + NOVEL programs.

| Task | Arm | N | Correct | X_a (rate) | X_b | OOC clusters |
|---|---|---|---|---|---|---|
| T03 | **S** | 2500 | 1917 | **412 (0.165)** | **78** | 63 |
| T03 | NE | 500 | 444 | 52 (0.104) | 0 | 13 |
| T03 | I0 | 500 | 471 | 57 (0.114) | 2 | 11 |
| T03 | EAP | 1250 | 787 | 31 (0.025) | 0 | 10 |
| T03 | BINT | 1250 | 947 | 23 (0.018) | 0 | 8 |
| T03 | B0 | 200 | 198 | 1 (0.005) | 0 | 1 |
| T03 | L (235B) | 500 | 441 | 67 (0.134) | 23 | 45 |
| T2 | **S** | 1500 | 1079 | **46 (0.031)** | 0 | 11 |
| T2 | NE | 500 | 414 | 1 (0.002) | 0 | 1 |
| T2 | I0 | 500 | 270 | 7 (0.014) | 0 | 3 |
| T2 | EAP | 750 | 499 | 6 (0.008) | 0 | 2 |
| T2 | BINT | 750 | 715 | 5 (0.007) | 0 | 4 |
| T2 | B0 | 200 | 200 | 0 | 0 | 0 |
| A3 | S | 1000 | 817 | 31 (0.031) | 0 | 7 |
| A3 | NE | 300 | 158 | 33 (0.110) | 0 | 4 |
| A3 | I0 | 300 | 94 | 17 (0.057) | 0 | 7 |
| A3 | EAP | 500 | 305 | 17 (0.034) | 0 | 6 |
| A3 | BINT | 500 | 486 | 9 (0.018) | 0 | 3 |
| A3 | B0 | 100 | 100 | 1 (0.010) | 0 | 1 |

**Primary test**, S vs K, where K = EAP on every task by the max rule (`results/ratio_tests.json`):

| Task | Level | R̂ | LB95 | Verdict |
|---|---|---|---|---|
| T2 | a | 3.83 | 1.83 | NOT MET |
| T03 | a | 6.65 | 4.86 (CI 4.61–9.91) | NOT MET |
| A3 | a | 0.91 | 0.54 | NOT MET |
| T03 | b | ∞ (78 vs 0) | 12.8 | STRONG |
| T2, A3 | b | — | — | NOT ESTIMABLE (0 vs 0) |

The overall verdict is NOT MET at both levels.

**Secondary contrasts and other findings:**

* **Is it evolution or the prompt?** On T03, S beats NE (no evolution, same prompt) at level b: 78 vs 0, LB95 5.1.
  It also beats I0 (instruction only): 7.8×, LB95 2.4. At level a, S's edge over NE and I0 is modest: 1.6× and 1.45×.
  The instruction itself does most of the level-a work (I0 vs K = 4.6×, LB95 3.1).
* **Composition across generations.** 66 of the 93 level-b S rows on T03 sit at depth ≥ 2 with non-seed parents.
  Figure F5 shows a known-outside-catalogue program reached after 13 generations.
* **Critic gaming (plan F8).** On T2, S's 15× level-a lead over NE (LB95 3.1) is entirely restyled SPFA: every level-a
  T2 program adjudicated is a catalogue variant or degenerate. Two of the search's out-of-catalogue-screen T2 programs are wrong in
  general despite passing every test, because they de-duplicate on distance modulo a constant (counterexample in
  `results/manual_reads.jsonl`).
* **A3.** The search loses to NE and I0, and nobody leaves the catalogue at level b.
* **Larger mutator.** L (235B) vs S's first 500 calls: level a 0.84×; level b 23 vs 9 (2.6×, LB95 1.3).
* **What the out-of-catalogue programs are.** All known techniques: value-range bisection ("binary search on the
  answer"), Fenwick-tree and treap order statistics, bucket/histogram select, partial selection sort.
* **Novelty claim.** 0 NOVEL. The rule-of-three bound is ≤ 7.5% over the 40 merged adjudicated clusters (≤ 2.0% over
  the 152 pre-merge clusters). The bound is ≤ 0.16% per correct T03-S program.
* **Robustness checks.**
  * The island bootstrap of S's rate on T03 is 0.173–0.227.
  * The arm-shuffle placebo is significant in 1–6% of shuffles, with median R̂ ≈ 1.
  * `audit/rederive.py` (stdlib only) re-derives every headline count, rate, ratio, CI and verdict: 109 checks,
    0 mismatches.

**Adjudication (honest account).**

* **The judge gate failed.** No judge family reached the pre-registered ≥ 9/10 control gate. Scores: Mistral Medium
  3.1 6, Kimi K2 8, Gemini 2.5 Flash 6, DeepSeek V3.1 6, GPT-4.1-mini 5. Every judge called the D'Esopo-Pape control a
  SPFA variant. Most called Floyd–Rivest and the sparse-table control variants. 3 of 5 called the decreasing-height
  control NOVEL.
* **So the reads decide.** Under the pre-registered fallback (F5), the final class of every candidate is the
  executor's manual read: 121 full reads and 123 structured reads.
* **Advisory votes.** The pre-registered pair was still run as ungated advisory votes. Their κ was 0.42 and raw
  agreement 0.87. Judge-vs-manual agreement was 0.75 and 0.74. All 11 judge NOVEL calls were overturned on reading:
  dead-code "tournaments", partial selection sort, and SPFA on a residue-lifted graph.
* **The reads were not blind to arm.** An arm-blind, rule-based re-classification (`src/rulecheck.py`) agrees with the
  manual classes on 94.4% of 816 distinct OOC programs. It reproduces the T03 level-b contrast: S 87/2500 vs EAP
  2/1250, LB95 6.7.
* **Propagation.** Unshown cluster members inherit their medoid's class; 84 of 92 read extras agreed with their
  medoid.
* **The boundary rule used in the reads** is in `results/deviations.json` (D22).

**Costs.** The OpenRouter spend was USD 0.89 in total: adjudication 0.75, labeller disputes 0.05, arm L 0.09. Total
generation was ≈ 1.0 GPU-hour. The measured throughput was about 16.8k S-shaped children per hour and about 43.9k B0
children per hour on T03.

**Deviations.** There are 24 deviations, each recorded with its consequence in `results/deviations.json`. The main
ones:

* eager vLLM (D2);
* the decoding of EAP and BINT held at T 1.0 (D4);
* A3's high s\* (D8);
* Level 2 run only partially on T03 (D12);
* the judge-gate failure leading to manual reads (D20, D21).

## Layout

| Path | What it is |
|---|---|
| `method.py` | Stage CLI: inputs, corpus, tests, commit0, calib, commit1, base, run, L, label, adjudicate, classes, analyse, outputs. |
| `src/common.py` | Paths, logging, hashing, the commitments hash chain. |
| `src/inputs.py` | Read-only vendoring of the non-declared inputs and task assembly: verified references, quick, hidden and stress stages. |
| `src/sandbox.py`, `src/sandbox_runner.py` | The AST pre-screen and the three-stage evaluator, run in fresh `-I -S` subprocesses with rlimits. |
| `src/labels.py` | Wrappers around the frozen labellers (T2, T03, A3), the combine rule, DS-signatures. |
| `src/critic.py` | The known-solution corpus (18,237 + 20 references), the tokeniser, sparse Jaccard, AST distances. |
| `src/prompts.py` | Every arm's prompt text; the exact strings are frozen in `predictions/prompts_frozen.json`. |
| `src/engine.py` | vLLM engine (per-request seeds, GPU-seconds apportioned by tokens) and the OpenRouter engine for arm L. |
| `src/search.py` | Islands × MAP-Elites archive, Boltzmann parents, resets, the frozen seed pool used by NE. |
| `src/run.py` | Calibration, base intents, and the interleaved search + i.i.d. run (resumable). |
| `src/arm_l.py` | The large-mutator arm. |
| `src/orclient.py` | OpenRouter guard: per-purpose USD caps and the stop rule for budget 403s. |
| `src/finalize.py` | Final labels, the OOC screen, `data/samples.jsonl`, the analysis stage. |
| `src/adjudicate.py` | Dedup, clusters, candidates, complexity probes, controls, judges, final classes. |
| `src/advisory.py` | Ungated advisory judge votes (the F5 path). |
| `src/manual_queue.py` | Prints programs for the manual reads. |
| `src/rulecheck.py` | Arm-blind level-b replication. |
| `src/analysis.py` | All decisive statistics; committed at #0. |
| `src/figures.py`, `src/outputs.py` | Figures F1–F6; `method_out.json`. |
| `tests/test_units.py` | CPU unit tests U1–U5 (13 tests, all pass). |
| `audit/rederive.py`, `audit/rederive_raw.py` | Stdlib-only re-derivations: from `data/samples.jsonl`, and independently from the raw rows (exact binomial sums, placebos, commit-timestamp check). Their reports are `audit/*_report.json`. |
| `reproducibility.md`, `restore.sh`, `pyproject.toml` | Exact reproduction record; environment restore; all 172 packages pinned. |
| `inputs/vendor/`, `inputs/vendor_manifest.json` | Vendored benches, labellers and prompts, with their source paths and sha256s. |
| `inputs/tasks/*.json` | Assembled task objects. |
| `predictions/` | commit0/1, amendments, prompts, throughput pilot, engine configs. |
| `commitments.log` | The hash chain. |
| `data/rows_{T2,T03,A3,L}.jsonl` | One row per generated program. |
| `data/samples.jsonl` | The protocol rows: labels, OOC screen, distinct/cluster ids, final classes. |
| `data/raw/` | Prompts and raw outputs per arm, EAP stage-1 lists, BINT intents. |
| `data/corpus/` | Corpus matrix, ids, codes, AST sequences. |
| `data/adjudication_candidates.json`, `data/controls.json`, `data/complexity.json`, `data/judge_calls.jsonl` | Adjudication inputs and calls. |
| `data/search_state_*.json`, `data/seeds_*.json` | Search state and seeds. |
| `results/verdict.json` | The verdicts. |
| `results/ratio_tests.json`, `results/arm_rates.json` | Primary and secondary tests; per task × arm counts. |
| `results/matched_effort.json`, `results/lineage.json`, `results/dynamics.json` | Matched-effort richness, lineage, archive dynamics. |
| `results/placebo.json`, `results/L_vs_S.json` | Placebos; arm L vs S. |
| `results/adjudication.json`, `results/judge_gate.json` | Adjudication summary; the control gate. |
| `results/manual_reads.jsonl` | The executor's reads, with rationales. |
| `results/propagation_check.json`, `results/levelb_rule_check.json` | Propagation reliability; the arm-blind rule check. |
| `results/deviations.json`, `results/costs.json`, `results/openrouter_ledger.jsonl` | Deviations, costs, the OpenRouter ledger. |
| `results/engine_check.json`, `results/a3_regate.json`, `results/archive_*.json` | Engine check, A3 re-gate, archive snapshots. |
| `figures/F1–F6` (.pdf and .png) | Discovery curves, archive heatmaps, novelty distributions, adjudication, lineage, program-space MDS. |
| `method_out.json` (plus `full_`, `mini_`, `preview_` variants) | Output in the exp_gen_sol_out schema: search_programs (6,274 distinct correct programs), adjudication (244 + 10 controls), arm_summary. |
| `logs/` | Stage logs. |

All outputs are small text, JSON or figure files (the largest is `data/samples.jsonl`, 30.5 MB), so everything except the
deleted caches below is in the published repository. No trained weights were produced.

## How to run

`reproducibility.md` has the complete record of what was run (commands, seeds, hardware, runtimes, expected numbers). `restore.sh` recreates the environment. `audit/rederive_raw.py` re-derives every primary and secondary result from the raw rows with exact binomial sums and placebos.

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r pyproject.toml
# the declared dependency: set ART_J3RM_DIR=<path to art_j3Rm_lr2nzR6> if it is not at the run-layout location
.venv/bin/python method.py --stage inputs
.venv/bin/python method.py --stage corpus
.venv/bin/python method.py --stage tests
.venv/bin/python method.py --stage commit0
.venv/bin/python method.py --stage calib
.venv/bin/python method.py --stage commit1 --gpu-hours 2.0
.venv/bin/python src/amend_intents.py
.venv/bin/python method.py --stage base
.venv/bin/python method.py --stage run
.venv/bin/python src/amend_level2.py
.venv/bin/python method.py --stage run --plan predictions/amendment3.json
.venv/bin/python method.py --stage L
.venv/bin/python method.py --stage label
.venv/bin/python method.py --stage adjudicate --tasks T03,T2,A3
.venv/bin/python src/advisory.py
# manual reads: results/manual_reads.jsonl (src/manual_queue.py prints the queue)
.venv/bin/python method.py --stage classes
.venv/bin/python method.py --stage analyse
.venv/bin/python src/rulecheck.py
.venv/bin/python method.py --stage outputs
python3 audit/rederive.py && python3 audit/rederive_raw.py
```

GPU stages (calib, base, run) need about 20 GB of VRAM. The model weights come from the Hugging Face cache, pinned
at revision `b968826d9c46dd6066d109eabc6255188de91218` for Qwen/Qwen3-8B and
`49e3418fbbbca6ecbdf9608b4d22e5a407081db4` for Qwen/Qwen3-8B-Base. OpenRouter stages need `OPENROUTER_BASE_URL` and
`OPENROUTER_API_KEY`.

## Restoring removed files

The `.aii/manifest.yaml` marks only regenerable caches for deletion:

| Removed path | Restore with |
|---|---|
| `.venv/` | `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r pyproject.toml` |
| `**/__pycache__/` | Recreated automatically by Python on the next run of any stage. |

The model weights were never stored in this workspace; they live in the shared Hugging Face cache. Restore them with:

```bash
huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218
huggingface-cli download Qwen/Qwen3-8B-Base --revision 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
```

## Licences and data notes

The corpus files under `data/corpus/` derive from the dependency's sources:

* Mercury and KodCode: CC-BY-NC.
* XLCoST: CC-BY-SA.
* LeetCodeDataset, TheAlgorithms, HumanEval+ and ENAMEL: Apache-2.0 or MIT.

They are used here for non-commercial research. The optional llm-creativity programs (no licence) were not
downloaded.
