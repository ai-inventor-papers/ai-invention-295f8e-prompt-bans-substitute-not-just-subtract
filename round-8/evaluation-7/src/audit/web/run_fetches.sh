#!/bin/bash
# Live re-verification of the positioning rows (STEP F), 2026-10-23. Each grep result lands in audit/web/<name>.txt.
# the skill lives at <repo root>/.claude/skills/aii-web-tools, nine levels above audit/web/ (override with AII_WEB_TOOLS_DIR)
SKILL_DIR="${AII_WEB_TOOLS_DIR:-$(cd "$(dirname "$0")/../../../../../../../../.." && pwd)/.claude/skills/aii-web-tools}"
PY="$SKILL_DIR/../.ability_client_venv/bin/python"
F="$SKILL_DIR/scripts/aii_fast_web_fetch.py"
S="$SKILL_DIR/scripts/aii_fast_web_search.py"
OUT=$(dirname "$0")
g() { timeout 120 "$PY" "$F" grep --url "$2" --pattern "$3" --max-matches 8 --context-chars 220 -i > "$OUT/$1.txt" 2>&1; echo "$1 exit $?" >> "$OUT/status.log"; }
s() { timeout 120 "$PY" "$S" --query "$2" --max-results 6 > "$OUT/$1.txt" 2>&1; echo "$1 exit $?" >> "$OUT/status.log"; }
: > "$OUT/status.log"
g tale_abs "https://arxiv.org/abs/2604.09921" "Two Temperatures|COLM|Comments|Submitted|\[v1\]|\[v2\]|diffusion" &
g icml_75333 "https://icml.cc/virtual/2026/75333" "Two Temperatures|AdaptFM|Workshop|Poster" &
g icml_74361 "https://icml.cc/virtual/2026/74361" "Two Temperatures|Structured Probabilistic|Workshop|Poster" &
g hotcold_abs "https://arxiv.org/abs/2309.02772" "Hot or Cold|AAAI|Comments|temperature|\[v1\]" &
g ctrltemp_abs "https://arxiv.org/abs/2510.01218" "Control the Temperature|COLM|Comments|\[v1\]" &
g entropy_abs "https://arxiv.org/abs/2605.09745" "Entropy-informed|branching|Comments|\[v1\]" &
g beyond8020_abs "https://arxiv.org/abs/2506.01939" "80/20|High-Entropy Minority|NeurIPS|Comments|\[v1\]" &
g mib_abs "https://arxiv.org/abs/2504.13151" "MIB|Mechanistic Interpretability Benchmark|ICML|Comments|\[v2\]" &
g funsearch "https://www.nature.com/articles/s41586-023-06924-6" "Mathematical discoveries from program search|Published|FunSearch" &
g alphaevolve_abs "https://arxiv.org/abs/2506.13131" "AlphaEvolve|coding agent|Comments|\[v1\]" &
g divalgo_abs "https://arxiv.org/abs/2610.19157" "DivAlgo|algorithmic diversity|Comments|\[v1\]" &
g beneath_abs "https://arxiv.org/abs/2609.00077" "Beneath the Diff|EMNLP|mode collapse|Comments|\[v1\]" &
g algdisc_abs "https://arxiv.org/abs/2504.05108" "Algorithm Discovery|Evolutionary Search|Reinforcement|Comments|\[v1\]" &
s cdas_search "CDAS Faithful Bi-Directional Model Steering via Distribution Matching and Distributed Interchange Interventions" &
wait
# second pass (same day): narrower patterns where the first grep's match list was truncated or the venue sat in the
# arXiv comment, plus the CDAS abstract found by the search above
g2() { timeout 120 "$PY" "$F" grep --url "$2" --pattern "$3" --max-matches "${4:-6}" --context-chars "${5:-160}" > "$OUT/$1.txt" 2>&1; echo "$1 exit $?" >> "$OUT/status.log"; }
g2 icml_75333_b "https://icml.cc/virtual/2026/75333" "Two Temperatures|Workshop: \[[^\]]{0,120}" &
g2 icml_74361_b "https://icml.cc/virtual/2026/74361" "Two Temperatures|Workshop: \[[^\]]{0,120}" &
g2 cdas_abs "https://arxiv.org/abs/2602.05234" "Title:|Comments:|Submitted on|ICLR" 6 140 &
g2 mib_venue "https://arxiv.org/abs/2504.13151" "Comments:|ICML 2025|International Conference on Machine Learning" 10 200 &
g2 hotcold_venue "https://arxiv.org/abs/2309.02772" "Comments:|AAAI" 10 200 &
wait
# drop the tool's own stderr noise (it carries local interpreter paths and is never evidence)
for f in "$OUT"/*.txt; do sed -i '/FutureWarning/d; /warnings.warn(/d' "$f"; done
echo ALLDONE >> "$OUT/status.log"
