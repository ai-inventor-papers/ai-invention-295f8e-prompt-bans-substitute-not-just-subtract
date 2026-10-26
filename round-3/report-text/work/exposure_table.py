import json, sys
E = sys.argv[1]
arm = json.load(open(f"{E}/results/arm_stats.json"))
rows = [json.loads(l) for l in open(f"{E}/results/c1_events.jsonl")]
named = [r for r in rows if r["event_type"] == "exposure_named"]
def fmt(c):
    return ", ".join(f"{k} {v}" for k, v in sorted(c.items(), key=lambda kv: -kv[1])) or "none"
def top(t):
    if t is None: return "n/a"
    return "/".join(t) if len(t) <= 2 else "tie"
print("| Task | Y | Priority | Default | Associate of Y | COPY: share Y | NAMED avoidance | NAMED landing (non-Y attempts) | Default share | Gate | SUBTRACT | PROXIMITY | Winner (>= 0.10 nats) |")
print("|-|-|-|-|-|-|-|-|-|-|-|-|-|")
for r in named:
    key = f"{r['task']}:{r['Y']}"
    a = arm.get(key, {})
    cp = a.get("copy", {}).get("Y_share")
    ls = r["logscore"]
    vals = {k: v for k, v in ls.items() if v is not None}
    win = "-"
    if r["gate_pass"] and r["disagreeing"] and vals:
        srt = sorted(vals.items(), key=lambda kv: -kv[1])
        if len(srt) > 1 and srt[0][1] - srt[1][1] >= 0.10:
            win = srt[0][0]
        else:
            win = "none"
    assoc = list(r["associate"].keys())[0] if r["associate"] else "n/a"
    print(f"| {r['task']} | {r['Y']} | {'yes' if r['priority'] else 'no'} | {r['default']} | {assoc} | {cp:.2f} | {r['avoidance']:.2f} | {fmt(r['landing_counts'])} | {r['default_share']:.2f} | {'pass' if r['gate_pass'] else 'fail'} | {top(r['top1']['SUBTRACT']) if r['forecasts']['SUBTRACT'] is not None else 'undefined'} | {top(r['top1']['PROXIMITY'])} | {win} |")
