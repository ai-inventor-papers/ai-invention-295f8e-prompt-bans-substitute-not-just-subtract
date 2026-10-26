#!/usr/bin/env python3
"""GPU worker: S3 tests, S4 ban-free arms, commit #2, S6 full ban + route arms, gate, K0, prefills, screen, S8.

Batch shape: every sampled batch has exactly B rows that share one SHAPE CLASS = (task, cache length, position of the
first generated token). Rows of one class may come from different templates (W1/W2 usually have equal prompt
lengths) and different arms; a CRN slot (task, template, k) therefore meets identical kernels in every arm of its
class (rows of a batch never interact). The last batch of a class is padded with duplicate rows that are discarded.
K0 / K0b drop the condition span from the cache (engine.drop_span), so they form their own class.
Ordering guarantees: no ban prompt is sampled before work/commit1_closed exists; no bench ban sample is drawn before
commit #2 (computed here from the labelled S4 rows) is in commitments.log. Resumable by row uid.
"""

from __future__ import annotations

import collections
import gc
import json
import os
import time
from typing import Any, Callable

import numpy as np
import torch
from loguru import logger

from cfg import (DECODING, MAX_NEW_TOKENS, MODEL_ID, PATH_TASKS, PRED_DIR, RAW, RESULTS_DIR, SAMPLES, STAGE_A,
                 TEMPLATE_IDS, THRESHOLDS, TOKEN_LP_DIR, WORK_DIR, append_jsonl, default_of, read_json, read_jsonl,
                 sha256_text, stable_seed, utc_now, write_json)
from commit import commit_files
from engine import drop_span, load_model, prefill, sample, score, splice, u_stream
from prompts_s1 import load_prompts

TIMING: dict[str, Any] = {"batches": [], "stages": {}, "decisions": []}
ATTEMPT_EXCLUDE = ("invalid", "no_code", "disputed")


def u_key(task: str, w: str, k: int) -> tuple:
    return ("beh", task, w, k)  # exp8's behaviour key: the T1/T2 screen and U9 reuse exp8's uniforms exactly


class Worker:
    def __init__(self, B: int, deadline: float | None, prune_after: int | None) -> None:
        self.B = B
        self.deadline = deadline
        self.prune_after = prune_after
        self.tok, self.model = load_model(vram_fraction=0.98)
        vocab = self.tok.convert_ids_to_tokens(list(range(len(self.tok))))
        self.tick_ids = {i for i, s in enumerate(vocab) if s and "`" in s}
        self.prompts = load_prompts()
        self.ngrams = read_json(PRED_DIR / "ngrams.json")
        self.prefills = read_json(PRED_DIR / "prefills.json")
        self.done_uids = {r["uid"] for r in read_jsonl(RAW)}
        self._pre: dict[str, dict[str, Any]] = {}
        self._arm: dict[tuple, dict[str, Any]] = {}
        self.max_new = MAX_NEW_TOKENS
        self.extra: dict[str, Any] = {}

    def decode(self, ids: list[int]) -> str:
        return self.tok.decode(ids, skip_special_tokens=True)

    def remaining(self) -> float:
        return float("inf") if self.deadline is None else self.deadline - time.time()

    def pre(self, ids: list[int]) -> dict[str, Any]:
        key = sha256_text(",".join(map(str, ids)))
        if key not in self._pre:
            self._pre[key] = prefill(self.model, ids)
        return self._pre[key]

    def clear(self) -> None:
        self._pre.clear()
        self._arm.clear()
        gc.collect()
        torch.cuda.empty_cache()

    def prefix_ids(self, task: str, pf: str) -> list[int]:
        if pf == "SIG":
            return self.prefills[task]["signature"]["ids"]
        if pf == "NEU":
            return self.prefills[task]["neutral_ids"]
        if pf == "HEAPQ":
            return self.prefills[task]["heapq_prefill_ids"]
        raise ValueError(pf)

    def shape_of(self, task: str, w: str, arm: str) -> tuple[int, int]:
        """(cache length, first generated position) from prompt metadata only."""
        b = self.prompts[(task, w, "ban")]
        P, p0, p1 = b["P"], b["p0"], b["p1"]
        if arm in ("K0", "K0b"):
            return P - (p1 - p0), P
        if "+" in arm:
            L = P + len(self.prefix_ids(task, arm.split("+")[1]))
            return L, L
        return P, P

    def arm_state(self, task: str, w: str, arm: str) -> dict[str, Any]:
        key = (task, w, arm)
        if key in self._arm:
            return self._arm[key]
        pr = self.prompts
        ban, ta, tb = pr[(task, w, "ban")], pr[(task, w, "twin_A")], pr[(task, w, "twin_B")]
        P, p0, p1 = ban["P"], ban["p0"], ban["p1"]
        if arm == "a":
            s = self.pre(ban["ids"])
            st = {"kv": s["kv"], "r_logits": s["r_logits"], "ids": ban["ids"], "kind": "ban"}
        elif arm == "K0":
            s = self.pre(ban["ids"])
            st = {"kv": drop_span(s["kv"], p0, p1), "r_logits": s["r_logits"], "ids": ban["ids"],
                  "kind": "ban|K0(span dropped)", "pos0": P}
        elif arm in ("b", "V1", "VP", "R2", "R3", "OPEN"):
            s = self.pre(ta["ids"])
            st = {"kv": s["kv"], "r_logits": s["r_logits"], "ids": ta["ids"], "kind": "twin_A"}
        elif arm == "K0b":
            s = self.pre(ta["ids"])
            st = {"kv": drop_span(s["kv"], p0, p1), "r_logits": s["r_logits"], "ids": ta["ids"],
                  "kind": "twin_A|K0(span dropped)", "pos0": P}
        elif arm == "bB":
            s = self.pre(tb["ids"])
            st = {"kv": s["kv"], "r_logits": s["r_logits"], "ids": tb["ids"], "kind": "twin_B"}
        elif arm == "c":
            A, X = self.pre(ta["ids"]), self.pre(ban["ids"])
            st = {"kv": splice(A["kv"], X["kv"], p1), "r_logits": X["r_logits"], "ids": ta["ids"][:p1] + ban["ids"][p1:],
                  "kind": "splice:twinA[0,p1)|ban[p1,P)+R(ban)"}
        elif arm == "d":
            A, X = self.pre(ta["ids"]), self.pre(ban["ids"])
            st = {"kv": splice(X["kv"], A["kv"], p1), "r_logits": A["r_logits"], "ids": ban["ids"][:p1] + ta["ids"][p1:],
                  "kind": "splice:ban[0,p1)|twinA[p1,P)+R(twinA)"}
        elif arm == "pl":
            A, Bn = self.pre(ta["ids"]), self.pre(tb["ids"])
            st = {"kv": splice(A["kv"], Bn["kv"], p1), "r_logits": Bn["r_logits"], "ids": ta["ids"][:p1] + tb["ids"][p1:],
                  "kind": "splice:twinA[0,p1)|twinB[p1,P)+R(twinB)"}
        elif "+" in arm:
            base, pf = arm.split("+")
            src = ban if base == "BAN" else ta
            pids = self.prefix_ids(task, pf)
            s = self.pre(src["ids"] + pids)
            st = {"kv": s["kv"], "r_logits": s["r_logits"], "ids": src["ids"] + pids, "kind": f"{base.lower()}+{pf.lower()}",
                  "prefix_ids": pids, "prefix_text": self.tok.decode(pids)}
        else:
            raise ValueError(arm)
        self._arm[key] = st
        return st

    def veto_for(self, task: str, arm: str) -> dict[str, Any] | None:
        ng = self.ngrams[task]
        if arm == "V1":
            return {"mode": "oneshot", "ngrams": [ng["ids"]]} if ng.get("defined") else None
        if arm == "VP":
            return {"mode": "persistent", "ngrams": [ng["ids"]]} if ng.get("defined") else None
        if arm in ("R2", "R3"):
            return {"mode": "persistent", "ngrams": self.extra[arm][task]["ngrams"]}
        if arm == "OPEN":
            return {"mode": "oneshot", "ngrams": [self.prefills[task]["opening_veto"]["line_ids"]]}
        return None

    def uid(self, s: dict[str, Any]) -> str:
        return f"{s['task']}|{s['arm']}|{s['w']}|{s['k']}"

    # -------------------------------------------------------------------------------------------- batches
    def run_rows(self, stage: str, specs: list[dict[str, Any]], est_steps: int = 300) -> int:
        todo = [s for s in specs if self.uid(s) not in self.done_uids]
        if not todo:
            return 0
        groups: dict[tuple, list[dict[str, Any]]] = collections.OrderedDict()
        for s in todo:
            L, pos0 = self.shape_of(s["task"], s["w"], s["arm"])
            groups.setdefault((s["task"], L, pos0), []).append(s)
        n = 0
        cur_task = None
        for (task, L, pos0), lst in groups.items():
            if cur_task is not None and task != cur_task:
                self.clear()
                # whole tasks only: stop before a task whose batches cannot finish in the remaining budget
                n_b = sum(-(-len(v) // self.B) for (t2, _, _), v in groups.items() if t2 == task)
                need = n_b * est_steps * 0.105
                if self.remaining() < need:
                    TIMING["decisions"].append({"utc": utc_now(), "event": "stage truncated", "stage": stage,
                                                "skipped_from_task": task, "need_s": need, "remaining_s": self.remaining()})
                    logger.warning(f"[{stage}] stopping before {task}: need ~{need:.0f}s, have {self.remaining():.0f}s")
                    break
            cur_task = task
            for i in range(0, len(lst), self.B):
                chunk = lst[i:i + self.B]
                n_real = len(chunk)
                chunk = chunk + [dict(chunk[-1], dup=True) for _ in range(self.B - n_real)]
                self._run_batch(stage, chunk, n_real, L, pos0)
                n += n_real
        self.clear()
        return n

    def _run_batch(self, stage: str, chunk: list[dict[str, Any]], n_real: int, L: int, pos0: int,
                   prune_after: int | None = None) -> None:
        rows, meta = [], []
        for s in chunk:
            st = self.arm_state(s["task"], s["w"], s["arm"])
            assert st["kv"][0][0].shape[2] == L and st.get("pos0", L) == pos0, (s, L, pos0)
            uk = u_key(s["task"], s["w"], s["k"])
            veto = self.veto_for(s["task"], s["arm"])
            rows.append({"kv": st["kv"], "r_logits": st["r_logits"], "u": u_stream(*uk),
                         "u2": u_stream(*uk, "veto", n=256), "veto": veto, "pos0": pos0,
                         "stop": "path" if s["task"] in PATH_TASKS else "bench",
                         "prefix_text": st.get("prefix_text", "")})
            meta.append((s, st, uk, veto))
        t0 = time.time()
        try:
            res = sample(self.model, rows, max_new=self.max_new, tick_ids=self.tick_ids, decode=self.decode,
                         prune_after=prune_after if prune_after is not None else self.prune_after)
        except torch.cuda.OutOfMemoryError:
            del rows
            gc.collect()
            torch.cuda.empty_cache()
            if prune_after is not None and prune_after <= 300:
                raise
            logger.error(f"OOM in {stage} {chunk[0]['task']} L={L}; retrying with memory-guard pruning after step 300")
            TIMING["decisions"].append({"utc": utc_now(), "event": "oom_retry_prune300", "stage": stage,
                                        "task": chunk[0]["task"], "L": L})
            return self._run_batch(stage, chunk, n_real, L, pos0, prune_after=300)
        dt = time.time() - t0
        out = []
        bid = f"{stage}|{chunk[0]['task']}|{L}|{int(t0)}"
        for (s, st, uk, veto), r in list(zip(meta, res))[:n_real]:
            gen = self.decode(r["token_ids"])
            pre_text = st.get("prefix_text", "")
            fire_ctx = None
            if r["veto_fired"] and r["fire_step"] is not None:
                fs = r["fire_step"]
                fire_ctx = self.decode(r["token_ids"][max(0, fs - 12):fs + 12])
            out.append({
                "uid": self.uid(s), "stage": stage, "task": s["task"], "template": s["w"], "w": s["w"], "k": s["k"],
                "sample_id": s["k"], "arm": s["arm"], "condition": s["arm"], "block": 0 if s["k"] < 10 else 1,
                "model": MODEL_ID, "decoding": DECODING, "seed": stable_seed(*uk), "u_key": list(uk),
                "prompt_kind": st["kind"], "prompt_sha256": sha256_text(",".join(map(str, st["ids"]))),
                "P": pos0, "cache_len": L, "prefill_id": st["kind"] if "+" in s["arm"] else None,
                "prefix_text": pre_text, "prefix_ids": st.get("prefix_ids"), "text": pre_text + gen, "gen_text": gen,
                "token_ids": r["token_ids"], "n_new_tokens": r["n_tokens"], "finish_reason": r["finish_reason"],
                "logprob_sum": r["logprob_sum"], "veto": veto, "veto_fired": r["veto_fired"],
                "fire_step": r["fire_step"], "fire_context": fire_ctx, "n_redraws": r["n_redraws"],
                "redraw_steps": r["redraw_steps"], "n_completions_drawn": r["n_completions_drawn"],
                "batch_id": bid, "batch_B": self.B, "batch_steps": r["steps"], "pruned_at": r["pruned_at"],
                "utc": utc_now(), "token_ids_file": "data/samples_raw.jsonl"})
        append_jsonl(RAW, out)
        self.done_uids.update(o["uid"] for o in out)
        TIMING["batches"].append({"stage": stage, "task": chunk[0]["task"], "L": L, "n_real": n_real,
                                  "arms": sorted({c["arm"] for c in chunk}), "steps": res[0]["steps"], "s": dt,
                                  "pruned_at": res[0]["pruned_at"], "utc": utc_now()})
        logger.info(f"[{stage}] {chunk[0]['task']} L={L} arms={sorted({c['arm'] for c in chunk[:n_real]})} rows={n_real} "
                    f"steps={res[0]['steps']} {dt:.1f}s" + (f" pruned@{res[0]['pruned_at']}" if res[0]["pruned_at"] else ""))
        if len(TIMING["batches"]) % 5 == 0:
            write_json(RESULTS_DIR / "timing.json", TIMING)

    def wait_for(self, cond: Callable[[], bool], what: str, poll: float = 15.0) -> None:
        t0 = time.time()
        last = 0.0
        while not cond():
            if time.time() - last > 120:
                logger.info(f"waiting for {what} ({time.time() - t0:.0f}s)")
                last = time.time()
            time.sleep(poll)
        TIMING["decisions"].append({"utc": utc_now(), "event": f"waited for {what}", "s": time.time() - t0})

    def stage_time(self, name: str, t0: float, n: int) -> None:
        dt = time.time() - t0
        TIMING["stages"][name] = {"s": dt, "rows": n, "utc_end": utc_now()}
        write_json(RESULTS_DIR / "timing.json", TIMING)
        logger.info(f"stage {name}: {n} rows in {dt / 60:.1f} min; remaining budget {self.remaining() / 60:.1f} min")


# ------------------------------------------------------------------------------------------------ labels
def labelled_uids() -> dict[str, dict[str, Any]]:
    return {r["uid"]: r for r in read_jsonl(SAMPLES)}


def all_labelled(uids: list[str]) -> bool:
    lab = labelled_uids()
    return all(u in lab for u in uids)


def share_default(rows: list[dict[str, Any]], task: str) -> tuple[int, int]:
    att = [r for r in rows if r["label"] not in ATTEMPT_EXCLUDE]
    return sum(r["label"] == default_of(task) for r in att), len(att)


def compute_commit2(tasks: list[str]) -> dict[str, Any]:
    lab = labelled_uids()
    ngrams = read_json(PRED_DIR / "ngrams.json")
    c2c, landings = {}, {}
    for t in tasks:
        rows = [r for r in lab.values() if r["task"] == t and r["arm"] == "V1"]
        D = default_of(t)
        nd, na = share_default(rows, t)
        fire = float(np.mean([bool(r["veto_fired"]) for r in rows])) if rows else float("nan")
        fired = [r for r in rows if r["veto_fired"] and r["label"] not in ATTEMPT_EXCLUDE]
        V = 1 - nd / na if na else float("nan")
        Vf = float(np.mean([r["label"] != D for r in fired])) if fired else float("nan")
        if not ngrams[t].get("defined") or not rows or not (fire >= THRESHOLDS["veto_min_fire_rate"]):
            cls = "UNDEFINED"
        elif V >= THRESHOLDS["veto_low_direct"]:
            cls = "LOW_DIRECT"
        elif V < THRESHOLDS["veto_high_direct"]:
            cls = "HIGH_DIRECT"
        else:
            cls = "NONE"
        cov = set(ngrams[t].get("co_vetoed") or [])
        nond = [r for r in rows if r["label"] not in ATTEMPT_EXCLUDE and r["label"] != D]
        land = collections.Counter(r["label"] for r in nond if r["label"] not in cov)
        tot = sum(land.values())
        corr = collections.Counter(r["label"] for r in nond if r["label"] not in cov and r.get("passed"))
        c2c[t] = {"V": V, "n_attempted": na, "n_default": nd, "fire_rate": fire, "V_fired": Vf,
                  "n_fired_attempted": len(fired), "class": cls,
                  "prediction": {"LOW_DIRECT": "F_direct <= 0.15", "HIGH_DIRECT": "F_direct >= 0.25"}.get(cls)}
        landings[t] = {"counts": dict(land), "dist": {k: v / tot for k, v in land.items()} if tot else {},
                       "modal": land.most_common(1)[0][0] if land else None, "correct_only": dict(corr),
                       "pass_rate": float(np.mean([bool(r.get("passed")) for r in rows])) if rows else None,
                       "co_vetoed_excluded": sorted(cov), "n_nondefault": len(nond),
                       "subtract_oneshot_forecast": {k: v / tot for k, v in land.items()} if tot else {}}
    return {"c2c": c2c, "landings": landings}


def compute_gate(tasks: list[str]) -> dict[str, Any]:
    lab = labelled_uids()
    out = {}
    for t in tasks:
        rows = [r for r in lab.values() if r["task"] == t and r["arm"] == "a"]
        nd, na = share_default(rows, t)
        s_a = nd / na if na else float("nan")
        out[t] = {"s_a": s_a, "avoidance": 1 - s_a, "n_attempted": na, "n_nondefault": na - nd, "n_rows": len(rows),
                  "gated": bool(na and (1 - s_a) >= THRESHOLDS["gate_avoidance"]
                                and (na - nd) >= THRESHOLDS["gate_min_nondefault"])}
    return out


def specs(tasks: list[str], arm_ks: list[tuple[str, range]]) -> list[dict[str, Any]]:
    """Rows ordered task -> template -> arm -> k (so each template's arms sit together in its shape class)."""
    return [{"task": t, "w": w, "k": k, "arm": a} for t in tasks for w in TEMPLATE_IDS for a, ks in arm_ks for k in ks]


R20, R10 = range(20), range(10)


# ------------------------------------------------------------------------------------------------ main queue
def run(B: int, deadline: float | None, prune_after: int | None) -> None:
    W = Worker(B, deadline, prune_after)
    TIMING.update({"B": B, "deadline_epoch": deadline, "prune_after": prune_after})
    bench = list(STAGE_A)
    # ---- S3.2 signature-prefix scoring where the exact-prefix rule did not decide (twin_A prompts only)
    pf = W.prefills
    changed = False
    for t, v in pf.items():
        if v["signature"].get("rule") == "needs_lp_scoring":
            cands = v["signature"]["candidates"]
            means = []
            for c in cands:
                means.append(float(np.mean([float(score(W.model, W.arm_state(t, w, "b"), [c])[0].sum())
                                            for w in TEMPLATE_IDS])))
            best = int(np.argmax(means))
            v["signature"].update({"rule": "max_mean_lp_under_twinA", "ids": cands[best], "lp_means": means})
            pf[t]["signature_text"] = W.tok.decode(cands[best])
            changed = True
            logger.info(f"S3.2 {t}: chose prefix {W.tok.decode(cands[best])!r} (mean lp {means[best]:.2f})")
            W.clear()
    if changed:
        write_json(PRED_DIR / "prefills.json", pf)
        W.prefills = pf
    if not (WORK_DIR / "commit1a").exists():
        commit_files("commit1", [PRED_DIR / f for f in ("ngrams.json", "prefills.json", "associate_proximity.json",
                                                         "seeds.json", "prereg.md")])
        (WORK_DIR / "commit1a").write_text(utc_now())

    # ---- S4: ban-free bench arms (b and the one-shot veto V1 share batches; same uniforms)
    t0 = time.time()
    s4 = specs(bench, [("b", R20), ("V1", R20)])
    n = W.run_rows("S4", s4, est_steps=180)
    W.stage_time("S4", t0, n)
    s4_uids = [W.uid(s) for s in s4]

    # ---- ban-free work while commit #1 / S4 labels are pending: path screen round 1 + twin-only controls
    t0 = time.time()
    q3 = specs(list(PATH_TASKS), [("V1", R10), ("VP", R20)] +
               [("OPEN", R10)] * 0)
    for t in PATH_TASKS:
        arms = [("V1", R10), ("VP", R20)] + ([("OPEN", R10)] if W.prefills[t].get("opening_veto", {}).get("defined") else [])
        q3 = [s for s in q3 if s["task"] != t] + specs([t], arms)
    n = W.run_rows("Q3", q3, est_steps=450)
    W.stage_time("Q3a", t0, n)
    t0 = time.time()
    ctrl = bench[:3]
    n = W.run_rows("Q9", specs(ctrl, [("pl", R10), ("bB", R10)]) + specs(ctrl, [("K0b", R10)]), est_steps=150)
    W.stage_time("Q9a", t0, n)

    # ---- after commit #1: engine tests on T2's frozen exp8 prompts (U1-U3, U9)
    W.wait_for(lambda: (WORK_DIR / "commit1_closed").exists(), "commit #1 (analysis code)")
    from gpu_tests import run_tests

    if not (RESULTS_DIR / "engine_validation.json").exists():
        run_tests(W)

    # ---- commit #2 (after S4 labels)
    W.wait_for(lambda: all_labelled(s4_uids), "S4 labels")
    if not (WORK_DIR / "commit2").exists():
        c2 = compute_commit2(bench)
        write_json(PRED_DIR / "c2c.json", c2["c2c"])
        write_json(PRED_DIR / "veto_landings.json", c2["landings"])
        commit_files("commit2", [PRED_DIR / "c2c.json", PRED_DIR / "veto_landings.json"])
        (WORK_DIR / "commit2").write_text(utc_now())
        logger.info("commit #2: " + json.dumps({t: (round(v["V"], 3), v["class"]) for t, v in c2["c2c"].items()}))

    # ---- S6 + Q1: full ban a with the route arms c and d, all 12 tasks in Stage-A order (whole tasks)
    t0 = time.time()
    s6 = specs(bench, [("a", R20), ("c", R20), ("d", R20)])
    n = W.run_rows("S6", s6, est_steps=380)
    W.stage_time("S6+Q1", t0, n)
    a_uids = [W.uid(s) for s in s6 if s["arm"] == "a"]

    # ---- gate (needs arm-a labels)
    W.wait_for(lambda: all_labelled([u for u in a_uids if u in W.done_uids]), "arm-a labels")
    gate = compute_gate(bench)
    write_json(RESULTS_DIR / "gate.json", gate)
    gated = [t for t in bench if gate[t]["gated"]]
    logger.info(f"gate: gated={gated}; avoidance=" + json.dumps({t: round(v['avoidance'], 3) for t, v in gate.items()}))

    # ---- Q2: K0 on gated tasks (N = 100)
    t0 = time.time()
    n = W.run_rows("Q2", specs(gated, [("K0", R20)]), est_steps=350)
    W.stage_time("Q2", t0, n)

    # ---- Q4 (+Q7 twin references in the same batches): prefills on gated tasks, N = 50
    t0 = time.time()
    n = W.run_rows("Q4", specs(gated, [("BAN+SIG", R10), ("TWIN+SIG", R10)]) +
                   specs(gated, [("BAN+NEU", R10), ("TWIN+NEU", R10)]), est_steps=300)
    W.stage_time("Q4", t0, n)

    # ---- Q3 round 2 (persistent veto + re-emerged n-gram) and the T2 heapq prefill pair
    from screen import round_ngrams

    t0 = time.time()
    vp_uids = [W.uid(s) for s in q3 if s["arm"] == "VP"]
    W.wait_for(lambda: all_labelled(vp_uids), "VP labels")
    W.extra["R2"] = round_ngrams(W.tok, "VP", None)
    write_json(PRED_DIR / "screen_round2.json", W.extra["R2"])
    n = 0
    if W.extra["R2"]:
        n += W.run_rows("Q3", specs(sorted(W.extra["R2"]), [("R2", R10)]), est_steps=450)
    n += W.run_rows("Q9", specs(["t2"], [("BAN+HEAPQ", R10), ("TWIN+HEAPQ", R10)]), est_steps=450)
    W.stage_time("Q3b", t0, n)

    # ---- S8 continuous companion readout (teacher-forced log-probs)
    t0 = time.time()
    lp_readout(W, gated if gated else bench)
    W.stage_time("S8", t0, 0)

    # ---- droppable tail, in reverse drop order: Q5 (non-gated c/d already run in S6), Q6, Q8, Q9 rest
    if W.extra["R2"] and W.remaining() > 12 * 60:
        r2_uids = [W.uid(s) for s in specs(sorted(W.extra["R2"]), [("R2", R10)])]
        W.wait_for(lambda: all_labelled(r2_uids), "R2 labels")
        W.extra["R3"] = round_ngrams(W.tok, "R2", W.extra["R2"])
        write_json(PRED_DIR / "screen_round3.json", W.extra["R3"])
        if W.extra["R3"]:
            t0 = time.time()
            n = W.run_rows("Q6", specs(sorted(W.extra["R3"]), [("R3", R10)]), est_steps=450)
            W.stage_time("Q6", t0, n)
    else:
        TIMING["decisions"].append({"utc": utc_now(), "event": "Q6 not run", "reason": "no re-emergence or time"})
    nongated = [t for t in bench if t not in gated]
    if nongated and W.remaining() > 15 * 60:
        t0 = time.time()
        n = W.run_rows("Q8", specs(nongated, [("K0", R10)]), est_steps=350)
        W.stage_time("Q8", t0, n)
    else:
        TIMING["decisions"].append({"utc": utc_now(), "event": "Q8 not run", "reason": "no non-gated task or time"})
    write_json(RESULTS_DIR / "timing.json", TIMING)
    (WORK_DIR / "gpu_done").write_text(utc_now())
    logger.info("GPU queue complete")


def lp_readout(W: Worker, tasks: list[str]) -> None:
    """S8: lp_X = sum of teacher-forced log-probs of the default's signature prefix under each arm's cache, plus each
    survivor's modal forced-program opening. K0 is scored on the span-dropped cache with position ids from P."""
    out: dict[str, Any] = {}
    for t in tasks:
        sig = W.prefills[t]["signature"].get("ids")
        if not sig:
            continue
        surv = survivor_openings(W.tok, t)
        per_w: dict[str, Any] = {}
        arrays = {}
        for w in TEMPLATE_IDS:
            res = {}
            for arm in ("a", "b", "c", "d"):
                st = W.arm_state(t, w, arm)
                lps = score(W.model, st, [sig] + list(surv.values()))
                res[arm] = {"sig": float(lps[0].sum()), "survivors": {m: float(x.sum()) for m, x in zip(surv, lps[1:])}}
                arrays[f"{w}|{arm}|sig"] = lps[0]
            # K0 on the full ban cache with the exp8 global-config knockout (scoring path)
            st = W.arm_state(t, w, "a")
            b = W.prompts[(t, w, "ban")]
            lps = score(W.model, st, [sig] + list(surv.values()), ko={"p0": b["p0"], "p1": b["p1"]})
            res["K0"] = {"sig": float(lps[0].sum()), "survivors": {m: float(x.sum()) for m, x in zip(surv, lps[1:])}}
            arrays[f"{w}|K0|sig"] = lps[0]
            per_w[w] = res
            W.clear()
        np.savez_compressed(TOKEN_LP_DIR / f"{t}.npz", **arrays)
        out[t] = {"per_template": per_w, "signature_ids": sig,
                  "survivor_openings": {m: W.tok.decode(v) for m, v in surv.items()}}
    write_json(RESULTS_DIR / "lp_readout_raw.json", out)


def survivor_openings(tok: Any, task: str) -> dict[str, list[int]]:
    from forecast_s2 import forced_sets

    forced, _ = forced_sets(task)
    out = {}
    for m, lst in forced.items():
        firsts: collections.Counter = collections.Counter()
        for r in lst:
            lines = [ln for ln in r["code"].splitlines() if ln.strip()]
            if lines:
                firsts[lines[0]] += 1
        if firsts:
            out[m] = list(tok("```python\n" + firsts.most_common(1)[0][0] + "\n", add_special_tokens=False).input_ids)
    return out


if __name__ == "__main__":
    from cfg import setup_logging

    setup_logging("gpu")
    B = int(os.environ.get("BRT_BATCH", "40"))
    dl = os.environ.get("BRT_GPU_DEADLINE")
    pa = os.environ.get("BRT_PRUNE_AFTER", "560")
    run(B, float(dl) if dl else None, int(pa) if pa else None)
