# What does a ban switch the model to?

A behavioural screen on **Qwen/Qwen3-8B** (thinking off, vLLM 0.11.0, T = 1.0) of two rival predictors of where
probability mass goes when a prompt bans an algorithm:

- **Substitution by association** (the proposed method): the model's own ranked "standard alternative to X" map,
  elicited with 20 permuted-order complete rankings per catalogue mode and Borda-aggregated.
- **Typicality ladder** (the baseline/rival): the latent baseline frequency of each mode, renormalised over the
  modes that survive the ban.

Two path-search tasks are used: T1, an unweighted grid path with 6 catalogue modes, and T2, a weighted shortest path
with 5 modes. Every prediction is frozen and sha256 hash-chained (`commitments.log`) **before** the samples it
predicts
are generated. All results are descriptive: two tasks and two informative events cannot support an inferential claim.

## Headline results (all numbers in `method_out.json` / `results/`)

| | T1 grid path | T2 weighted shortest path |
|---|---|---|
| Baseline (N=300, also T=1.3 and no neutral segment) | 100% BFS | 100% Dijkstra |
| Single ban of the modal mode | compliance 0.90 → all 38 compliant correct samples are **DFS** | compliance 0.91 → all 86 compliant correct samples are **Bellman-Ford/SPFA** |
| Association (Borda) nomination | Dijkstra (clarity 0.20; DFS ranked last) → **miss** | Bellman-Ford/SPFA → **hit** |
| Frequency (typicality) nomination | tied over all survivors (baseline fully collapsed) | tied |
| Free-text "standard alternative" / listall cue | DFS / DFS → hit / hit | Bellman-Ford/SPFA / Bellman-Ford/SPFA → hit / hit |
| Cumulative double ban (succession step 2) | compliance **0.06**; 41/94 recurrent programs never name the banned algorithm ("backtracking") | compliance **0.00**; 58/100 recurrent programs never name it ("BFS with pruning" = SPFA) |

- **Contest result.** Association beat frequency on 1 of 2 informative events. The mean paired log-score difference
  was −0.27 nats/sample. Within-event CIs are degenerate because every compliant sample in each event has the same
  label. The model's own free-text answer and the "list all approaches" typicality cue nominated the realised
  substitute in both events.
- **Post-hoc textbook map.** gpt-4.1-mini (`elicitation/ref_assoc_objects.json`), collected after the freeze and
  so not a contest predictor, shows the same split for X = BFS: its Borda winner is bidirectional BFS, while its
  free-text answer is DFS. The ranking question appears to elicit the closest shortest-path variant rather than
  the canonical "standard alternative".
- **Succession.** Both successions stopped at step 2 under the pre-registered fewer-than-20-compliant rule: with two
  banned names the model re-implements the banned mechanism under another description.
- **Mention twins are not placebos.** Mentioning an absent mode moves +56 to +100 pp of mass to it (DFS, IDDFS,
  A*, Bellman-Ford/SPFA, Floyd-Warshall), but about 0 pp for Dijkstra on grids, Dial and bidirectional Dijkstra.
- **Sham bans.** Banning an absent mode leaves the modal mode at 77–100%. It shifts up to 23% of mass toward a
  related mode: a Floyd-Warshall ban gives 23% Bellman-Ford/SPFA.
- **Labeller.** Both labellers identify all 22 reference variants. The gate's runtime-accuracy targets were **not**
  met on the evaluation gold: kappa runtime-vs-AST 0.75, runtime vs adjudicated 0.84, AST vs adjudicated 0.89,
  combined label vs adjudicated 0.97. Per protocol, every runtime/AST disagreement is labelled by the blind judge,
  and `gate_passed=false` is recorded.
- **Cost.** OpenRouter USD 0.27 in total (judge, gold adjudication, Llama + gpt-4.1-mini elicitation); about 6 GPU-minutes of generation on one RTX 5090.

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator; one sub-command per stage (see "How to run"). |
| `pipeline.py` | Stage code for the task suite, labelling (extract → tests + probes → AST/runtime → judge → combine) and the gate dispatcher. |
| `common.py` | Frozen protocol constants: task texts, catalogue and display names, thresholds, the hash-chain commit helper. |
| `gen/prompts.py` | Builds every paraphrase of every condition and the elicitation prompts. |
| `gen/run_vllm.py` | Async batch runner against one `vllm serve` process: chat template with `enable_thinking=False`, prompts sent as token ids, per-request seeds. |
| `prompts/conditions.json` | All frozen prompts (sha256-committed before any generation). |
| `tasks/{t1_grid,t2_wsp}/spec.txt` | Task specification (DESCRIPTION + FORMAT). |
| `tasks/{t1_grid,t2_wsp}/references/*.py` | 12 + 10 reference implementations, at least 2 variants per catalogue mode. |
| `tasks/{t1_grid,t2_wsp}/tests.json`, `limits.json` | Seeded hidden tests (48 / 45 cases) and per-case time limits (max(1 s, 10 × the slowest reference)). |
| `tasks/tests_gen.py` | Hidden-test generators and checkers. |
| `tasks/sandbox_tests.py` | Fresh-process test runner: stdlib-only CPython `-I -S`, 2 GB RLIMIT_AS, 256 MB thread stack, forbidden-import screen. |
| `tasks/harness.py` | Parent-side subprocess harness. |
| `labeller/extract.py` | Code-block extraction. |
| `labeller/ast_rules.py` | Static labeller. |
| `labeller/tracer.py` | Runtime tracer subprocess (heapq / deque / queue proxies, list-pop direction, grid-access order, line scaling). |
| `labeller/runtime_rules.py` | Runtime decision rules. |
| `labeller/judge.py` | Strategy-blind OpenRouter judge with cost ledger and budget stop. |
| `labeller/combine.py` | Combines runtime, AST and judge labels. |
| `labeller/gate.py` | Labeller gate. |
| `labeller/gold_set.jsonl`, `labeller/gate_report.json` (+ `_round0`) | Adjudicated gold set and gate metrics. |
| `labeller/judge_cache.jsonl` | Every judge response, keyed by model and code sha256. |
| `elicitation/*.jsonl`, `elicitation/assoc_objects.json`, `elicitation/baseline_objects.json` | Qwen and Llama-3.1-8B rankings and free-text answers; Borda / first-rank / clarity / Kendall's W maps; baseline frequencies and strata. |
| `predictions/*.json`, `commitments.log` | Frozen composed predictions and their sha256 hash chain. |
| `data/raw_*.jsonl` | Raw generations (pre-ban, ban arms, succession, ranking retries, smoke, reproducibility check). |
| `data/labelled.jsonl` | Every program row with code, tests, runtime/AST/judge labels and raw text. |
| `data/samples.jsonl` | One row per generated program in the shared screen schema (3,260 rows). |
| `data/program_eval_cache.jsonl` | Per-unique-program test results and raw tracer probes. |
| `data/condition_summaries.json` | Per-condition label counts, pass rates (Wilson), Hill_cc, other / no-code / truncation rates. |
| `analysis/assoc.py`, `analysis/stages.py`, `analysis/succession.py` | Association objects, prediction composition, freeze and ban/succession stages. |
| `analysis/metrics.py`, `analysis/score.py`, `analysis/outputs.py` | Statistics and scoring, `method_out.json` and figures. |
| `results/*.json` | Event table, contest, T9 family test, S1 sham control (+ sham-vs-baseline), mention effects, C4, landing table, commitment audit, disguised recurrence, gate, task-suite acceptance, OpenRouter cost ledger, seed reproducibility check. |
| `figures/*.png` | Predicted-vs-realised bars, paired log scores, landing chart. |
| `method_out.json` (+ `full_` / `mini_` / `preview_`) | Final output in the `exp_gen_sol_out` schema: one example per event plus the reference conditions and mention twins. |
| `logs/` | Stage logs and the vLLM server log, which shows the effective SamplingParams of every request. |
| `audit/rederive.py`, `results/independent_rederivation.json` | Independent re-derivation of the 36 headline numbers from raw files, through separate code, plus placebo runs of the contest and T9 comparisons (36/36 match; placebos fail as they should). |
| `reproducibility.md`, `restore.sh` | Step-by-step reproduction: Path A (exact, CPU only, from the published raw generations) and Path B (full regeneration); venv restore. |
| `pyproject.toml`, `uv.lock` | All 167 installed packages pinned with `==` (from `uv pip freeze`), with the matching linux x86_64 lock. |

Everything stays on the run's volume; nothing here is 100 MB or larger, so everything is published except
`.venv/`.

## How to run

See `reproducibility.md` for the complete, ordered procedure. It covers exact CPU-only re-analysis from the
published raw generations, and full regeneration.

Full regeneration requires a GPU with at least 20 GB (32 GB used here), `uv`, and the OpenRouter env vars
(`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY`). Candidate programs run in a stdlib-only CPython 3.12: set
`SANDBOX_PYTHON` if `python3.12` is not at `/usr/local/bin` or `/usr/bin`.

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml   # or: ./restore.sh
# one long-lived server for every GPU stage (no C compiler in this container -> --enforce-eager)
.venv/bin/vllm serve Qwen/Qwen3-8B --dtype bfloat16 --gpu-memory-utilization 0.90 --max-model-len 2048 \
  --max-num-seqs 128 --seed 1234 --generation-config vllm --enable-prefix-caching --enforce-eager \
  --port 8011 --host 127.0.0.1 --served-model-name qwen3-screen --enable-log-requests --max-log-len 120 &
uv run method.py prompts                    # freeze + hash prompts
uv run method.py smoke                      # template / extraction / ranking-parse smoke test
uv run method.py preban --limit 10; uv run method.py preban --limit 100; uv run method.py preban
uv run method.py tasks                      # hidden tests, time limits, reference + mutation acceptance
uv run method.py label --src data/raw_preban.jsonl --no-judge   # mechanical labels only (rule development)
uv run method.py gate                       # labeller gate (gold set adjudication)
uv run method.py label --src data/raw_preban.jsonl              # full labelling incl. judge
uv run method.py elicit; uv run method.py external; uv run method.py assoc
# (optional, post hoc, descriptive) textbook-consensus map with gpt-4.1-mini, run after the freeze here:
uv run method.py reference_map
uv run method.py freeze                     # predictions hash-committed BEFORE any ban prompt
uv run method.py bans                       # ban arms N=100 + mention twins N=50, then labelling
uv run method.py succession                 # greedy cumulative bans (each step frozen before generation)
uv run method.py score; uv run method.py outputs
```

Every stage resumes from what is already on disk: generation skips request ids that are present, and evaluation
and judge calls are cached by code sha256.

**Reproducibility.** Per-request seeds are `int(sha256('task|condition|paraphrase|stage')[:8], 16)` and are stored in
every row. Re-sending 6 requests (64 samples) to the same server reproduced 39/64 texts exactly
(`results/seed_reproducibility_check.json`). bf16 numerics depend on batch composition, so reproducibility is at the
distribution level, not the token level.

## Deviations from the plan (also in `method_out.json` → `metadata.deviations`)

- The smoke test omitted the ban prompt, so that no ban output existed before the freeze.
- vLLM ran with `--enforce-eager` because the container has no C compiler for Triton/Inductor. Only speed is
  affected.
- `max_num_seqs=128` and `gpu_memory_utilization=0.90`, because the pod had a 32 GB card.
- The first character of every condition segment is upper-cased.
- Gate revision round 1 made the tracer pre-inject common stdlib names. It changed no gold label, and the gate
  targets were still not met.
- 60/440 free-text answers were truncated at 32 tokens.
- Both baselines are fully collapsed (degenerate-baseline fallback): the frequency predictor is uniform for every
  event, its nomination is tied/unstable, the STABLE-D-AF stratum is empty, and the subtraction family in the T9
  test is uniform.
- Succession stopped at step 2 for both tasks (ban failure), so there are only 2 informative contest events.
- Gold adjudication used gpt-4.1-mini and gemini-2.5-flash, with deepseek-chat-v3.1 as tie-breaker. The production
  judge is gpt-4.1-mini, so the combined-label gold accuracy is optimistic.

## Restoring removed files

Only regenerable bulk is marked for deletion in `.aii/manifest.yaml`:

- `.venv/` (about 14 GB): run `./restore.sh`, or
  `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`. All 167 packages
  are pinned exactly, e.g. `vllm==0.11.0`, `torch==2.8.0`, `transformers==4.57.6`.
- `__pycache__/`, `analysis/__pycache__/`, `gen/__pycache__/`, `labeller/__pycache__/` and `tasks/__pycache__/`
  (bytecode caches, about 50 KB to 1 MB each) are recreated automatically on import by any stage. To rebuild them
  all at once: `uv run python -m compileall -q -l method.py pipeline.py common.py analysis gen labeller tasks`.
- The model weights are not stored in this workspace (they live in the run's shared HF cache). To re-download:
  `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
