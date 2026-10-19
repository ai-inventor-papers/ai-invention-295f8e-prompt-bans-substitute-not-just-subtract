"""Parent-side labelling pool: one sandboxed subprocess per distinct program, cached by code sha256."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from loguru import logger

from harness.extract import extract_code, sha256

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "harness" / "run_program.py"
CACHE_DIR = ROOT / "scratch" / "label_cache"
TMP_DIR = ROOT / "scratch" / "tmp"


def _wall_timeout(task: str) -> float:
    spec = json.loads((ROOT / "tasks" / f"{task}_cases.json").read_text())
    return float(sum(spec["limits"])) + 30.0


class LabelPool:
    """Thread pool launching `python -I harness/run_program.py` subprocesses; results cached on disk."""

    def __init__(self, workers: int = 5) -> None:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        self.ex = ThreadPoolExecutor(max_workers=workers)
        self.lock = threading.Lock()
        self.inflight: dict[str, Future] = {}
        self.wall = {t: _wall_timeout(t) for t in ("T1", "T2")}
        self.n_run = 0
        self.n_cache = 0

    def _run(self, task: str, code: str, key: str) -> dict:
        cpath = CACHE_DIR / f"{key}.json"
        if cpath.exists():
            try:
                return json.loads(cpath.read_text())
            except json.JSONDecodeError:
                pass
        with tempfile.NamedTemporaryFile("w", suffix=".py", dir=TMP_DIR, delete=False) as fh:
            fh.write(code)
            code_file = fh.name
        out_file = code_file + ".json"
        try:
            proc = subprocess.run([sys.executable, "-I", str(RUNNER), "--task", task, "--code", code_file, "--out",
                                   out_file, "--raw"], capture_output=True, timeout=self.wall[task], text=True)
            if Path(out_file).exists():
                res = json.loads(Path(out_file).read_text())
            else:
                res = {"passed": False, "label": None, "labeller_source": "crash", "runtime_label": None,
                       "ast_label": None, "first_error": f"runner died rc={proc.returncode}: {proc.stderr[-300:]}"}
        except subprocess.TimeoutExpired:
            res = {"passed": False, "label": None, "labeller_source": "wall_timeout", "runtime_label": None,
                   "ast_label": None, "first_error": "wall timeout"}
        finally:
            for p in (code_file, out_file):
                try:
                    Path(p).unlink()
                except FileNotFoundError:
                    pass
        if res.get("label") is None:
            # child died before labelling (e.g. os._exit, segfault, wall timeout): fall back to AST in the parent
            from labeller.ast_rules import ast_label
            lab, _ = ast_label(task, code)
            res["ast_label"] = res.get("ast_label") or lab
            res["label"], res["labeller_source"] = res["ast_label"], "ast_fallback_crash"
        cpath.write_text(json.dumps(res))
        with self.lock:
            self.n_run += 1
        return res

    def submit(self, task: str, text: str) -> Future:
        """Label one model response (full text). Returns a Future of the result dict (with code + sha)."""
        code = extract_code(text)
        if code is None:
            fut: Future = Future()
            fut.set_result({"passed": False, "label": "no_code", "labeller_source": "no_block",
                            "runtime_label": "no_code", "ast_label": "no_code", "code": None, "code_sha256": None,
                            "first_error": "no ```python block", "wall_s": 0.0})
            return fut
        key = f"{task}_{sha256(code)}"
        with self.lock:
            if key in self.inflight:
                self.n_cache += 1
                return self.inflight[key]
            fut = self.ex.submit(self._wrap, task, code, key)
            self.inflight[key] = fut
        return fut

    def _wrap(self, task: str, code: str, key: str) -> dict:
        try:
            res = self._run(task, code, key)
        except Exception as e:  # noqa: BLE001
            logger.exception(f"label job failed: {e}")
            res = {"passed": False, "label": "other", "labeller_source": "pool_error", "first_error": str(e)}
        res = dict(res)
        # AST labels are recomputed in the parent with the current rules (cache entries may predate a rule fix)
        from labeller.ast_rules import ast_label
        if res.get("labeller_source") not in ("no_solve", "no_block"):
            alab, _ = ast_label(task, code)
            res["ast_label"] = alab
            if res.get("labeller_source") in ("ast_fallback", "ast_fallback_crash"):
                res["label"] = alab
        res["code"] = code
        res["code_sha256"] = key.split("_", 1)[1]
        return res

    def shutdown(self) -> None:
        self.ex.shutdown(wait=True)
