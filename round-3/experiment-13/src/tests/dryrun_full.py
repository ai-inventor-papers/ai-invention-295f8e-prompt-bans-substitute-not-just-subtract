#!/usr/bin/env python3
"""Pre-commitment dry run of the committed analysis on the full ban-free data: the NOVELTY arm stands in for the
ban (no ban is sampled before the seal).  A second pass relaxes the C2b one-shot avoidance floor (in this process
only) so that the eligible-event code path is exercised.  Outputs go to scratch/ and results/dryrun_full*/."""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from common import PRED, RESULTS, ROOT as R, setup_logging  # noqa: E402

setup_logging("dryrun_full")
import analyze  # noqa: E402
import forecasts  # noqa: E402

forecasts.build("")
scratch = R / "scratch"
scratch.mkdir(exist_ok=True)
fcp = scratch / "forecasts_dryrun_full.json"
shutil.move(str(PRED / "forecasts.json"), fcp)
analyze.FIGS = scratch / "figs_dryrun"
res = analyze.run("", fake_ban_from="novelty", fc_path=fcp, head="dryrun", out_dir=RESULTS / "dryrun_full",
                  make_figures=True)
print("C1:", res["c1"]["verdict"], res["c1"]["n_gated"], res["c1"]["n_gated_disagreeing"], res["c1"]["advance"]["wins"])
print("camp:", res["c1"]["camp_contest"]["wins"], res["c1"]["camp_contest"]["n_events"])
print("C2b:", {k: (v["verdict"], v["n_eligible"]) for k, v in res["c2b"].items() if isinstance(v, dict)})
print("TE:", {k: v for k, v in res["template_effect"]["mixed_glm"].items() if k != "vc_names"},
      res["template_effect"]["fixed_effects_lr"])
analyze.FROZEN_CONSTANTS["c2b"]["min_one_shot_avoidance"] = 0.0
res2 = analyze.run("", fake_ban_from="novelty", fc_path=fcp, head="dryrun", out_dir=RESULTS / "dryrun_full_c2b_relaxed",
                   make_figures=False)
print("C2b relaxed:", {k: (v["verdict"], v["n_eligible"]) for k, v in res2["c2b"].items() if isinstance(v, dict)})
for e in res2["c2b"]["oneshot"]["events"]:
    if e.get("eligible"):
        print("  ", e["task"], e["modal_veto"], e["modal_ban"], round(e["js"], 3), round(e["null_p95"], 3),
              e["reproduces"], e["elsewhere"])
