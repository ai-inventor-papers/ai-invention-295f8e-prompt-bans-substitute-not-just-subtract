#!/usr/bin/env python3
"""vLLM sampling: one long-lived `vllm serve` subprocess per session (PID-managed), an async client that sends
chat-templated prompts as token ids to /v1/completions, and the session-1 / session-2 request builders.

Adapted from iteration-1 exp1 gen/run_vllm.py: prompts rendered locally with enable_thinking=False; every sampling
field passed explicitly; the server runs with --generation-config vllm so Qwen3's generation_config.json defaults
(top_k=20, top_p=0.8, ...) cannot leak in. Generated token ids are returned with return_token_ids (logprobs are NOT
requested: in vLLM 0.11 the sampled-token rank uses a torch.compile'd kernel that needs a C compiler, which this
container lacks), so teacher forcing can reproduce the exact sampled sequence.
"""

from __future__ import annotations

import asyncio
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

import aiohttp
from loguru import logger

from common import (DATA_DIR, DECODING, LOG_DIR, MODEL_ID, MODEL_REVISION, N_PER_TEMPLATE, ROOT, SERVED_NAME,
                    VLLM_PORT, VLLM_URL, read_jsonl, request_seed, timing, utc_now, write_json)
from mb.prompts import EXPECTED_TAIL, tokenizer

SERVER_PID_FILE = LOG_DIR / "vllm_server.pid"
MAX_NUM_SEQS = int(os.environ.get("MB_MAX_NUM_SEQS", "24"))


def render_ids(text: str) -> list[int]:
    tok = tokenizer()
    ids = tok.apply_chat_template([{"role": "user", "content": text}], tokenize=True, add_generation_prompt=True,
                                  enable_thinking=False)
    if isinstance(ids, dict):
        ids = ids["input_ids"]
    ids = list(ids)
    assert tok.decode(ids).endswith(EXPECTED_TAIL)
    return ids


def start_server(session: str) -> int:
    """Start `vllm serve` in the background; returns its PID (also written to logs/vllm_server.pid)."""
    log = (LOG_DIR / f"vllm_server_{session}.log").open("a")
    cmd = [str(ROOT / ".venv" / "bin" / "vllm"), "serve", MODEL_ID, "--revision", MODEL_REVISION,
           "--dtype", "bfloat16", "--gpu-memory-utilization", "0.90", "--max-model-len", "2048",
           "--max-num-seqs", str(MAX_NUM_SEQS), "--seed", "0", "--generation-config", "vllm",
           "--enable-prefix-caching", "--enforce-eager", "--port", str(VLLM_PORT), "--host", "127.0.0.1",
           "--served-model-name", SERVED_NAME, "--enable-log-requests", "--max-log-len", "100"]
    env = dict(os.environ)
    env["VLLM_LOGGING_LEVEL"] = "INFO"
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, start_new_session=True)
    SERVER_PID_FILE.write_text(str(proc.pid))
    logger.info(f"vLLM server ({session}) started, PID {proc.pid}: {' '.join(cmd)}")
    return proc.pid


def stop_server() -> None:
    if not SERVER_PID_FILE.exists():
        return
    pid = int(SERVER_PID_FILE.read_text().strip())
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    for _ in range(60):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(1)
    else:
        try:
            os.killpg(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    SERVER_PID_FILE.unlink(missing_ok=True)
    logger.info(f"vLLM server PID {pid} stopped")


async def wait_for_server(timeout_s: float = 1200.0) -> None:
    t0 = time.time()
    async with aiohttp.ClientSession() as s:
        while time.time() - t0 < timeout_s:
            try:
                async with s.get(f"{VLLM_URL}/v1/models", timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        js = await r.json()
                        logger.info(f"vLLM server ready: {[m['id'] for m in js.get('data', [])]} "
                                    f"after {time.time() - t0:.0f}s")
                        return
            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass
            await asyncio.sleep(5)
    raise TimeoutError("vLLM server did not come up")


async def _post(session: aiohttp.ClientSession, payload: dict[str, Any]) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(4):
        try:
            async with session.post(f"{VLLM_URL}/v1/completions", json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(f"HTTP {resp.status}: {body[:300]}")
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as e:
            last_err = e
            logger.warning(f"completion request failed (attempt {attempt + 1}): {str(e)[:200]}")
            await asyncio.sleep(5 * (attempt + 1))
    raise RuntimeError(f"completion request failed after retries: {last_err}")


def _parse_ids(ch: dict[str, Any]) -> tuple[list[int] | None, float | None]:
    if ch.get("token_ids") is not None:
        return [int(x) for x in ch["token_ids"]], None
    lp = ch.get("logprobs") or {}
    toks = lp.get("tokens")
    if not toks:
        return None, None
    ids = []
    for t in toks:
        if isinstance(t, str) and t.startswith("token_id:"):
            ids.append(int(t.split(":", 1)[1]))
        else:
            return None, None
    vals = [x for x in (lp.get("token_logprobs") or []) if x is not None]
    return ids, (float(sum(vals)) if vals else None)


async def run_requests_async(reqs: list[dict[str, Any]], out_path: Path, concurrency: int = 24) -> dict[str, Any]:
    """Each request: req_id, prompt, n, seed (+ metadata copied to rows). Appends one row per sample to out_path and
    resumes by skipping req_ids already present."""
    out_path = Path(out_path)
    done = {r["req_id"] for r in read_jsonl(out_path)}
    todo = [r for r in reqs if r["req_id"] not in done]
    logger.info(f"{out_path.name}: {len(reqs)} requests, {len(done)} done, {len(todo)} to run "
                f"({sum(int(r['n']) for r in todo)} samples)")
    if not todo:
        return {"n_requests": 0, "n_samples": 0, "seconds": 0.0, "output_tokens": 0}
    lock = asyncio.Lock()
    stats = {"n_requests": 0, "n_samples": 0, "output_tokens": 0, "truncated": 0}
    t_start = time.time()
    timeout = aiohttp.ClientTimeout(total=7200, sock_read=7200)
    connector = aiohttp.TCPConnector(limit=concurrency * 2)
    sem = asyncio.Semaphore(concurrency)
    fh = out_path.open("a")
    tok = tokenizer()

    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:

        async def one(req: dict[str, Any]) -> None:
            async with sem:
                ids = render_ids(req["prompt"])
                payload = {"model": SERVED_NAME, "prompt": ids, "n": int(req["n"]),
                           "max_tokens": int(DECODING["max_tokens"]), "temperature": float(DECODING["temperature"]),
                           "top_p": float(DECODING["top_p"]), "top_k": int(DECODING["top_k"]), "min_p": 0.0,
                           "repetition_penalty": 1.0, "presence_penalty": 0.0, "frequency_penalty": 0.0,
                           "seed": int(req["seed"]), "return_token_ids": True}
                gen_start = utc_now()
                js = await _post(session, payload)
                gen_end = utc_now()
                rows = []
                meta = {k: v for k, v in req.items() if k != "prompt"}
                for ch in sorted(js["choices"], key=lambda c: c.get("index", 0)):
                    text = ch.get("text", "")
                    gids, lpsum = _parse_ids(ch)
                    ntok = len(gids) if gids is not None else len(tok.encode(text, add_special_tokens=False))
                    row = dict(meta)
                    row.update({"sample_index": int(ch.get("index", 0)), "text": text, "token_ids": gids,
                                "vllm_logprob_sum": lpsum, "finish_reason": ch.get("finish_reason"),
                                "n_output_tokens": ntok, "n_prompt_tokens": len(ids), "gen_start_utc": gen_start,
                                "gen_utc": gen_end, "model": MODEL_ID, "prompt": req["prompt"]})
                    rows.append(row)
                    stats["output_tokens"] += ntok
                    stats["truncated"] += int(ch.get("finish_reason") == "length")
                async with lock:
                    for row in rows:
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                    fh.flush()
                    stats["n_requests"] += 1
                    stats["n_samples"] += len(rows)
                    if stats["n_requests"] % 25 == 0 or stats["n_requests"] == len(todo):
                        el = time.time() - t_start
                        logger.info(f"{out_path.name}: {stats['n_requests']}/{len(todo)} requests, "
                                    f"{stats['n_samples']} samples, {stats['output_tokens'] / max(el, 1e-6):.0f} "
                                    f"out-tok/s, {el:.0f}s")

        results = await asyncio.gather(*[one(r) for r in todo], return_exceptions=True)
    fh.close()
    errs = [r for r in results if isinstance(r, Exception)]
    for e in errs[:5]:
        logger.error(f"request error: {e!r}")
    stats["seconds"] = time.time() - t_start
    stats["errors"] = len(errs)
    logger.info(f"{out_path.name}: finished {stats}")
    timing(f"vllm:{out_path.stem}", stats["seconds"], max(stats["n_samples"], 1), note=f"{stats['output_tokens']} tok")
    return stats


def run_requests(reqs: list[dict[str, Any]], out_path: Path, concurrency: int = 24) -> dict[str, Any]:
    return asyncio.run(run_requests_async(reqs, out_path, concurrency))


# ------------------------------------------------------------------------------------------------ request builders
def forced_requests(frozen: dict[str, Any], stage: str, n: int, variants: dict[str, str] | None = None,
                    only: list[tuple[str, str]] | None = None) -> list[dict[str, Any]]:
    """Forced prompts F_j: 10 paraphrases per algorithm, n samples each. variants: (task:key) -> 'plain'|'desc'."""
    reqs = []
    for task, td in frozen["tasks"].items():
        for key in frozen["catalogue"][task]:
            if only is not None and (task, key) not in only:
                continue
            var = (variants or {}).get(f"{task}:{key}", "plain")
            cname = f"forced_desc:{key}" if var == "desc" else f"forced:{key}"
            for it in td["conditions"][cname]:
                p = it["paraphrase_id"]
                reqs.append({"req_id": f"{task}|{cname}|F|{p}|{stage}", "task": task, "condition": cname,
                             "algorithm": key, "template": "F", "paraphrase_id": p, "stage": stage, "n": n,
                             "seed": request_seed(task, cname, "F", p, stage), "prompt": it["prompt"],
                             "segment": it["segment"], "variant": var})
    return reqs


def baseline_requests(frozen: dict[str, Any], n: int = 10) -> list[dict[str, Any]]:
    reqs = []
    for task, td in frozen["tasks"].items():
        for it in td["conditions"]["baseline"]:
            p = it["paraphrase_id"]
            reqs.append({"req_id": f"{task}|baseline|B|{p}|s1", "task": task, "condition": "baseline",
                         "template": "B", "paraphrase_id": p, "stage": "s1", "n": n,
                         "seed": request_seed(task, "baseline", "B", p), "prompt": it["prompt"],
                         "segment": it["segment"]})
    return reqs


def ban_requests(task: str, cname: str, items: list[dict[str, Any]], stage: str,
                 n: int = N_PER_TEMPLATE) -> list[dict[str, Any]]:
    """Sampled ban conditions: the 'ban' prompt of half 1 for each template W1-W5 (the ban prompt never depends on
    the half; only its neutral twin does)."""
    reqs = []
    for it in items:
        w = it["template"]
        tr = it["halves"]["1"]
        reqs.append({"req_id": f"{task}|{cname}|{w}|0|{stage}", "task": task, "condition": cname, "template": w,
                     "paraphrase_id": 0, "stage": stage, "n": n, "seed": request_seed(task, cname, w, 0),
                     "prompt": tr["prompts"]["ban"], "segment": tr["segments"]["ban"],
                     "banned": it.get("banned") or [cname.split(":", 1)[1]]})
    return reqs


def session1_main_requests(frozen: dict[str, Any]) -> list[dict[str, Any]]:
    reqs = baseline_requests(frozen)
    reqs += ban_requests("t1", "single:bfs", frozen["tasks"]["t1"]["conditions"]["single:bfs"], "s1")
    reqs += ban_requests("t2", "single:dijkstra", frozen["tasks"]["t2"]["conditions"]["single:dijkstra"], "s1")
    for s in frozen["catalogue"]["t2"]:
        reqs += ban_requests("t2", f"los:{s}", frozen["tasks"]["t2"]["conditions"][f"los:{s}"], "s1")
    return reqs


def staged_run(reqs: list[dict[str, Any]], out_path: Path, stages: tuple[int, ...] = (10, 100)) -> None:
    """Scale 10 -> 100 -> full (counted in samples), logging time per sample at each stage."""
    total = sum(int(r["n"]) for r in reqs)
    for lim in list(stages) + [total]:
        acc, sub = 0, []
        for r in reqs:
            if acc >= lim:
                break
            sub.append(r)
            acc += int(r["n"])
        st = run_requests(sub, out_path)
        if st.get("n_samples"):
            logger.info(f"stage <= {lim} samples: {st['seconds'] / st['n_samples']:.3f} s/sample; "
                        f"extrapolated remaining {(total - acc) * st['seconds'] / st['n_samples'] / 60:.1f} min")
        if st.get("errors"):
            raise RuntimeError(f"{st['errors']} request errors in {out_path.name}")


def gen_stats(path: Path) -> dict[str, Any]:
    rows = read_jsonl(path)
    from labeller_ext.extract import extract_code

    n = len(rows)
    ext = sum(1 for r in rows if extract_code(r["text"])[0] is not None)
    trunc = sum(1 for r in rows if r.get("finish_reason") == "length")
    think = sum(1 for r in rows if "<think>" in r["text"] or "</think>" in r["text"])
    st = {"n": n, "extracted": ext, "extract_rate": ext / max(n, 1), "truncated": trunc,
          "trunc_rate": trunc / max(n, 1), "thinking_text": think, "utc": utc_now()}
    write_json(DATA_DIR / f"{path.stem}_stats.json", st)
    return st
