## What was done

1. **Setup and provenance (A).** The frozen bench (exp11) and the exp10, exp8 and exp7 inputs were copied read-only into `inputs/`.
   - Every bench file was checked against `bench/commitment.json`, and exp10's canon against its `SHA256SUMS`.
   - The four model shards were checked against exp10's record.
   - `X0` was frozen first: the modal attempted label of exp11's FP8 Llama pilot.
2. **Label-independent generations (B).** All use vLLM 0.11 with token-id prompts and every SamplingParams field explicit: T = 1.0, top-p = 1.0, top-k off, min-p 0, `generation_config='vllm'`.
   - B1: 600 neutral-twin baseline samples.
   - B2: 1,000 association answers.
   - B3: forced programs, 1,000 in round 1 and 540 in round 2.
   - B4: 600 veto pass-1 samples.
   - B5: 600 nonce bans and 600 novelty prompts.
   - Neutral twins are token-length matched under Llama's tokenizer with `' .'` padding. Their ids are identical from `Task:` to the end (500/500 pairs pass).
3. **Labels and freezes (C).** Each program is labelled with the bench runtime tracer (primary) and the AST rules, with a blind judge (gemini-2.5-flash-lite, name-scrubbed code) on disagreements only.
   - **Decision set:** the FP8 pilot plus B1, after a Fisher-Freeman-Halton Monte Carlo homogeneity test.
   - **Default D:** the modal *correct* label when there are ≥ 10 correct programs and a lead ≥ 2; otherwise the modal attempted label.
   - **Present-minor events:** ≥ 10% of correct programs, ≥ 3 correct, and a task with ≥ 10 correct programs.
   - **ASSOCIATE targets:** taken from Llama's own association answers.
4. **Signature n-grams and exact vetoes (D).**
   - **N-gram rule:** n ≤ 6, present in ≥ 80% of the target's programs and of its generated ids. Among those, the one that minimises the worst-case collateral share in other algorithms' forced programs.
   - **One-shot and persistent vetoes:** done by truncate-and-redraw. The redraw uses `logit_bias = -100`, then the run continues, unmasked for one-shot and with a request-level `AdapterLogitsProcessor` mask for persistent, which also sees the prompt tail. The two arms share pass-1 and the redraw, and use the same continuation seed.
   - **Iterated rounds:** run while the default re-emerges in ≥ 20% of attempts, up to 3 rounds.
5. **Matched-norm random directions (E).**
   - HF prompt-only forward passes give the ban's own displacement norm n_{l,i} (ban vs twin, fp32) at the spec positions of layers 11–21.
   - Three seeded unit directions per layer are added at those norms during prefill only, in vLLM through forward hooks: 1,800 samples.
6. **Forecasts and commitment (F).**
   - SUBTRACT, LADDER, ASSOCIATE and PROXIMITY. ASSOCIATE and PROXIMITY use the mass-transfer form; point-mass forms are kept as sensitivities.
   - PROXIMITY uses Zhang-Shasha distance on identifier-normalised ASTs, with the bench token Levenshtein as a sensitivity.
   - Smoothing is 0.93 f + 0.05 U(S) + 0.02 δ(other).
   - A grep audit shows 0 ban prompts were rendered before the commit. `predictions/` was then made read-only.
7. **Bans (G).** 12 modal bans plus 6 present-minor bans, each W1–W5 × 20.
8. **Path-task screen (B6/D4/H6, descriptive).** On exp10's two path tasks, 300 new generations were run (vetofree pass-1, nonce, novelty), followed by one-shot, persistent and iterated vetoes of BFS (T1) and Dijkstra (T2). The resulting forecasts are scored against exp10's existing ban landings and never pooled with the bench.
9. **Analysis (H).** The frozen C1 rule, sensitivities, C2b-descriptive, the present-minor gain, the knob view, figures, and an independent re-derivation with a placebo.

## Layout

| path | what it is |
|---|---|
| `method.py` | CLI orchestrator, one sub-command per stage: `setup gen1 label freeze assoc hf push veto proximity commit ban analyse screen`. |
| `src/ws.py` | Paths, frozen constants, seeds (`sha256(task\|cond\|tpl\|sample)`), and jsonl helpers. |
| `src/prompts_llama.py` | Llama-3.1 renderer (date_string 26 Jul 2024, BOS and tail asserts). Builds ban, neutral-twin, nonce, novelty, forced, association and copy prompts. |
| `src/engine_vllm.py` | vLLM engine, explicit SamplingParams, `VetoAdapter` (persistent n-gram mask) and `PushHooks` (prefill-only random-direction hooks). |
| `src/engine_hf.py` | HF ban-displacement norms, seeded directions (sha256 recorded), and the T4 hook tests. |
| `src/jobs.py` | Request builders per phase and the staged 10 → 100 → rest, resumable runner with timings. |
| `src/label.py` | Extraction rule, bench labellers, judge on disagreements, association mapping, and the Llama label audit. |
| `src/freeze.py` | Decision set, homogeneity test, D, present-minor events, and ASSOCIATE targets. |
| `src/ngrams.py`, `src/veto.py`, `src/veto_job.py` | Signature n-grams; exact truncate-and-redraw; iterated veto rounds. |
| `src/proximity.py` | Zhang-Shasha on identifier-normalised ASTs and the canon token Levenshtein. |
| `src/forecasts.py`, `src/scoring.py` | Forecast families and the frozen C1 scoring rule (both copied into `predictions/` and hash-chained). |
| `src/analysis.py`, `src/outputs.py`, `src/figures.py` | Step H analysis, `method_out.json`, and figures. |
| `src/screen.py`, `screen10/` | Path-task screen: exp10's config (paths patched) and a writable copy of exp10's canon labeller. |
| `data/screen_raw.jsonl`, `data/screen_labels.jsonl`, `data/screen_veto_summary.json`, `results/screen.json` | Screen generations, labels, veto rounds, and scores. |
| `audit/rederive.py` | Independent re-derivation from the raw files, a family-permutation placebo, and the hash-chain check. |
| `audit/rederive_tests.py` | Separate re-derivation of the statistical headlines with placebos. It covers the exact-enumeration Wilcoxon, Holm, the binomial top-1 tests and D per task, and imports nothing from src/ or scipy. |
| `tests/` | T1 prompts, T3 vetoes (synthetic part), T7 scoring. |
| `scripts/` | `labeller_recheck.py` (A3/T0), `run_label_audit.py` (C3), `fix_veto_decoding.py`, `write_deviations.py`, `make_readme.py`, and the README text fragments. |
| `inputs/` | Read-only copies of the inputs, plus `inputs/provenance.json` with sha256 and size per file. |
| `data/raw_gen.jsonl` | Every generation: prompt sha, seed, output ids, text, finish reason, and veto metadata. |
| `data/labels_raw.jsonl`, `data/labels.jsonl` | Per-program labeller outputs and combined labels. |
| `data/association.jsonl`, `data/veto_summary.json` | Mapped association answers; per-event veto rounds, n-grams and surfaces. |
| `data/samples.jsonl` | Shared per-sample schema over all labelled programs. |
| `predictions/` | x0, events, association targets, proximity, n-grams, random directions, forecasts, frozen code, and the pre-commit grep audit. |
| `commitments.log` | sha256 hash chain of every committed prediction file. |
| `results/` | Analysis, `c1_events.jsonl`, tests, timings, model record, norms, hook stats, deviations, and the label audit. |
| `figures/` | fig1 ban landings, fig2 log-score forest, fig3 baseline vs pilot. Each has a PDF, a PNG and its JSON spec. |
| `method_out.json` (+ `full_`/`mini_`/`preview_`) | `exp_gen_sol_out` output: datasets `llama_bench_events`, `llama_ban_samples` and `llama_screen_events`. |

Kept artifacts stay on the run's volume at the paths above. Nothing here is a model checkpoint. The Llama weights are not in this folder: they are read from the run's shared Hugging Face cache at revision `0e9e39f249a16976918f6564b8830bc894c89659`, with shard sha256s in `results/model_record.json`.

## How to run

```bash
./restore.sh                         # venv (vLLM 0.11.0, torch 2.8.0, transformers 4.57.6, zss)
.venv/bin/python method.py setup     # provenance, sha256 checks, X0 freeze
.venv/bin/python method.py gen1      # B1-B5 (vLLM)
.venv/bin/python method.py label     # labels (run after every generation stage)
.venv/bin/python method.py freeze    # D, present-minor events
.venv/bin/python method.py assoc     # association map + forced summary
.venv/bin/python method.py hf        # ban norms + hook tests (HF)
.venv/bin/python method.py push      # forced round 2 + random-direction pushes (vLLM, hooks)
.venv/bin/python method.py label --phases E3,B3r2
.venv/bin/python method.py veto      # n-grams + iterated vetoes (vLLM)
.venv/bin/python method.py proximity
.venv/bin/python method.py commit    # forecasts, hash chain, grep audit
.venv/bin/python method.py ban       # bans (vLLM), then: method.py label --phases G1,G2
.venv/bin/python method.py analyse   # C1 + everything descriptive -> method_out.json
.venv/bin/python audit/rederive.py
python3 -I audit/rederive_tests.py   # stdlib only
.venv/bin/python method.py screen    # optional path-task screen (descriptive)
```

A CPU-only re-analysis from the published raw files needs only `analyse` and `audit/rederive.py`. Every generation stage resumes, because it skips row ids that already exist.

## Restoring removed files

`.aii/manifest.yaml` marks only regenerable bulk for deletion.

- `.venv/`: `./restore.sh`, i.e. `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`.
- `__pycache__/`: `.venv/bin/python -m compileall -q method.py`
- `src/__pycache__/`: `.venv/bin/python -m compileall -q src`
- `tests/__pycache__/`: `.venv/bin/python -m compileall -q tests`
- `screen10/__pycache__/`: `.venv/bin/python -m compileall -q screen10`
- `screen10/canon/gen/__pycache__/`: `.venv/bin/python -m compileall -q screen10/canon/gen`
- `screen10/canon/labeller/__pycache__/`: `.venv/bin/python -m compileall -q screen10/canon/labeller`
- `screen10/canon/tasks/__pycache__/`: `.venv/bin/python -m compileall -q screen10/canon/tasks`
- The model weights are not stored here: `huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --revision 0e9e39f249a16976918f6564b8830bc894c89659`.

All the `__pycache__/` directories are also recreated automatically on import.

Everything else (`data/`, `results/`, `predictions/`, `inputs/`, `screen10/canon/`, `figures/`, the code and the JSON outputs) is text or small and is always kept.
