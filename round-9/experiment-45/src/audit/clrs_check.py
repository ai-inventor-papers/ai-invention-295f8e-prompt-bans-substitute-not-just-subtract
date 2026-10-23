#!/usr/bin/env python3
"""Order statistics on canonical CLRS-30 traces (art_j3Rm_lr2nzR6 clrs_text), excluding degenerate traces in which
the source reaches fewer than 2 vertices (no consecutive pair exists). Separate from the committed gate_v9.clrs_check,
whose BFS minimum was 0.0 only because of such single-vertex traces. Usage: python audit/clrs_check.py"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    rows = [json.loads(l) for l in open(os.path.join(ROOT, "inputs", "dataset", "clrs_bfs_dfs.jsonl"))]
    out = {}
    for alg in ("bfs", "dfs"):
        stats, pis, n_deg = [], 0, 0
        for r in [x for x in rows if x["algorithm"] == alg][:40]:
            A, s = r["A"], r.get("s", 0)
            m = len(A)
            nb = [[j for j in range(m) if A[i][j] and j != i] for i in range(m)]
            if alg == "bfs":
                pi, d, order, q = list(range(m)), [None] * m, [s], [s]
                d[s] = 0
                pi[s] = s
                while q:
                    u = q.pop(0)
                    for v in nb[u]:
                        if d[v] is None:
                            d[v], pi[v] = d[u] + 1, u
                            q.append(v)
                            order.append(v)
                if len(order) < 2:
                    n_deg += 1
                    continue
                pm = [int(d[b] >= d[a]) for a, b in zip(order, order[1:])]
                stats.append(sum(pm) / len(pm))
            else:
                pi, color, order = list(range(m)), [0] * m, []

                def visit(u):
                    color[u] = 1
                    order.append(u)
                    for v in nb[u]:
                        if color[v] == 0:
                            pi[v] = u
                            visit(v)

                for u in range(m):
                    if color[u] == 0:
                        visit(u)
                stack, expd, ok, tot = [], set(), 0, 0
                for x in order:
                    if stack:
                        while stack and not any(v not in expd for v in nb[stack[-1]]):
                            stack.pop()
                        if stack:
                            tot += 1
                            ok += int(x in nb[stack[-1]] or any(x in nb[y] for y in stack))
                    expd.add(x)
                    stack.append(x)
                stats.append(ok / tot if tot else 1.0)
            pis += int(pi == r["pi_final"])
        out[alg] = {"n": len(stats), "degenerate_excluded": n_deg, "pi_match": pis, "stat_min": min(stats) if stats
                    else None, "stat_mean": sum(stats) / len(stats) if stats else None,
                    "stat": "p_mono" if alg == "bfs" else "p_lifo (stack adjacency)"}
    out["passed"] = all(o["n"] > 0 and o["stat_min"] == 1.0 for o in (out["bfs"], out["dfs"]))
    with open(os.path.join(ROOT, "results", "clrs_check.json"), "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
