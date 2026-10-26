import sys, json, torch
sys.path.insert(0, '.')
from common import read_json, DATA_DIR
from mb.score import Scorer, program_items
from mb.prompts import load_frozen
ps = read_json(DATA_DIR / 'program_sets.json')
progs = ps['t1:bfs']['programs'][:4] + ps['t1:gbfs']['programs'][:4]
prompt = load_frozen()['tasks']['t1']['conditions']['baseline'][0]['prompt']
sc = Scorer()
items = program_items(sc, progs, with_pos=False)
batched = sc.score(prompt, items)['l']
single = {}
for it in items:
    single[it['uid']] = sc.score(prompt, [it])['l'][it['uid']]
pids = sc.chat_ids(prompt)
full = {}
with torch.no_grad():
    for it in items:
        ids = torch.tensor([pids + it['resp_ids']], device='cuda')
        lg = sc.head(sc.model.model(input_ids=ids).last_hidden_state)[0]
        lp = torch.log_softmax(lg[len(pids)-1:-1], -1)
        full[it['uid']] = float(lp.gather(-1, ids[0, len(pids):, None]).sum())
out = []
for it in items:
    u = it['uid']
    out.append({'n_tok': len(it['resp_ids']), 'cached_b8': round(batched[u], 3), 'cached_b1': round(single[u], 3), 'full': round(full[u], 3),
                'b8_minus_full': round(batched[u]-full[u], 3), 'b1_minus_full': round(single[u]-full[u], 3), 'b8_minus_b1': round(batched[u]-single[u], 3)})
for o in out: print(o)
json.dump(out, open('results/scoring_diag.json', 'w'), indent=1)
