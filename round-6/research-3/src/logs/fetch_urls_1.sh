PY=${AII_SKILLS_DIR}/.ability_client_venv/bin/python
cd "$(dirname "$0")/.."
while read key url; do
  $PY -I tools/fetch_texts.py --url "$key" "$url" 2>&1 | grep -v -e onnxruntime -e FutureWarning -e warnings.warn
done <<'LIST'
nla https://transformer-circuits.pub/2026/nla/index.html
nla_readme_raw https://raw.githubusercontent.com/kitft/natural_language_autoencoders/main/README.md
nla_github https://github.com/kitft/natural_language_autoencoders
hf_nla_qwen25_7b_L20_av https://huggingface.co/kitft/nla-qwen2.5-7b-L20-av
hf_nla_qwen25_7b_L20_av_meta https://huggingface.co/kitft/nla-qwen2.5-7b-L20-av/raw/main/nla_meta.yaml
hf_gemma_scope_2 https://huggingface.co/google/gemma-scope-2
hf_gemma_scope_2_4b_it https://huggingface.co/google/gemma-scope-2-4b-it
circuit_tracer_readme_raw https://raw.githubusercontent.com/safety-research/circuit-tracer/main/README.md
circuit_tracer_github https://github.com/safety-research/circuit-tracer
vllm_fp8 https://docs.vllm.ai/en/latest/features/quantization/fp8.html
arxiv_abs_2506.09501v1 https://arxiv.org/abs/2506.09501v1
friendli_nanonla https://friendli.ai/models/ceselder/nanoNLA
pmlr_selfie https://proceedings.mlr.press/v235/chen24ae.html
LIST
