## Positioning (from the dependency audit art_OUuQUYQn5voE, search dated 2026-10-22)

- Permitted wording for the DAS part: "the first interchange/DAS localization of *which algorithm* a code LLM will write
  that is validated by scoring the generated programs, with Sutter-style map-class, random-initialization and
  shuffled-label controls". Forbidden: "first causal localization of a plan", "new method", "first DAS-based steering"
  (CDAS, ICLR 2026, already validates DAS steering by generation, on refusal and a CoT backdoor).
- For temperature, "temperature is not the creativity knob" is not a new claim. What is new here is a pre-registered,
  quantitative account: the BFS share at every temperature is predicted from teacher-forced fork logits divided by T,
  before any temperature sample.
- Why Gemma when circuit-tracer ships Qwen-3 transcoders: this artifact continues iteration 6's Gemma fork (same
  model, prompts, c*, fork-token table and labeller). Gemma Scope 2 (22 Dec 2025) ships per-layer transcoders for
  gemma-3-4b-it, and a 4B model fits the 16 GB GPU used here.

## Layout

| Path | What |
|---|---|
| `method.py` | entry point, one function per stage (`--stage s0, engine, label, g3a, g3b, yv, g2smoke, g2, g2r, g2d, g2pairs, g1p, g1v, g1gen, novelty, analysis, figures, outputs`) |
| `src/cfg.py` | constants, paths, CRN keys, design parameters (B/D token ids, templates, doses, temperatures) |
| `src/engine.py`, `src/push.py`, `src/prompts.py`, `src/label_worker.py`, `src/regate_rules.py`, `src/fork.py`, `src/commit.py`, `src/novelty.py` | iteration 6's engine, prompt builders, labellers, partial-code labeller, hash chain and novelty audit (vendored; `engine.decode` gained a per-row top-k sampler) |
| `src/gen7.py` | generation runner: fixed-shape CRN batches, per-row temperature/top-k, module-level edits (resid, head z, MLP out) applied in the prefill, logit-only mode (G2-L), multi-prompt path (U6 a) |
| `src/fork7.py` | c*, B/D classes, fork margin m, the 120 twin variants, forced prompts with equal-length display names, position classes |
| `src/g1.py` | G1-P: AtP screen, exact noising/denoising patching, edge path patching, matched random nulls, real-model validation (ABLATE/STEER, sign-flip + Holm, joint sets), generation arms |
| `src/g2.py` | G2: single-position KV-cache forward, DAS (nested ranks, seeds), RAND/SHUF/DiM/natural-variance controls, RINIT, dose sweep + G2-L, per-pair export; also the U3 test and the DAS toy |
| `src/g3.py` | G3: U6 diagnosis, G3-cal table, committed predictions (COMMIT #1), temperature sweep and its analysis |
| `src/ct_graph.py`, `src/prep_ct.py` | G1-T: circuit-tracer attribution graphs (run in `.venv_ct`) and their input builder |
| `src/analysis7.py` | analyses, decision rules, figures F1-F7, `method_out.json` builder |
| `audit/verify_chain.py`, `audit/rederive.py` | standard-library audits: the hash chain and commit-before-sample ordering; re-derivation of headline counts/tests from raw rows, with placebos |
| `inputs/iter6_gemma/` | read-only copy of the iteration-6 Gemma artifact's code, results, raw T1 rows and its staged inputs (exp8 suite = T1 spec, hidden tests, references, runtime+AST labeller; dependency extracts), with `MANIFEST.sha256` |
| `predictions/`, `commitments.log` | commits #0 (design, rules), #1 (G3 predictions), #2b (G1 node list and nulls; #2 superseded, see D07), #3 (L*, k*, subspaces, doses, DiM betas) |
| `data/` | raw generations (`raw_*.jsonl`) and labels (`labels.jsonl`) of every cell; judge cache |
| `results/` | every analysis result (JSON); `deviations.json` lists all deviations |
| `figures/` | F1-F7 (PNG + PDF); geometry in actual activation coordinates |
| `cache/states/`, `cache/das_subspaces/` | fork states (all blocks) of the 120 variants, 40 sources and 5 twins; trained subspaces (kept on the run's volume) |
| `method_out.json`, `full_/mini_/preview_method_out.json` | exp_gen_sol_out output (datasets below; metadata = every results file) |
| `logs/` | stage logs, batch timings, OpenRouter spend |

## How to run

```bash
uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
.venv/bin/python method.py --stage label --follow &          # CPU label worker (frozen T1 labeller), follows data/raw_*.jsonl
for st in s0 engine yv g3a g3b g2 g2r g2d g2pairs g1p g1v g1gen; do .venv/bin/python method.py --stage $st; done
# G1-T attempt (needs a C compiler for Triton; scratch/bin/cc wraps the ziglang wheel installed in .venv_ct)
.venv/bin/python src/prep_ct.py scratch/ct_input.json && CC=$(pwd)/scratch/bin/cc timeout 720 .venv_ct/bin/python src/ct_graph.py scratch/ct_input.json results/g1t_graphs.json
for st in novelty analysis figures outputs; do .venv/bin/python method.py --stage $st; done
python3 audit/verify_chain.py && python3 audit/rederive.py
```

Hardware used: one NVIDIA RTX 2000 Ada (16 GB), 6 CPUs, 28 GB RAM. GPU time is about 2.5 hours in all. The model
(`google/gemma-3-4b-it` at revision `093f9f388b31de276ce2de164bdc2081324b9767`) and the transcoders were read from a
shared Hugging Face cache outside this folder.

## Restoring removed files

`.aii/manifest.yaml` marks these for deletion after the round; all are regenerable:

- `.venv/`: `uv venv .venv --python=3.12 && uv pip install --python .venv/bin/python -r pyproject.toml`
- `.venv_ct/`: `uv venv .venv_ct --python=3.12 && uv pip install --python .venv_ct/bin/python "circuit-tracer @ git+https://github.com/safety-research/circuit-tracer@255d989e93be1299d53d67b59e9fd76a0e274b14"`
- `src/__pycache__/`: created automatically by any Python run.
- Model weights and transcoders are not stored here. Download them with
  `huggingface-cli download google/gemma-3-4b-it --revision 093f9f388b31de276ce2de164bdc2081324b9767` and
  `huggingface-cli download mwhanna/gemma-scope-2-4b-it --revision 61cb16ec74f348f4a8643fe3a0157be9dc8a851d --include "transcoder_all/width_16k_l0_big_affine/*.safetensors" "transcoder_all/width_16k_l0_big_affine/config.yaml"`.
  The code downloads them on first use.

`cache/states/` (fork states, 14-42 MB per file) and `cache/das_subspaces/` (trained subspaces, 1.8 MB) are
**kept** on the run's volume at these paths. Suggested upload-ignore patterns for the published repository are
`(^|/)cache/states/`, `(^|/)scratch/bin/` and `(^|/)paths\.local\.json$`, so the binary caches stay only on the volume.
To rebuild them, run `method.py --stage yv` (about 2 GPU-minutes), then `--stage g2` (about 47 GPU-minutes).
