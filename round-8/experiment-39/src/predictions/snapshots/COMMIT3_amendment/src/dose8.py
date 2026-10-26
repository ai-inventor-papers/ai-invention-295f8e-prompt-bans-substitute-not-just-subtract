#!/usr/bin/env python3
"""Stage 2 (CPU part) and COMMIT #1: token maps, composed predictions, dose table, per-slot replay predictions,
placebo positions, class-uniform draws, the MAE noise ceiling and the T1 validation verdict.

Reads: data/samples.jsonl + labels.jsonl (twins A0), data/continuations.jsonl + continuation_labels.jsonl (MAP rows),
cache/nodes/<unit>_<node>.json (teacher-forced top-64 logits per template). Writes predictions/commit1_dose_table.json
(committed) and results/dose_table_view.json, results/tokenmap.json.
"""

from __future__ import annotations

import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfg8 import (CACHE_DIR, CONT_LABELS, CONTS, DOSE_GRID, ENTROPY_WINDOW, LABELS, PRED_DIR, RESULTS_DIR,  # noqa
                  SAMPLES, SEED_CLASS_UNIFORM, SEED_RANDOM_WINDOW, TEMPLATES, THRESH, TOPK_DOSE, UNITS, read_json,
                  read_jsonl, slot_template, slot_ukey, u_stream, utc_now, write_json, log_deviation)
import predict8 as PR  # noqa: E402
import units8 as U8  # noqa: E402

NODE_DIR = CACHE_DIR / "nodes"
BAD = {"invalid", "no_code", "label_error", "extraction"}
LOCATED_ORDER = ("T10", "T1", "B3", "A3", "B6", "G")


# ------------------------------------------------------------------------------------------------ labels/classes
def classes_of(unit: str) -> list[str]:
    return list(UNITS[unit]["catalogue"]) + ["other", "invalid"]


def cls(unit: str, label: str | None) -> str:
    if label is None or label in BAD:
        return "invalid"
    if label in UNITS[unit]["catalogue"]:
        return label
    return "other"


def load_labels() -> dict[str, dict[str, Any]]:
    """Frozen labels; rows resolved by the judge adjudication (results/adjudicated_labels.json) take that label."""
    out = {r["sid"]: r for r in read_jsonl(LABELS)}
    out.update({r["sid"]: r for r in read_jsonl(CONT_LABELS)})
    adj_p = RESULTS_DIR / "adjudicated_labels.json"
    if adj_p.exists():
        for sid, lab in read_json(adj_p).items():
            if sid in out:
                out[sid] = {**out[sid], "label": lab, "labeller_source": "adjudicated"}
    return out


def twin_rows(unit: str, labels: dict[str, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    out = {}
    for r in read_jsonl(SAMPLES):
        if r["unit"] == unit and r["arm"] == "A0":
            L = labels.get(r["sid"], {})
            r["label"] = L.get("label")
            r["cls"] = cls(unit, L.get("label"))
            r["passed"] = bool(L.get("passed"))
            out[r["slot"]] = r
    return out


def node_info(unit: str, node: str) -> dict[str, Any] | None:
    p = NODE_DIR / f"{unit}_{node}.json"
    return read_json(p) if p.exists() else None


def token_maps(unit: str, node: str, labels: dict[str, dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Phat / Pfail / Pcorrect / Prev per mapped token at one node, from its K continuations."""
    C = classes_of(unit)
    default = UNITS[unit]["default"]
    by_tok: dict[int, list[tuple[str, bool]]] = defaultdict(list)
    for r in read_jsonl(CONTS):
        if r.get("arm") != "MAP" or r["unit"] != unit or r.get("node") != node:
            continue
        L = labels.get(r["sid"])
        if L is None:
            continue
        by_tok[int(r["token"])].append((cls(unit, L.get("label")), bool(L.get("passed"))))
    out = {}
    node_classes = sorted({c for lst in by_tok.values() for c, _ in lst})
    for t, lst in by_tok.items():
        labs = [c for c, _ in lst]
        ph = np.array([sum(1 for c in labs if c == k) for k in C], dtype=float) / len(labs)   # plug-in (D05)
        ph_s = PR.phat_vec(labs, node_classes)                 # pseudo-count 0.5 over the node's observed classes
        ph_s_full = np.zeros(len(C))
        for k, v in zip(node_classes, ph_s):
            ph_s_full[C.index(k)] = v
        corr = np.zeros(len(C))
        for c, ok in lst:
            if ok:
                corr[C.index(c)] += 1
        corr = corr / max(len(lst), 1)
        com = PR.committal(ph_s_full, C)
        off = com is not None and com != default
        prev = (sum(1 for c in labs if c == default) / len(labs)) if off else 0.0
        out[t] = {"phat": ph, "phat_smoothed": ph_s_full, "pfail": 1.0 - sum(ok for _, ok in lst) / len(lst),
                  "pcorrect": corr, "n": len(lst),
                  "counts": dict(Counter(labs)), "committal": com, "off_default": off, "prev": prev}
    return out


def resid_of(tmap: dict[int, dict[str, Any]], weights: dict[int, float], C: int) -> dict[str, Any]:
    tot = sum(weights.get(t, 0.0) for t in tmap) or 1.0
    ph = sum(weights.get(t, 0.0) * m["phat"] for t, m in tmap.items()) / tot if tmap else np.full(C, 1.0 / C)
    pf = sum(weights.get(t, 0.0) * m["pfail"] for t, m in tmap.items()) / tot if tmap else 0.0
    pc = sum(weights.get(t, 0.0) * m["pcorrect"] for t, m in tmap.items()) / tot if tmap else np.zeros(C)
    return {"phat": ph, "pfail": pf, "pcorrect": pc, "prev": 0.0}


STRING_CLASS = {"T10": [(r"(?i)\bdfs|depth", "dfs"), (r"(?i)\bbfs|breadth|queue|deque", "bfs"),
                        (r"(?i)union|find|parent|disjoint|dsu|root", "union_find")]}


def string_class(unit: str, s: str) -> str | None:
    for pat, c in STRING_CLASS.get(unit, []):
        if re.search(pat, s):
            return c
    return None


# ------------------------------------------------------------------------------------------------ composition
BAN: dict[str, set[int]] = {}        # amendment (COMMIT #3): tokens removed at a dosed node, keyed by node id


def compose(z: tuple, T: float, tmap: dict[int, dict[str, Any]], resid: dict[str, Any], C: int,
            second: dict[int, dict[str, Any]] | None = None, k: int = TOPK_DOSE,
            ban: set[int] | None = None, ban2: set[int] | None = None) -> dict[str, Any]:
    """F_T at one node and template: attempted shares, correct shares, fail mass, reversion mass, off-token mass.
    ban: tokens removed from this node's top-k (renormalised over the rest); ban2: the same at the second node."""
    ids, p = PR.dist_topk(z, T, k)
    if ban:
        keep = np.array([int(t) not in ban for t in ids.tolist()])
        if keep.any():
            ids, p = ids[keep], p[keep] / p[keep].sum()
    F = np.zeros(C)
    Fc = np.zeros(C)
    fail = rev = off = 0.0
    for t, pt in zip(ids.tolist(), p.tolist()):
        if second is not None and t in second:
            sub = compose(second[t]["z"], T, second[t]["tmap"], second[t]["resid"], C, None, k, ban=ban2)
            F += pt * sub["F"]
            Fc += pt * sub["Fc"]
            fail += pt * sub["fail"]
            rev += pt * sub["rev"]
            off += pt * sub["off"]
            continue
        m = tmap.get(t, resid)
        F += pt * m["phat"]
        Fc += pt * m["pcorrect"]
        fail += pt * m["pfail"]
        if m.get("off_default"):
            off += pt
            rev += pt * m["prev"]
    return {"F": F, "Fc": Fc, "fail": fail, "rev": rev, "off": off}


class UnitModel:
    """Everything needed to predict a unit's cell at any fork dose (per template, averaged over templates)."""

    def __init__(self, unit: str, labels: dict[str, dict[str, Any]]):
        self.unit = unit
        self.C = classes_of(unit)
        self.default = UNITS[unit]["default"]
        self.twin = twin_rows(unit, labels)
        self.nodes = []
        for nd in U8.nodes(unit):
            info = node_info(unit, nd["id"])
            if info is None:
                continue
            tm = token_maps(unit, nd["id"], labels)
            self.nodes.append({"id": nd["id"], "pos": nd["pos"], "info": info, "tmap": tm})
        self.second = None
        if unit == "T10":
            info11 = node_info(unit, "n11")
            tm11 = token_maps(unit, "n11", labels) if info11 else {}
            self.second = {"info": info11, "tmap": tm11}
        # off-opening composition q_rest from the twin
        on = [s for s, r in self.twin.items() if r.get("reached_decision")]
        offs = [r for s, r in self.twin.items() if not r.get("reached_decision")]
        self.q_rest = PR.phat_vec([r["cls"] for r in offs], self.C) if offs else np.full(len(self.C), 1 / len(self.C))
        self.q_rest_fail = (1 - np.mean([r["passed"] for r in offs])) if offs else 0.0
        self.q_rest_corr = np.zeros(len(self.C))
        for r in offs:
            if r["passed"]:
                self.q_rest_corr[self.C.index(r["cls"])] += 1.0 / len(offs)
        self.n_on = len(on)

    def second_tokens(self) -> set[int]:
        """T10 index-10 tokens that trigger the index-11 dose: ' def' (n11 is pre-registered as its second decision;
        at T = 1 it is followed by ' find' 97% of the time, so its T = 1 map reads union-find) plus every
        non-committal token that has a teacher-forced index-11 distribution (mass >= 1e-4)."""
        if self.unit != "T10" or not self.nodes:
            return set()
        nd = self.nodes[0]
        out = {U8.T10_DEF}
        for t, m in nd["tmap"].items():
            if m["committal"] is None and str(t) in nd["info"].get("second_tf", {}):
                out.add(int(t))
        return out

    def _node_parts(self, nd: dict[str, Any], w: str) -> tuple[tuple, dict, dict, dict | None, float]:
        tf = nd["info"]["tf"][w]
        z = (tf["top_ids"], tf["top_z"])
        pooled = {int(k): v for k, v in nd["info"]["pooled_p20"].items()}
        resid = resid_of(nd["tmap"], pooled, len(self.C))
        second = None
        if self.unit == "T10" and nd["id"] == "n10" and self.second and self.second["info"]:
            second = {}
            for t, m in nd["tmap"].items():
                if t not in self.second_tokens():
                    continue
                if t == U8.T10_DEF:
                    tf11 = self.second["info"]["tf"][w]
                    p11 = {int(k): v for k, v in self.second["info"]["pooled_p20"].items()}
                    second[t] = {"z": (tf11["top_ids"], tf11["top_z"]), "tmap": self.second["tmap"],
                                 "resid": resid_of(self.second["tmap"], p11, len(self.C))}
                elif str(t) in nd["info"].get("second_tf", {}):
                    tf2 = nd["info"]["second_tf"][str(t)][w]
                    tm2 = {}
                    for t2 in tf2["top_ids"][:TOPK_DOSE]:
                        j2 = tf2["top_ids"].index(t2)
                        c2 = string_class(self.unit, tf2.get("top_str", [""] * 64)[j2] if j2 < 24 else "")
                        if c2 is not None:
                            ph = PR.phat_vec([c2] * 10, self.C)
                            tm2[int(t2)] = {"phat": ph, "pfail": m["pfail"], "pcorrect": ph * (1 - m["pfail"]),
                                            "off_default": c2 != self.default, "prev": 0.0, "committal": c2}
                    second[t] = {"z": (tf2["top_ids"], tf2["top_z"]), "tmap": tm2,
                                 "resid": {"phat": m["phat"], "pfail": m["pfail"], "pcorrect": m["pcorrect"],
                                           "prev": 0.0}}
        w_c = math.exp(tf["path_logprob"])
        return z, nd["tmap"], resid, second, w_c

    def predict(self, T: float) -> dict[str, Any]:
        C = len(self.C)
        P = np.zeros(C)
        Pc = np.zeros(C)
        fail = rev = off = on = 0.0
        for w in TEMPLATES:
            Pw = np.zeros(C)
            Pcw = np.zeros(C)
            fw = rw = ow = ws = 0.0
            for nd in self.nodes:
                z, tm, resid, second, w_c = self._node_parts(nd, w)
                r = compose(z, T, tm, resid, C, second, ban=BAN.get(f"{self.unit}:{nd['id']}"),
                            ban2=BAN.get(f"{self.unit}:n11"))
                Pw += w_c * r["F"]
                Pcw += w_c * r["Fc"]
                fw += w_c * r["fail"]
                rw += w_c * r["rev"]
                ow += w_c * r["off"]
                ws += w_c
            ws = min(ws, 1.0)
            Pw += (1 - ws) * self.q_rest
            Pcw += (1 - ws) * self.q_rest_corr
            fw += (1 - ws) * self.q_rest_fail
            P += Pw / len(TEMPLATES)
            Pc += Pcw / len(TEMPLATES)
            fail += fw / len(TEMPLATES)
            rev += rw / len(TEMPLATES)
            off += ow / len(TEMPLATES)
            on += ws / len(TEMPLATES)
        return {"P": P, "Pc": Pc, "fail": fail, "reversion": rev / off if off > 1e-12 else 0.0, "off_mass": off,
                "on_opening": on}

    def off_default_share(self, P: np.ndarray) -> float:
        return float(sum(P[i] for i, c in enumerate(self.C) if c not in (self.default, "other", "invalid")))

    # ---------------------------------------------------------------- per-slot replay
    def slot_replay(self, s: int, T: float, k: int = TOPK_DOSE) -> dict[str, Any]:
        """Predicted class distribution of slot s under a fork dose T (identity property for unchanged tokens)."""
        r = self.twin[s]
        Cn = len(self.C)
        onehot = np.zeros(Cn)
        onehot[self.C.index(r["cls"])] = 1.0
        if not r.get("reached_decision") or r.get("dec_top_ids") is None:
            return {"dist": onehot, "changed": False, "token": None, "dosed": False}
        u = u_stream(*slot_ukey(self.unit, s))
        dpos = r["decision_pos"]
        nd_id = U8.nodes(self.unit)[r["decision_node"]]["id"]
        bn = BAN.get(f"{self.unit}:{nd_id}")
        if bn:
            ids_k = [t for t in r["dec_top_ids"][:k] if t not in bn]
            zs = [z for t, z in zip(r["dec_top_ids"][:k], r["dec_top_z"][:k]) if t not in bn]
            t_new = PR.replay_token(ids_k, zs, float(u[dpos]), T, len(ids_k)) if ids_k else r["decision_token"]
        else:
            t_new = PR.replay_token(r["dec_top_ids"], r["dec_top_z"], float(u[dpos]), T, k)
        if t_new == r["decision_token"]:
            return {"dist": onehot, "changed": False, "token": t_new, "dosed": True, "pass": r["passed"]}
        nd = next((n for n in self.nodes if n["id"] == U8.nodes(self.unit)[r["decision_node"]]["id"]), None)
        if nd is None:
            return {"dist": onehot, "changed": True, "token": t_new, "dosed": True}
        m = nd["tmap"].get(t_new)
        if m is None:
            m = resid_of(nd["tmap"], {int(a): b for a, b in nd["info"]["pooled_p20"].items()}, Cn)
            m["committal"] = None
        dist = m["phat"]
        if self.unit == "T10" and t_new in self.second_tokens() and self.second and self.second["info"]:
            # second dose at index 11: composition over index-11 tokens under this slot's template
            _, _, _, second, _ = self._node_parts(nd, slot_template(s))
            if second and t_new in second:
                sub = compose(second[t_new]["z"], T, second[t_new]["tmap"], second[t_new]["resid"], Cn, None, k,
                              ban=BAN.get(f"{self.unit}:n11"))
                dist = sub["F"]
        return {"dist": np.asarray(dist), "changed": True, "token": t_new, "dosed": True,
                "pfail": float(m.get("pfail", 0.0))}

    def replay_cell(self, T: float) -> dict[str, Any]:
        dists, changed = [], 0
        per = {}
        for s in sorted(self.twin):
            rr = self.slot_replay(s, T)
            dists.append(rr["dist"])
            changed += int(rr["changed"])
            per[s] = {"token": rr["token"], "changed": rr["changed"],
                      "pred": self.C[int(np.argmax(rr["dist"]))], "dist": np.round(rr["dist"], 4).tolist()}
        return {"P": np.mean(dists, 0) if dists else np.zeros(len(self.C)), "n_changed": changed, "per_slot": per}


# ------------------------------------------------------------------------------------------------ doses
def dose_table(M: UnitModel, role: str) -> dict[str, Any]:
    curve = {T: M.predict(T) for T in DOSE_GRID}
    share = {T: M.off_default_share(curve[T]["P"]) for T in DOSE_GRID}
    mx = max(share.values())          # attainable maximum over the grid (the curve is not monotone in T)
    T_mx = max(share, key=lambda T: share[T])
    if role == "collapsed":
        t1, t2 = THRESH["attempted_d1"], THRESH["attempted_d2"]
        if mx >= t2:
            d1, d2 = PR.pick_dose(share, t1), PR.pick_dose(share, t2)
            tgt1 = t1
            rule = "targets 0.20 / 0.40 attempted off-default"
        else:
            d2 = PR.pick_dose(share, 0.95 * mx)
            d1 = PR.pick_dose(share, 0.5 * mx) if mx < t1 else PR.pick_dose(share, t1)
            tgt1 = 0.5 * mx if mx < t1 else t1
            rule = f"attainable max {mx:.3f} < 0.40: d2 = 0.95 x max, d1 = " + ("half of max" if mx < t1 else "0.20")
    else:
        tw = share[1.0]
        if mx >= THRESH["minority_d1"]:
            d1 = PR.pick_dose(share, THRESH["minority_d1"])
            tgt1 = THRESH["minority_d1"]
            rule = "d1: minority share 0.5"
        else:
            d1 = PR.pick_dose(share, (tw + mx) / 2)
            tgt1 = (tw + mx) / 2
            rule = f"0.5 unattainable (max {mx:.3f}): d1 at midpoint of twin {tw:.3f} and max"
        d2 = PR.pick_dose(share, 0.95 * mx) if mx > tw else DOSE_GRID[-1]
    d1 = d1 or DOSE_GRID[-1]
    d2 = d2 or DOSE_GRID[-1]
    if d2 < d1:
        d1, d2 = d2, d1
    return {"d1": d1, "d2": d2, "rule": rule, "target_share_d1": tgt1, "T_at_max": T_mx, "share_curve": share, "max_share": mx, "twin_pred_share": share[1.0],
            "curve": {T: {"P": curve[T]["P"].tolist(), "Pc": curve[T]["Pc"].tolist(), "fail": curve[T]["fail"],
                          "reversion": curve[T]["reversion"], "on_opening": curve[T]["on_opening"]}
                      for T in DOSE_GRID}}


def committed_tokens(M: UnitModel) -> dict[int, dict[str, list[int]]]:
    """Per node index and decision class: the most probable committal token (by template-averaged T = 1 mass) whose
    continuations are not all failing; T10 also gets ' def' + <index-11 token> pairs for classes reached via n11."""
    out: dict[int, dict[str, list[int]]] = {}
    for ni, nd in enumerate(M.nodes):
        pooled = {int(k): v for k, v in nd["info"]["pooled_p20"].items()}
        by_class: dict[str, list[tuple[float, int]]] = defaultdict(list)
        for t, m in nd["tmap"].items():
            if m["committal"] is not None and m["committal"] not in ("other", "invalid") and m["pfail"] < 1.0:
                by_class[m["committal"]].append((pooled.get(t, 0.0), t))
        out[ni] = {c: [max(lst)[1]] for c, lst in by_class.items()}
    if M.unit == "T10" and M.second and M.second["tmap"]:
        p11 = {int(k): v for k, v in M.second["info"]["pooled_p20"].items()}
        best: dict[str, tuple[float, int]] = {}
        for t, m in M.second["tmap"].items():
            c = m["committal"]
            if c is None or c in ("other", "invalid") or m["pfail"] >= 1.0:
                continue
            if c not in best or p11.get(t, 0.0) > best[c][0]:
                best[c] = (p11.get(t, 0.0), t)
        for c, (_, t) in best.items():
            if c not in out.get(0, {}):
                out.setdefault(0, {})[c] = [U8.T10_DEF, t]
    return out


def placebo_positions(M: UnitModel) -> dict[str, Any]:
    ents = []
    jstar, rpos = {}, {}
    width = 2 if M.unit == "T10" else 1
    for s, r in sorted(M.twin.items()):
        e = r.get("entropy") or []
        ents.extend(e[:ENTROPY_WINDOW])
        if e:
            jstar[s] = int(np.argmax(e[:ENTROPY_WINDOW]))
        dec = set()
        if r.get("reached_decision"):
            dec = {r["decision_pos"]} | ({r["decision_pos"] + 1} if M.unit == "T10" else set())
        rng = np.random.default_rng(SEED_RANDOM_WINDOW + s)
        cand = [j for j in range(ENTROPY_WINDOW - width + 1) if not any((j + d) in dec for d in range(width))]
        j0 = int(rng.choice(cand))
        rpos[s] = [j0 + d for d in range(width)]
    q90 = float(np.percentile(ents, 90)) if ents else float("nan")
    return {"q90": q90, "jstar": jstar, "rpos": rpos, "width": width, "n_entropy_values": len(ents)}


def t1_validation(M: UnitModel) -> dict[str, Any]:
    nd = M.nodes[0]
    best = []
    for t, m in nd["tmap"].items():
        cnt = m["counts"]
        n_off = sum(v for c, v in cnt.items() if c not in (M.default, "other", "invalid"))
        best.append({"token": t, "n": m["n"], "n_off_attempted": n_off, "pass_rate": 1 - m["pfail"]})
    ok = [b for b in best if b["n_off_attempted"] >= THRESH["t1_valid_k"] and b["pass_rate"] >= THRESH["t1_valid_pass"]]
    return {"validated": bool(ok), "qualifying": ok, "per_token": sorted(best, key=lambda b: -b["n_off_attempted"])}


def build_commit1(units: list[str]) -> dict[str, Any]:
    labels = load_labels()
    out: dict[str, Any] = {"utc": utc_now(), "units": {}}
    models = {}
    t1v = None
    for u in units:
        if u not in LOCATED_ORDER:
            continue
        M = UnitModel(u, labels)
        if not M.nodes:
            log_deviation(f"D_nomap_{u}", f"no token map for {u}; unit dropped from K1 predictions", "major")
            continue
        models[u] = M
        if u == "T1":
            t1v = t1_validation(M)
    roles = {u: UNITS[u]["role"] for u in models}
    if "T1" in models and not (t1v or {}).get("validated"):
        roles["T1"] = "boundary"
    for u, M in models.items():
        role = roles[u]
        if role == "boundary":
            out["units"][u] = {"role": "boundary", "t1_validation": t1v}
            continue
        dt = dose_table(M, role)
        pp = placebo_positions(M)
        ctn = committed_tokens(M)
        ct = ctn.get(0, {})
        dec_classes = sorted({c for d in ctn.values() for c in d})
        cs = {s: dec_classes[int(np.random.default_rng(SEED_CLASS_UNIFORM + s).integers(len(dec_classes)))]
              for s in range(50)} if dec_classes else {}
        arms = {}
        base = M.predict(1.0)
        for name, T in (("A9", dt["d1"]), ("A10", dt["d2"])):
            pr = M.predict(T)
            rp = M.replay_cell(T)
            arms[name] = {"T": T, "attempted": dict(zip(M.C, np.round(pr["P"], 5).tolist())),
                          "correct": dict(zip(M.C, np.round(pr["Pc"], 5).tolist())),
                          "pass_cost": float(pr["fail"] - base["fail"]), "reversion": pr["reversion"],
                          "off_default_attempted": M.off_default_share(pr["P"]),
                          "replay": {"attempted": dict(zip(M.C, np.round(rp["P"], 5).tolist())),
                                     "n_changed": rp["n_changed"], "per_slot": rp["per_slot"]}}
        # class-uniform forcing prediction
        Cn = len(M.C)
        dists = []
        for s in range(50):
            r = M.twin.get(s)
            if r is None:
                continue
            if not r.get("reached_decision") or s not in cs:
                oh = np.zeros(Cn)
                oh[M.C.index(r["cls"])] = 1
                dists.append(oh)
                continue
            node_i = r["decision_node"] if 0 <= r["decision_node"] < len(M.nodes) else 0
            toks = ctn.get(node_i, {}).get(cs[s])
            if not toks:
                oh = np.zeros(Cn)
                oh[M.C.index(r["cls"])] = 1
                dists.append(oh)
                continue
            if M.unit == "T10" and len(toks) == 2:
                m = M.second["tmap"].get(toks[1])
            else:
                m = M.nodes[node_i]["tmap"].get(toks[0])
            dists.append(m["phat"] if m else np.full(Cn, 1 / Cn))
        arms["A11"] = {"class_draws": cs, "tokens": ct, "tokens_by_node": {str(k): v for k, v in ctn.items()},
                       "attempted": dict(zip(M.C, np.round(np.mean(dists, 0), 5).tolist())) if dists else {}}
        # placebos: per-slot predicted (twin label unless the position equals the decision index)
        for name, pos in (("A7", pp["jstar"]), ("A8", pp["rpos"])):
            hits, dists = 0, []
            for s, r in M.twin.items():
                ps = pos.get(s)
                ps = [ps] if isinstance(ps, int) else (ps or [])
                hit = r.get("reached_decision") and r["decision_pos"] in ps
                hits += int(bool(hit))
                if hit:
                    dists.append(M.slot_replay(s, dt["d2"])["dist"])
                else:
                    oh = np.zeros(Cn)
                    oh[M.C.index(r["cls"])] = 1
                    dists.append(oh)
            arms[name] = {"T": dt["d2"], "hits_decision": hits,
                          "attempted": dict(zip(M.C, np.round(np.mean(dists, 0), 5).tolist()))}
        # entropy check (c): twin decision-token entropy vs q90
        dH = [r["decision_H1"] for r in M.twin.values() if r.get("decision_H1") is not None]
        below = float(np.mean([h < pp["q90"] for h in dH])) if dH else None
        g_extra = {}
        if u == "G":
            nd = M.nodes[0]
            g_extra = {"pass_cost_terms": {}, "queue_term": None}
            for w in TEMPLATES:
                tf = nd["info"]["tf"][w]
                ids, p = PR.dist_top_from_saved(tf["top_ids"], tf["top_z"], dt["d2"], TOPK_DOSE)
                for t, pt in zip(ids.tolist(), p.tolist()):
                    m = nd["tmap"].get(t)
                    if m:
                        g_extra["pass_cost_terms"][str(t)] = g_extra["pass_cost_terms"].get(str(t), 0) + \
                            pt * m["pfail"] / len(TEMPLATES)
            g_extra["queue_term"] = g_extra["pass_cost_terms"].get("15204")
            g_extra["sum_pi_Pfail_d2"] = float(sum(g_extra["pass_cost_terms"].values()))
        out["units"][u] = {"role": role, "classes": M.C, "dose": {k: dt[k] for k in ("d1", "d2", "rule", "max_share",
                                                                                     "twin_pred_share",
                                                                                     "target_share_d1")},
                           "share_curve": dt["share_curve"], "q90": pp["q90"], "jstar": pp["jstar"],
                           "rpos": pp["rpos"], "entropy_check_c": {"twin_dec_H_below_q90_frac": below, "n": len(dH)},
                           "arms": arms, "twin_pred": {"attempted": dict(zip(M.C, np.round(base["P"], 5).tolist())),
                                                       "fail": base["fail"]},
                           "n_twin_on_opening": M.n_on, "q_rest": dict(zip(M.C, np.round(M.q_rest, 4).tolist())),
                           "token_map": {str(nd["id"]): {str(t): {"counts": m["counts"], "committal": m["committal"],
                                                                  "pfail": m["pfail"], "n": m["n"],
                                                                  "str": nd["info"]["map_token_str"].get(str(t))}
                                                         for t, m in nd["tmap"].items()} for nd in M.nodes},
                           **({"token_map_n11": {str(t): {"counts": m["counts"], "committal": m["committal"],
                                                          "pfail": m["pfail"], "n": m["n"]}
                                                 for t, m in M.second["tmap"].items()}} if M.second else {}),
                           **g_extra}
        if u == "T1":
            out["units"][u]["t1_validation"] = t1v
    # boundary window dose = T10's d2
    d2_t10 = out["units"].get("T10", {}).get("dose", {}).get("d2")
    out["boundary_window_T"] = d2_t10
    if "T10" in models:
        out["units"]["T10"]["second_dose_tokens"] = sorted(models["T10"].second_tokens())
    out["roles"] = roles
    # MAE noise ceiling over located (non-boundary) units: cells {d1, d2} x classes
    preds = []
    for u, e in out["units"].items():
        if e.get("role") == "boundary":
            continue
        for a in ("A9", "A10"):
            preds.append(np.array([e["arms"][a]["attempted"][c] for c in e["classes"]]))
    out["mae_noise_ceiling"] = {"P_mae_le_0.10_if_true": PR.mae_noise_ceiling(preds) if preds else None,
                                "n_cells": len(preds), "draws": 10000, "N": 50}
    per_unit_nc = {}
    for u, e in out["units"].items():
        if e.get("role") == "boundary":
            continue
        pu = [np.array([e["arms"][a]["attempted"][c] for c in e["classes"]]) for a in ("A9", "A10")]
        per_unit_nc[u] = PR.mae_noise_ceiling(pu, draws=4000)
    out["mae_noise_ceiling"]["per_unit"] = per_unit_nc
    return out


if __name__ == "__main__":
    import json
    units = sys.argv[1].split(",") if len(sys.argv) > 1 else list(LOCATED_ORDER)
    res = build_commit1(units)
    print(json.dumps({u: {k: v for k, v in e.items() if k in ("role", "dose", "q90")} for u, e in res["units"].items()},
                     indent=1, default=str))
