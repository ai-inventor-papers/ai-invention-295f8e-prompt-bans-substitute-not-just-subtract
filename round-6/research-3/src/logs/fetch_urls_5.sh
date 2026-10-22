PY=${AII_SKILLS_DIR}/.ability_client_venv/bin/python
cd "$(dirname "$0")/.."
$PY -I tools/fetch_texts.py 2610.20683 2610.20808 2607.20469 2602.22600 2>&1 | grep -v -e onnxruntime -e FutureWarning -e warnings.warn
while read key url; do
  $PY -I tools/fetch_texts.py --url "$key" "$url" 2>&1 | grep -v -e onnxruntime -e FutureWarning -e warnings.warn
done <<'LIST'
tl_issue_1884 https://github.com/TransformerLensOrg/TransformerLens/issues/1884
lw_dreaming_vectors https://www.lesswrong.com/posts/rdhyHtjf3LcZxuQPm/dreaming-vectors-gradient-descented-steering-vectors-from
gh_easynla_readme https://raw.githubusercontent.com/syvb/EasyNLA/main/README.md
tc_attribution_graphs_methods https://transformer-circuits.pub/2025/attribution-graphs/methods.html
LIST
