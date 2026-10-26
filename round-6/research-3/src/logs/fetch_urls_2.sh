PY=${AII_SKILLS_DIR}/.ability_client_venv/bin/python
cd "$(dirname "$0")/.."
while read key url; do
  $PY -I tools/fetch_texts.py --url "$key" "$url" 2>&1 | grep -v -e onnxruntime -e FutureWarning -e warnings.warn
done <<'LIST'
jaisood_nla https://jaisood.substack.com/p/natural-language-autoencoders-can
lw_gemma_scope_2 https://www.lesswrong.com/posts/YQro5LyYjDzZrBCdb/announcing-gemma-scope-2
gw_gemma_scope_2 https://www.greaterwrong.com/posts/YQro5LyYjDzZrBCdb/announcing-gemma-scope-2
anthropic_nla https://www.anthropic.com/research/natural-language-autoencoders
gw_hide_nla https://www.greaterwrong.com/posts/3oRQxpxn4LiWKwbeQ/can-you-hide-from-a-natural-language-autoencoder
LIST
