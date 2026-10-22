PY=${AII_SKILLS_DIR}/.ability_client_venv/bin/python
cd "$(dirname "$0")/.."
while read key url; do
  $PY -I tools/fetch_texts.py --url "$key" "$url" 2>&1 | grep -v -e onnxruntime -e FutureWarning -e warnings.warn
done <<'LIST'
gemma_scope_2_tech_report https://storage.googleapis.com/deepmind-media/DeepMind.com/Blog/gemma-scope-2-helping-the-ai-safety-community-deepen-understanding-of-complex-language-model-behavior/Gemma_Scope_2_Technical_Paper.pdf
hf_mwhanna_qwen3_8b_transcoders https://huggingface.co/mwhanna/qwen3-8b-transcoders
hf_ceselder_nanonla https://huggingface.co/ceselder/nanoNLA
gh_nanonla_qwen3_8b_run https://raw.githubusercontent.com/ceselder/nanoNLA/main/docs/qwen3_8b_run.md
gh_nanonla_readme https://raw.githubusercontent.com/ceselder/nanoNLA/main/README.md
vllm_fp8_raw https://raw.githubusercontent.com/vllm-project/vllm/main/docs/features/quantization/fp8.md
llmcompressor_fp8_readme https://raw.githubusercontent.com/vllm-project/llm-compressor/main/examples/quantization_w8a8_fp8/README.md
LIST
