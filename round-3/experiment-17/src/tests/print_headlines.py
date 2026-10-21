"""Print the headline numbers used in README.md from results/*.json (no recomputation)."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[1] / "results"
def j(n):
    p = R / n
    return json.loads(p.read_text()) if p.exists() else None
c2e = j("c2e.json")
if c2e:
    for t, v in c2e["primary"].items():
        if v.get("status") != "testable":
            print("C2e", t, v.get("status")); continue
        st = {p: round(v["state_curves"][p]["max_ba"], 3) for p in ["R", "k1", "k2", "k3", "k4", "k8", "k16"]}
        print("C2e", t, "n", v["n"], v["n_default"], v["n_other"], "tmpl", round(v["template_only_ba"], 3), "locus", v["locus"], "state", st)
        print("    text k8", {a: round(b, 3) for a, b in v["text_controls"]["k8"].items()}, "k16", {a: round(b, 3) for a, b in v["text_controls"]["k16"].items()})
        print("    null k8", round(v["null_layer_max"]["k8"]["q95"], 3), "det", {k: x["max_abs_diff"] for k, x in v["determinism_check"].items()}, "fd", {c: x["median"] for c, x in v["first_divergence"].items()})
    for t, v in c2e.get("secondary_archive_pooled", {}).items():
        print("C2e archive", t, v.get("status"), v.get("n"), v.get("n_default"), "locus", v.get("locus"),
              {p: round(v["state_curves"][p]["max_ba"], 3) for p in ["k1", "k8", "k16"]} if v.get("status") == "testable" else "",
              "text k16", {a: round(b, 3) for a, b in v["text_controls"]["k16"].items()} if v.get("status") == "testable" else "")
ext = j("c2e_extension.json")
if ext:
    for t, v in ext.items():
        for k, x in v["positions"].items():
            if "state_max_ba" in x:
                print("C2e-X", t, k, "n", x["n"], x["n_default"], "state", round(x["state_max_ba"], 3), "null", round(x["null_layer_max_q95"], 3), {a: round(b, 3) for a, b in x["text"].items()}, "beats", x["state_beats_text_by_0.10_and_null"])
            else:
                print("C2e-X", t, k, x)
u = j("unit_tests_u1b.json")
print("U1b", u)
sae = j("sae_transfer.json")
if sae:
    for L, v in sae["per_layer"].items():
        print("0g", L, {k: (round(x, 4) if isinstance(x, float) else x) for k, x in v.items()})
    for c, v in sae["cells"].items():
        print("0g cell", c, "ce_clean", round(v["ce_clean"], 4), {L: (round(x["fr_zero"], 4), round(x["fr_mean"], 4), round(x["dce"], 4), round(x["kl_sae"], 4), round(x["fvu"], 3), round(x["ce_zero"], 2)) for L, x in v["layers"].items()})
    print("0g disp", {L: (round(v["cos_mean_all"], 3), {t: round(x, 2) for t, x in v["norm_ratio_median_by_task"].items()}) for L, v in (sae.get("displacement_preservation") or {}).items()})
    print("0g sanity", sae.get("sanity"))
