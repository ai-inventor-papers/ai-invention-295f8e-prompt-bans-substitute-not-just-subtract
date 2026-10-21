"""Crafted probe inputs per task (3-5 per task, deterministic) and the parent-side tracer call."""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

from .harness import PY, _limit_mem

TRACER = Path(__file__).resolve().parent / "tracer.py"


def _pairs(rng, n, lo, hi, wmax, wmin=0):
    out = []
    for _ in range(n):
        s = rng.randint(lo, hi - wmax)
        out.append([s, s + rng.randint(wmin, wmax)])
    return out


def make_probes(task: str) -> list[dict]:
    rng = random.Random(7 + sum(map(ord, task)))
    P = []
    if task == "T03":
        P.append({"name": "rand300", "args": {"nums": [rng.randint(-1000, 1000) for _ in range(300)], "k": 100},
                  "wrap": {"nums": "clist_int"}})
        P.append({"name": "sorted200", "args": {"nums": list(range(200)), "k": 10}, "wrap": {"nums": "clist_int"}})
        P.append({"name": "wide100", "args": {"nums": [rng.choice([-10000, 10000]) if i < 2 else rng.randint(-10000, 10000)
                                                       for i in range(100)], "k": 50}, "wrap": {"nums": "clist_int"}})
    elif task == "T04":
        h = "".join(rng.choice("ab") for _ in range(300))
        nd = "abbaabbbab"
        h = h[:250] + nd + h[260:]
        P.append({"name": "find300", "args": {"haystack": h, "needle": nd}, "wrap": {"haystack": "cstr", "needle": "cstr"}})
        P.append({"name": "adv200", "args": {"haystack": "a" * 200 + "b", "needle": "a" * 10 + "b"},
                  "wrap": {"haystack": "cstr", "needle": "cstr"}})
    elif task == "T05":
        vals = rng.sample(range(-10**6, 10**6), 200)
        P.append({"name": "end200", "args": {"nums": vals, "target": vals[-1] + vals[-2]}, "wrap": {"nums": "clist_int"}})
    elif task == "T06":
        a = list(range(1, 201)) + [137]
        rng.shuffle(a)
        P.append({"name": "perm200", "args": {"nums": a}, "wrap": {"nums": "clist_int"}})
        b = [v for v in range(1, 101) if v not in (11, 12, 13)] + [7] * 4
        rng.shuffle(b)
        P.append({"name": "multi100", "args": {"nums": b}, "wrap": {"nums": "clist_int"}})
    elif task == "T08":
        for n in (64, 128, 256):
            P.append({"name": f"n{n}", "args": {"n": n}, "wrap": {}, "trace_lines": True})
    elif task == "T10":
        P.append({"name": "path40", "args": {"n": 40, "edges": [[i, i + 1] for i in range(39)]},
                  "wrap": {"edges": "clist_pairs"}})
        s, e = set(), []
        while len(e) < 120:
            u, v = rng.randrange(80), rng.randrange(80)
            if u != v and (min(u, v), max(u, v)) not in s:
                s.add((min(u, v), max(u, v)))
                e.append([u, v])
        P.append({"name": "rand80", "args": {"n": 80, "edges": e}, "wrap": {"edges": "clist_pairs"}})
    elif task == "T11":
        P.append({"name": "rand150", "args": {"nums": [rng.randint(-500, 500) for _ in range(150)]}, "wrap": {"nums": "clist_int"}})
        P.append({"name": "inc80", "args": {"nums": list(range(80))}, "wrap": {"nums": "clist_int"}})
    elif task == "T13":
        P.append({"name": "rand80", "args": {"intervals": _pairs(rng, 80, 0, 1000, 30)}, "wrap": {"intervals": "clist_pairs"}})
        P.append({"name": "rand40w", "args": {"intervals": _pairs(rng, 40, 0, 400, 60)}, "wrap": {"intervals": "clist_pairs"}})
    elif task == "T14":
        vals = rng.sample(range(-500, 500), 25)
        arr = []
        for i, v in enumerate(vals):
            arr += [v] * (i + 1)
        rng.shuffle(arr)
        P.append({"name": "zipf25", "args": {"nums": arr, "k": 4}, "wrap": {"nums": "clist_int"}})
    elif task == "R1":
        P.append({"name": "rand80", "args": {"intervals": _pairs(rng, 80, -1000, 1000, 80, 1)}, "wrap": {"intervals": "clist_pairs"}})
        P.append({"name": "rand40", "args": {"intervals": _pairs(rng, 40, 0, 300, 40, 1)}, "wrap": {"intervals": "clist_pairs"}})
    elif task == "R2":
        tri = [[0, 1], [1, 2], [2, 0]]
        tree = [[rng.randrange(v), v] for v in range(4, 60)]
        P.append({"name": "cyc_early60", "args": {"n": 60, "edges": tri + tree}, "wrap": {"edges": "clist_pairs"}})
        forest = [[rng.randrange(v), v] for v in range(1, 60) if v % 15]
        P.append({"name": "forest60", "args": {"n": 60, "edges": forest}, "wrap": {"edges": "clist_pairs"}})
    elif task == "R3":
        perm = list(range(40))
        rng.shuffle(perm)
        s, e = set(), []
        while len(e) < 80:
            i, j = sorted(rng.sample(range(40), 2))
            if (i, j) not in s:
                s.add((i, j))
                e.append([perm[j], perm[i]])
        P.append({"name": "dag40", "args": {"n": 40, "prerequisites": e}, "wrap": {"prerequisites": "clist_pairs"}})
        P.append({"name": "cyc30", "args": {"n": 30, "prerequisites": [[i + 1, i] for i in range(29)] + [[0, 29]]},
                  "wrap": {"prerequisites": "clist_pairs"}})
    elif task == "R6":
        a = sorted(rng.randint(0, 5000) for _ in range(2000))
        a = [x for x in a if x != 777]
        a = a[:1500] + [777] * 20 + a[1500:]
        a.sort()
        P.append({"name": "run2000", "args": {"nums": a, "target": 777}, "wrap": {"nums": "clist_int"}})
        P.append({"name": "absent2000", "args": {"nums": a, "target": 778 if 778 not in a else 5001}, "wrap": {"nums": "clist_int"}})
    for p in P:
        p["kwargs_json"] = json.dumps(p.pop("args"))
    return P


def run_trace(code: str, task: str, probes: list[dict] | None = None, timeout: float = 10.0) -> dict:
    probes = probes if probes is not None else make_probes(task)
    payload = {"code": code, "probes": probes, "timeout": timeout}
    try:
        pr = subprocess.run([PY, "-I", "-S", str(TRACER)], input=json.dumps(payload), capture_output=True, text=True,
                            timeout=timeout * len(probes) + 20, preexec_fn=_limit_mem)
        lines = [json.loads(l) for l in pr.stdout.splitlines() if l.startswith("{")]
    except subprocess.TimeoutExpired:
        lines = [{"probe": None, "error": "tracer timeout"}]
    except json.JSONDecodeError:
        lines = [{"probe": None, "error": "tracer output unparseable"}]
    out = {"probes": {}, "error": None}
    for l in lines:
        if l.get("probe") is None:
            out["error"] = l.get("error")
        else:
            out["probes"][l["probe"]] = l
    if not lines:
        out["error"] = "no tracer output"
    return out
