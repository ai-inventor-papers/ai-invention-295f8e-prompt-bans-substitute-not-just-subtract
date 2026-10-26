import sys, time, json
sys.path.insert(0, "src")
from config import setup_logging, seed_unit, MAX_TOKENS_SHORT
setup_logging("smoke")
from prompts import neutral_twins, ids_of
from client import run_batch
tw = {t: neutral_twins(t) for t in ["T1", "T2"]}
reqs = []
for t in ["T1", "T2"]:
    for i, w in enumerate(["W1","W2","W3","W4","W5"]*4):
        reqs.append({"prompt_ids": tw[t][w]["ids"], "seed": seed_unit(1000 + 100*(t=="T2") + i), "max_tokens": MAX_TOKENS_SHORT})
out, dt = run_batch("bf16", reqs)
print("n", len(out), "dt", dt, "mean_tok", sum(o["n_new_tokens"] for o in out)/len(out))
print(out[0]["text"][:300])
print(out[0]["token_ids"][:20], out[0]["finish_reason"])
# veto check: veto ' deque' style tokens
v = [ids_of(" deque"), ids_of("deque"), ids_of(" popleft"), ids_of("popleft")]
print("veto seqs", v)
reqs2 = [{"prompt_ids": tw["T1"]["W1"]["ids"], "seed": seed_unit(5000+i), "max_tokens": MAX_TOKENS_SHORT, "veto": v} for i in range(8)]
out2, dt2 = run_batch("bf16", reqs2)
for o in out2:
    ids = o["token_ids"]
    occ = sum(1 for s in v for j in range(len(ids)-len(s)+1) if ids[j:j+len(s)] == s)
    print("occ", occ, "deque" in o["text"], "popleft" in o["text"], o["text"][:120].replace("\n"," | "))
