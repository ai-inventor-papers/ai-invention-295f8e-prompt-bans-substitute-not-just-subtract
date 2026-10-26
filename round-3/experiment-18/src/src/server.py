"""PID-managed vLLM OpenAI server (one per precision): bf16 Qwen3-8B or the official Qwen3-8B-FP8 checkpoint.

Never kills by name: the PID is written to logs/server_<kind>.pid and only that PID is signalled.
No C compiler exists on this machine, so the server runs eager with torch.compile disabled; FP8 uses the
precompiled weight-only FP8 Marlin kernels (as exp11 did on sm_89).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from loguru import logger

from config import LOGS, PORTS, ROOT, SERVED, SRC, model_dir

VENV_BIN = ROOT / ".venv" / "bin"


def pid_file(kind: str) -> Path:
    return LOGS / f"server_{kind}.pid"


def is_up(kind: str) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORTS[kind]}/health", timeout=3) as r:
            return r.status == 200
    except Exception:  # noqa: BLE001 - any failure means not up
        return False


def start(kind: str, max_model_len: int, max_num_seqs: int, gpu_util: float = 0.92,
          max_batched: int = 4096) -> int:
    if is_up(kind):
        logger.info(f"server {kind} already up")
        return int(pid_file(kind).read_text()) if pid_file(kind).exists() else -1
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{SRC}:{env.get('PYTHONPATH', '')}".rstrip(":")
    env["TORCH_COMPILE_DISABLE"] = "1"
    env["VLLM_NO_USAGE_STATS"] = "1"
    env["VLLM_LOGGING_LEVEL"] = "INFO"
    if kind == "fp8":
        env["VLLM_TEST_FORCE_FP8_MARLIN"] = "1"
    cmd = [str(VENV_BIN / "vllm"), "serve", model_dir(kind), "--served-model-name", SERVED[kind],
           "--host", "127.0.0.1", "--port", str(PORTS[kind]), "--dtype", "bfloat16",
           "--max-model-len", str(max_model_len), "--gpu-memory-utilization", str(gpu_util),
           "--enable-prefix-caching", "--max-num-seqs", str(max_num_seqs),
           "--max-num-batched-tokens", str(max_batched), "--enforce-eager",
           "--logits-processors", "veto:NGramVeto", "--seed", "0", "--generation-config", "vllm"]
    log = (LOGS / f"server_{kind}.log").open("a")
    log.write(f"\n==== start {time.strftime('%H:%M:%S')} {' '.join(cmd)}\n")
    log.flush()
    p = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(ROOT),
                         start_new_session=True)
    pid_file(kind).write_text(str(p.pid))
    logger.info(f"server {kind} launched pid={p.pid}: {' '.join(cmd)}")
    return p.pid


def wait_ready(kind: str, timeout: float = 1200.0) -> bool:
    t0 = time.time()
    pid = int(pid_file(kind).read_text()) if pid_file(kind).exists() else None
    while time.time() - t0 < timeout:
        if is_up(kind):
            logger.info(f"server {kind} ready after {time.time() - t0:.0f}s")
            return True
        if pid is not None:
            try:
                os.kill(pid, 0)
            except OSError:
                logger.error(f"server {kind} pid {pid} died; see logs/server_{kind}.log")
                return False
        time.sleep(5)
    return False


def stop(kind: str) -> None:
    pf = pid_file(kind)
    if not pf.exists():
        return
    pid = int(pf.read_text())
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
    for _ in range(60):
        try:
            os.kill(pid, 0)
            time.sleep(1)
        except OSError:
            break
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass
    pf.unlink(missing_ok=True)
    logger.info(f"server {kind} (pid {pid}) stopped")


if __name__ == "__main__":
    from config import setup_logging

    setup_logging("server_cli")
    kind, action = sys.argv[1], sys.argv[2]
    if action == "start":
        mml = int(sys.argv[3]) if len(sys.argv) > 3 else 4608
        mns = int(sys.argv[4]) if len(sys.argv) > 4 else 32
        start(kind, mml, mns)
        ok = wait_ready(kind)
        sys.exit(0 if ok else 1)
    elif action == "stop":
        stop(kind)
