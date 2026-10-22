#!/usr/bin/env bash
# Print the aii-web-tools skill interpreter: <dir>/.claude/skills/.ability_client_venv/bin/python, found by walking up
# from this script's directory (override the skills directory with AII_SKILLS_DIR).
if [ -n "$AII_SKILLS_DIR" ]; then echo "$AII_SKILLS_DIR/.ability_client_venv/bin/python"; exit 0; fi
d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
while [ "$d" != "/" ]; do
  if [ -x "$d/.claude/skills/.ability_client_venv/bin/python" ]; then echo "$d/.claude/skills/.ability_client_venv/bin/python"; exit 0; fi
  d="$(dirname "$d")"
done
echo "aii-web-tools skill interpreter not found; set AII_SKILLS_DIR" >&2; exit 1
