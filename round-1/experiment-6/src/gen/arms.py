#!/usr/bin/env python3
"""vLLM generation arms A0-A6 (thinking off and on), staged and resumable.

Every request has its own seed and fully explicit SamplingParams. Rows are appended per batch to
results/raw/<arm>.jsonl keyed by (task, condition, paraphrase_id, sample_id, T, sampler), so a crash resumes.
Run: .venv/bin/python gen/arms.py [--probe-only] [--deadline HH:MM] [--arms A0,A1,...]
"""

from __future__ import annotations

import argparse
import datetime as dt
import gc
import json
import os
import re
import sys
import time
from pathlib import Path

WS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS))
_EC = WS / ".engine_cache"
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("VLLM_CACHE_ROOT", str(_EC / "vllm"))
os.environ.setdefault("TRITON_CACHE_DIR", str(_EC / "triton"))
os.environ.setdefault("TORCHINDUCTOR_CACHE_DIR", str(_EC / "inductor"))
os.environ.setdefault("XDG_CACHE_HOME", str(_EC / "xdg"))
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import numpy as np  # noqa: E402

from common import (CAPACITY_FILE, DEFAULT_MODEL, EARLY_STOP_TEXT, FALLBACK_MODEL, LOGS, MODES, RAW,  # noqa: E402
                    TASK_TEXT, THINK_END_ID, append_jsonl, model_id, read_jsonl, setup_logging, stable_seed,
                    write_json)
from prompts.build import (GTS_STAGE2, chat_ids, forced_segment, segment, user_message,  # noqa: E402
                           GTS_STAGE1, TASK_TEXT_NO_FORMAT)

logger = setup_logging("gen_arms")

TEMPS = [0.3, 0.7, 1.0, 1.3]
SAMPLERS = {"topk10": dict(top_k=10, top_p=1.0), "topp095": dict(top_k=None, top_p=0.95),
            "pure": dict(top_k=None, top_p=1.0)}
EOS_IDS = {151645, 151643}  # <|im_end|>, <|endoftext|>
TOPK_OFF = -1  # replaced by 0 if this vLLM version rejects -1 (checked at start-up)
MAX_MODEL_LEN = 4096


def decoding(T: float, sampler: str, max_tokens: int, thinking: bool) -> dict:
    s = SAMPLERS[sampler]
    return dict(T=T, sampler=sampler, top_k=s["top_k"] if s["top_k"] else "off", top_p=s["top_p"],
                thinking=thinking, max_tokens=max_tokens)


def req(arm: str, task: str, condition: str, p: int, s: int, message: str, dec: dict, **extra) -> dict:
    key = f"{arm}|{task}|{condition}|p{p}|s{s}|T{dec['T']}|{dec['sampler']}|think{int(dec['thinking'])}"
    seed = stable_seed(task, condition, p, s, arm, dec["T"], dec["sampler"], dec["thinking"])
    return dict(key=key, arm=arm, task=task, condition=condition, paraphrase_id=p, sample_id=s,
                user_message=message, decoding={**dec, "seed": seed}, **extra)


def build_requests(arm: str, n_think: int = 5) -> list[dict]:
    R: list[dict] = []
    if arm == "A0":
        for task in ("T1", "T2"):
            for p in range(10):
                for s in range(10):
                    R.append(req(arm, task, "baseline", p, s, user_message(segment(task, "baseline", p), task),
                                 decoding(1.0, "pure", 1024, False)))
    elif arm == "A1":
        for task in ("T1", "T2"):
            for sampler in ("topk10", "topp095"):
                for T in TEMPS:
                    for p in range(10):
                        for s in range(10):
                            R.append(req(arm, task, "baseline", p, s,
                                         user_message(segment(task, "baseline", p), task),
                                         decoding(T, sampler, 1024, False)))
    elif arm == "A2":
        for task in ("T1", "T2"):
            for cond in ("seed_entropy", "seed_word", "seed_semantic"):
                for p in range(10):
                    for s in range(10):
                        R.append(req(arm, task, cond, p, s, user_message(segment(task, cond, p), task),
                                     decoding(1.0, "pure", 1024, False)))
    elif arm == "A3":
        for task in ("T1", "T2"):
            for cond in ("instr_creative", "instr_new_algo", "instr_fully_novel", "instr_enumerate"):
                mt = 1536 if cond == "instr_enumerate" else 1024
                for p in range(10):
                    for s in range(10):
                        R.append(req(arm, task, cond, p, s, user_message(segment(task, cond, p), task),
                                     decoding(1.0, "pure", mt, False)))
    elif arm == "A5":
        for task in ("T1", "T2"):
            for mode in MODES[task]:
                for f in range(20):
                    R.append(req(arm, task, f"forced:{mode}", f, 0,
                                 user_message(forced_segment(task, mode, f), task),
                                 decoding(1.0, "pure", 1024, False)))
    elif arm == "A4s1":
        for task in ("T1", "T2"):
            for s in range(100):
                R.append(req(arm, task, "gts_stage1", -1, s,
                             user_message(GTS_STAGE1, task, TASK_TEXT_NO_FORMAT[task]),
                             decoding(1.0, "pure", 400, False)))
    elif arm == "A4s2":
        R = build_gts_stage2()
    elif arm in ("A6a", "A6b", "A6c", "A6d"):
        task, sampler = {"A6a": ("T1", "topk10"), "A6b": ("T1", "topp095"), "A6c": ("T2", "topk10"),
                         "A6d": ("T2", "topp095")}[arm]
        for T in TEMPS:
            for p in range(10):
                for s in range(n_think):
                    R.append(req(arm, task, "baseline", p, s, user_message(segment(task, "baseline", p), task),
                                 decoding(T, sampler, 2048, True)))
    else:
        raise ValueError(arm)
    return R


ITEM_RE = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*|__)?\s*(\d{1,2})\s*[.):]\s*(.+?)\s*$")


def parse_items(text: str) -> list[str]:
    """Numbered list items 1..10 from a stage-1 output (first occurrence of each number, in order)."""
    items: dict[int, str] = {}
    for line in text.splitlines():
        m = ITEM_RE.match(line)
        if not m:
            continue
        k = int(m.group(1))
        body = re.sub(r"(\*\*|__|`)", "", m.group(2)).strip()
        if 1 <= k <= 10 and k not in items and len(body) >= 3:
            items[k] = body
    return [items[k] for k in sorted(items)]


def build_gts_stage2() -> list[dict]:
    R: list[dict] = []
    for row in read_jsonl(RAW / "A4s1.jsonl"):
        items = parse_items(row["text"])
        s = row["sample_id"]
        if not items:
            continue
        rng = np.random.default_rng(20261019 + s + (0 if row["task"] == "T1" else 100000))
        k = int(rng.integers(len(items)))
        msg = user_message(GTS_STAGE2.format(item=items[k]), row["task"])
        R.append(req("A4s2", row["task"], "gen_then_select", -1, s, msg, decoding(1.0, "pure", 1024, False),
                     gts_items=items, gts_k=k, gts_item=items[k], gts_n_items=len(items)))
    return R


def sampling_params(dec: dict, max_tokens: int | None = None, seed: int | None = None):
    from vllm import SamplingParams
    return SamplingParams(n=1, temperature=float(dec["T"]), top_p=float(dec["top_p"]),
                          top_k=int(dec["top_k"]) if dec["top_k"] != "off" else TOPK_OFF,
                          min_p=0.0, presence_penalty=0.0, frequency_penalty=0.0, repetition_penalty=1.0,
                          max_tokens=int(max_tokens or dec["max_tokens"]),
                          seed=int(seed if seed is not None else dec["seed"]), skip_special_tokens=True)


def make_engine(model: str, max_num_seqs: int):
    from vllm import LLM
    attempts = [dict(gpu_memory_utilization=0.92, enforce_eager=True),
                dict(gpu_memory_utilization=0.95, enforce_eager=True)]
    last: Exception | None = None
    for extra in attempts:
        try:
            t0 = time.time()
            llm = LLM(model=model, dtype="bfloat16", max_model_len=MAX_MODEL_LEN, max_num_seqs=max_num_seqs,
                      seed=0, generation_config="vllm", enable_prefix_caching=True, **extra)
            info = dict(extra, load_s=round(time.time() - t0, 1), max_num_seqs=max_num_seqs,
                        max_model_len=MAX_MODEL_LEN)
            try:
                cc = llm.llm_engine.vllm_config.cache_config
                info.update(num_gpu_blocks=cc.num_gpu_blocks, block_size=cc.block_size,
                            kv_tokens=(cc.num_gpu_blocks or 0) * cc.block_size,
                            max_concurrency_at_max_len=round((cc.num_gpu_blocks or 0) * cc.block_size
                                                             / MAX_MODEL_LEN, 2))
            except AttributeError as e:
                logger.warning(f"could not read cache config: {e}")
            logger.info(f"engine up: {info}")
            return llm, info
        except Exception as e:  # noqa: BLE001 - try the next memory setting
            last = e
            logger.exception(f"engine init failed with {extra}")
            gc.collect()
    raise RuntimeError(f"could not initialise vLLM for {model}: {last}")


def check_topk_off() -> None:
    global TOPK_OFF
    from vllm import SamplingParams
    try:
        SamplingParams(top_k=-1)
        TOPK_OFF = -1
    except (ValueError, TypeError):
        TOPK_OFF = 0
    logger.info(f"top_k disabled value for this vLLM: {TOPK_OFF}")


class Generator:
    def __init__(self, llm, tok):
        self.llm, self.tok = llm, tok
        self.pass1_max = 2048

    def run(self, prompt_ids: list[list[int]], params: list) -> tuple[list, float]:
        from vllm.inputs import TokensPrompt
        t0 = time.time()
        outs = self.llm.generate([TokensPrompt(prompt_token_ids=list(p)) for p in prompt_ids], params,
                                 use_tqdm=False)
        return outs, time.time() - t0

    def single_pass(self, reqs: list[dict]) -> tuple[list[dict], dict]:
        pids = [chat_ids(self.tok, r["user_message"], thinking=False) for r in reqs]
        outs, dt_s = self.run(pids, [sampling_params(r["decoding"]) for r in reqs])
        rows, ntok = [], 0
        for r, pid, o in zip(reqs, pids, outs):
            c = o.outputs[0]
            ids = list(c.token_ids)
            ntok += len(ids)
            rows.append(dict(r, prompt_token_ids=pid, output_token_ids=ids, text=c.text,
                             answer_text=c.text, thinking_text=None, finish_reason=c.finish_reason,
                             n_output_tokens=len(ids), truncated_thinking=None, n_thinking_tokens=None,
                             two_pass=None, model=model_id()))
        return rows, dict(n=len(reqs), tokens=ntok, seconds=round(dt_s, 1), tok_s=round(ntok / max(dt_s, 1e-6)))

    def thinking(self, reqs: list[dict]) -> tuple[list[dict], dict]:
        """Two-pass budget forcing (Qwen recipe): 2048-token thinking pass, then <=1024 answer tokens."""
        pids = [chat_ids(self.tok, r["user_message"], thinking=True) for r in reqs]
        outs1, dt1 = self.run(pids, [sampling_params(r["decoding"], max_tokens=self.pass1_max) for r in reqs])
        early_ids = self.tok(EARLY_STOP_TEXT, add_special_tokens=False)["input_ids"] + [THINK_END_ID] + \
            self.tok("\n\n", add_special_tokens=False)["input_ids"]
        state = []
        cont_prompts, cont_params, cont_idx = [], [], []
        for i, (r, pid, o) in enumerate(zip(reqs, pids, outs1)):
            c = o.outputs[0]
            ids1 = list(c.token_ids)
            st = dict(ids1=ids1, fr1=c.finish_reason, ids2=[], fr2=None, forced=[], mode="single")
            has_end = THINK_END_ID in ids1
            if has_end and c.finish_reason == "stop":
                st["mode"] = "complete_pass1"
            else:
                base = ids1[:]
                while base and base[-1] in EOS_IDS:
                    base.pop()
                if has_end:
                    st["mode"] = "answer_cut_continue"
                    st["forced"] = []
                else:
                    st["mode"] = "thinking_truncated_forced"
                    st["forced"] = early_ids
                    base = base + early_ids
                room = MAX_MODEL_LEN - len(pid) - len(base) - 1
                mt = min(1024, room)
                if mt > 0:
                    cont_prompts.append(pid + base)
                    cont_params.append(sampling_params(r["decoding"], max_tokens=mt,
                                                       seed=stable_seed(r["decoding"]["seed"], "pass2")))
                    cont_idx.append(i)
                st["base"] = base
            state.append(st)
        dt2 = 0.0
        if cont_prompts:
            outs2, dt2 = self.run(cont_prompts, cont_params)
            for i, o in zip(cont_idx, outs2):
                state[i]["ids2"] = list(o.outputs[0].token_ids)
                state[i]["fr2"] = o.outputs[0].finish_reason
        rows, ntok = [], 0
        for r, pid, st in zip(reqs, pids, state):
            if st["mode"] == "complete_pass1":
                full = st["ids1"]
                fr = st["fr1"]
            else:
                full = st["base"] + st["ids2"]
                fr = st["fr2"] or st["fr1"]
            ntok += len(st["ids1"]) + len(st["ids2"])
            if THINK_END_ID in full:
                j = full.index(THINK_END_ID)
                think_ids, ans_ids = full[:j], full[j + 1:]
            else:
                think_ids, ans_ids = full, []
            think_txt = self.tok.decode(think_ids, skip_special_tokens=True)
            ans_txt = self.tok.decode(ans_ids, skip_special_tokens=True)
            rows.append(dict(r, prompt_token_ids=pid, output_token_ids=full,
                             text=self.tok.decode(full, skip_special_tokens=False), answer_text=ans_txt,
                             thinking_text=think_txt.replace("<think>", "").strip(), finish_reason=fr,
                             n_output_tokens=len(full), truncated_thinking=st["mode"] == "thinking_truncated_forced",
                             n_thinking_tokens=len(think_ids), two_pass=st["mode"],
                             forced_ids=st["forced"], model=model_id()))
        dt_s = dt1 + dt2
        return rows, dict(n=len(reqs), tokens=ntok, seconds=round(dt_s, 1), tok_s=round(ntok / max(dt_s, 1e-6)),
                          n_pass2=len(cont_prompts))


def done_keys(arm: str) -> set[str]:
    return {r["key"] for r in read_jsonl(RAW / f"{arm}.jsonl")}


def deadline_ts(s: str | None) -> float:
    if not s:
        return float("inf")
    now = dt.datetime.now()
    h, m = map(int, s.split(":"))
    d = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if d < now - dt.timedelta(hours=12):
        d += dt.timedelta(days=1)
    return d.timestamp()


def run_arm(gen: Generator, arm: str, deadline: float, stats: dict, n_think: int, chunk: int = 640) -> None:
    reqs = build_requests(arm, n_think=n_think)
    have = done_keys(arm)
    todo = [r for r in reqs if r["key"] not in have]
    st = stats.setdefault(arm, dict(n_requested=len(reqs), n_done=len(have), stages=[]))
    st["n_requested"] = len(reqs)
    logger.info(f"[{arm}] requested={len(reqs)} already_done={len(have)} todo={len(todo)}")
    if not todo:
        return
    thinking = todo[0]["decoding"]["thinking"]
    stage_sizes = [10, 100] if not have else [100]
    i = 0
    per_sample = None
    while i < len(todo):
        size = stage_sizes.pop(0) if stage_sizes else (chunk if not thinking else 200)
        batch = todo[i:i + size]
        if per_sample is not None:
            eta = per_sample * len(batch)
            if time.time() + eta > deadline:
                logger.warning(f"[{arm}] next batch ({len(batch)}) would cross the deadline (eta {eta:.0f}s); "
                               f"stopping arm at n_done={st['n_done']}")
                st["stopped_by_deadline"] = True
                break
        rows, info = gen.thinking(batch) if thinking else gen.single_pass(batch)
        append_jsonl(RAW / f"{arm}.jsonl", rows)
        st["n_done"] += len(rows)
        per_sample = info["seconds"] / max(len(rows), 1)
        remaining = len(todo) - i - len(batch)
        info.update(stage=len(batch), s_per_sample=round(per_sample, 3),
                    extrapolated_remaining_s=round(per_sample * remaining, 1))
        st["stages"].append(info)
        st["time_per_sample"] = round(per_sample, 3)
        logger.info(f"[{arm}] batch {len(batch)}: {info}")
        write_json(LOGS / "gen_stats.json", stats)
        i += len(batch)


def capacity_probe(gen: Generator, info: dict) -> dict:
    reqs = []
    for k in range(64):
        p = k % 10
        reqs.append(req("probe", "T1", "baseline", p, 1000 + k, user_message(segment("T1", "baseline", p), "T1"),
                        decoding(1.0, "pure", 1024, False)))
    rows, ginfo = gen.single_pass(reqs)
    append_jsonl(RAW / "capacity_probe.jsonl", rows)
    mean_out = float(np.mean([r["n_output_tokens"] for r in rows]))
    core = 3820
    # throughput at 64-way concurrency is a lower bound for the full queue; extrapolate conservatively
    est_min = core * mean_out / max(ginfo["tok_s"], 1) / 60
    cap = dict(info, probe=ginfo, mean_output_tokens=round(mean_out, 1), core_generations=core,
               core_estimate_min=round(est_min, 1))
    return cap


def smoke(gen: Generator) -> None:
    """Stage-1 GPU smoke test: 16 A0 samples per task and 4 thinking traces (one truncated at 64 tokens)."""
    out = {}
    reqs = [r for r in build_requests("A0") if r["sample_id"] == 9 and r["paraphrase_id"] < 8] + \
        [r for r in build_requests("A0") if r["sample_id"] == 8 and r["paraphrase_id"] < 8]
    rows, info = gen.single_pass(reqs)
    out["a0"] = info
    out["a0_samples"] = [dict(task=r["task"], fr=r["finish_reason"], n=r["n_output_tokens"],
                              head=r["text"][:300]) for r in rows[:4]]
    th = [r for r in build_requests("A6a", n_think=1) if r["paraphrase_id"] < 3 and r["decoding"]["T"] == 1.0]
    rows_t, info_t = gen.thinking(th)
    gen.pass1_max = 64
    rows_x, info_x = gen.thinking([build_requests("A6c", n_think=1)[0]])
    gen.pass1_max = 2048
    out["thinking"] = [dict(mode=r["two_pass"], trunc=r["truncated_thinking"], n_think=r["n_thinking_tokens"],
                            n=r["n_output_tokens"], fr=r["finish_reason"], ans_head=r["answer_text"][:200],
                            think_head=(r["thinking_text"] or "")[:150]) for r in rows_t + rows_x]
    out["thinking_info"] = [info_t, info_x]
    write_json(LOGS / "smoke_gpu.json", out)
    append_jsonl(RAW / "smoke.jsonl", rows + rows_t + rows_x)
    logger.info(json.dumps(out, indent=1)[:4000])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe-only", action="store_true")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--deadline", default=None, help="HH:MM local time after which no new batch starts")
    ap.add_argument("--arms", default="A0,A1,A2,A6a,A3,A5,A4s1,A4s2,A6b,A6c,A6d")
    ap.add_argument("--n-think", type=int, default=5, help="samples per paraphrase in thinking cells")
    ap.add_argument("--max-num-seqs", type=int, default=128)
    args = ap.parse_args()
    from transformers import AutoTokenizer
    import vllm
    check_topk_off()
    model = model_id()
    tok = AutoTokenizer.from_pretrained(model)
    llm, info = make_engine(model, args.max_num_seqs)
    info.update(model=model, vllm_version=vllm.__version__)
    gen = Generator(llm, tok)
    if args.smoke:
        smoke(gen)
        return
    if not CAPACITY_FILE.exists() or "core_estimate_min" not in json.loads(CAPACITY_FILE.read_text()):
        cap = capacity_probe(gen, info)
        cap["decision"] = "keep_8B" if cap["core_estimate_min"] <= 120 else "switch_to_4B"
        if cap["decision"] == "switch_to_4B" and model == DEFAULT_MODEL:
            cap["model"] = FALLBACK_MODEL
            write_json(CAPACITY_FILE, cap)
            logger.warning(f"core estimate {cap['core_estimate_min']} min > 120: switching to {FALLBACK_MODEL}; "
                           "restart this script")
            return
        cap["model"] = model
        write_json(CAPACITY_FILE, cap)
        logger.info(f"capacity: {cap}")
    if args.probe_only:
        return
    deadline = deadline_ts(args.deadline)
    stats_path = LOGS / "gen_stats.json"
    stats = json.loads(stats_path.read_text()) if stats_path.exists() else {}
    for arm in args.arms.split(","):
        if time.time() > deadline:
            logger.warning(f"deadline passed before arm {arm}")
            stats.setdefault(arm, {})["skipped_by_deadline"] = True
            continue
        try:
            run_arm(gen, arm, deadline, stats, args.n_think)
        except Exception:
            logger.exception(f"arm {arm} failed; continuing with the next arm")
            stats.setdefault(arm, {})["error"] = True
        write_json(stats_path, stats)
    logger.info("all arms finished")


if __name__ == "__main__":
    main()
