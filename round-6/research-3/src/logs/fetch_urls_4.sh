PY=${AII_SKILLS_DIR}/.ability_client_venv/bin/python
cd "$(dirname "$0")/.."
while read key url; do
  $PY -I tools/fetch_texts.py --url "$key" "$url" 2>&1 | grep -v -e onnxruntime -e FutureWarning -e warnings.warn
done <<'LIST'
pmlr_selfie_chen24ao https://proceedings.mlr.press/v235/chen24ao.html
iclr2024_makelov_poster https://iclr.cc/virtual/2024/poster/19100
pmlr_das_clear2024 https://proceedings.mlr.press/v236/geiger24a.html
neurips2025_sutter https://neurips.cc/virtual/2025/poster/116000
LIST
