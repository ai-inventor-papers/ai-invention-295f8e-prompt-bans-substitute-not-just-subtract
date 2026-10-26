#!/usr/bin/env python3
"""Iteration-8 design constants (claim G: prefill-matched prompting, free-generation dial, dormancy checks at the
BFS-vs-DFS fork of gemma-3-4b-it). Everything inherited from iteration 7 (engine, prompts, c*, B/D ids, templates,
display pairs, CRN keys) lives in cfg.py / fork7.py, vendored unchanged from art_HY7uYZz-OjRW.

Notation: block l = decoder block l (0-based), edits act on its output (HF hidden_states[l + 1]); L = 17.
c* = the shared 32-token opening; the fork token is response index 32; p_f = the position of c*[31].
S50 = {(w, k): w in W1..W5, k in 0..9} with ukey slot_key7('G2', w, k) (iteration 7's dose-sweep streams);
S30 = the k in 0..5 subset; HT30 = {(w, k): w in W4, W5, k in 10..24} (fresh streams, held-out extension).
"""

from __future__ import annotations

from cfg import DATA_DIR, INPUTS, ROOT, TEMPLATE_IDS, slot_key7

L = 17
KSTAR = 4
RANKS = (1, 2, 4, 8)
SEEDS = (0, 1, 2)
MAX_NEW = 1024                 # kept from iteration 7 (protocol v8 says 1,536 for path tasks; deviation D-maxnew)
REC_UPTO = 97                  # per-step diagnostics for response indices 0..96 (decision window)
DEC_MIN, DEC_MAX = 8, 96       # R2 window
Q_ID = 15204                   # ' queue'
VISITED_ID = 53227             # ' visited'
ALG_STRINGS = ("deque", "queue", "visited", "stack", "heapq", "heappush", "popleft", "pop(0)", "dfs", "bfs",
               "recurs")
TRAIN_W = ("W1", "W2", "W3")
HELD_W = ("W4", "W5")

S50 = [(w, k) for w in TEMPLATE_IDS for k in range(10)]
S30 = [(w, k) for w in TEMPLATE_IDS for k in range(6)]
HT30 = [(w, k) for w in HELD_W for k in range(10, 25)]


def ukey(w: str, k: int) -> tuple[str, str, str, int]:
    return slot_key7("G2", w, k)


def rid(cell: str, w: str, k: int) -> str:
    return f"g8|{cell}|{w}|{k}"


# ------------------------------------------------------------------------------------------------ cells
PREFILLED_TWIN_CELLS = ("P-twin", "P-DAS-bfs", "P-DAS-dfs")
G1_CELLS = ("G1a", "G1b", "G1c", "G1d")
FREE_CORE = ("F-DAS-r4-bfs-1.0", "F-DAS-r4-bfs-0.5", "F-DAS-r1-bfs-1.0", "F-DAS-r1-bfs-0.5", "F-DiM-bfs",
             "F-DAS-r4-dfs-1.0", "F-DiM-dfs")
FREE_OPTIONAL = ("F-RAND-r4-1.0", "F-DAS-s2-r4-bfs-1.0")
FREE_SPECS = {   # cell -> (method, rank, dir, lambda, seed)
    "F-DAS-r4-bfs-1.0": ("DAS", 4, "bfs", 1.0, 0),
    "F-DAS-r4-bfs-0.5": ("DAS", 4, "bfs", 0.5, 0),
    "F-DAS-r1-bfs-1.0": ("DAS", 1, "bfs", 1.0, 0),
    "F-DAS-r1-bfs-0.5": ("DAS", 1, "bfs", 0.5, 0),
    "F-DiM-bfs": ("DiM", 1, "bfs", None, 0),
    "F-DAS-r4-dfs-1.0": ("DAS", 4, "dfs", 1.0, 0),
    "F-DiM-dfs": ("DiM", 1, "dfs", None, 0),
    "F-RAND-r4-1.0": ("RAND", 4, "bfs", 1.0, 0),
    "F-DAS-s2-r4-bfs-1.0": ("DAS", 4, "bfs", 1.0, 2),
}
TARGET_OF = {"P-twin": "bfs", "P-DAS-bfs": "bfs", "P-DAS-dfs": "dfs", "G1a": "bfs", "G1b": "dfs", "G1c": "bfs",
             "G1d": "bfs", "F-twin": "bfs", "REV-DAS": "dfs", "REV-FULL": "dfs"}
TARGET_OF.update({c: FREE_SPECS[c][2] for c in FREE_SPECS})
REV_CELLS = ("REV-DAS", "REV-FULL")

RAW = {"engine": DATA_DIR / "raw_engine.jsonl", "g1": DATA_DIR / "raw_g1.jsonl",
       "ftwin": DATA_DIR / "raw_ftwin.jsonl", "fcells": DATA_DIR / "raw_fcells.jsonl",
       "rev": DATA_DIR / "raw_rev.jsonl"}
STEPS = DATA_DIR / "steps_free.jsonl"       # per-row per-step diagnostics of free cells (indices 0..96)
I7 = ROOT / "inputs" / "iter7"              # copied iteration-7 results (read-only copies)
I7_LABELS = I7 / "data" / "labels.jsonl"
I7_RAW_DOSE = I7 / "data" / "raw_g2dose.jsonl"

# ------------------------------------------------------------------------------------------------ thresholds
P1_MIN_CORRECT = 40
P2_MIN_CORRECT = 30
PASS_RATIO = 0.8
P3_REACH = 0.80
P4_AGREE = 0.90
P7_TOL = 0.10
MIN_DENOM_NAT = 0.5           # |mean full-state reverse| below this -> reverse ratio UNDEFINED
REV_GEN_MIN_DENOM = 2         # REV-FULL must restore > 2 DFS programs for restoration_gen to be defined
DORMANT_RETENTION = 0.5
DORMANT_REVERSE = 0.5
DORMANT_FORWARD = 0.8
N_HAAR_VAR = 1000
N_HAAR_REV = 50
N_BOOT_PAIRS = 2000
N_BOOT_SLOTS = 10000
PC_MAIN, PC_SENS = 64, (32, 100)
U3P_TOL = 0.3
JUDGE_CAP_USD = 0.20
OPENROUTER_CAP_USD = 1.00      # whole artifact (labeller judge 0.20 + novelty/positioning)

DECISION_RULES = {
    "P1": "G1a (forced-BFS F5 + c* prefilled, no edit, S50): correct BFS >= 40/50.",
    "P1b": "P-DAS-bfs vs G1a on correct BFS, two-sided exact McNemar over the 50 CRN slots: p >= 0.05 -> "
           "'MATCHES (not distinguishable at N = 50)'; p < 0.05 with more DAS correct -> 'DIAL BEATS MATCHED "
           "PROMPTING'; p < 0.05 with fewer -> 'DIAL LOSES TO MATCHED PROMPTING'.",
    "P2": "F-DAS-r4-bfs-1.0: correct BFS >= 30/50 AND pass >= 0.8 x F-twin pass AND correct BFS > F-twin "
          "(one-sided exact McNemar p < 0.05). Holds -> 'free-generation knob'; fails -> 'the dial works only with "
          "a teacher-forced prefill'.",
    "P3": "Reach share (R1 or R2) over the 50 F-twin slots >= 0.80; R1 share about 0.86.",
    "P4": "On R1 slots, free and prefilled programs agree on label in >= 0.90 of slots, for the twin pair "
          "(F-twin vs P-twin) and the DAS pair (F-DAS-r4-bfs-1.0 vs P-DAS-bfs); (label, pass) agreement and "
          "byte-identical code shares are reported beside it.",
    "P5": "Dormancy reported either way; the D5/K2 account predicts reverse recovery >= 0.5 and retention >= 0.5 at "
          "k = 4; iteration-7 numbers predict LOW_NATURAL_VARIANCE at k = 1, 2, 4.",
    "P6": "F-DiM-bfs: pass < 0.8 x F-twin pass.",
    "P7": "|TF-predicted attempted-BFS share - observed attempted-BFS share| <= 0.10 in every prefilled cell "
          "(P-twin, P-DAS-bfs, P-DAS-dfs, G1a, G1b).",
    "G2_HOLM": "The 4 free DAS toward-BFS cells vs F-twin, one-sided exact McNemar on correct BFS, Holm.",
    "DECISION_POSITION": "R1: F-twin tokens[0:32] == c* -> i_d = 32. R2: else the first i in [8, 96] with "
                         "tokens[i-1] == c*[31] (body-indent token), p_B(i) + p_D(i) >= 0.5, p_D(i) >= 0.01 and no "
                         "algorithm-identifying string (deque, queue, visited, stack, heapq, heappush, popleft, "
                         "pop(0), dfs, bfs, recurs; case-insensitive) in decode(tokens[0:i]). Else NOT_REACHED "
                         "(no edit; intention to treat). Diagnostic only: the literal rule (first i <= 96 with "
                         "p_B + p_D >= 0.5).",
    "FREE_EDIT": "The edit f acts on the block-17 output of row b at the decode step whose INPUT token is response "
                 "index i_d - 1 (its logits choose token i_d); the edited state persists in the KV cache.",
    "REVERSE_RECOVERY": "reverse recovery_k = mean(dm_das) / mean(dm_full) over (base, source) pairs, bases = "
                        "forced-BFS F4/F5 x 4 display pairs + c*, sources = the 24 twin variants of the aligned "
                        "template (W4<->F4, W5<->F5); UNDEFINED if |mean dm_full| < 0.5 nat (then the absolute DAS "
                        "reverse is reported against 50 Haar rank-k subspaces). Base-clustered bootstrap CI.",
    "RETENTION": "retention_k = mean dy_dir(R_proj) / mean dy_dir(R_k) over iteration 7's 768 held-out forward "
                 "pairs, R_proj = qr(U64 U64^T R_k), U64 = top-64 PCs of the 120 twin-variant block-17 p_f states.",
    "FORWARD_RECOVERY": "iteration 7's statistic: median over held-out pairs with |dy_full| >= 1 of dy / dy_full "
                        "(seed 0 for the rule; seed median reported).",
    "DORMANT_FLAG": "(retention_k < 0.5 OR reverse recovery_k < 0.5) AND forward recovery_k >= 0.8 "
                    "[art_veI9l_Rb9wDY rule].",
    "LOW_NATURAL_VARIANCE": "share_k <= the 95th percentile of 1,000 Haar rank-k subspaces.",
    "VERDICT": "DORMANT/OFF-MANIFOLD HANDLE if DORMANT_FLAG; else UNDETERMINED if the reverse ratio is UNDEFINED; "
               "else SUFFICIENT, LOW-VARIANCE if LOW_NATURAL_VARIANCE; else USED VARIABLE.",
    "RESTORATION_GEN": "(correct DFS(REV-DAS) - correct DFS(G1a)) / (correct DFS(REV-FULL) - correct DFS(G1a)) on "
                       "S30; UNDEFINED if the denominator <= 2 programs.",
}
DROP_ORDER = ["F-RAND-r4-1.0", "F-DAS-s2-r4-bfs-1.0", "G1d", "HT30 extension", "F-DiM-bfs / F-DiM-dfs",
              "REV generation"]
NEVER_DROP = ["P-twin", "P-DAS-bfs", "G1a", "G1c", "F-twin", "F-DAS-r4-bfs-1.0", "G3 (i)-(iii) at k = 1, 2, 4, 8",
              "novelty audit"]

_ = (INPUTS,)
