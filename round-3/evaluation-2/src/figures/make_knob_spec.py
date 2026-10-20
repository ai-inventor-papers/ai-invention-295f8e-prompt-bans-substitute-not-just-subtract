#!/usr/bin/env python3
"""Write figures/knob_ranking_spec.json (an aii-data-fig-gen 'barh' spec) from results/knob_table.json: rarefied
Hill-1 at depth 25 of the ten best KNOB rows costing fewer than 20 pass points. Render with
`python <aii-data-fig-gen>/scripts/chart_gen.py --spec figures/knob_ranking_spec.json --out figures/knob_ranking`."""
import json
from pathlib import Path

WS = Path(__file__).resolve().parent.parent
k = json.loads((WS / "results" / "knob_table.json").read_text())
rows = k["ranking"][:10]
cats = [f"{r['exp']} {r['task'].upper()} {r['condition'].replace('steer:', '').replace(':L=18', '')}"
        + (f" ({r['arm'].split(':')[0]})" if r["arm"] else "") + f", {r['pass_points']:.0f} pts" for r in rows]
spec = {"type": "barh", "title": "Best knobs under 20 pass points (rarefied Hill-1, depth 25)",
        "xlabel": "Rarefied Hill-1 over correct compliant programs", "aspect": "4:3", "categories": cats,
        "series": [{"values": [round(r["hill_rar25"], 4) for r in rows]}]}
(WS / "figures" / "knob_ranking_spec.json").write_text(json.dumps(spec, indent=1))
print("wrote figures/knob_ranking_spec.json")
