#!/usr/bin/env python3
"""STEP 8: COMMIT #2 (pre-ban). Grep audit of every model-fed prompt; per-task predictions (D, MOVABLE and the
predicted compliance class, E_t with exact binomial CIs, opening margin, rivals, four landing forecasts with
defined flags); the frozen analysis code; all hash-chained before any ban prompt is built."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg import (ALL_TASKS, ALPHAS, BINOM_ALPHA, COMPLY_THRESH, DATA_DIR, ESCAPE_EXCESS, ESCAPE_PASS_FRAC,
                 ESCAPE_SEEDS, P0_FLOOR, PRED_DIR, RESULTS_DIR, ROOT, read_json, read_jsonl, setup_logging,
                 sha256_file, write_json)
import predictors as PR
import prompts_gemma as PG
from commit import commit, verify_chain

EDGE_RULES = {
    "all_one_compliance_class": "BA untestable; Spearman(E_t, A_t) alone",
    "single_predicted_class": "BA = 0.5 ('no discrimination'); disconfirming only if both outcome classes exist",
    "ties_in_E_t": "average ranks",
    "no_confirmed_escape_anywhere": "every prediction 'immovable'; C3a untestable as a discriminator; stage-1 "
                                    "off-default shares and PN shares reported as continuous predictors",
    "disputed_labels": "never counted as default, off-default or avoidance; fallback labels in a sensitivity",
    "flagged_tasks": "R6 (off-catalogue modal default linear_scan; ban names X_q): C3a also reported without it",
}


def grep_audit() -> dict[str, Any]:
    reg = read_jsonl(DATA_DIR / "prompts_fed.jsonl")
    texts = [(r["kind"], r["text"]) for r in reg]
    aud = PG.grep_audit(texts, list(ALL_TASKS))
    # planted positive (T4): a ban prompt must be caught, a twin must pass
    planted = PG.grep_audit([("planted_ban", PG.TEMPLATES["W3"][0].format(X=PG.display("T2", "dijkstra"))),
                             ("twin", PG.p_twin("T2", "dijkstra", "W3")["text"])], list(ALL_TASKS))
    aud["planted_check"] = {"n_hits": planted["n_hits"], "caught_planted_only": planted["n_hits"] >= 1 and all(
        h["kind"] == "planted_ban" for h in planted["hits"])}
    aud["kinds"] = dict(__import__("collections").Counter(k for k, _ in texts))
    return aud


def proximity_cached(t: str, D: str) -> dict[str, Any]:
    p = RESULTS_DIR / "proximity.json"
    cache = read_json(p) if p.exists() else {}
    key = f"{t}|{D}"
    if key not in cache:
        cache[key] = PR.proximity(t, D)
        write_json(p, cache)
    return cache[key]


def task_record(t: str, ladder: dict[str, Any]) -> dict[str, Any]:
    conf = PR.confirm(t)
    D = conf["D"]
    lad = ladder.get(t, {"defined": False})
    rv = PR.rivals(t, D, lad)
    fc = {"push_landing": PR.push_landing(t, conf),
          "opening_ladder": {"defined": bool(lad.get("defined")), "distribution": lad.get("distribution", {}),
                             "top1": lad.get("top1")},
          "association": PR.association(t, D),
          "proximity": proximity_cached(t, D)}
    return {"D": D, "D_display": PG.display(t, D), "D_g": PR.D_of(t), "D_changed_after_twin": D != PR.D_of(t),
            "survivors": PR.survivors(t, D), "movable": conf["movable"],
            "predicted_class": "obeys (A_t >= 0.5)" if conf["movable"] else "fails (A_t < 0.5)",
            "predicted_C": int(conf["movable"]), "E_t_1": conf["E_alpha"].get("a1"), "E_t_2": conf["E_alpha"].get("a2"),
            "E_t": conf["E_t"], "E_t_ci95_exact": conf["E_t_ci95"], "n_directions_run": conf["n_directions_run"],
            "confirmed": conf["confirmed"], "p0": conf["p0"], "twin_pass": conf["twin_pass"], "n_twin": conf["n_twin"],
            "stage1_cells": conf["cells"], "confirm_cells": conf["confirm_cells"],
            "opening_margin": lad.get("margin"), "opening_margin_ownD": lad.get("margin_ownD_sensitivity"),
            "rivals": rv, "forecasts": fc}


def main() -> None:
    setup_logging("commit2")
    assert not (PRED_DIR / "commit_preban.json").exists(), "commit #2 already made"
    aud = grep_audit()
    write_json(RESULTS_DIR / "grep_audit.json", aud)
    assert aud["pass"] and aud["planted_check"]["caught_planted_only"], f"grep audit failed: {aud['hits'][:3]}"
    ladder = read_json(RESULTS_DIR / "opening_ladder.json") if (RESULTS_DIR / "opening_ladder.json").exists() else {}
    tasks = {}
    for t in ALL_TASKS:
        tasks[t] = task_record(t, ladder)
        logger.info(f"{t}: D={tasks[t]['D']} E_t={tasks[t]['E_t']} movable={tasks[t]['movable']} "
                    f"margin={tasks[t]['opening_margin']}")
    c1 = read_json(PRED_DIR / "commit1.json")
    qr = read_json(RESULTS_DIR / "qwen_ratio.json")
    labels_sha = sha256_file(DATA_DIR / "labels.jsonl")
    rec = {"tasks": tasks,
           "escape_rule": {"excess": ESCAPE_EXCESS, "pass_frac": ESCAPE_PASS_FRAC, "binom_alpha": BINOM_ALPHA,
                           "p0_floor": P0_FLOOR, "stage1_N": 10, "confirm_N": 30, "seeds": list(ESCAPE_SEEDS),
                           "alphas": list(ALPHAS),
                           "off_default": "label not in {D, invalid, disputed} over all attempts"},
           "compliance_rule": {"A_t": "catalogue-only avoidance = #(ban label in catalogue minus {D}) / N_ban (N=100)",
                               "C_t": f"1[A_t >= {COMPLY_THRESH}]", "prediction": "MOVABLE (E_t > 0) -> C_t = 1"},
           "c3a_rule": {"confirmed": "BA >= 0.8 AND Fisher two-sided p < 0.05 AND Spearman rho >= 0.5",
                        "disconfirmed": "BA <= 0.6", "otherwise": "INCONCLUSIVE"},
           "edge_rules": EDGE_RULES,
           "rival_signs": {"twin_modal_share": -1, "twin_modal_share_correct": -1, "opening_margin": -1,
                           "can_max": 1, "t13_off": 1, "novelty_off": 1, "pn_a1_off": 1, "pn_a2_off": 1},
           "model": c1["model"], "revision": c1["revision"], "weights": c1["weights"],
           "screen_json_sha256": sha256_file(RESULTS_DIR / "screen.json"),
           "qwen_ratio_sha256": sha256_file(RESULTS_DIR / "qwen_ratio.json"),
           "r_Q": qr["r_Q"], "r_Q_ox": qr["r_Q_ox"], "unit": "outlier-excluded (src/units.py, deviation D3)",
           "banfree_labels_sha256_at_commit": labels_sha, "B": c1["B"], "caps": c1["caps"]}
    p = PRED_DIR / "commit_preban.json"
    write_json(p, rec)
    shutil.copy2(ROOT / "src" / "analysis_c3.py", PRED_DIR / "analysis_c3.py")
    c = commit("commit2_preban", [p, PRED_DIR / "analysis_c3.py", RESULTS_DIR / "grep_audit.json",
                                  RESULTS_DIR / "screen.json", RESULTS_DIR / "qwen_ratio.json",
                                  PRED_DIR / "commit1.json"],
               note="pre-ban predictions; no ban prompt has been built or fed")
    v = verify_chain()
    write_json(RESULTS_DIR / "commit_chain_verify_after_commit2.json", v)
    logger.info(f"commit #2 {c['hash'][:12]}; chain ok={v['ok']}; movable={[t for t in tasks if tasks[t]['movable']]}")


if __name__ == "__main__":
    main()
