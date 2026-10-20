# Banning five path algorithms at once

What does Qwen3-8B (thinking off) write when one prompt bans four or five of its usual grid path-search algorithms?
This is the run's literal multi-ban test (C4). The study extends the iteration-1 canonical suite to a 10-algorithm grid
catalogue and validates the labeller. It then computes forced-ratio latent probabilities (FRLP) for every planned
condition and hash-commits the landing forecasts. Only after that does it sample the multi-bans, and it reads the result
at the mechanism level, in activation space as well.

## Headline results

All numbers come from `results/` and `method_out.json`. The behavioural and FRLP headline numbers were re-derived
independently by `audit/rederive.py` (`results/independent_rederivation.json`) and match exactly.

| Condition (T1 grid, N = 100 = 5 templates x 20) | Banned | Landing (attempted programs) | Avoidance (Wilson 95%) |
|---|---|---|---|
| Baseline | none | BFS 100 | n/a |
| Single ban (reference) | BFS | DFS 86, BFS 14 | 0.86 (0.78-0.91) |
| TOP (top 4 by FRLP; F4 form for K = 7) | BFS, DFS, greedy, IDDFS | BFS 59, DFS 26, greedy 2, other 13 | 0.13 (0.08-0.21) |
| ARC (geodesic window) | BFS, BiBFS, A*, greedy | BFS 63, DFS 37 (survivor) | 0.37 (0.28-0.47) |
| SCATTER (max-min distance) | BFS, DFS, greedy, IDA* | BFS 69, DFS 27, A* 2, other 2 | 0.04 (0.02-0.10) |
| TOP5 (literal five-name ban) | BFS, DFS, greedy, IDDFS, A* | BFS 63, DFS 36, IDDFS 1 | 0.00 (0.00-0.04) |

- **Every multi-ban fails its gate.** The gate requires avoidance >= 0.5 and >= 20 non-banned programs. With four or
  five names banned, the model mostly re-implements the banned BFS or DFS. Between 41% and 92% of these banned-mechanism
  programs never name their own mechanism (disguise; DFS is often called "backtracking"). This extends iteration 1's
  double-ban collapse: a single ban works (0.84-0.86 avoidance), and a list ban does not.
- **The list content barely matters (post hoc, not pre-registered).** Across the four multi-bans the model writes the
  same BFS/DFS mix: the BFS share among BFS+DFS programs is 0.69, 0.63, 0.72 and 0.64 (chi-square p = 0.48;
  permutation p = 0.57; `results/posthoc_mix_homogeneity.json`). This holds whether DFS is banned (TOP, SCATTER, TOP5)
  or allowed (ARC). Avoidance differences therefore come from which of BFS and DFS happens to be on the list, not from a
  list-specific landing. A single BFS ban moves the model to DFS 86%. A four- or five-name list moves it only to about
  one third DFS, which is closer to a generic perturbation of the default than to a veto.
- **Template is a large random effect.** ARC avoidance runs from 0.00 (W4) to 0.85 (W5), and TOP from 0.00 to 0.45.
  The template-cluster bootstrap intervals are wide accordingly.
- **FRLP-implied avoidance**, committed before sampling, was below 1e-8 for TOP, SCATTER and TOP5. Realised avoidance
  was 0.13, 0.04 and 0.00, so the likelihoods foresaw the failure. For ARC the implied avoidance was 0.9995 and the
  realised value 0.37, so it was over-optimistic. A ban prompt raises the likelihood of the banned algorithms' scrubbed
  programs relative to the neutral twin (priming): for example, G_DFS is about +10 nats under the TOP W1 ban.
- **Landing tests are degenerate.** Only ARC (37 DFS programs) and SCATTER (2 A*) have survivor mass. On ARC, the
  LADDER, PRIME-AND-VETO, FRLP-BAN, GENERIC and CORPUS forecasts all named DFS as top-1 (log score +1.06 nats/program
  over uniform). PROXIMITY named IDA* and missed (-0.02). With 3 survivors the exact permutation floor is 1/6; every
  per-set p is >= 0.33 and every pooled p is >= 0.11, so nothing is significant. All of these results are descriptive.
- **Per-row predictors** (`method_out.json` predict_* fields; `results/predictor_accuracy.json`). Every example
  carries two predictions. predict_default is the task's baseline algorithm (no change). predict_ladder is the
  highest-ranked non-banned algorithm. Multi-ban rows also carry each committed top-1 survivor, and forced rows carry
  predict_requested.
  - Multi-bans: the no-change default is right for 64% of programs, against at most 10% for any committed survivor
    forecast.
  - Single bans: the ladder is right for 85% of programs, against 15% for the default.
  - Forced prompts: the requested algorithm is written 66% of the time.
- **T2 leave-one-survivor ("will" vs "can").** When the other four are banned, the model writes Dijkstra 95% and
  Bellman-Ford/SPFA 51% of the time. It writes bidirectional Dijkstra, Floyd-Warshall and Dial 0% of the time,
  falling back to the banned Dijkstra or BF/SPFA instead, even though when forced it can write Floyd (40/40 correct)
  and Dial (36/40 attempted).
- **Catalogue extension failed the keep rule** (>= 70% of 40 forced programs labelled as requested). Only BFS (40/40),
  DFS (40/40), IDDFS (37/40), greedy best-first (35/40) and IDA* (36/40, descriptive prompt) pass. A* (11/40) is most
  often written as a cost-only heap (Dijkstra-like). Unit-weight Dijkstra (13/40) is often written as BFS. JPS (7/40)
  and bidirectional A* (5/40) mostly come out as BFS and A*, and BiBFS reaches 21/40. Under F4, K = 7 gives 4-name
  sets. The analysis catalogue keeps A* and BiBFS, flagged keep-failed: they have >= 10 programs and pass the gold set.
- **Labeller.** References score 25/25 on both the runtime and AST labels, and the targeted unit probes 4/4. The
  canonical exp1 labeller re-check gives 135/144 = 0.94 and 22/22. The 40-program gold gate was not met: 33/40 in round
  0 and 32/40 after the one allowed revision. Runtime-vs-AST kappa is 0.53. Unit-weight Dijkstra, JPS and bidirectional
  A* are excluded (< 3/4 gold).
- **Geometry and internals.** Centroid MDS stress-1 is 0.025 (T1) and 0.006 (T2). Nearest neighbours: BFS-BiBFS,
  DFS-IDDFS and A*-greedy. Nearest-neighbour stability is 0.70 across settings and 0.96 under the program bootstrap.
  Persistent H1: no evidence of a loop on either task. Within-ban probes at the label-independent g16 position are near
  chance for every T1 condition and reach 0.69 balanced accuracy on T2 LOS(BF/SPFA) (p = 0.03). Probes at 'pre' are
  confounded by the label-dependent position (deviation D-pre-leak). The forced difference-in-means direction is aligned
  with the natural within-ban direction at 'pre' (cosine 0.6-0.95) and on T2 at g16 (0.3-0.99). It is not aligned at g16
  for the T1 BFS ban (-0.13 to -0.01).
- **Cost.** About 1 GPU-hour on one RTX 4090 and USD 0.42 of OpenRouter judge calls (857 calls).

## What was run (stage order)

1. Prompts frozen and committed (`prompts/frozen_prompts.json`, commitments line 0).
2. vLLM session 1: forced smoke, then the descriptive-variant decision, then baseline, single bans and T2 LOS, then
   the rest of the forced programs.
3. Labeller extension and validation.
4. Keep rule and scrubbed program sets.
5. HF stage 1a: baseline and denominators, plus the base, forced and own states.
6. Set selection: TOP, ARC, SCATTER, plus TOP5.
7. HF stage 1b: FRLP cells for the ban, mention and neutral twins, the nonce ban, LOS and tier 3.
8. Commit: forecasts and `analysis/landing.py`, sha256 hash-chained.
9. vLLM session 2: the multi-bans.
10. HF stage 2: states, plus the noun-B placebo.
11. Analysis and outputs.

`reproducibility.md` lists the exact commands.

## Layout

| Path | What it is |
|---|---|
| `method.py` | Orchestrator, one sub-command per stage (`uv run method.py <stage>`). |
| `common.py` | Frozen protocol: task texts, the 10 + 5 catalogue, display names, W1-W5 templates, thresholds, hash-chain helpers. |
| `mb/prompts.py` | S1 freeze: forced, baseline, ban, mention and neutral segments, neutral nouns, padding, multi-name rule. |
| `mb/gen.py` | PID-managed `vllm serve` session plus async client (token-id prompts, per-request seeds, staged 10 -> 100 -> full). |
| `mb/label.py` | Extended labelling (tests, small tier, tracer, runtime/AST rules, blind judge, combine), references, unit probes, canonical re-check, gold set. |
| `mb/stages.py` | Smoke decision, remaining forced runs, keep rule, program sets, session 2. |
| `mb/scrub.py` | Tokenize-driven name scrubber with verification. |
| `mb/score.py`, `mb/score_stages.py` | HF teacher-forced scoring (prefix-cached, fp32 head) with residual hooks; stages 1a, 1b and 2; self-checks; placebo. |
| `mb/sets.py` | Geodesic consensus matrix, Held-Karp seriation, TOP, ARC and SCATTER selection, stability and context sensitivity. |
| `mb/forecasts.py` | The committed forecasts (LADDER, PRIME_AND_VETO, PROXIMITY, FRLP_BAN, GENERIC, plus CORPUS). |
| `mb/aux_datasets.py` | Uses the other nine dependency datasets (corpus ladder, external T2 labels, CLRS canon, harness screen check). |
| `mb/outputs.py` | `data/samples.jsonl` and `method_out.json`. |
| `analysis/landing.py` | S10 behaviour and landing tests (sha256 committed before session 2). |
| `analysis/manifold.py` | S11 manifold, figures, within-ban probes, persistence. |
| `analysis/extra.py` | Shingle coverage check, FRLP sanity (T4), ESS distribution, commit-order audit. |
| `audit/rederive.py` | Independent re-derivation of the headline numbers plus placebos. |
| `labeller_ext/` | Extended tracer, runtime rules, AST rules, judge, combine; `gold_set_v2.jsonl` (+ `_round0`). |
| `tasks/` | Hidden tests (canonical and small tier), references (22 exp1 + IDA*, JPS4, bidirectional A*), sandbox and harness. |
| `canon/` | Read-only copy of the iteration-1 exp1 suite (sha256 in `results/provenance.json`). |
| `prompts/` | Frozen prompts and the segment token-length log. |
| `predictions/forecasts_*.json` | Committed forecasts per banned set. |
| `commitments.log` | sha256 hash chain: prompts, planned conditions, forecasts and the landing script. |
| `data/` | Raw generations (`raw_*.jsonl`), labelled rows, evaluation cache, program sets, denominators, teacher-forced scores, `samples.jsonl`. |
| `results/` | All analysis JSON (`frlp_cells.jsonl`, `landing.json`, `los.json`, `sets_and_geometry.json`, `manifold.json`, `persistence.json`, `catalogue_keep.json`, `labeller_*.json`, `checks.json`, `deviations.json`, ...). |
| `figures/` | `fig_manifold_*`, `fig_kstab_*`, `fig_landing`, `fig_los` (PNG + PDF). |
| `states/` | Teacher-forced residuals (about 0.95 GB). Kept on the run volume and NOT in the published repository. |
| `method_out.json`, `full_/mini_/preview_method_out.json` | Final output (exp_gen_sol_out schema, validated). |

## How to run

See `reproducibility.md`. Running `uv run method.py` with no stage rebuilds `method_out.json` (and `data/samples.jsonl`)
from the saved results in about a second. Short form of the full run:

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
uv run method.py freeze && uv run method.py recheck && uv run method.py refs
uv run method.py serve --session s1 && uv run method.py smoke && uv run method.py s1main   # ... see reproducibility.md
```

## Deviations

Every deviation is in `results/deviations.json` and in `method_out.json -> metadata.deviations`. The main ones:

- RTX 4090 instead of the planned A4500. vLLM ran with `max_num_seqs` 24, eager mode and no logprobs, because the
  container has no C compiler.
- A duplicated forced paraphrase was replaced.
- The keep rule failed, so the analysis catalogue was widened (D-catalogue). F4 gives 4-name sets, and the literal
  five-name TOP5 was added.
- The gold gate was missed and its one revision round applied.
- bf16 scoring-path noise of about 1 nat per program means T3(a) is not met (D-bf16-noise).
- Duplicate-program uids (D-dup-uid).
- The 'pre' position leaks the label into probes (D-pre-leak).
- The T2 FRLP sum is below 0.3 (D-t4-sum).
- The placebo ran after session 2.

## Restoring removed files

`.aii/manifest.yaml` marks only regenerable bulk for deletion:

- `.venv/` (about 15 GB):
  `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`. All 176 packages are
  pinned exactly, e.g. `vllm==0.11.0`, `torch==2.8.0`, `transformers==4.57.6`.
- `__pycache__/` directories (`./`, `mb/`, `analysis/`, `tasks/`) are recreated on import, or with
  `uv run python -m compileall -q .`.
- Model weights are not stored here; they live in the HF cache. To re-download:
  `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
- `states/` is KEPT on the run volume but excluded from the published repository (`upload_ignore_regexes`).
  To regenerate it, run `uv run method.py score1a` and `uv run method.py score2` (about 10 GPU-minutes).
