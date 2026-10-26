#!/usr/bin/env bash
# Restore the bulk that .aii/manifest.yaml deletes after the round (all paths relative to this folder):
#   .venv/          -> rebuilt with uv from the pinned pyproject.toml
#   cache/states/   -> copied back from iteration 7's artifact art_HY7uYZz-OjRW and sha256-verified
# Where art_HY7uYZz-OjRW is looked up (the same order as method.py's artifact_dir):
#   1. $AII_ART_HY7UYZZ_OJRW, if set;
#   2. the sibling folder ../art_HY7uYZz-OjRW (the published repository's layout);
#   3. the run-volume layout ../../../iter_7/gen_art/gen_art_experiment_38.
# If that artifact's cache/states/ is not present (it is excluded from its published copy), rebuild it there first
# with iteration 7's own code: (cd <that folder> && .venv/bin/python method.py --stage yv), about 2 GPU-minutes.
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  uv venv .venv --python=3.12
  uv pip install --python .venv/bin/python -r pyproject.toml
fi
if [ -n "${AII_ART_HY7UYZZ_OJRW:-}" ]; then
  SRC="$AII_ART_HY7UYZZ_OJRW"
elif [ -d "../art_HY7uYZz-OjRW" ]; then
  SRC="../art_HY7uYZz-OjRW"
else
  SRC="../../../iter_7/gen_art/gen_art_experiment_38"
fi
mkdir -p cache/states
for f in fork_variants fork_sources fork_twins; do
  if [ ! -f "cache/states/$f.pt" ]; then
    if [ -f "$SRC/cache/states/$f.pt" ]; then
      cp "$SRC/cache/states/$f.pt" cache/states/
    else
      echo "missing $SRC/cache/states/$f.pt: rebuild it with iteration 7's 'method.py --stage yv' (see above)" >&2
      exit 1
    fi
  fi
done
python3 - << 'PY'
import hashlib, json
from pathlib import Path
want = json.loads(Path("inputs/input_hashes.json").read_text())["copies"]
bad = []
for f in ("fork_variants", "fork_sources", "fork_twins"):
    p = Path(f"cache/states/{f}.pt")
    if hashlib.sha256(p.read_bytes()).hexdigest() != want[f"cache/states/{f}.pt"]["sha256"]:
        bad.append(str(p))
print("cache/states restored and verified" if not bad else f"sha256 mismatch (a rebuilt copy differs in bf16 bits): {bad}")
PY
