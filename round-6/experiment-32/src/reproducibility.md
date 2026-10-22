# Reproducing this artifact (iteration 6, experiment 32: "Reading the planned algorithm in words")

This file describes what was **actually run**, in order, on 2026-10-22 (UTC 04:50-07:45). Every path below is relative
to this artifact's folder.

## 1. Get the artifact

The workspace is published as one folder of a public GitHub repository.

```bash
git clone <the run's repository URL>
cd <repository>/<this artifact's folder>      # the folder that holds this file, method.py and README.md
```

The folder already contains:
- every input copied from earlier artifacts of this research direction (`inputs/`, hashes in `inputs/SHA256SUMS`);
- all prompts, raw samples, labels, explanations and judgements (`data/`);
- the result files (`results/`), the figures (`figures/`) and the pre-registration chain (`commitments.log`,
  `predictions/`).

Two things are not in the published folder, by design:
- `cache/*.npz` (layer-20 states, AR reconstructions, causal deltas). These are binary and 70-91 MB each. They stay
  on the run volume and are rebuilt by steps S4/S6 below. Their indexes (`cache/*_index.jsonl`) are published.
- `.venv/` and the `.git/` folders of the two `third_party/` clones. The venv is rebuilt by section 2 and the clones by section 3.

**User uploads:** none. The run's `user_uploads` folder was empty, and no private input was used.

## 2. System, Python and libraries

- **OS and tools.** Debian 12 (bookworm) container; any Ubuntu 22.04+ works. You need `git`, `curl` and
  `uv` 0.6.14.
- **Python.** CPython **3.12.14**. A `python3.12` binary must also be on `PATH`, because the bench labellers run every
  candidate program in a sandboxed `python3.12 -I -S` subprocess. `BENCH_SANDBOX_PYTHON` overrides that binary.
- **GPU.** One NVIDIA L4, 24 GB (23.7 GB usable), driver 595.91.07 (CUDA 13.2 driver API). torch 2.8.0 is the
  PyPI CUDA-12.8 wheel. Any ≥ 22 GB GPU works; 7B bf16 needs about 15.2 GB plus a KV cache of up to about 5 GB.
- **CPU and RAM.** 6 CPUs (cgroup quota) and 66 GB RAM (cgroup limit). Scripts cap themselves with `RLIMIT_AS` at
  60 GB.

```bash
uv venv .venv --python=3.12
uv pip install --python .venv/bin/python -r pyproject.toml   # 89 packages, all pinned (== versions)
```

`pyproject.toml` pins every package to the exact version installed in `.venv` (`uv pip freeze`; the same list is in
`env_freeze.txt`). The packages that matter are torch==2.8.0, transformers==4.57.6, accelerate==1.15.0,
safetensors==0.8.0, tokenizers==0.22.2, huggingface-hub==0.36.2, datasets==5.0.1, numpy==2.2.6, scipy==1.18.1,
pandas==3.0.6, scikit-learn==1.9.1, matplotlib==3.11.2, openai==3.35.1, loguru==0.7.3, pyyaml==6.0.3 and
rapidfuzz==3.14.6. The venv was created with uv, so it contains no `pip`; `uv pip freeze` replaces `pip freeze`.

## 3. Downloads, environment variables and the dependency

**Models.** Fetch them into the Hugging Face cache, at the exact revisions used:

```bash
hf download Qwen/Qwen2.5-7B-Instruct    --revision a09a35458c702b33eeacc393d103063234e8bc28   # 15.2 GB
hf download kitft/nla-qwen2.5-7b-L20-av --revision b88469162777ae6553bc14208eb0cb579336f8f4   # 15.3 GB (AV)
hf download kitft/nla-qwen2.5-7b-L20-ar --revision e2c9e57eac213d37a31612087f645ab6332c1bb6   # 10.9 GB (AR + value_head)
```

**Reference code.** It is read only for the recipe, never imported:

```bash
git clone https://github.com/kitft/nla-inference.git third_party/nla-inference                         # commit 38b802a33d1d
git clone https://github.com/kitft/natural_language_autoencoders.git third_party/natural_language_autoencoders  # commit 0577769b55ad
```

The sidecars (`nla_meta.yaml`, configs, chat templates) are copied into `third_party/hf_meta/`.

**Dataset dependency `art_j3Rm_lr2nzR6`** (`full_data_out.json`, 96 MB). Only `src/dep_usage.py` reads it, through
the single constant `cfg.DEP_DATASET_DIR`. That constant defaults to the sibling folder `../art_j3Rm_lr2nzR6`, which
is how the repository publishes it; the environment variable `ART_J3RM_DIR` points elsewhere. Its outputs are already
published: `data/reference_sources.json`, `data/novelty_pool.jsonl` and `results/dependency_usage.json`.

**Ultra-FineWeb.** `src/dep_usage.py` streams `openbmb/Ultra-FineWeb` (split `en`) and keeps the first 20 documents of
1,200-6,000 characters. They are saved and published as `data/ultrafineweb_docs.json`, so a re-run reuses them and
needs no streaming.

**Environment variables** (names only, never values):

| variable | required? | purpose |
|---|---|---|
| `OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY` | required | every judge call (S3 re-gate, S7, novelty audit, local control) |
| `HF_HOME` / `HF_HUB_CACHE` | optional | model cache location; the code resolves snapshots from `HF_HUB_CACHE` |
| `HF_TOKEN` | optional | model downloads; the models are not gated |
| `ART_J3RM_DIR` | optional | location of the dependency, see above |
| `BENCH_SANDBOX_PYTHON` | optional | the sandbox interpreter for the labellers |

## 4. What was run, in order

The GPU stages load one model at a time. Seeds:
- **CRN uniform streams:** `PCG64(sha256("task|template|slot"))`, shared by every arm.
- **AV sampling:** `torch.manual_seed(stable_seed("av", tag, first explanation id))`.
- **Random deltas and perturbations:** `stable_seed("rand_delta"|"eps", ...)`.
- **Bootstrap:** seed 20261022.
- **Judge item shuffle:** `stable_seed("judge_shuffle")`.

Judges run at temperature 0, but API outputs are not bit-reproducible. Their caches are published
(`data/judge_nla_cache.jsonl`, `data/judge_cache*.jsonl`), so re-runs reuse every cached answer.

| # | command | where | time |
|---|---|---|---|
| S0 | `.venv/bin/python src/tests_cpu.py` (51/51 references labelled correctly) | CPU | 1 min |
| S0 | `.venv/bin/python src/dep_usage.py` (all ten dependency datasets; reference documents) | CPU + network | 1 min |
| S0 | commit #0, run inline; identical to `.venv/bin/python src/commit0.py` | CPU | — |
| S1-S3 | `.venv/bin/python src/gen.py twin engine_check forced_seed ban` | GPU | 30 min |
| | beside it, `.venv/bin/python src/labels.py --raw data/samples_raw.jsonl --out data/labels.jsonl --follow-until data/flag_ban.done --name label_behaviour` | CPU | |
| | after the twin labels, before the ban stage: `.venv/bin/python src/behaviour.py defaults` (commit #1) | CPU | |
| S3 | `.venv/bin/python src/behaviour.py report` then `.venv/bin/python src/behaviour.py regate` | CPU + API | 4 min |
| S4 | `.venv/bin/python src/states.py` | GPU | 1.5 min |
| S7a | `.venv/bin/python src/judges.py calibrate` (rubric v1, then v2; see deviations D-rubric-v2 and D-judge-swap) | API | 2 min |
| | `.venv/bin/python src/commit2.py` (commit #2) | CPU | — |
| S5a | `.venv/bin/python src/nla_av.py gate` (smoke tests and reference set, both conventions) | GPU | 2 min |
| S5-S8 | `./run_chain.sh` | GPU + API | 25 min + 15 min |

`./run_chain.sh` runs these steps in turn:
1. `nla_ar.py gate`, which picks the layer convention, hidden_states[21];
2. `nla_av.py production`, 6,180 explanations;
3. `nla_ar.py production`, which writes the gate, the edits, the deltas and commit #3;
4. `judges.py run`, run in the background;
5. `labels.py --raw data/samples_causal_raw.jsonl --out data/labels_causal.jsonl --follow-until data/flag_causal.done`;
6. `causal_gen.py --deadline-min 70`.

The rest was run by hand after the chain:

| # | command | where | time |
|---|---|---|---|
| S7 | `.venv/bin/python src/judges.py run --conc 8`, re-run from cache until the final pass (see deviations D-judge-projection, D-judge-json, D-judge-j3-missing) | API | 10 min |
| S9 | `.venv/bin/python analysis/causal.py`, `analysis/readout.py`, `analysis/geometry.py` | CPU | 1 min |
| EXPL | `.venv/bin/python src/causal_extra.py && .venv/bin/python src/labels.py --raw data/samples_causal_extra_raw.jsonl --out data/labels_causal_extra.jsonl` | GPU | 10 min |
| EXPL | `.venv/bin/python src/causal_extra2.py && .venv/bin/python src/labels.py --raw data/samples_causal_extra2_raw.jsonl --out data/labels_causal_extra2.jsonl` | GPU | 17 min |
| EXPL | `.venv/bin/python src/local_control.py` | GPU + API | 8 min |
| S9 | `.venv/bin/python analysis/causal_extra.py`, `src/novelty.py`, `src/figures.py` | CPU + API | 3 min |
| audit | `python3 audit/rederive.py` (stdlib only), then `.venv/bin/python audit/rederive_headlines.py` | CPU | 1 min |
| out | `.venv/bin/python src/outputs.py`, then the aii-json format script (`--input method_out.json`) | CPU | 1 min |

`method.py` chains the pre-registered stages S0-S9 (`.venv/bin/python method.py [--from STAGE]`). The exploratory
commands are listed separately in `README.md`. Total wall-clock was about 2.9 h, of which about 2 h was GPU.
OpenRouter spend was about USD 2.0.

**Determinism notes.**
- Generation is exact-CRN in bf16 on the same GPU and kernels, with CRN determinism 8/8.
- The batch composition (left padding) changes about 1 in 16 labels (batch invariance 15/16). A different GPU or
  kernel version can change individual tokens but not the aggregate conclusions.
- The prefill states are bit-identical for identical prefixes.

## 5. What you should get

The README's "Results in detail" section reproduces every number below. There is no paper yet; the README is the
write-up.

| quantity | file | value |
|---|---|---|
| defaults (modal correct twin share) | `results/behaviour.json` | T1 BFS 1.00, T2 Dijkstra 0.88, T05 hash map 0.98, T06 hash set 0.71, T10 DFS 0.62, T04 naive 1.00, R6 binary search 1.00, T03 none (quickselect 0.40) |
| bans | `results/behaviour.json` | only T05 has a substitute (brute force 32/46 correct); T10 DFS rises 29 → 43 (15 union-find → DFS flips); W4 70/70 attempts use the default |
| layer convention | `results/layer_convention.json` | FVE_ref hs20 0.580 vs hs21 0.695 → hs21; pipeline check vs 0.752 passes |
| task gate | `results/gate.json` | FVE_ref 0.512, PARTIAL (READ 0.65, SPEC 0.50, g2 0.28), mean cosine 0.826 |
| N1, N2, N3, N8b | `results/readout.json` | 0/16, 0/112, 0.00 on all 7 tasks, 0/96 |
| N6 | `results/readout.json` | NLA 0.066 vs outside reader 0.253, exact McNemar 20:88, p = 2.3e-11 |
| committed causal arm | `results/causal.json` | 0 of 4 tasks pass |
| exploratory: GEN-site edit | `results/causal_exploratory_followup.json` | T06 Floyd 0.76 vs C0 0.28 (25:1 over N=50; replication 13:0); T05 brute force 10:0 at ×8, 23:0 at ×16; T10 DIM ×16 15:1 |
| exploratory: local control | `results/local_control.json` | mention at the name token 0.80 (forced) / 0.89 (ban); at the end of the prompt 8/1080 and 3/420 |
| novelty | `results/novelty.json` | 10 correct "other" programs: 8 labeller misses, 2 degenerate, 0 novel |
| re-derivations | `results/rederive.json`, `results/rederive_headlines.json` | every number above recomputed independently; placebos fail |
| outputs | `method_out.json` (= `full_method_out.json`), `mini_method_out.json`, `preview_method_out.json` | 5 datasets, 8,480 examples; exp_gen_sol_out schema validated |
