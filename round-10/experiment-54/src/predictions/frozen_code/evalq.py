#!/usr/bin/env python3
"""S9 evaluation consumer: reads data/samples_raw_<model>.jsonl continuously and appends one analysis row per sample
(plus later update rows for held-out and quality results) to data/eval_rows.jsonl; decision vectors go to
data/decisions.jsonl. BP9 EvalPool, 5 spawn workers, RLIMIT_AS 2 GiB.

Per row: extract -> compile + screen -> SEL-OR (20 instances, 30 s CPU) + probes under seeds 0 and 1 (seeds 2 and 3
if STOCHASTIC) -> VALID (compiled, SEL-OR without exception or shape error, probe errors on <= 1% of states) ->
class, A_c for every catalogue rule (all and informative states), RF match, maximum corpus agreement and nearest
heuristic, lexical and synonym flags. Then H-OR3 (60 s CPU) for every VALID program and H-FSW5k (300 s) for those
with H-OR3 excess <= 4.294%; SEL-W (150 s) for QUALITY (F <= 1.1) and VALID_FULL, lowest priority."""
from __future__ import annotations

import time
from concurrent.futures import FIRST_COMPLETED, Future, wait
from typing import Any

import numpy as np
from loguru import logger

import bp
import extract
import instr
import lexical
import probes
import sandbox
from common import (DATA, RESULTS, ROOT, append_jsonl, elapsed_h, partial_status, read_json, read_jsonl,
                    setup_logging, sha256_text)
from corpus import load_vectors

MODEL_KEYS = ["q8", "q32", "q14"]
LIM = {"SEL-OR": 30.0, "SEL-W": 150.0, "H-OR3": 60.0, "H-FSW5k": 300.0}
HO_OR3_T = 4.294
HO_W5K_T = 3.187
QUALITY_STOP_H = 5.0          # SEL-W quality queue is not started after this elapsed time
PRIO = {"BASE": 0, "stage1": 1, "stoch": 1, "fsw5k": 2, "or3": 3, "selw_other": 6, "selw": 8}


class Evaluator:
    def __init__(self, n_workers: int = 5, probe: str = "P10") -> None:
        self.probe = probe
        gname = "instrument_gate.json" if probe == "P10" else f"instrument_gate_{probe}.json"
        g = read_json(RESULTS / gname)
        self.refs = {c: {int(s): np.array(v, dtype=np.uint16) for s, v in sv.items()}
                     for c, sv in g["reference_vectors"].items()}
        self.states = probes.load_states(probe)
        self.meta = probes.load_meta(probe)
        self.inf = np.array([m["informative"] for m in self.meta])
        self.matcher = instr.RFMatcher(self.states, self.meta, self.refs["RF"])
        cv = load_vectors()
        corpus = read_json(RESULTS / "corpus.json")
        self.corpus_names = [m["name"] for m in corpus["members"] if m.get("probe_err_share", 1.0) < 0.5]
        self.corpus_vecs = {n: cv[n] for n in self.corpus_names}
        self.corpus_stoch = {m["name"]: bool(m.get("stochastic")) for m in corpus["members"]}
        self.corpus_ok = list(self.corpus_names)
        hg = read_json(RESULTS / "harness_gate_v10.json")
        self.fit = bp.Fitness(bp.load_set("SEL-OR"), bp.load_set("SEL-W"), hg["sel_bf"]["or_excess"],
                              hg["sel_bf"]["w_excess"])
        self.l1 = {n: [x["l1"] for x in bp.load_set(n)] for n in ["SEL-OR", "SEL-W", "H-OR3", "H-FSW5k"]}
        self.pool = sandbox.EvalPool(n_workers, ROOT, 2.0)
        self.done = {r["row_id"] for r in read_jsonl(DATA / "eval_rows.jsonl") if r.get("stage") == "main"}
        self.pending: dict[Future, tuple[str, dict[str, Any]]] = {}
        self.n_done = len(self.done)

    # ------------------------------------------------------------------------------------------ helpers
    def corpus_agreement(self, vecs: dict[int, np.ndarray]) -> tuple[float, str, list[tuple[str, float]]]:
        vals = [(n, instr.A(vecs, self.corpus_vecs[n], self.corpus_stoch.get(n, False))) for n in self.corpus_ok]
        vals.sort(key=lambda x: -x[1])
        return vals[0][1], vals[0][0], [(n, round(a, 4)) for n, a in vals[:3]]

    def new_raw(self) -> list[dict[str, Any]]:
        out = []
        for mk in MODEL_KEYS:
            for r in read_jsonl(DATA / f"samples_raw_{mk}.jsonl"):
                rid = f"{mk}|{r['cell']}|{int(r['slot'])}"
                if rid in self.done or any(rid == v[0] for v in self.pending.values()):
                    continue
                r["row_id"] = rid
                out.append(r)
        return out

    def base_row(self, raw: dict[str, Any]) -> dict[str, Any]:
        fin = raw.get("finish_reason")
        reasoning = raw.get("reasoning") or ""
        return {"row_id": raw["row_id"], "stage": "main", "model": raw["model_key"], "model_id": raw.get("model"),
                "engine": raw.get("engine"), "provider": raw.get("provider"), "task": "online_bin_packing",
                "cell": raw["cell"], "condition": raw.get("condition"), "k": raw.get("k"),
                "template": raw.get("template"), "slot": int(raw["slot"]), "seed": raw.get("seed"),
                "finish_reason": fin, "truncated": fin in ("length", "idle_timeout_180s", "total_cap_900s"),
                "failed_request": bool(raw.get("failed")), "prompt_tokens": raw.get("prompt_tokens"),
                "completion_tokens": raw.get("completion_tokens"), "reasoning_tokens": raw.get("reasoning_tokens"),
                "reasoning_present": bool(reasoning.strip()), "cost_usd": raw.get("cost_usd"),
                "gen_seconds": raw.get("gen_seconds"), "raw_utc": raw.get("utc")}

    # ------------------------------------------------------------------------------------------ stage 1
    def submit_stage1(self, raw: dict[str, Any]) -> None:
        row = self.base_row(raw)
        ex = extract.extract(raw.get("content") or "")
        row.update(extract_ok=ex["ok"], extract_how=ex["how"], code=ex["code"], raw_block=ex["raw"],
                   code_sha256=sha256_text(ex["code"]) if ex["code"] else None,
                   norm_key=sandbox.normalise_key(ex["code"]) if ex["ok"] else None)
        vis = extract.visible_only(raw.get("content") or "")
        reasoning = raw.get("reasoning") or ""
        prog_text = ex["raw"] or ""
        row.update(hits_program=sorted(lexical.rules_hit(prog_text)),
                   hits_program_nonneg=sorted(lexical.rules_hit(prog_text, ignore_negated=True)),
                   hits_text=sorted(lexical.rules_hit(vis)), hits_reason=sorted(lexical.rules_hit(reasoning)),
                   synonyms=lexical.synonyms(prog_text), syn_category=lexical.synonym_category(prog_text),
                   claims_novelty=lexical.claims_novelty(vis),
                   self_id_rules=[r for r in lexical.RULES if lexical.self_identifies(reasoning, [r])])
        if not ex["ok"]:
            row.update(valid=False, compiled=False, error_type="syntax", error_msg=ex["error"])
            self.finish_main(row, None)
            return
        f = self.pool.submit({"code": ex["code"], "sets": ["SEL-OR"], "limits": LIM, "probes": [self.probe],
                              "probe_seeds": [0, 1]}, priority=PRIO["BASE"] if row["cell"] == "BASE" else
                             PRIO["stage1"])
        self.pending[f] = (row["row_id"], {"kind": "stage1", "row": row})

    def on_stage1(self, row: dict[str, Any], res: dict[str, Any]) -> None:
        row["error_type"] = res["error_type"]
        row["error_msg"] = res.get("msg", "")[:300]
        row["compiled"] = res["error_type"] not in ("syntax", "forbidden")
        vecs = {int(k.split("@")[1]): sandbox.decode(v) for k, v in res.get("probes", {}).items()}
        row["sel_or_bins"] = res.get("bins", {}).get("SEL-OR")
        row["probe_s"] = res.get("probe_s")
        if res["error_type"] != "ok" or not vecs or any(v is None for v in vecs.values()):
            row["valid"] = False
            row["probe_error"] = res.get("probe_error")
            self.finish_main(row, vecs or None)
            return
        if instr.is_stochastic(vecs):
            f = self.pool.submit({"code": row["code"], "sets": [], "probes": [self.probe], "probe_seeds": [2, 3]},
                                 priority=PRIO["stoch"])
            self.pending[f] = (row["row_id"], {"kind": "stoch", "row": row, "vecs": vecs})
            return
        self.classify_and_finish(row, vecs)

    def on_stoch(self, row: dict[str, Any], vecs: dict[int, np.ndarray], res: dict[str, Any]) -> None:
        for k, v in res.get("probes", {}).items():
            vecs[int(k.split("@")[1])] = sandbox.decode(v)
        self.classify_and_finish(row, vecs)

    def classify_and_finish(self, row: dict[str, Any], vecs: dict[int, np.ndarray]) -> None:
        good = {s: v for s, v in vecs.items() if v is not None}
        err = max(float(np.mean(v == instr.ERR)) for v in good.values()) if good else 1.0
        row["probe_err_share"] = err
        stoch = instr.is_stochastic(good)
        row["stochastic"] = stoch
        row["seeds_probed"] = sorted(good)
        info = instr.classify(good, self.refs, self.matcher, stoch)
        info_inf = instr.classify(good, self.refs, self.matcher, stoch, mask=self.inf)
        row["A"] = {k: round(v, 6) for k, v in info["A"].items()}
        row["A_inf"] = {k: round(v, 6) for k, v in info_inf["A"].items()}
        row["rf_match"] = bool(info["rf_match"])
        row["rf_stats"] = info["rf_stats"]
        row["valid"] = bool(err <= 0.01 and row["error_type"] == "ok")
        row["label"] = info["class"] if row["valid"] else "invalid"
        mx, nearest, top3 = self.corpus_agreement(good)
        row["corpus_max_agree"] = round(mx, 6)
        row["corpus_nearest"] = nearest
        row["corpus_top3"] = top3
        self.finish_main(row, good)
        if row["valid"]:
            f = self.pool.submit({"code": row["code"], "sets": ["H-OR3"], "limits": LIM}, priority=PRIO["or3"])
            self.pending[f] = (row["row_id"], {"kind": "or3", "row": row})
            if elapsed_h() < QUALITY_STOP_H:
                pr = PRIO["selw_other"] if row["label"] == "other" else PRIO["selw"]
                f2 = self.pool.submit({"code": row["code"], "sets": ["SEL-W"], "limits": LIM}, priority=pr)
                self.pending[f2] = (row["row_id"], {"kind": "selw", "row": row})

    def finish_main(self, row: dict[str, Any], vecs: dict[int, np.ndarray] | None) -> None:
        row.setdefault("valid", False)
        row.setdefault("label", "invalid")
        row["eval_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        append_jsonl(DATA / "eval_rows.jsonl", row)
        if vecs:
            append_jsonl(DATA / "decisions.jsonl", {"row_id": row["row_id"], "probe": self.probe,
                                                    "vecs": {str(s): v.tolist() for s, v in vecs.items()
                                                             if v is not None}})
        self.done.add(row["row_id"])
        self.n_done += 1

    # ------------------------------------------------------------------------------------------ later stages
    def on_or3(self, row: dict[str, Any], res: dict[str, Any]) -> None:
        upd: dict[str, Any] = {"row_id": row["row_id"], "stage": "or3"}
        if res["error_type"] == "ok":
            ex = 100 * bp.family_excess(res["bins"]["H-OR3"], self.l1["H-OR3"])
            upd["h_or3_excess"] = ex
            if ex <= HO_OR3_T:
                f = self.pool.submit({"code": row["code"], "sets": ["H-FSW5k"], "limits": LIM},
                                     priority=PRIO["fsw5k"])
                self.pending[f] = (row["row_id"], {"kind": "fsw5k", "row": row})
            else:
                upd["better"] = False
        else:
            upd["h_or3_error"] = res["error_type"]
            upd["better"] = False
        append_jsonl(DATA / "eval_rows.jsonl", upd)

    def on_fsw5k(self, row: dict[str, Any], res: dict[str, Any]) -> None:
        upd: dict[str, Any] = {"row_id": row["row_id"], "stage": "fsw5k"}
        if res["error_type"] == "ok":
            ex = 100 * bp.family_excess(res["bins"]["H-FSW5k"], self.l1["H-FSW5k"])
            upd["h_fsw5k_excess"] = ex
            upd["better"] = bool(ex <= HO_W5K_T)
        else:
            upd["h_fsw5k_error"] = res["error_type"]
            upd["better"] = False
        append_jsonl(DATA / "eval_rows.jsonl", upd)

    def on_selw(self, row: dict[str, Any], res: dict[str, Any]) -> None:
        upd: dict[str, Any] = {"row_id": row["row_id"], "stage": "selw"}
        if res["error_type"] == "ok" and row.get("sel_or_bins"):
            b25 = list(row["sel_or_bins"]) + list(res["bins"]["SEL-W"])
            F = self.fit.F(b25)
            eo, ew = self.fit.parts(b25)
            upd.update(F=F, F_parts=[eo, ew], quality=bool(F <= 1.1), valid_full=True,
                       sel_w_s=res.get("set_s", {}).get("SEL-W"))
        else:
            upd.update(valid_full=False, quality=False, selw_error=res["error_type"])
        append_jsonl(DATA / "eval_rows.jsonl", upd)

    # ------------------------------------------------------------------------------------------ loop
    def step(self, timeout: float = 2.0) -> int:
        new = self.new_raw()
        for raw in new:
            try:
                self.submit_stage1(raw)
            except Exception as e:  # noqa: BLE001 - a bad row must not stop the consumer
                logger.error(f"stage1 submit failed for {raw.get('row_id')}: {e!r}")
                row = self.base_row(raw)
                row.update(valid=False, error_type="runtime", error_msg=f"evaluator: {e!r}"[:300])
                self.finish_main(row, None)
        if not self.pending:
            time.sleep(timeout)
            return len(new)
        done, _ = wait(list(self.pending), timeout=timeout, return_when=FIRST_COMPLETED)
        for f in done:
            rid, ctx = self.pending.pop(f)
            try:
                res = f.result()
                k = ctx["kind"]
                if k == "stage1":
                    self.on_stage1(ctx["row"], res)
                elif k == "stoch":
                    self.on_stoch(ctx["row"], ctx["vecs"], res)
                elif k == "or3":
                    self.on_or3(ctx["row"], res)
                elif k == "fsw5k":
                    self.on_fsw5k(ctx["row"], res)
                elif k == "selw":
                    self.on_selw(ctx["row"], res)
            except Exception as e:  # noqa: BLE001
                logger.error(f"evaluation callback failed for {rid}: {e!r}")
        return len(new)

    def pending_counts(self) -> dict[str, int]:
        c: dict[str, int] = {}
        for _, ctx in self.pending.values():
            c[ctx["kind"]] = c.get(ctx["kind"], 0) + 1
        return c


def run_forever(n_workers: int = 5, probe: str = "P10") -> None:
    setup_logging("evalq")
    ev = Evaluator(n_workers, probe)
    logger.info(f"evaluator up: {len(ev.corpus_names)} corpus members, {ev.n_done} rows already done")
    last = 0.0
    while True:
        ev.step()
        if time.time() - last > 60:
            last = time.time()
            pc = ev.pending_counts()
            logger.info(f"evaluated {ev.n_done} rows; pending {pc}; backlog {ev.pool.backlog()}")
            partial_status({"evaluator": {"n_done": ev.n_done, "pending": pc, "respawns": ev.pool.n_respawn}})
            if (RESULTS / "STOP_EVAL").exists() and not ev.pending:
                logger.info("STOP_EVAL found and nothing pending: exiting")
                break
            if (RESULTS / "STOP_EVAL_NOW").exists():
                logger.info("STOP_EVAL_NOW: exiting with pending work counted as not evaluated")
                break
    ev.pool.close()
