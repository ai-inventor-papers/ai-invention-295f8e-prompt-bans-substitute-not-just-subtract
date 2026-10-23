"""Pilot statistics, neutral nouns, freeze commitments, audits and method_out.json (exp_gen_sol_out)."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from loguru import logger

from .catalogue import FORCED_TEMPLATES, TASK_ORDER, TASKS, display_name
from .commit import canon_json, commit, sha256_file, sha256_text, verify_chain
from .prompts import spec_text
from .stats import bootstrap_ci, hill1, rarefied_hill1, wilson

BAN_RE = re.compile(r"(?i)\b(do not|don't|must not|never|without using|avoid|instead of|not allowed|forbidden|banned?|"
                    r"prohibit\w*|zorblax|novel|unusual|creative|unconventional)\b")


def pilot_stats(rows: list[dict], task: str) -> dict:
    rs = [r for r in rows if r["task"] == task]
    labels = [r["label"] for r in rs]
    att = [r for r in rs if r["label"] != "invalid"]
    cnt = Counter(r["label"] for r in att)
    n_att = len(att)
    modal, mk = (cnt.most_common(1)[0] if cnt else (None, 0))
    second = cnt.most_common(2)[1] if len(cnt) > 1 else (None, 0)
    correct = [r["label"] for r in att if r["passed"]]
    rare = rarefied_hill1(correct, 25)
    ci = bootstrap_ci(correct, lambda s: rarefied_hill1(s, 25, reps=200), reps=300) if rare is not None else (None, None)
    return {"n_samples": len(rs), "pilot_counts": dict(Counter(labels)), "n_attempted": n_att,
            "pass_rate": sum(r["passed"] for r in att) / max(n_att, 1),
            "pass_rate_all": sum(r["passed"] for r in rs) / max(len(rs), 1),
            "modal_label": modal, "modal_share": mk / max(n_att, 1), "modal_share_ci95": list(wilson(mk, n_att)),
            "second_label": second[0], "second_share": second[1] / max(n_att, 1),
            "second_share_ci95": list(wilson(second[1], n_att)) if n_att else None,
            "presence_flag": (second[1] / max(n_att, 1)) >= 0.10, "collapse_flag": (mk / max(n_att, 1)) >= 0.90,
            "hill1_correct": hill1(correct) if correct else None, "hill_rarefied25": rare,
            "hill_rarefied25_ci90": list(ci), "other_share": cnt.get("other", 0) / max(n_att, 1),
            "invalid_share": labels.count("invalid") / max(len(rs), 1),
            "labeller_source_shares": {k: v / max(len(rs), 1) for k, v in Counter(r["labeller_source"] for r in rs).items()},
            "presence_power_note": "N=50: P(>=5 of 50 | true share 0.10) ~ 0.57; ~0.98 at 0.20"}


def neutral_nouns(root: Path) -> dict:
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B-FP8")
    cands = json.loads((root / "data" / "extract" / "neutral_nouns.json").read_text())
    used = set()
    out = {}
    for t in TASK_ORDER:
        out[t] = {}
        for m in TASKS[t]["modes"]:
            dn = display_name(t, m)
            n_tok = len(tok(" " + dn, add_special_tokens=False)["input_ids"])
            ranked = sorted(cands, key=lambda c: (abs(c["tok_space"] - n_tok), -c["freq"], c["word"]))
            pick = [c for c in ranked if c["word"] not in used][:2]
            used.update(c["word"] for c in pick)
            out[t][m] = {"display_name": dn, "display_tokens_qwen3": n_tok,
                         "nouns": [{"word": c["word"], "qwen3_tokens": c["tok_space"], "subtlex_freq": c["freq"]} for c in pick]}
        (root / "bench" / TASKS[t]["task_id"] / "neutral_nouns.json").write_text(json.dumps(out[t], indent=1))
    return out


def no_ban_audit(root: Path) -> dict:
    n_prompts, hits = 0, []
    for name in ("prompts_rendered.jsonl",):
        p = root / "logs" / name
        if p.exists():
            for l in p.open():
                r = json.loads(l)
                n_prompts += 1
                txt = r["user_text"]
                spec_free = txt
                if BAN_RE.search(spec_free):
                    hits.append({"sample_id": r["sample_id"], "match": BAN_RE.search(spec_free).group(0)})
    return {"n_prompts_audited": n_prompts, "ban_lexicon_hits": len(hits), "examples": hits[:5],
            "lexicon": BAN_RE.pattern, "zorblax_hits": sum(1 for h in hits if h["match"].lower() == "zorblax"),
            "note": "the 15 frozen W1-W5 strings are not available to this artifact; a superset ban/novelty lexicon is used"}


def freeze(root: Path, gated: list[str]) -> dict:
    per = {}
    for t in gated:
        d = root / "bench" / TASKS[t]["task_id"]
        files = ["spec.json", "tests.jsonl", "checker.py", "ast_rules.py", "runtime_rules.py", "probes.json",
                 "gold_set.jsonl", "frlp_sets.json"]
        h = {f: sha256_file(d / f) for f in files if (d / f).exists()}
        for rf in sorted((d / "references").glob("*.py")):
            h[f"references/{rf.name}"] = sha256_file(rf)
        h["catalogue"] = sha256_text(canon_json(json.loads((d / "spec.json").read_text())["catalogue"]))
        per[t] = {"files": h, "task_sha256": sha256_text(canon_json(h))}
    combined = sha256_text("".join(per[t]["task_sha256"] for t in sorted(per)))
    doc = {"tasks": per, "combined_sha256": combined}
    (root / "bench" / "commitment.json").write_text(json.dumps(doc, indent=1))
    commit(root / "commitments.log", "bench_freeze", combined, {"n_tasks": len(per), "tasks": sorted(per)})
    return doc


def verify_commitments(root: Path) -> dict:
    doc = json.loads((root / "bench" / "commitment.json").read_text())
    bad = []
    for t, v in doc["tasks"].items():
        d = root / "bench" / TASKS[t]["task_id"]
        for f, h in v["files"].items():
            if f == "catalogue":
                continue
            if sha256_file(d / f) != h:
                bad.append(f"{t}:{f}")
    chain_ok = verify_chain(root / "commitments.log")
    return {"file_hash_mismatches": bad, "hash_chain_ok": chain_ok}


def recount(root: Path, stats: dict) -> dict:
    """Independent recount of pilot counts / modal share / flags from data/samples_pilot.jsonl."""
    rows = [json.loads(l) for l in (root / "data" / "samples_pilot.jsonl").open()]
    mism = []
    for t in TASK_ORDER:
        labs = [r["label"] for r in rows if r["task"] == t]
        att = [x for x in labs if x != "invalid"]
        c = Counter(att)
        mk = c.most_common(1)[0][1] if c else 0
        sec = c.most_common(2)[1][1] if len(c) > 1 else 0
        exp = {"modal_share": mk / max(len(att), 1), "presence_flag": sec / max(len(att), 1) >= 0.10,
               "collapse_flag": mk / max(len(att), 1) >= 0.90, "n_attempted": len(att)}
        for k, v in exp.items():
            if stats[t][k] != v:
                mism.append((t, k, stats[t][k], v))
        if dict(Counter(labs)) != stats[t]["pilot_counts"]:
            mism.append((t, "pilot_counts"))
    return {"n_mismatches": len(mism), "mismatches": mism}


def build_method_out(root: Path, ctx: dict) -> dict:
    examples, cell_examples = [], []
    for t in TASK_ORDER:
        c = TASKS[t]
        st = ctx["pilot_stats"][t]
        a_tab = ctx["stageA"]["table"][t]
        b_tab = ctx["stageB"]["table"][t] if ctx.get("stageB") else None
        modal = a_tab["modal"]
        evA = a_tab["events"][modal]
        evB = b_tab["events"][modal] if b_tab else None
        frlp = {r["algorithm"]: {k: r[k] for k in ("L", "L_corr", "ess", "n_programs", "adherence", "flags")}
                for r in ctx["frlp_cells"] if r["task"] == t and r["half"] == "all" and r["variant"] == "main"}
        sets = json.loads((root / "bench" / c["task_id"] / "frlp_sets.json").read_text())
        for j in frlp:
            frlp[j]["M_j"] = sets[j]["M"]
            frlp[j]["n_attempts"] = sets[j]["n_attempts"]
            frlp[j]["proposal_counts"] = sets[j]["proposal_counts"]
        gate = json.loads((root / "bench" / c["task_id"] / "gate.json").read_text())
        status = "frozen" if t in ctx["frozen"] else ctx["status"].get(t, "not_reached")
        assoc = {x: {"dist": e["association"]["dist"], "n_answers": e["association"]["n_answers"],
                     "n_valid": e["association"]["n_valid"], "n_names_X": e["association"]["n_names_X"],
                     "n_off_catalogue": e["association"]["n_off_catalogue"]} for x, e in a_tab["events"].items()}
        summary = {"task": t, "modal": modal, "modal_share": st["modal_share"], "collapse": st["collapse_flag"],
                   "pass_rate": st["pass_rate"], "build_status": status,
                   "nominations_stageA": evA["nominations"], "nominations_stageB": evB["nominations"] if evB else None,
                   "frlp_L_corr": {j: v["L_corr"] for j, v in frlp.items()}}
        ex = {"input": spec_text(t), "output": json.dumps(summary),
              "metadata_task_id": c["task_id"], "metadata_task": t, "metadata_leetcode_ids": c["leetcode_ids"],
              "metadata_catalogue": [{"mode": m, "display_name": d[0], "mechanism": d[1]} for m, d in c["modes"].items()],
              "metadata_pilot_counts": st["pilot_counts"], "metadata_n_attempted": st["n_attempted"],
              "metadata_pass_rate": st["pass_rate"], "metadata_modal_label": st["modal_label"],
              "metadata_modal_share": st["modal_share"], "metadata_modal_share_ci95": st["modal_share_ci95"],
              "metadata_presence_flag": st["presence_flag"], "metadata_second_share_ci95": st["second_share_ci95"],
              "metadata_collapse_flag": st["collapse_flag"], "metadata_hill1_correct": st["hill1_correct"],
              "metadata_hill_rarefied25": st["hill_rarefied25"], "metadata_hill_rarefied25_ci90": st["hill_rarefied25_ci90"],
              "metadata_other_share": st["other_share"], "metadata_invalid_share": st["invalid_share"],
              "metadata_labeller_source_shares": st["labeller_source_shares"],
              "metadata_association": assoc, "metadata_frlp_baseline": frlp,
              "metadata_frlp_validity": ctx["frlp_validity"]["validity"].get(t),
              "metadata_frlp_coverage": ctx["frlp_validity"]["coverage"].get(t),
              "metadata_nominations_stageA": {x: e["nominations"] for x, e in a_tab["events"].items()},
              "metadata_nominations_stageB": ({x: e["nominations"] for x, e in b_tab["events"].items()} if b_tab else None),
              "metadata_disagreement_stageA": {"D_task": a_tab["D_task"], "D_allK": a_tab["D_allK"],
                                               "pairwise_modal_event": evA["pairwise_agree"]},
              "metadata_disagreement_stageB": ({"D_task": b_tab["D_task"], "D_allK": b_tab["D_allK"],
                                                "pairwise_modal_event": evB["pairwise_agree"]} if b_tab else None),
              "metadata_gate": gate, "metadata_build_status": status,
              "metadata_build_report": json.loads((root / "bench" / c["task_id"] / "build_report.json").read_text()),
              "metadata_llama_pilot": ctx.get("llama", {}).get(t),
              "predict_ladder": "|".join(evA["nominations"]["ladder"]),
              "predict_association": "|".join(evA["nominations"]["association"]),
              "predict_proximity": "|".join(evA["nominations"]["proximity"])}
        if evB:
            ex["predict_ladder_stageB"] = "|".join(evB["nominations"]["ladder"])
            ex["predict_proximity_stageB"] = "|".join(evB["nominations"]["proximity"])
        examples.append(ex)
        for j, v in frlp.items():
            cell_examples.append({
                "input": f"{t} ({c['task_id']}): baseline FRLP of mode '{j}' ({display_name(t, j)}); forced proposal "
                         f"templates {sorted(v['proposal_counts'])}",
                "output": json.dumps({"L": v["L"], "L_corr": v["L_corr"], "ess": v["ess"], "M_j": v["M_j"],
                                      "adherence": v["adherence"], "flags": v["flags"]}),
                "metadata_task": t, "metadata_algorithm": j, "metadata_L": v["L"], "metadata_L_corr": v["L_corr"],
                "metadata_ess": v["ess"], "metadata_M_j": v["M_j"], "metadata_adherence": v["adherence"],
                "metadata_n_attempts": v["n_attempts"], "metadata_proposal_counts": v["proposal_counts"],
                "metadata_flags": v["flags"], "metadata_pilot_share": st["pilot_counts"].get(j, 0) / max(st["n_attempted"], 1),
                "predict_frlp_implied_prob": str((ctx["frlp_validity"]["validity"].get(t) or {}).get("pi", {}).get(j)),
                "predict_uniform_prob": str(1.0 / (len(c["modes"]) + 1))})
    return {"metadata": ctx["metadata"],
            "datasets": [{"dataset": "bench_candidates", "examples": examples},
                         {"dataset": "frlp_baseline_cells", "examples": cell_examples}]}
