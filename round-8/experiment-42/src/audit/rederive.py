#!/usr/bin/env python3
"""Independent standard-library re-derivation of the headline numbers from the raw label rows (data/labels.jsonl),
compared with results/analysis.json; plus placebos that must FAIL (within-slot cell-label swaps destroy the paired
contrasts; the slot-shuffled unpaired version is reported beside the paired test). No numpy, no project imports."""

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S50 = [(w, k) for w in ("W1", "W2", "W3", "W4", "W5") for k in range(10)]
S30 = [(w, k) for w in ("W1", "W2", "W3", "W4", "W5") for k in range(6)]
DFS_CELLS = {"P-DAS-dfs", "G1b", "F-DAS-r4-dfs-1.0", "F-DiM-dfs", "REV-DAS", "REV-FULL"}


def load(p: Path) -> list:
    out = {}
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if ln:
            r = json.loads(ln)
            out[r["row_id"]] = r
    return list(out.values())


def tail_ge(k: int, n: int) -> float:
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n if n else 1.0


def mcnemar(b: int, c: int, alt: str) -> float:
    n = b + c
    if n == 0:
        return 1.0
    if alt == "greater":
        return tail_ge(b, n)
    return min(1.0, 2 * min(tail_ge(b, n), tail_ge(c, n)))


def correct(r: dict, t: str) -> bool:
    return r.get("label") == t and bool(r.get("passed"))


def main() -> None:
    lab = load(ROOT / "data" / "labels.jsonl")
    A = json.loads((ROOT / "results" / "analysis.json").read_text())
    cells = {}
    for r in lab:
        cells.setdefault(r["cell"], {})[(r["template"], int(r["slot"]))] = r
    checks = []

    def chk(name: str, mine, theirs, tol: float = 1e-9) -> None:
        if mine is None or theirs is None:
            ok = mine is None and theirs is None
        elif isinstance(mine, bool) or isinstance(theirs, bool):
            ok = bool(mine) == bool(theirs)
        else:
            ok = abs(float(mine) - float(theirs)) <= tol * max(1.0, abs(float(theirs)))
        checks.append({"name": name, "rederived": mine, "analysis": theirs, "ok": bool(ok)})
    # ---------------- per-cell counts
    for c, rows in cells.items():
        t = "dfs" if c in DFS_CELLS else "bfs"
        sl = S30 if c in ("REV-DAS", "REV-FULL") else S50
        rr = [rows[s] for s in sl if s in rows]
        if c not in A["cells"]:
            continue
        chk(f"{c}.n", len(rr), A["cells"][c]["n"])
        chk(f"{c}.correct_target", sum(correct(r, t) for r in rr), A["cells"][c]["correct_target"])
        chk(f"{c}.attempted_target", sum(r.get("label") == t for r in rr), A["cells"][c]["attempted_target"])
        chk(f"{c}.pass", sum(bool(r.get("passed")) for r in rr), A["cells"][c]["pass"])

    def pair(a: str, b: str, t: str, alt: str, slots=S50, key: str | None = None) -> dict:
        x, y = cells[a], cells[b]
        bb = sum(1 for s in slots if s in x and s in y and correct(x[s], t) and not correct(y[s], t))
        cc = sum(1 for s in slots if s in x and s in y and correct(y[s], t) and not correct(x[s], t))
        p = mcnemar(bb, cc, alt)
        if key:
            T = A["tests"][key]
            chk(f"{key}.a_only", bb, T["a_only"])
            chk(f"{key}.b_only", cc, T["b_only"])
            chk(f"{key}.p", p, T["p_two_sided"] if alt == "two-sided" else T["p_a_greater"], 1e-9)
        return {"b": bb, "c": cc, "p": p}
    pair("P-DAS-bfs", "G1a", "bfs", "two-sided", key="dial_vs_prompt_prefilled_P1b")
    pair("F-DAS-r4-bfs-1.0", "G1c", "bfs", "two-sided", key="dial_vs_prompt_free")
    pair("P-DAS-bfs", "F-DAS-r4-bfs-1.0", "bfs", "two-sided", key="prefilled_vs_free_dial")
    pair("G1a", "G1c", "bfs", "two-sided", key="prefilled_vs_free_prompt")
    pair("P-twin", "F-twin", "bfs", "two-sided", key="twin_prefilled_vs_free")
    fam = {}
    for c in ("F-DAS-r4-bfs-1.0", "F-DAS-r4-bfs-0.5", "F-DAS-r1-bfs-1.0", "F-DAS-r1-bfs-0.5"):
        fam[c] = pair(c, "F-twin", "bfs", "greater")["p"]
        chk(f"holm_family.{c}.p_raw", fam[c], A["tests"]["G2_holm_family"][c]["p_a_greater"])
    items = sorted(fam.items(), key=lambda kv: kv[1])
    run = 0.0
    for i, (c, p) in enumerate(items):
        run = max(run, min(1.0, (len(items) - i) * p))
        chk(f"holm_family.{c}.p_holm", run, A["tests"]["G2_holm_family"][c]["p_holm"])
    # interaction (point estimate)
    def share(c: str) -> float:
        return sum(correct(cells[c][s], "bfs") for s in S50) / 50
    inter = (share("P-DAS-bfs") - share("G1a")) - (share("F-DAS-r4-bfs-1.0") - share("G1c"))
    chk("interaction", inter, A["tests"]["interaction_slot_bootstrap"]["interaction"])
    # scorecard
    sc = A["scorecard"]
    g1a = sum(correct(cells["G1a"][s], "bfs") for s in S50)
    chk("P1.holds", g1a >= 40, sc["P1"]["holds"])
    p1b = pair("P-DAS-bfs", "G1a", "bfs", "two-sided")
    chk("P1b.holds", p1b["p"] >= 0.05, sc["P1b"]["holds"])
    fd = cells["F-DAS-r4-bfs-1.0"]
    ft = cells["F-twin"]
    f_c = sum(correct(fd[s], "bfs") for s in S50)
    f_p = sum(bool(fd[s]["passed"]) for s in S50) / 50
    t_p = sum(bool(ft[s]["passed"]) for s in S50) / 50
    t_c = sum(correct(ft[s], "bfs") for s in S50)
    p2 = f_c >= 30 and f_p >= 0.8 * t_p and f_c > t_c and fam["F-DAS-r4-bfs-1.0"] < 0.05
    chk("P2.holds", p2, sc["P2"]["holds"])
    dim_p = sum(bool(cells["F-DiM-bfs"][s]["passed"]) for s in S50) / 50
    chk("P6.holds", dim_p < 0.8 * t_p, sc["P6"]["holds"])
    # reverse generation
    base = sum(correct(cells["G1a"][s], "dfs") for s in S30)
    full = sum(correct(cells["REV-FULL"][s], "dfs") for s in S30)
    das = sum(correct(cells["REV-DAS"][s], "dfs") for s in S30)
    rest = (das - base) / (full - base) if (full - base) > 2 else None
    chk("restoration_gen", rest, A["reverse_generation"]["restoration_gen"])
    # dormancy verdicts from the stored summary numbers (committed rule)
    D = json.loads((ROOT / "results" / "dormancy.json").read_text())["summary_by_k"]
    for k, s in D.items():
        low = s["share"] <= s["random_p95"]
        flag = (s["forward_recovery"] >= 0.8) and ((s["retention"] < 0.5) or (s["reverse_defined"] and s["reverse_recovery"] < 0.5))
        if flag:
            v = "DORMANT/OFF-MANIFOLD HANDLE"
        elif not s["reverse_defined"] and s["retention"] >= 0.5:
            v = "UNDETERMINED"
        elif low:
            v = "SUFFICIENT, LOW-VARIANCE"
        else:
            v = "USED VARIABLE"
        checks.append({"name": f"dormancy.k{k}.verdict", "rederived": v, "analysis": s["verdict"], "ok": v == s["verdict"]})
    # engine check vs iteration 7's rows
    i7 = {}
    for ln in (ROOT / "inputs" / "iter7" / "data" / "labels.jsonl").read_text().splitlines():
        if ln.strip():
            r = json.loads(ln)
            i7[r["row_id"]] = r
    for c, c7 in (("P-twin", "twin"), ("P-DAS-bfs", "DAS|bfs|1.0")):
        ag = sum(cells[c][s]["label"] == i7[f"g2|{c7}|{s[0]}|{s[1]}"]["label"] for s in S50) / 50
        chk(f"engine.{c}.label_agreement", ag, A["engine_check"][c]["label_agreement"])
    # ---------------- placebos (must fail)
    rng = random.Random(0)
    plc = {}
    for a, b, t in (("F-DAS-r4-bfs-1.0", "F-twin", "bfs"), ("P-DAS-bfs", "G1a", "bfs")):
        x, y = cells[a], cells[b]
        sig = 0
        for _ in range(1000):                       # within-slot cell-label swap (sign-flip null)
            bb = cc = 0
            for s in S50:
                u, v = correct(x[s], t), correct(y[s], t)
                if rng.random() < 0.5:
                    u, v = v, u
                bb += u and not v
                cc += v and not u
            sig += mcnemar(bb, cc, "two-sided") < 0.05
        perm = S50[:]
        rng.shuffle(perm)                           # slot-shuffled pairing (marginals kept)
        bb = sum(1 for s, q in zip(S50, perm) if correct(x[s], t) and not correct(y[q], t))
        cc = sum(1 for s, q in zip(S50, perm) if correct(y[q], t) and not correct(x[s], t))
        plc[f"{a}_vs_{b}"] = {"cell_label_swap_share_p_lt_0.05": sig / 1000,
                              "slot_shuffled_unpaired_p": mcnemar(bb, cc, "two-sided"),
                              "note": "the swap null must be non-significant (~0.05); the unpaired p keeps the marginal "
                                      "difference and is reported beside the paired test"}
    # interaction under within-slot label swaps of the four cells
    inters = []
    keys = ("P-DAS-bfs", "G1a", "F-DAS-r4-bfs-1.0", "G1c")
    for _ in range(2000):
        tot = [0, 0, 0, 0]
        for s in S50:
            vals = [correct(cells[k][s], "bfs") for k in keys]
            rng.shuffle(vals)
            for i in range(4):
                tot[i] += vals[i]
        inters.append((tot[0] - tot[1] - tot[2] + tot[3]) / 50)
    inters.sort()
    plc["interaction_cell_label_shuffle"] = {"mean": sum(inters) / len(inters), "p95_abs": sorted(abs(v) for v in inters)[1899],
                                             "observed": inter}
    n_bad = sum(not c["ok"] for c in checks)
    res = {"n_checks": len(checks), "n_mismatch": n_bad, "checks": checks, "placebos": plc}
    (ROOT / "results" / "rederive.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({"n_checks": len(checks), "n_mismatch": n_bad, "placebos": plc}, indent=1))
    for c in checks:
        if not c["ok"]:
            print("MISMATCH", c)


if __name__ == "__main__":
    main()
