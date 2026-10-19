# Reproducing "What does a ban switch the model to?"

This file describes what was **actually run** to produce the numbers in `method_out.json`, in order, and two ways to
reproduce them:

- **Path A** re-runs every analysis from the published raw generations. It needs only a CPU, no GPU and no API key,
  and gives byte-identical numbers.
- **Path B** regenerates everything from scratch. It needs a GPU and an OpenRouter key, and gives results that
  agree at the level of distributions; exact tokens are not reproducible (see §6).

All paths below are relative to this folder.

## 1. Get the artifact

This workspace is published as one folder of the run's public GitHub repository:

```bash
git clone <repository-url>
cd <repository>/<this-artifact-folder>   # the folder that contains this file, method.py and README.md
```

Nothing in this artifact reads another artifact's outputs; it builds its own task material. No user-uploaded input
is used.

## 2. System, Python and libraries (what was actually used)

| Item | Used for the published results |
|---|---|
| OS | Debian 12 (bookworm) container, kernel 6.8. Ubuntu 22.04/24.04 works the same with the steps below. |
| GPU | 1 × NVIDIA GeForce RTX 5090, 32 GB VRAM (Blackwell, sm_120); driver 595.91.07 (CUDA 13.2 capable) |
| CPU / RAM | 14 vCPUs (AMD Ryzen 9 9950X), 55 GB container RAM limit |
| Python | CPython 3.12.14, used both for the venv and for the candidate sandbox (`python3.12 -I -S`) |
| Package manager | uv 0.6.14 |
| Key libraries | vllm 0.11.0, torch 2.8.0 (cu128 wheel), transformers 4.57.6, tokenizers 0.22.2, xformers 0.0.32.post1, triton 3.4.0, numpy 2.2.6, scipy 1.18.1, pandas 3.0.6, openai 3.35.1, aiohttp 3.14.5, loguru 0.7.3, matplotlib 3.11.2 |
| C compiler | **none** in the container, so Triton/Inductor could not compile and vLLM ran with `--enforce-eager` |

All 167 installed packages are pinned with `==` in `pyproject.toml`, from `uv pip freeze`; the uv venv has no `pip`
binary. `uv.lock` is the matching lock, restricted to linux x86_64.

On Ubuntu:

```bash
# NVIDIA driver with CUDA 12.8 support (>= 570 for Blackwell cards); then:
sudo apt-get update && sudo apt-get install -y git curl ca-certificates
curl -LsSf https://astral.sh/uv/install.sh | sh          # uv (0.6.14 was used)
uv python install 3.12                                     # or: apt install python3.12 (deadsnakes PPA)
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml   # exact pins; ~10 GB of wheels (torch + CUDA libs)
```

`restore.sh` runs the venv steps above.

The hidden tests and the runtime tracer run each candidate program in a stdlib-only CPython 3.12 with `-I -S`.
`tasks/harness.py` uses `$SANDBOX_PYTHON` if it is set, otherwise `/usr/local/bin/python3.12` or
`/usr/bin/python3.12` if one exists, otherwise `python3.12` on PATH, otherwise the venv interpreter. With `-I -S`
no site-packages are visible, so candidates can import only the standard library.

## 3. Downloads, environment variables, keys (names only)

- **Model.** `Qwen/Qwen3-8B` from the Hugging Face Hub, snapshot revision
  `b968826d9c46dd6066d109eabc6255188de91218`. `vllm serve` downloads it on first start; to fetch it ahead of time:
  `huggingface-cli download Qwen/Qwen3-8B --revision b968826d9c46dd6066d109eabc6255188de91218`.
- **Environment variables:**
  - `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL` are needed only for Path B and the judge. Use an
    OpenRouter-compatible base URL; for public OpenRouter it is `https://openrouter.ai/api/v1`.
  - `HF_HOME` (optional cache location) and `HF_TOKEN` (optional).
  - `SANDBOX_PYTHON` (optional, see §2).
  - `SCREEN_MODEL` (optional; default `Qwen/Qwen3-8B`) and `SCREEN_VLLM_PORT` (optional; default `8011`).
- **OpenRouter models called (total spend USD 0.27):**
  - `openai/gpt-4.1-mini`: production judge, gold judge A, and the post-hoc reference map.
  - `google/gemini-2.5-flash`: gold judge B, with a reasoning budget of 0.
  - `deepseek/deepseek-chat-v3.1`: gold tie-breaker.
  - `meta-llama/llama-3.1-8b-instruct`: external elicitation.

## 4. Path A: exact re-analysis from the published raw generations (CPU only, about 2 minutes)

The published `data/raw_*.jsonl` hold every model output. Program evaluations are cached by code sha256 in
`data/program_eval_cache.jsonl`, and every judge response is cached in `labeller/judge_cache.jsonl`. Re-running the
CPU stages therefore issues no GPU or API call and reproduces every number exactly:

```bash
uv run method.py label --src data/raw_preban.jsonl
uv run method.py label --src data/raw_bans.jsonl
uv run method.py label --src data/raw_succession.jsonl
uv run method.py score
uv run method.py outputs
uv run audit/rederive.py          # independent re-derivation + placebo checks -> results/independent_rederivation.json
```

To re-execute every candidate program instead of using the evaluation cache, delete
`data/program_eval_cache.jsonl` first. That takes about 1 minute on 12 threads, and labels can differ only if a
program sits exactly at its time limit (limits are at least 1 s).

## 5. Path B: full regeneration (GPU ≥ 20 GB + OpenRouter key), exactly as run

Start from a clean slate, because every stage resumes from what is on disk and `prompts` refuses to overwrite a
frozen file:

```bash
mkdir -p ../previous_run && mv data predictions results elicitation commitments.log prompts/conditions.json \
   labeller/judge_cache.jsonl labeller/gold_set.jsonl labeller/gate_report*.json ../previous_run/ 2>/dev/null
```

Then run in this order. The times in brackets are from the published run on the RTX 5090.

```bash
# 1  freeze prompts (sha256 + commitments.log)                                          [<1 s]
uv run method.py prompts
# 2  one long-lived vLLM server for every GPU stage                                      [~5 min to ready]
.venv/bin/vllm serve Qwen/Qwen3-8B --dtype bfloat16 --gpu-memory-utilization 0.90 --max-model-len 2048 \
  --max-num-seqs 128 --seed 1234 --generation-config vllm --enable-prefix-caching --enforce-eager \
  --port 8011 --host 127.0.0.1 --served-model-name qwen3-screen --enable-log-requests --max-log-len 120 \
  > logs/vllm_server.log 2>&1 & echo $! > logs/vllm_server.pid
# 3  smoke test: chat-template tail, no <think> text, code extraction, ranking parse       [~1.5 min]
uv run method.py smoke
# 4  pre-ban generation, staged 10 -> 100 -> all requests (1,410 programs + 440 short queries) [~4 min]
uv run method.py preban --limit 10 && uv run method.py preban --limit 100 && uv run method.py preban
# 5  task suite: hidden tests, per-case limits, reference/mutation/robustness acceptance  [~10 s]
uv run method.py tasks
# 6  mechanical labels only (runtime tracer + AST), used while developing the rules         [~30 s]
uv run method.py label --src data/raw_preban.jsonl --no-judge
# 7  labeller gate: gold set adjudicated by 2 judge families + tie-breaker                [~1.5 min]
uv run method.py gate
# 8  full pre-ban labelling, blind judge on every runtime/AST disagreement                 [~15 s]
uv run method.py label --src data/raw_preban.jsonl
# 9  elicitation parsing (+ retries on GPU), external replication, association objects    [~2 min]
uv run method.py elicit && uv run method.py external && uv run method.py assoc
# 10 freeze + hash-chain the 11 single-ban predictions BEFORE any ban prompt               [<1 s]
uv run method.py freeze
# 11 ban arms (N=100) + mention twins (N=50) for all 11 modes, then labelling             [~4 min]
uv run method.py bans
# 12 greedy cumulative-ban succession; each step is frozen before it is generated          [~2 min]
uv run method.py succession
# 13 scoring and outputs                                                                  [~15 s]
uv run method.py score && uv run method.py outputs
# 14 optional, post hoc (after the freeze): gpt-4.1-mini textbook-consensus map            [~1.5 min]
uv run method.py reference_map && uv run method.py outputs
# 15 stop the server
kill "$(cat logs/vllm_server.pid)"
```

Two things happened in the published run that differ from simply running the commands above:

1. **Gate revisions.** The runtime rules were developed between steps 6 and 7 on the 22 references and the
   development half of the gold set. After the first gate run (kept as `labeller/gate_report_round0.json`), one
   revision round added stdlib-name pre-injection to the tracer, and the gate was re-run with identical metrics.
   The published code is the final version, so a fresh run executes the final rules directly.
2. **Seed check.** A reproducibility check re-sent 6 requests to the same server
   (`data/repro_check.jsonl`, `results/seed_reproducibility_check.json`).

**Seeds and configs:**

- Server: `--seed 1234`.
- Per request: `int(sha256('task|condition|paraphrase|stage')[:8], 16)`, with child seeds seed + index for n > 1.
  Seeds are stored in every row.
- Sampling: T = 1.0 (T = 1.3 for the baseline_T13 arm), top_p 1.0, top_k left at the vLLM 0.11 default 0
  (disabled), min_p 0, neutral penalties, max_tokens 1024 (64 / 32 for rankings / free text), thinking disabled
  through the chat template.
- Bootstrap and permutation seeds are fixed in `analysis/*.py`.
- Thresholds are in `common.py` (`THRESHOLDS`).

## 6. What you should get

| Quantity | Value | Where |
|---|---|---|
| Baseline modes (N=300 per task; also T=1.3 and no neutral segment) | T1 100% BFS; T2 100% Dijkstra; Hill_cc 1.00 | `elicitation/baseline_objects.json`, `method_out.json` → `metadata.baseline` |
| Modal single bans | T1 ban:BFS compliance 0.90, all 38 compliant correct samples DFS; T2 ban:Dijkstra compliance 0.91, all 86 Bellman-Ford/SPFA | `results/event_table.json`, `figures/landing_table_steps.png` |
| Borda association nominations | T1 Dijkstra (clarity 0.20, DFS ranked last); T2 Bellman-Ford/SPFA | `elicitation/assoc_objects.json`, `predictions/*_single_bans.json` |
| Log scores (assoc / freq) | T1 −2.817 / −1.630; T2 −0.755 / −1.406; mean paired difference −0.268; association wins 1 of 2 | `results/contest.json`, `figures/informative_events_pred_vs_realised.png`, `figures/paired_log_score.png` |
| Secondary predictors (top-1 hits over the 2 events) | free text 2/2, listall 2/2, Llama map 1.5/2, T=1.3 frequency 0.45 | `results/contest.json` → `strata.all_informative.summary` |
| Succession step 2 (double bans) | compliance T1 0.06, T2 0.00; recurrent programs not naming the banned algorithm 41/94 and 58/100 | `results/event_table.json`, `results/disguised_recurrence.json` |
| Mention effects (pp vs baseline) | DFS +100, IDDFS +72, A*/GBFS +56, Bellman-Ford/SPFA +100, Floyd-Warshall +86; Dijkstra (T1), Dial, bidirectional Dijkstra 0 | `results/mention_effects.json` |
| Labeller gate (evaluation gold, n=92) | kappa runtime-vs-AST 0.753; runtime vs adjudicated 0.843; combined vs adjudicated 0.966; `gate_passed=false` | `results/labeller_gate.json` |
| Pre-commitment audit | hash chain valid; all 13 events committed before their first generation | `results/commitment_audit.json` |
| Independent re-derivation | 36/36 headline numbers match; placebo checks fail as expected | `results/independent_rederivation.json` |

There is no paper in this artifact. A write-up should cite these files and fields, with the honest summary in
`method_out.json` → `metadata.honest_summary`.

Determinism:

- **Path A** reproduces every number above exactly.
- **Path B** reproduces the per-request seeds but not the exact tokens, because bf16 numerics depend on batch
  composition. Re-sending 6 requests reproduced 39 of 64 texts. Re-generated runs should therefore match at the
  distribution level (e.g. baselines fully collapsed, modal bans landing on DFS and Bellman-Ford/SPFA), not
  token-for-token.
