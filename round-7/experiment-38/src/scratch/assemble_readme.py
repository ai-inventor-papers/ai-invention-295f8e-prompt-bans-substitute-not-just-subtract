"""Assemble README.md from the scratch parts (G1-T text passed as files)."""
from pathlib import Path
S = Path("scratch")
head = (S / "README_head.md").read_text()
short = (S / "short_answer.md").read_text()
g1t_sentence = (S / "g1t_sentence.md").read_text().strip() if (S / "g1t_sentence.md").exists() else "G1-T: see below."
g1t_section = (S / "g1t_section.md").read_text().strip() if (S / "g1t_section.md").exists() else "Not run."
short = short.replace("G1T_SENTENCE", g1t_sentence)
head = head.replace("SHORT_ANSWER_PLACEHOLDER", short.strip())
mid = (S / "README_mid.md").read_text()
g1 = (S / "README_g1.md").read_text().replace("G1T_SECTION", g1t_section)
dev = (S / "README_dev.md").read_text()
tail = (S / "README_tail.md").read_text()
figs = """
## Figures (`figures/`, PNG + PDF)

| Figure | What it shows |
|---|---|
| F1 `F1_g1_graph` | G1-P graph: nodes by layer x position class, kept edges |
| F2 `F2_g1_validation` | real-model ABLATE/STEER effect per prompt vs the matched random null, per top node |
| F3 `F3_g2_das` | full-state ceiling by layer, the rank-1 layer scan, and held-out recovery by rank with RAND, SHUF, DiM and RINIT |
| F4 `F4_g2_geometry` | the 120 twin variants and 40 forced sources in the (R_1, R_2) plane at L17 (actual activation coordinates), coloured by y_v, with the DAS dose path and the DiM direction |
| F5 `F5_g2_dose` | dose response (attempted, correct, pass) for DAS vs DiM toward BFS and toward DFS, with the twin, the forced-BFS ceiling and the logit-only DAS cell |
| F6/F7 `F6_F7_g3_temperature` | predicted vs observed BFS share by temperature (both samplers), and H(label \\| fork class) by T |
"""
out = head.rstrip() + "\n\n" + mid.strip() + "\n" + g1.rstrip() + "\n" + figs + "\n" + dev.strip() + "\n\n" + tail.strip() + "\n"
Path("README.md").write_text(out)
print(len(out.splitlines()), "lines")
