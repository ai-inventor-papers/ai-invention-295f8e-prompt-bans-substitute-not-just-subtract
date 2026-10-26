"""GPU stages: the vLLM engine (bf16, eager, prefix caching, persistent n-gram veto), staged sampling with concurrent
labelling, GPU smoke tests (T2), the iterated veto rounds + SUBTRACT-IN-CONTEXT (stage 1) and the exposure bans
(stage 2).  Every request carries a seed shared by all arms of one (task, Y, shown program, sample index)."""

from __future__ import annotations

import os
import statistics
import time
from collections import Counter, defaultdict

from loguru import logger

from . import ngram as NG
from .core import (BASE_SEED, DATA, DTYPE, MAX_MODEL_LEN, MAX_ROUNDS, MIN_NONY_SUBTRACT, MODEL_ID, MODEL_REV,
                   N_BASELINE_CHECK, NGRAM_MAX, PRED, PRESENCE_MIN, REEMERGE_MIN, RESULTS, ROOT, TASK_ORDER,
                   append_jsonl, deviation, fenced, read_json, read_jsonl, seed_of, sha256_text, write_json)

GEN_PATH = DATA / "generations.jsonl"
SMOKE_PATH = DATA / "smoke_raw.jsonl"
LABELS_RAW = DATA / "labels_raw.jsonl"
LABELS_COMBINED = DATA / "labels_combined.jsonl"
CHUNK = 640


def set_cache_env() -> None:
    os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")  # no C compiler on this machine: no Triton / Inductor
    os.environ.setdefault("VLLM_NO_USAGE_STATS", "1")
    os.environ.setdefault("DO_NOT_TRACK", "1")
    cache = ROOT / ".cache"
    for k, sub in [("VLLM_CACHE_ROOT", "vllm"), ("TRITON_CACHE_DIR", "triton"), ("TORCHINDUCTOR_CACHE_DIR", "inductor"),
                   ("XDG_CACHE_HOME", "xdg"), ("FLASHINFER_WORKSPACE_BASE", "flashinfer")]:
        os.environ.setdefault(k, str(cache / sub))
        (cache / sub).mkdir(parents=True, exist_ok=True)


class Engine:
    def __init__(self, max_num_seqs: int = 64, gpu_util: float = 0.92, max_batched: int = 4096):
        set_cache_env()
        from vllm import LLM
        t0 = time.time()
        self.cfg = {"model": MODEL_ID, "revision": MODEL_REV, "dtype": DTYPE, "gpu_memory_utilization": gpu_util,
                    "max_model_len": MAX_MODEL_LEN, "enable_prefix_caching": True, "max_num_seqs": max_num_seqs,
                    "max_num_batched_tokens": max_batched, "enforce_eager": True,
                    "logits_processors": ["exposure.veto:NgramVeto"], "seed": BASE_SEED, "generation_config": "vllm"}
        self.llm = LLM(model=MODEL_ID, revision=MODEL_REV, tokenizer_revision=MODEL_REV, dtype=DTYPE,
                       gpu_memory_utilization=gpu_util, max_model_len=MAX_MODEL_LEN, enable_prefix_caching=True,
                       max_num_seqs=max_num_seqs, max_num_batched_tokens=max_batched,
                       logits_processors=["exposure.veto:NgramVeto"], enforce_eager=True, seed=BASE_SEED,
                       generation_config="vllm")
        self.tok = self.llm.get_tokenizer()
        self.stop_ids = [self.tok.convert_tokens_to_ids("<|im_end|>"), self.tok.convert_tokens_to_ids("<|endoftext|>")]
        self.load_seconds = time.time() - t0
        logger.info(f"vLLM engine up in {self.load_seconds:.0f}s: {self.cfg}")

    def sampling_params(self, r: dict):
        from vllm import SamplingParams
        return SamplingParams(temperature=1.0, top_p=1.0, top_k=-1, min_p=0.0, repetition_penalty=1.0,
                              presence_penalty=0.0, frequency_penalty=0.0, max_tokens=r["max_tokens"], seed=r["seed"],
                              stop_token_ids=self.stop_ids, extra_args=({"veto": r["veto"]} if r.get("veto") else None))

    def generate(self, reqs: list[dict], out_path=GEN_PATH) -> list[dict]:
        if not reqs:
            return []
        t0 = time.time()
        outs = self.llm.generate([{"prompt_token_ids": r["prompt_ids"]} for r in reqs],
                                 sampling_params=[self.sampling_params(r) for r in reqs], use_tqdm=False)
        dt = time.time() - t0
        rows, n_tok = [], 0
        for r, o in zip(reqs, outs):
            c = o.outputs[0]
            n_tok += len(c.token_ids)
            rows.append({k: v for k, v in r.items() if k not in ("prompt_ids",)} |
                        {"text": c.text, "token_ids": list(c.token_ids), "finish_reason": c.finish_reason,
                         "n_new_tokens": len(c.token_ids), "n_prompt_tokens": len(r["prompt_ids"]), "model": MODEL_ID,
                         "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": -1, "min_p": 0.0,
                                      "max_tokens": r["max_tokens"], "thinking": False, "dtype": DTYPE},
                         "gen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        append_jsonl(out_path, rows)
        logger.info(f"  generated {len(reqs)} seqs, {n_tok} new tokens in {dt:.1f}s ({n_tok / max(dt, 1e-9):.0f} tok/s, "
                    f"{dt / len(reqs):.3f} s/seq)")
        return rows


# --------------------------------------------------------------------------------------------- request building
def load_design() -> dict:
    prompts = {r["prompt_key"]: r for r in read_jsonl(PRED / "prompts.jsonl")}
    shown = defaultdict(list)
    for r in read_jsonl(PRED / "shown_programs.jsonl"):
        shown[r["key"]].append(r)
    elig = read_json(PRED / "eligibility.json")
    return {"prompts": prompts, "shown": dict(shown), "alloc": read_json(PRED / "allocation.json"),
            "ngrams": read_json(PRED / "ngrams.json"), "elig": elig}


def ordered_keys(design: dict) -> list[str]:
    from .forecasts import ordered_eligible
    keys = [f"{e['task']}:{e['Y']}" for e in ordered_eligible(design["elig"])]
    return [k for k in keys if k in design["shown"]]


def priority_of(design: dict) -> dict:
    return {f"{e['task']}:{e['Y']}": e["priority"] for e in design["elig"]["eligible"]}


class PromptIds:
    """Chat-render + tokenise committed user texts, checking the committed chat sha256."""

    def __init__(self, tok):
        from bench_copy.common.prompts import render_chat
        self.tok, self.render, self.cache = tok, render_chat, {}

    def __call__(self, prec: dict) -> list[int]:
        k = prec["prompt_key"]
        if k not in self.cache:
            chat = self.render(self.tok, prec["user_text"])
            if sha256_text(chat) != prec["chat_sha256"]:
                raise RuntimeError(f"rendered prompt {k} does not match its committed sha256")
            self.cache[k] = self.tok(chat, add_special_tokens=False)["input_ids"]
        return self.cache[k]


def arm_requests(design: dict, pid: PromptIds, key: str, arm: str, rnd: int = 0, veto: list | None = None,
                 per_program: int | None = None, prompt_arm: str | None = None) -> list[dict]:
    t, y = key.split(":")
    reqs = []
    for p in design["shown"][key]:
        i = p["p_index"]
        n_p = per_program if per_program is not None else design["alloc"][key][i]
        prec = design["prompts"][f"{t}:{y}:{prompt_arm or arm}:p{i}"]
        ids = pid(prec)
        for j in range(n_p):
            reqs.append({"sample_id": f"{t}:{y}:{arm}:r{rnd}:p{i}:s{j}", "task": t, "Y": y, "arm": arm, "round": rnd,
                         "p_index": i, "j": j, "seed": seed_of(f"{t}:{y}:p{i}:s{j}"),
                         "prompt_key": prec["prompt_key"], "prompt_sha256": prec["chat_sha256"],
                         "template": {"copy": None, "veto": None, "named": "W5", "unnamed": "UNNAMED"}.get(arm, arm),
                         "max_tokens": prec["max_tokens"], "prompt_ids": ids, "veto": veto})
    return reqs


def baseline_requests(design: dict, pid: PromptIds) -> list[dict]:
    reqs = []
    for t in TASK_ORDER:
        prec = design["prompts"][f"{t}:baseline"]
        ids = pid(prec)
        for j in range(N_BASELINE_CHECK):
            reqs.append({"sample_id": f"{t}:baseline:baseline:r0:p0:s{j}", "task": t, "Y": None, "arm": "baseline",
                         "round": 0, "p_index": None, "j": j, "seed": seed_of(f"{t}:baseline:s{j}"),
                         "prompt_key": prec["prompt_key"], "prompt_sha256": prec["chat_sha256"], "template": None,
                         "max_tokens": prec["max_tokens"], "prompt_ids": ids, "veto": None})
    return reqs


def done_ids(path=GEN_PATH) -> set:
    return {r["sample_id"] for r in read_jsonl(path)}


def run_staged(eng: Engine, reqs: list[dict], pool, label: str, budget_note: dict) -> list[dict]:
    """10 -> 100 -> full, chunked; each chunk's rows go to the labelling pool as soon as they exist."""
    have = done_ids()
    todo = [r for r in reqs if r["sample_id"] not in have]
    logger.info(f"[{label}] {len(todo)} requests to generate ({len(reqs) - len(todo)} already done)")
    rows_all = []
    steps = [10, 100] if len(todo) > 110 else []
    pos = 0
    for n in steps:
        chunk = todo[pos:pos + n]
        pos += n
        t0 = time.time()
        rows = eng.generate(chunk)
        dt = time.time() - t0
        pool.submit(rows)
        rows_all += rows
        from bench_copy.common.harness import extract_code
        parse = sum(1 for r in rows if extract_code(r["text"])) / len(rows)
        per = dt / len(rows)
        remaining = len(todo) - pos
        budget_note.setdefault(label, []).append({"n": len(rows), "seconds": dt, "s_per_sample": per,
                                                  "parse_rate": parse, "mean_new_tokens": statistics.mean(
                                                      r["n_new_tokens"] for r in rows),
                                                  "projected_remaining_s_upper": per * remaining})
        logger.info(f"[{label}] scale step {n}: {dt:.1f}s, parse rate {parse:.2f}, mean new tokens "
                    f"{statistics.mean(r['n_new_tokens'] for r in rows):.0f}; serial-rate upper bound for the remaining "
                    f"{remaining}: {per * remaining / 60:.1f} min (batching makes it far shorter)")
        if n == 10:
            for r in rows[:3]:
                logger.info(f"--- sample {r['sample_id']} ({r['n_new_tokens']} tokens, {r['finish_reason']}):\n{r['text'][:1500]}")
        if parse < 0.9 and n == 100:
            logger.warning(f"[{label}] parse rate {parse:.2f} < 0.9 at the 100-sample step")
    while pos < len(todo):
        chunk = todo[pos:pos + CHUNK]
        pos += len(chunk)
        rows = eng.generate(chunk)
        pool.submit(rows)
        rows_all += rows
        logger.info(f"[{label}] {pos}/{len(todo)} generated; labelling backlog {pool.pending()}")
    return rows_all


# ---------------------------------------------------------------------------------------------- labels -> rows
def combined_labels(write: bool = True) -> dict[str, dict]:
    from bench_copy.common.harness import extract_code
    from .labels import combine
    gens = {r["sample_id"]: r for r in read_jsonl(GEN_PATH)}
    labs = [l for l in read_jsonl(LABELS_RAW) if l["sample_id"] in gens]
    seen, uniq = set(), []
    for l in labs:
        if l["sample_id"] not in seen:
            seen.add(l["sample_id"])
            uniq.append(l)
    comb = combine(uniq, {sid: extract_code(gens[sid]["text"]) for sid in seen}, {sid: gens[sid]["task"] for sid in seen})
    if write:
        with LABELS_COMBINED.open("w") as f:
            import json
            for c in comb:
                f.write(json.dumps(c) + "\n")
    return {c["sample_id"]: c for c in comb}


# ---------------------------------------------------------------------------------------------- smoke tests (T2)
def smoke_tests(eng: Engine, design: dict, pid: PromptIds) -> dict:
    if (RESULTS / "smoke_tests.json").exists():
        return read_json(RESULTS / "smoke_tests.json")
    key = ordered_keys(design)[0]
    t, y = key.split(":")
    g = design["ngrams"][key]["ids"]
    tok = eng.tok
    out = {"key": key, "g_star": g, "g_star_text": tok.decode(g)}
    base = arm_requests(design, pid, key, "copy", per_program=5)[:20]
    for r in base:
        r["sample_id"] = "smoke:" + r["sample_id"]
    plain = eng.generate([dict(r, sample_id=r["sample_id"] + ":plain") for r in base], SMOKE_PATH)
    veto = eng.generate([dict(r, sample_id=r["sample_id"] + ":veto", veto=[g]) for r in base], SMOKE_PATH)
    out["veto_occurrences"] = sum(NG.contains(r["token_ids"], g) for r in veto)
    out["copy_occurrences"] = sum(NG.contains(r["token_ids"], g) for r in plain)
    rare = [[tok.convert_tokens_to_ids("ĠZorblax")]] if tok.convert_tokens_to_ids("ĠZorblax") not in (None, tok.unk_token_id) else [[151000]]
    inert = eng.generate([dict(r, sample_id=r["sample_id"] + ":inert", veto=rare) for r in base], SMOKE_PATH)
    from bench_copy.common.harness import extract_code

    def parse(rows):
        return sum(1 for r in rows if extract_code(r["text"])) / len(rows)

    out["inert_veto"] = {"ids": rare, "parse_plain": parse(plain), "parse_inert": parse(inert),
                         "mean_len_plain": statistics.mean(r["n_new_tokens"] for r in plain),
                         "mean_len_inert": statistics.mean(r["n_new_tokens"] for r in inert),
                         "identical_to_plain": sum(a["token_ids"] == b["token_ids"] for a, b in zip(plain, inert))}
    heapq_ids = tok(" heapq", add_special_tokens=False)["input_ids"]
    t3 = [k for k in ordered_keys(design) if k.startswith("T03:")][0]
    planted_base = arm_requests(design, pid, t3, "copy", per_program=5)[:20]
    planted = eng.generate([dict(r, sample_id="smoke:" + r["sample_id"] + ":heapq", veto=[heapq_ids]) for r in planted_base],
                           SMOKE_PATH)
    planted_plain = eng.generate([dict(r, sample_id="smoke:" + r["sample_id"] + ":heapq_plain") for r in planted_base],
                                 SMOKE_PATH)
    out["planted_1gram"] = {"ids": heapq_ids, "key": t3,
                            "occurrences_with_veto": sum(NG.contains(r["token_ids"], heapq_ids) for r in planted),
                            "occurrences_without_veto": sum(NG.contains(r["token_ids"], heapq_ids) for r in planted_plain),
                            "text_mentions_with_veto": sum("heapq" in r["text"] for r in planted)}
    tw = []
    for a, b in zip(plain, veto):
        ia, ib = a["token_ids"], b["token_ids"]
        k = next((i for i in range(min(len(ia), len(ib))) if ia[i] != ib[i]), min(len(ia), len(ib)))
        first_g = next((i + len(g) - 1 for i in NG.occurrences(ia, g)), None)
        tw.append({"first_divergence": k, "first_vetoed_completion_in_copy": first_g,
                   "consistent": (first_g is None and ia == ib) or (first_g is not None and k == first_g)})
    out["twin_diagnostic"] = {"n": len(tw), "n_consistent": sum(x["consistent"] for x in tw), "pairs": tw}
    out["passed"] = bool(out["veto_occurrences"] == 0 and out["planted_1gram"]["occurrences_with_veto"] == 0
                         and abs(out["inert_veto"]["parse_plain"] - out["inert_veto"]["parse_inert"]) <= 0.15)
    write_json(RESULTS / "smoke_tests.json", out)
    logger.info(f"SMOKE: veto occurrences {out['veto_occurrences']} (copy {out['copy_occurrences']}), planted ' heapq' "
                f"{out['planted_1gram']['occurrences_with_veto']} vs {out['planted_1gram']['occurrences_without_veto']}, "
                f"inert identical {out['inert_veto']['identical_to_plain']}/20, twin consistent "
                f"{out['twin_diagnostic']['n_consistent']}/{len(tw)} -> passed={out['passed']}")
    if not out["passed"]:
        raise RuntimeError("GPU smoke tests failed (veto processor not behaving); see results/smoke_tests.json")
    return out


# --------------------------------------------------------------------------------------------- veto iteration
SPECIAL_MIN_ID = 151643  # Qwen3: ids >= 151643 are special tokens (<|endoftext|>, <|im_start|>, <|im_end|>, ...)


def plain_ids(ids: list[int]) -> list[int]:
    """Generated ids without special tokens (vLLM keeps the stop token <|im_end|> in token_ids)."""
    return [i for i in ids if i < SPECIAL_MIN_ID]


def reemergence_ngram(tok, y_rows: list[dict], groups: dict, mask: list[list[int]]) -> dict | None:
    """Round r+1 n-gram by the same rule as g*: canonical tokenisation of fenced(extracted code) of the round-r
    Y-labelled programs (the collateral groups are tokenised the same way); n-grams already masked are excluded."""
    from bench_copy.common.harness import extract_code
    ref = []
    for r in y_rows:
        code = extract_code(r["text"])
        if code:
            ref.append(NG.ngram_set(tok(fenced(code), add_special_tokens=False)["input_ids"], NGRAM_MAX))
    return NG.select_distinctive(ref, groups, None, presence_min=PRESENCE_MIN, exclude={tuple(g) for g in mask},
                                 allow_relaxed=True)


def surfaces(tok, y_rows: list[dict], copy_y_rows: list[dict], mask: list[list[int]]) -> dict:
    """Re-emergence surfaces: frequent new n-grams, windows around vetoed prefixes, text-level bypasses."""
    pres, base = Counter(), Counter()
    for r in y_rows:
        pres.update({g for g in NG.ngram_set(plain_ids(r["token_ids"]), 3)})
    for r in copy_y_rows:
        base.update({g for g in NG.ngram_set(plain_ids(r["token_ids"]), 3)})
    nb = max(len(copy_y_rows), 1)
    new = [(g, c / len(y_rows)) for g, c in pres.items() if base[g] / nb < 0.2]
    new.sort(key=lambda x: (-x[1], len(x[0])))
    windows = []
    for r in y_rows:
        ids = r["token_ids"]
        for g in mask:
            if len(g) < 2:
                continue
            for i in NG.occurrences(ids, g[:-1]):
                windows.append({"sample_id": r["sample_id"], "vetoed": tok.decode(g),
                                "window": tok.decode(ids[max(0, i - 10):i + len(g) + 9])})
    bypass = []
    for r in y_rows:
        for g in mask:
            txt = tok.decode(g)
            if txt.strip() and txt in r["text"] and not NG.contains(r["token_ids"], g):
                bypass.append({"sample_id": r["sample_id"], "vetoed": txt})
    return {"new_ngrams": [{"text": tok.decode(list(g)), "ids": list(g), "presence": p} for g, p in new[:10]],
            "vetoed_prefix_windows": windows[:15], "n_vetoed_prefix_windows": len(windows),
            "text_bypasses": bypass[:15], "n_text_bypasses": len(bypass)}
