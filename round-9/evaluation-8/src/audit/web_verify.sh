#!/usr/bin/env bash
# Live verification of positioning neighbours with aii-web-tools fetch_grep; raw outputs land in audit/web/.
set -u
W="$(cd "$(dirname "$0")/.." && pwd)"
SKILL_DIR="${AII_WEB_TOOLS_DIR:?set AII_WEB_TOOLS_DIR to the aii-web-tools skill directory}"
PY="$SKILL_DIR/../.ability_client_venv/bin/python"
DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "$DATE" > "$W/audit/web/_run_utc.txt"
run_one() {
  name="$1"; url="$2"; pat="$3"
  out="$W/audit/web/${name}.txt"
  { echo "# url: $url"; echo "# pattern: $pat"; echo "# utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"; echo "# tool: aii-web-tools aii_fast_web_fetch.py grep"; echo; 
    timeout 150 "$PY" "$SKILL_DIR/scripts/aii_fast_web_fetch.py" grep --url "$url" --pattern "$pat" --max-matches 25 --context-chars 260 2>&1 | grep -v "FutureWarning\\|warnings.warn("; echo "# exit: ${PIPESTATUS[0]}"; } > "$out"
}
export -f run_one; export W SKILL_DIR PY
while IFS=$'\t' read -r n u p; do [ -n "$n" ] && echo -e "$n\t$u\t$p"; done < "$W/audit/web_jobs.tsv" | \
  xargs -P 8 -d '\n' -I{} bash -c 'IFS=$'"'"'\t'"'"' read -r n u p <<< "{}"; run_one "$n" "$u" "$p"'
echo "done $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$W/audit/web/_run_utc.txt"
