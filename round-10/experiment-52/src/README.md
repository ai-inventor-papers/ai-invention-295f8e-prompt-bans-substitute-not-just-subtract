# NOV-B2: can guided LLM program search invent online bin-packing rules? (second, independent run)

This folder is a complete, resumable experiment. A FunSearch-style island search uses Qwen3-8B-FP8 (vLLM 0.11,
thinking off) to mutate Python priority functions for online bin packing. The question is where the sampling
randomness should be spent. Arms run at matched calls in lockstep rounds:

| arm | what it does |
|---|---|
| T1.0 | temperature 1.0 |
| T1.6 | temperature 1.6, top-p 0.95 |
| DTB | decision-token branching: force a rank-2..8 token at the highest-entropy eligible position among the first 48 body tokens |
| RPB | the same forcing at a random eligible position (placebo) |
| IDEA | an instruction to use a different idea |
| NS | no selection (Zhang et al.'s random-sampling baseline) |

It is the pre-registered replication on seeds 2 and 3 (protocol v10), implemented independently from the shared
specification. It adds an exploratory, separately pre-registered extension on seeds 4 and 5.

## Design in one paragraph

- **Harness.** FunSearch's exact priority harness: pre-allocated bins, argmax with first-index ties, score = used
  bins. It was copied from the iteration-9 workspace, verified by sha256 and re-gated before any call: best fit
  212.0 bins / 5.37 % (OR3) and 2067.0 / 3.98 % (Weibull 5k); c12 207.45 / 3.11 %; c14 2001.4 / 0.68 %.
- **Selection** uses SEL-OR + SEL-W only (F = mean of the two excesses normalised by best fit; BF has F = 1).
- **Held-out sets.** Primary: FunSearch's Weibull 5k test set (H-FSW5k) and OR-Library binpack3 (H-OR3). Six more:
  binpack1/2/4, fresh Weibull 5k/10k and a shifted Weibull.
- **Behaviour** is the bin choice on 2,000 committed probe states (P10). Clusters use complete linkage at 0.95
  agreement.
- **Novelty** means agreement below 0.9 with every corpus program. The corpus holds 82 published, textbook and
  dependency programs (FunSearch, EoH runs 1-3, HSEvo, MCTS-AHD, ReEvo, LLM4AD, RAISE, the S3b scan) plus all 3,843
  members of the ab family (Herrmann & Pallez). Candidates passing that filter then went through gated LLM judges and
  an arm-blind manual read.
- **Baselines:**
  - FF, BF, WF, AWF, next fit and harmonic-k;
  - every retrievable published heuristic;
  - the tuned ab member (random search with C* evaluations);
  - NS.
- **Pre-registration.** Every rule was hash-committed before the first generation call (`commitments.log`,
  `predictions/commit1.json`). C* = 2000 calls per arm-seed was chosen by the committed rule (commit #2), and the
  extension and corpus additions by commit #3.

## Results (pre-registered verdicts, seeds 2-3; every number independently re-derived by `audit/rederive.py`)

| claim | verdict | key numbers |
|---|---|---|
| V1: every core arm's best beats 0.8 x BF on both primary sets | **PARTIAL** | H-FSW5k / H-OR3 excess: DTB 2.395 / 3.852 %, RPB 1.720 / 3.703 %, IDEA 2.133 / 3.554 % (pass; limits 3.187 / 4.294 %); T1.0 3.672 / 4.821 % and T1.6 3.984 / 5.368 % (= BF) fail |
| V2: DTB finds more behaviour clusters than temperature (x1.5) and than its random-position placebo (x1.2) | **PARTIAL** | clusters per 2,000 calls, seed 2 / 3: DTB 230 / 143, RPB 269 / 233, IDEA 134 / 150, T1.0 13 / 8, T1.6 1 / 1, NS (1,000 calls) 5 / 3. R_T1.0 = 17.8, R_T1.6 = 186.5, R_RPB = 0.74 (fails); shuffled-arm placebo: 0 / 200 supported |
| V3: at least one novel-and-better heuristic | **DISCONFIRMED** | 151 candidates; 50 pass the 0.8 rule; 48 also pass the corpus-novelty filter; 40 judged; 0 NOVEL in the decisive arm-blind manual read (rule-of-three bound 7.5 %) |
| V6: the IDEA instruction mostly yields behavioural renames | **PARTIAL** | rename share (agreement >= 0.95 with a parent): IDEA 0.670, T1.0 0.959; 0.4 % of IDEA offspring claim a new idea in a comment |
| V5 (descriptive): are discoveries carried by single decision tokens? | n = 30 | forcing the argmax back at the offspring's high-entropy deviating token reverts it to a parent's behaviour in 49.8 % of continuations vs 25.5 % at random deviating positions (diff 0.243, bootstrap 95 % CI [0.079, 0.417], sign-flip p = 0.0086) |

What the results say:

- **Temperature is not a creativity knob here.** T1.6 with top-p 0.95 is effectively greedy, because the model's
  top token has p > 0.95: in 4,000 calls it only ever copies the parent, giving one cluster. T1.0 copies 96 % of the
  time.
- **Forcing pays, the position does not.** Forcing any non-top token (DTB or the RPB placebo) or asking for a
  different idea (IDEA) yields 7-18x more behaviours and better held-out heuristics. Choosing the forced position by
  entropy is not better than choosing it at random.
- **No new rules.** The 48 behaviour-level-novel candidates all recombine known principles: BF on near-exact fits,
  an avoided residual band (the ab family and c12), and a target residual of about c x item, which is already in the
  published EoH run-3 and MCTS-AHD programs.
- **The tuned baseline is strong.** The tuned ab member ab-FF(5,22) reaches F = 0.740 against 0.726 for the best
  searched program. On held-out data it scores 2.143 % / 3.057 % on H-FSW5k / H-OR3: it beats every arm's best on
  H-OR3, while the best RPB and IDEA programs beat it on H-FSW5k.
- **Judges.** The two judge families, and the replacement family, failed their 10-control gates by calling
  everything known. They are therefore advisory; their labels agree with the manual read.
- **Exploratory seeds 4-5** (`results/extension_ext45.json`). The same frozen rules give V2 **SUPPORTED** (R_RPB
  1.47) and V1 PARTIAL. Per-seed DTB/RPB cluster ratios are 0.86, 0.61, 1.92 and 1.11 for seeds 2-5, and the
  4-seed pooled R_RPB is 1.08. The entropy-targeting effect is within seed-to-seed noise; forcing over temperature is
  robust (pooled R_T1.0 = 25.5, R_T1.6 = 248).
- **Engine check.** The bf16 replay (`results/hf_replay.json`) matches the FP8 engine's top-1 token at every
  position of 20 DTB calls. It picks the same forced position in 20/20 and places the forced token within ranks 2-8 in
  20/20.

All protocol departures, with reasons, are in `results/deviations.json`; it is also copied into
`method_out.json` metadata.

## Layout

| path | content |
|---|---|
| `method.py` | entry point: `python method.py <stage>` or `all` (stage list in its docstring) |
| `src/bp.py`, `src/sandbox.py`, `src/gate.py` | harness copied from iteration 9; v10 changes in `results/harness_changes.diff` |
| `src/probes.py`, `src/corpus.py` | P10 probe states + probe gate; known corpus, ab grid, tuned ab, stateful baselines |
| `src/prompts.py`, `src/engine.py`, `src/operators.py` | prompt/render/body extraction; vLLM launcher + async client; arms incl. DTB/RPB |
| `src/islands.py`, `src/search.py` | island database; lockstep scheduler, C* rule, resume, smoke test, NS |
| `src/analysis.py` | frozen analysis (commit #1): clusters, sensitivities, bootstrap, placebo, verdicts |
| `src/heldout.py`, `src/judges.py`, `src/v3final.py` | held-out scoring and V3 filters; gated judges; V3 combination |
| `src/v5.py`, `src/hfreplay.py`, `src/figures.py`, `src/outputs.py` | V5; bf16 replay; F1-F7; method_out.json |
| `src/commit.py`, `commitments.log`, `predictions/` | hash-chained pre-registration (commit1-3), hardware record |
| `audit/rederive.py` | stdlib-only re-derivation of every headline number + placebos -> `results/audit_rederive.json` |
| `tests/test_offline.py` | 40 offline unit tests -> `results/tests_offline.json` |
| `scripts/` | S3b scan, decision profiles for the manual read, extension analysis |
| `data/instances/`, `data/probes/P10.json` | 14 instance sets (sha256-verified), the probe states |
| `data/gen_s{2,3,4,5}.jsonl` | one row per LLM call (prompt hash, parents, completion, code, operator fields) |
| `data/eval/eval_part_00{1,2}.jsonl` | one row per evaluated call (bins, F, error type, cache info), split under 100 MB |
| `data/decisions.bin`, `data/decisions_index.jsonl` | P10 decision vectors of every unique evaluated program |
| `data/corpus_decisions.npy`, `data/ab_decisions.npy` | P10 vectors of the corpus and of all 3,843 ab members |
| `data/db_s*_*.pkl`, `data/search_state*.pkl`, `data/r1_tops_*.jsonl` | island databases, resume state, logged top-20 tables of DTB/RPB request 1 |
| `results/` | every analysis (verdicts, clusters, held-out, corpus, judges, manual read, V5, replay, extension, positioning, audit) |
| `figures/` | F1-F7 as PDF + PNG |
| `method_out.json`, `full_/mini_/preview_method_out.json` | main output (exp_gen_sol_out schema) |
| `ext/`, `inputs/`, `inputs_manifest.json` | external primary sources (data only) and copy provenance |
| `reproducibility.md` | exact commands, versions, hardware, timings |

## How to run

```bash
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r <(python3 -c "import tomllib;print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))")
python method.py tests          # offline checks
python method.py all            # full pipeline (about 3 h on one RTX 4090; judges need OPENROUTER_* env vars)
```

To re-derive the results from the stored rows without a GPU, run `.venv/bin/python src/analysis.py clusters`, then
`.venv/bin/python src/analysis.py verdicts`, then `python3 -I audit/rederive.py`.

## Kept artifacts

Everything under `data/`, `results/`, `logs/`, `figures/` and `predictions/`, plus `commitments.log` and the
`method_out` files, is kept at these relative paths on the run's storage volume. The 42,000 search programs, their
evaluations and decision vectors cannot be regenerated byte-for-byte, because FP8 batching is not deterministic. No
file here reaches 100 MB: the evaluation rows are split into `data/eval/eval_part_*.jsonl`, so the published
repository holds every raw row. Model weights are not stored here; they live in the shared Hugging Face cache.

## Restoring removed files

| removed path | restore with |
|---|---|
| `.venv/` (16 GB) | `uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r <(python3 -c "import tomllib;print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))")` |
| `src/__pycache__/` | regenerated by any Python run, e.g. `python method.py tests` |
| model weights (not in this folder) | `huggingface-cli download Qwen/Qwen3-8B-FP8 --revision 220b46e3b2180893580a4454f21f22d3ebb187d3` and, for the bf16 replay, `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218` |
