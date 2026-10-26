import json, sys
def show(o, d=0, maxd=4, maxk=40, pre=""):
    ind = "  " * d
    if isinstance(o, dict):
        ks = list(o.keys())
        if d >= maxd:
            print(f"{ind}{pre}dict({len(ks)}): {ks[:15]}"); return
        print(f"{ind}{pre}dict({len(ks)})")
        for k in ks[:maxk]:
            show(o[k], d+1, maxd, maxk, pre=f"{k}: ")
        if len(ks) > maxk: print(f"{ind}  ... +{len(ks)-maxk} keys: {ks[maxk:maxk+20]}")
    elif isinstance(o, list):
        print(f"{ind}{pre}list({len(o)})")
        if o and d < maxd:
            show(o[0], d+1, maxd, maxk, pre="[0]: ")
    else:
        s = repr(o)
        print(f"{ind}{pre}{s[:120]}")
p = sys.argv[1]; maxd = int(sys.argv[2]) if len(sys.argv) > 2 else 4
if p.endswith(".jsonl"):
    with open(p) as f:
        for i, line in enumerate(f):
            if i >= 1: break
            show(json.loads(line), 0, maxd)
    print("lines:", sum(1 for _ in open(p)))
else:
    show(json.load(open(p)), 0, maxd)
