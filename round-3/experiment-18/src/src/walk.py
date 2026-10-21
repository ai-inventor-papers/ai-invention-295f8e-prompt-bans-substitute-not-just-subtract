"""4b TOKEN WALK: cumulative persistent logit vetoes of each landed algorithm's distinctive token n-gram under the
neutral twins (no ban text), plus the SHAM veto and the fixed-TOP5 veto (T1), driven by a lockstep scheduler that
fills every GPU batch with independent filler jobs (LOS and two-step bans) once their forecasts are committed.

Per step k (k = 1..5) up to 3 mask rounds (r = 0..2): sample N = 50 (10 per template W1-W5) with the persistent
mask, label every program, then
  leak > 0.05            -> add the observed covering token spans to the mask, next round;
  max re-emergence >= .2 -> add expand(distinctive(A, re-emerged programs of A, survivors' forced programs));
  else finalise the step: STALLED if < 20 non-vetoed attempts or vetoed share > 0.5; DEGENERATE / OFF-CATALOGUE if
  the modal non-vetoed label is invalid / other; otherwise rung k+1 = modal non-vetoed label L_k, which is vetoed
  next (its distinctive n-gram scored against the not-yet-vetoed survivors).
Every mask is committed (hash chain) before the samples it governs.
"""

from __future__ import annotations

import ast
import time
from collections import Counter
from typing import Any, Callable

from loguru import logger

from client import run_batch
from commit import commit_json
from config import (CO_VETO_SHARE, DATA, LEAK_THRESHOLD, N_PER_TEMPLATE, NGRAM_PRESENCE, PRED, REEMERGE_THRESHOLD,
                    RESULTS, STALL_MIN_NONVETOED, STALL_VETOED_SHARE, STEP0_MIN_DEFAULT, TASKS, W_IDS,
                    WALK_MAX_EXTRA_ROUNDS, WALK_MAX_STEPS, MAX_TOKENS_SHORT, append_jsonl, seed_sham, seed_top5,
                    seed_walk, sha256_text, utc_now, write_json)
from label import label_programs
from ngram import distinctive, expand, occurrences, program_text, sham, string_leak
from programs import forced_as_requested, refs_default
from prompts import ids_of, neutral_twins, tokenizer
from stats import hill1, hill1_rarefied, wilson


def decode(ids: list[int]) -> str:
    return tokenizer().decode(list(ids))


def encode(s: str) -> list[int]:
    return ids_of(s)


def prog_ids(rows: list[dict[str, Any]]) -> list[list[int]]:
    return [encode(program_text(r)) for r in rows]


# ------------------------------------------------------------------------------------------------ AST surfaces
def ast_features(code: str | None) -> set[str]:
    out: set[str] = set()
    if not code:
        return out
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return {"unparseable"}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                out.add(f"import {a.name}")
        elif isinstance(n, ast.ImportFrom):
            for a in n.names:
                out.add(f"from {n.module} import {a.name}")
        elif isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                tag = f".{f.attr}("
                if f.attr == "pop" and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == 0:
                    tag = ".pop(0)"
                out.add(tag)
            elif isinstance(f, ast.Name):
                out.add(f"{f.id}(")
        elif isinstance(n, ast.ClassDef):
            out.add(f"class {n.name}")
    return out


def surfaces(reemerged: list[dict[str, Any]], refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Features frequent (>= 30%) in re-emerged programs of A but rare (< 10%) in A's reference programs."""
    if not reemerged:
        return []
    fr = Counter(f for r in reemerged for f in ast_features(r.get("code")))
    fref = Counter(f for r in refs for f in ast_features(r.get("code"))) if refs else Counter()
    out = []
    for f, k in fr.most_common():
        s_re = k / len(reemerged)
        s_ref = fref[f] / len(refs) if refs else 0.0
        if s_re >= 0.3 and s_ref < 0.1:
            out.append({"feature": f, "share_reemerged": round(s_re, 3), "share_refs": round(s_ref, 3)})
    return out[:15]


# ------------------------------------------------------------------------------------------------ masks
def mask_item(kind: str, algo: str, step: int, rnd: int, d: dict[str, Any]) -> dict[str, Any]:
    seqs = expand(d["ids"], decode, encode)
    kinds = ["g", "space", "newline", "bare"]
    variants = []
    core = d["string"].lstrip(" \n\t")
    for s in seqs:
        dec = decode(s)
        v = "g" if s == list(d["ids"]) else ("space" if dec == " " + core else ("newline" if dec == "\n" + core
                                                                                 else "bare"))
        variants.append({"ids": s, "variant": v if v in kinds else "bare", "string": dec})
    info = {k: v for k, v in d.items() if k not in ("ids", "string")}
    return {"kind": kind, "algo": algo, "step": step, "round": rnd, "ids": list(d["ids"]), "string": d["string"],
            "variants": variants, "seqs": [v["ids"] for v in variants], "info": info}


def veto_seqs(items: list[dict[str, Any]], drop_space: bool = False) -> list[list[int]]:
    out: list[list[int]] = []
    for it in items:
        for v in it["variants"]:
            if drop_space and v["variant"] == "space":
                continue
            if v["ids"] not in out:
                out.append(v["ids"])
    return out


def fires(out_ids: list[int], seqs: list[list[int]]) -> int:
    prefixes = {tuple(s[:-1]) for s in seqs if len(s) >= 2}
    lens = sorted({len(p) for p in prefixes})
    n = 0
    for p in range(1, len(out_ids) + 1):
        for m in lens:
            if p >= m and tuple(out_ids[p - m:p]) in prefixes:
                n += 1
                break
    return n


# ------------------------------------------------------------------------------------------------ summaries
def summarize(rows: list[dict[str, Any]], vetoed: list[str]) -> dict[str, Any]:
    n = len(rows)
    labels = [r["label"] for r in rows]
    counts = Counter(labels)
    att = [r for r in rows if r["label"] != "invalid"]
    n_att = len(att)
    k_pass = sum(r["passed"] for r in att)
    nonv = [r for r in att if r["label"] not in vetoed]
    nonv_ok = [r for r in nonv if r["passed"]]
    land = Counter(r["label"] for r in nonv)
    land_ok = Counter(r["label"] for r in nonv_ok)
    reem = {a: (sum(r["label"] == a for r in att) / n_att if n_att else 0.0) for a in vetoed}
    nv_modal = Counter(r["label"] for r in rows if r["label"] not in vetoed).most_common(1)
    return {"n": n, "attempted": n_att, "counts": dict(counts), "pass_rate": k_pass / n_att if n_att else None,
            "pass_ci": wilson(k_pass, n_att), "landing": dict(land), "landing_correct": dict(land_ok),
            "n_nonvetoed_attempted": len(nonv), "vetoed_share": (sum(r["label"] in vetoed for r in att) / n_att)
            if n_att else None, "reemergence": reem, "modal_nonvetoed": nv_modal[0][0] if nv_modal else None,
            "modal_correct_nonvetoed": land_ok.most_common(1)[0][0] if land_ok else None,
            "hill_cc": hill1(land_ok.values()),
            "hill_cc_rarefied20": hill1_rarefied([r["label"] for r in nonv_ok], 20),
            "other_share": counts.get("other", 0) / n if n else None,
            "invalid_share": counts.get("invalid", 0) / n if n else None,
            "leak_rate": sum(bool(r.get("string_leak")) for r in rows) / n if n else None,
            "truncated_share": sum(r.get("finish_reason") == "length" for r in rows) / n if n else None,
            "veto_occurrences_total": sum(r.get("veto_occurrences", 0) for r in rows),
            "fires_mean": (sum(r.get("fires", 0) for r in rows) / n) if n else None,
            "per_template": {w: dict(Counter(r["label"] for r in rows if r["template"] == w)) for w in W_IDS}}


# ------------------------------------------------------------------------------------------------ arms
class Arm:
    """Base: produces requests for one round, consumes its labelled rows."""
    arm = "base"

    def __init__(self, task: str) -> None:
        self.task = task
        self.D = TASKS[task]["default"]
        self.cat = TASKS[task]["catalogue"]
        self.twins = neutral_twins(task)
        self.items: list[dict[str, Any]] = []
        self.vetoed: list[str] = []
        self.step = 0
        self.rnd = 0
        self.active = True
        self.status = "RUNNING"
        self.history: list[dict[str, Any]] = []
        self.drop_space = False
        self.notes: list[str] = []

    def seed(self, i: int) -> int:
        raise NotImplementedError

    def requests(self) -> list[tuple[dict[str, Any], dict[str, Any]]]:
        seqs = veto_seqs(self.items, self.drop_space)
        out = []
        for wi, w in enumerate(W_IDS):
            for j in range(N_PER_TEMPLATE):
                i = wi * N_PER_TEMPLATE + j
                s = self.seed(i)
                meta = {"arm": self.arm, "task": self.task, "step": self.step, "round": self.rnd, "template": w,
                        "i": i, "seed": s, "prompt_sha256": sha256_text(self.twins[w]["user_text"]),
                        "veto_seqs": seqs}
                out.append((meta, {"prompt_ids": self.twins[w]["ids"], "seed": s, "max_tokens": MAX_TOKENS_SHORT,
                                   "veto": seqs or None}))
        return out

    def commit_mask(self) -> None:
        obj = {"utc": utc_now(), "arm": self.arm, "task": self.task, "step": self.step, "round": self.rnd,
               "vetoed": list(self.vetoed), "mask_items": self.items, "drop_space_variants": self.drop_space,
               "veto_seqs": veto_seqs(self.items, self.drop_space),
               "seeds": [self.seed(i) for i in range(len(W_IDS) * N_PER_TEMPLATE)]}
        p = PRED / f"{self.arm}_{self.task}_s{self.step}_r{self.rnd}.json"
        if p.exists():
            return
        commit_json(p, obj, f"{self.arm} mask {self.task} step {self.step} round {self.rnd}")

    def save(self) -> None:
        write_json(RESULTS / f"state_{self.arm}_{self.task}.json", self.state())

    def state(self) -> dict[str, Any]:
        return {"arm": self.arm, "task": self.task, "default": self.D, "status": self.status, "vetoed": self.vetoed,
                "mask_items": self.items, "history": self.history, "notes": self.notes, "step": self.step,
                "round": self.rnd, "active": self.active}

    def leak_items(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        spans: list[list[int]] = []
        existing = veto_seqs(self.items)
        for r in rows:
            for it in (r.get("leak_detail") or []):
                for sp in it["spans"]:
                    if sp and sp not in spans and sp not in existing:
                        spans.append(sp)
        out = []
        for sp in spans:
            s = decode(sp)
            out.append({"kind": "leak_span", "algo": "leak", "step": self.step, "round": self.rnd + 1, "ids": sp,
                        "string": s, "variants": [{"ids": sp, "variant": "g", "string": s}], "seqs": [sp],
                        "info": {"source": "observed covering span of a string leak"}})
        return out

    def reemergence_items(self, rows: list[dict[str, Any]], targets: list[str], survivors: list[str]) -> list[dict]:
        out = []
        summ = summarize(rows, targets)
        for a, sh in summ["reemergence"].items():
            if sh < REEMERGE_THRESHOLD:
                continue
            re_rows = [r for r in rows if r["label"] == a]
            others = {o: prog_ids(forced_as_requested(self.task, o)) for o in survivors}
            try:
                d = distinctive(prog_ids(re_rows), others, decode, TASKS[self.task]["signature"], NGRAM_PRESENCE,
                                CO_VETO_SHARE)
            except ValueError as e:
                self.notes.append(f"step {self.step} r{self.rnd}: no re-emergence n-gram for {a}: {e}")
                continue
            it = mask_item("reemergence", a, self.step, self.rnd + 1, d)
            it["info"]["surfaces"] = surfaces(re_rows, self._refs_for(a))
            out.append(it)
        return out

    def _refs_for(self, a: str) -> list[dict[str, Any]]:
        if a == self.D:
            return [r for r in refs_default()[self.task] if r["label"] == self.D]
        return forced_as_requested(self.task, a)


class WalkArm(Arm):
    arm = "walk"

    def seed(self, i: int) -> int:
        return seed_walk(self.task, self.step, self.rnd, i)

    def __init__(self, task: str) -> None:
        super().__init__(task)
        self.rungs: list[dict[str, Any]] = [{"rung": 1, "label": self.D, "source": "default (step 0)"}]
        self.degenerate_retry = False
        refs = [r for r in refs_default()[task] if r["label"] == self.D]
        others = {o: prog_ids(forced_as_requested(task, o)) for o in self.cat if o != self.D}
        self.d_default = distinctive(prog_ids(refs), others, decode, TASKS[task]["signature"], NGRAM_PRESENCE,
                                     CO_VETO_SHARE)
        logger.info(f"[{task}] distinctive n-gram of default {self.D}: {self.d_default['string']!r} "
                    f"(n={self.d_default['n']}, presence {self.d_default['presence_refs']:.2f}, score "
                    f"{self.d_default['score']:.2f}, co-vetoed {self.d_default['co_vetoed']})")

    def state(self) -> dict[str, Any]:
        s = super().state()
        s["rungs"] = self.rungs
        s["distinctive_default"] = self.d_default
        return s

    def consume(self, rows: list[dict[str, Any]]) -> None:
        summ = summarize(rows, self.vetoed)
        rec = {"step": self.step, "round": self.rnd, "vetoed": list(self.vetoed), "summary": summ,
               "n_mask_items": len(self.items), "drop_space": self.drop_space, "utc": utc_now()}
        self.history.append(rec)
        if self.step == 0:
            sh = summ["counts"].get(self.D, 0) / max(1, summ["attempted"])
            rec["default_share"] = sh
            if sh < STEP0_MIN_DEFAULT:
                self.status, self.active = "HALTED_STEP0", False
                self.notes.append(f"step 0 default share {sh:.2f} < {STEP0_MIN_DEFAULT}: walk halted")
                self.save()
                return
            self.vetoed = [self.D]
            self.items = [mask_item("distinctive", self.D, 1, 0, self.d_default)]
            self.step, self.rnd = 1, 0
            self.save()
            return
        # ----- extra mask rounds
        if summ["leak_rate"] is not None and summ["leak_rate"] > LEAK_THRESHOLD and self.rnd < WALK_MAX_EXTRA_ROUNDS:
            new = self.leak_items(rows)
            if new:
                self.items += new
                rec["decision"] = f"leak {summ['leak_rate']:.2f} > {LEAK_THRESHOLD}: +{len(new)} leak spans"
                self.rnd += 1
                self.save()
                return
        if max(summ["reemergence"].values(), default=0.0) >= REEMERGE_THRESHOLD and self.rnd < WALK_MAX_EXTRA_ROUNDS:
            survivors = [a for a in self.cat if a not in self.vetoed]
            new = self.reemergence_items(rows, self.vetoed, survivors)
            if new:
                self.items += new
                rec["decision"] = (f"re-emergence {summ['reemergence']} >= {REEMERGE_THRESHOLD}: +"
                                   f"{[it['string'] for it in new]}")
                self.rnd += 1
                self.save()
                return
        # ----- finalise the step
        rec["final_round_of_step"] = True
        rec["surfaces"] = {a: surfaces([r for r in rows if r["label"] == a], self._refs_for(a))
                           for a in self.vetoed if summ["reemergence"].get(a, 0) > 0}
        if (summ["invalid_share"] or 0) >= 0.5 and not self.degenerate_retry and self.rnd < WALK_MAX_EXTRA_ROUNDS + 1:
            self.degenerate_retry, self.drop_space = True, True
            rec["decision"] = "invalid share >= 0.5: one extra round without leading-space variants (F3)"
            self.notes.append(rec["decision"])
            self.rnd += 1
            self.save()
            return
        if summ["n_nonvetoed_attempted"] < STALL_MIN_NONVETOED or (summ["vetoed_share"] or 0) > STALL_VETOED_SHARE:
            self.status, self.active = "STALLED", False
            rec["decision"] = (f"STALLED: non-vetoed attempts {summ['n_nonvetoed_attempted']}, vetoed share "
                               f"{summ['vetoed_share']}")
            self.save()
            return
        L = summ["modal_nonvetoed"]
        if L == "invalid":
            self.status, self.active = "DEGENERATE", False
            rec["decision"] = "modal non-vetoed label is invalid"
            self.save()
            return
        if L == "other":
            self.status, self.active = "OFF-CATALOGUE", False
            rec["decision"] = "modal non-vetoed label is other"
            self.rungs.append({"rung": self.step + 1, "label": "other", "correct_only": summ["modal_correct_nonvetoed"]})
            self.save()
            return
        self.rungs.append({"rung": self.step + 1, "label": L, "correct_only": summ["modal_correct_nonvetoed"],
                           "share": summ["landing"].get(L, 0) / max(1, summ["n_nonvetoed_attempted"])})
        survivors = [a for a in self.cat if a not in self.vetoed and a != L]
        if self.step >= WALK_MAX_STEPS or not survivors:
            self.status, self.active = "REACHED_END", False
            rec["decision"] = f"rung {self.step + 1} = {L}; stop ({'step 5' if self.step >= WALK_MAX_STEPS else 'no survivors'})"
            self.save()
            return
        refs_rows = [r for r in rows if r["label"] == L]
        refs_src = "walk programs"
        if len(refs_rows) < 10:
            refs_rows, refs_src = forced_as_requested(self.task, L), "forced programs"
        others = {o: prog_ids(forced_as_requested(self.task, o)) for o in survivors}
        try:
            d = distinctive(prog_ids(refs_rows), others, decode, TASKS[self.task]["signature"], NGRAM_PRESENCE,
                            CO_VETO_SHARE)
        except ValueError as e:
            self.status, self.active = "STOPPED_NO_NGRAM", False
            rec["decision"] = f"rung {self.step + 1} = {L}; no distinctive n-gram ({e})"
            self.save()
            return
        it = mask_item("distinctive", L, self.step + 1, 0, d)
        it["info"]["refs_source"] = refs_src
        it["info"]["collateral_on_vetoed"] = {
            o: (sum(1 for x in prog_ids(forced_as_requested(self.task, o)) if tuple(d["ids"]) in
                    {tuple(x[i:i + d["n"]]) for i in range(len(x) - d["n"] + 1)}) /
                max(1, len(forced_as_requested(self.task, o)))) for o in self.vetoed}
        self.items.append(it)
        self.vetoed.append(L)
        rec["decision"] = f"rung {self.step + 1} = {L}; veto {d['string']!r} next"
        self.step, self.rnd = self.step + 1, 0
        self.drop_space = False
        self.save()


class MaskArm(Arm):
    """Fixed mask from the start (sham: one round; fixed-TOP5: up to 2 extra rounds on leak / re-emergence)."""

    def __init__(self, task: str, arm: str, items: list[dict[str, Any]], targets: list[str], extra_rounds: int) -> None:
        super().__init__(task)
        self.arm = arm
        self.items = items
        self.vetoed = list(targets)
        self.extra = extra_rounds
        self.step = 1

    def seed(self, i: int) -> int:
        return seed_sham(self.task, self.rnd, i) if self.arm == "sham" else seed_top5(self.rnd, i)

    def consume(self, rows: list[dict[str, Any]]) -> None:
        summ = summarize(rows, self.vetoed)
        rec = {"round": self.rnd, "summary": summ, "utc": utc_now()}
        if self.arm == "sham":
            rec["default_share_attempted"] = summ["counts"].get(self.D, 0) / max(1, summ["attempted"])
        self.history.append(rec)
        if self.rnd < self.extra:
            if summ["leak_rate"] and summ["leak_rate"] > LEAK_THRESHOLD:
                new = self.leak_items(rows)
                if new:
                    self.items += new
                    rec["decision"] = f"leak {summ['leak_rate']:.2f}: +{len(new)} spans"
                    self.rnd += 1
                    self.save()
                    return
            if max(summ["reemergence"].values(), default=0.0) >= REEMERGE_THRESHOLD:
                survivors = [a for a in self.cat if a not in self.vetoed]
                new = self.reemergence_items(rows, self.vetoed, survivors)
                if new:
                    self.items += new
                    rec["decision"] = f"re-emergence {summ['reemergence']}: +{[i['string'] for i in new]}"
                    self.rnd += 1
                    self.save()
                    return
        rec["final"] = True
        self.status, self.active = "DONE", False
        self.save()


def build_sham(walk: WalkArm) -> tuple[MaskArm, dict[str, Any]]:
    t = walk.task
    refs = [r for r in refs_default()[t] if r["label"] == walk.D]
    all_others = {o: prog_ids(forced_as_requested(t, o)) for o in walk.cat if o != walk.D}
    sh = sham(prog_ids(refs), all_others, decode, TASKS[t]["signature"], walk.d_default["n"],
              walk.d_default["presence_refs"], NGRAM_PRESENCE, exclude=[walk.d_default["ids"]])
    if not sh["rule"].startswith("generic"):
        info = {"utc": utc_now(), "task": t, "sham_candidate": sh, "status": "NOT_CONSTRUCTIBLE",
                "reason": "no algorithm-generic n-gram (>= 0.8 presence in every algorithm's programs, identifier "
                          "text, outside the signature) exists; the fallback candidate is default-specific, so it "
                          "would not be a sham"}
        write_json(RESULTS / f"sham_not_constructible_{t}.json", info)
        return None, info
    item = mask_item("sham", "sham", 1, 0, sh)
    pred = {"utc": utc_now(), "task": t, "sham": sh, "sham_seqs": item["seqs"],
            "distinctive_default": {k: walk.d_default[k] for k in ("ids", "string", "n", "presence_refs", "score",
                                                                   "collateral", "co_vetoed")},
            "prediction": f"default ({walk.D}) share >= 0.9 of attempted programs under the sham veto",
            "seeds": [seed_sham(t, 0, i) for i in range(len(W_IDS) * N_PER_TEMPLATE)]}
    p = PRED / f"sham_{t}.json"
    if not p.exists():
        commit_json(p, pred, f"sham prediction {t}")
    arm = MaskArm(t, "sham", [item], [], extra_rounds=0)
    return arm, pred


def build_top5(walk: WalkArm) -> MaskArm:
    t = walk.task
    assert t == "T1"
    targets = ["bfs", "dfs", "iddfs", "astar_gbfs"]
    items = []
    for a in targets:
        refs = [r for r in refs_default()[t] if r["label"] == a] if a == walk.D else forced_as_requested(t, a)
        others = {o: prog_ids(forced_as_requested(t, o)) for o in walk.cat if o != a}
        d = distinctive(prog_ids(refs), others, decode, TASKS[t]["signature"], NGRAM_PRESENCE, CO_VETO_SHARE)
        items.append(mask_item("fixed_top5", a, 1, 0, d))
    arm = MaskArm(t, "fixed_top5", items, targets, extra_rounds=WALK_MAX_EXTRA_ROUNDS)
    return arm


# ------------------------------------------------------------------------------------------------ scheduler
def label_and_rows(kind: str, batch: list[tuple[dict[str, Any], dict[str, Any]]],
                   outs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = [{"task": m["task"], "text": o["text"]} for (m, _), o in zip(batch, outs)]
    labs = label_programs(items)
    rows = []
    model = "Qwen/Qwen3-8B" if kind == "bf16" else "Qwen/Qwen3-8B-FP8"
    for (m, rq), o, lab in zip(batch, outs, labs):
        seqs = m.get("veto_seqs") or []
        mask_items = m.get("mask_items_for_leak") or []
        leak = string_leak(o["text"], o["token_ids"], mask_items, decode) if mask_items else {"leak": False,
                                                                                             "items": []}
        row = {"model": model, "engine_dtype": kind, "task": m["task"], "condition": m.get("condition", m["arm"]),
               "arm": m["arm"], "template": m.get("template"), "sample_id": f"{m['arm']}|{m['task']}|"
               f"{m.get('cond_id', '')}|s{m.get('step', '')}r{m.get('round', '')}|{m['i']}", "seed": m["seed"],
               "prompt_sha256": m["prompt_sha256"], "label": lab["label"], "labeller_source": lab["labeller_source"],
               "runtime_label": lab.get("runtime_label"), "ast_label": lab.get("ast_label"),
               "judge_label": lab.get("judge_label"), "passed": bool(lab.get("passed")),
               "finish_reason": o["finish_reason"], "n_new_tokens": o["n_new_tokens"],
               "code_sha256": lab["code_sha256"], "code": lab["code"], "step": m.get("step"), "round": m.get("round"),
               "n_veto_seqs": len(seqs), "veto_occurrences": occurrences(o["token_ids"], seqs) if seqs else 0,
               "fires": fires(o["token_ids"], seqs) if seqs else 0, "string_leak": leak["leak"],
               "leak_detail": leak["items"], **{k: v for k, v in m.items() if k.startswith("meta_")}}
        rows.append(row)
        raw = {"sample_id": row["sample_id"], "arm": m["arm"], "task": m["task"], "text": o["text"],
               "token_ids": o["token_ids"], "finish_reason": o["finish_reason"], "veto_seqs": seqs}
        append_jsonl(DATA / f"raw_{m['arm']}.jsonl", [raw])
    by_arm: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_arm.setdefault(r["arm"], []).append(r)
    for a, rs in by_arm.items():
        append_jsonl(DATA / f"samples_{a}.jsonl", rs)
    return rows


class Scheduler:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self.filler: list[tuple[dict[str, Any], dict[str, Any]]] = []
        self.hooks: list[Callable[["Scheduler", list[Arm]], None]] = []
        self.timings: list[dict[str, Any]] = []

    def add_filler(self, jobs: list[tuple[dict[str, Any], dict[str, Any]]]) -> None:
        self.filler.extend(jobs)

    def run(self, arms: list[Arm], max_filler_per_batch: int = 1000) -> None:
        it = 0
        while any(a.active for a in arms) or self.filler:
            batch: list[tuple[dict[str, Any], dict[str, Any]]] = []
            owners: list[Arm | None] = []
            for a in arms:
                if a.active:
                    a.commit_mask()
                    reqs = a.requests()
                    for m, rq in reqs:
                        m["mask_items_for_leak"] = a.items
                    batch += reqs
                    owners += [a] * len(reqs)
            take = self.filler[:max_filler_per_batch]
            self.filler = self.filler[max_filler_per_batch:]
            batch += take
            owners += [None] * len(take)
            if not batch:
                break
            t0 = time.time()
            outs, dt_gen = run_batch(self.kind, [rq for _, rq in batch])
            rows = label_and_rows(self.kind, batch, outs)
            dt = time.time() - t0
            self.timings.append({"iter": it, "n": len(batch), "gen_s": round(dt_gen, 1), "total_s": round(dt, 1),
                                 "new_tokens": sum(o["n_new_tokens"] for o in outs), "utc": utc_now()})
            logger.info(f"scheduler iter {it}: {len(batch)} programs, gen {dt_gen:.0f}s, total {dt:.0f}s")
            for a in arms:
                mine = [r for r, o in zip(rows, owners) if o is a]
                if mine:
                    a.consume(mine)
                    last = a.history[-1]
                    s = last["summary"]
                    logger.info(f"  [{a.arm} {a.task}] step {last.get('step', a.step)} r{last.get('round')}: "
                                f"counts {s['counts']} pass {s['pass_rate']} leak {s['leak_rate']} "
                                f"reem {s['reemergence']} -> {last.get('decision', '')} status {a.status}")
            for h in self.hooks:
                h(self, arms)
            it += 1
            write_json(RESULTS / f"scheduler_timings_{self.kind}.json", self.timings)
