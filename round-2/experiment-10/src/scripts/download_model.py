"""Download Llama-3.1-8B-Instruct (safetensors + configs only) into the run's shared HF cache.

Falls back to unsloth/Llama-3.1-8B-Instruct on a gated-repo / auth error.
Writes the resolved repo id, commit sha and local path to results/model_download.json.
"""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
from huggingface_hub import snapshot_download, HfApi  # noqa: E402
from huggingface_hub.utils import GatedRepoError, HfHubHTTPError  # noqa: E402
from loguru import logger

OUT = Path(__file__).resolve().parent.parent / "results" / "model_download.json"
OUT.parent.mkdir(parents=True, exist_ok=True)
PATTERNS = ["*.json", "*.safetensors", "tokenizer*", "LICENSE*", "USE_POLICY*", "README*"]


def fetch(repo: str) -> dict:
    t0 = time.time()
    info = HfApi().model_info(repo, token=os.environ.get("HF_TOKEN"))
    path = snapshot_download(repo, revision=info.sha, allow_patterns=PATTERNS,
                             ignore_patterns=["original/*"], token=os.environ.get("HF_TOKEN"),
                             max_workers=16)
    _ = path  # the snapshot lives in the HF cache; src/ws.model_path() resolves it from repo_id + commit_sha
    return {"repo_id": repo, "commit_sha": info.sha,
            "local_path": f"<HF cache>/models--{repo.replace('/', '--')}/snapshots/{info.sha}",
            "seconds": round(time.time() - t0, 1)}


@logger.catch(reraise=True)
def main() -> None:
    rec = {"attempts": []}
    for repo in ["meta-llama/Llama-3.1-8B-Instruct", "unsloth/Llama-3.1-8B-Instruct"]:
        try:
            r = fetch(repo)
            rec.update(r)
            rec["attempts"].append({"repo": repo, "ok": True})
            break
        except (GatedRepoError, HfHubHTTPError, OSError) as e:  # gated / 401 / 403 / network
            rec["attempts"].append({"repo": repo, "ok": False, "error": f"{type(e).__name__}: {str(e)[:300]}"})
            print(f"FAILED {repo}: {e}", file=sys.stderr)
    OUT.write_text(json.dumps(rec, indent=2))
    print(json.dumps(rec, indent=2))
    if "local_path" not in rec:
        sys.exit(1)


if __name__ == "__main__":
    main()
