import csv, json, ast
A=str(__import__("pathlib").Path(__file__).resolve().parents[3] / 'round-3/evaluation-2/src')
NAME={'bfs':'BFS','dfs':'DFS','bibfs':'bidirectional BFS','iddfs':'IDDFS','astar_gbfs':'A*','dijkstra':'Dijkstra','bf_spfa':'Bellman-Ford/SPFA','bidijkstra':'bidirectional Dijkstra','floyd':'Floyd-Warshall','dial':'Dial','other':'other','astar':'A*','gbfs':'greedy best first','idastar':'IDA*'}
def nm(x):
    if x is None or x=='' : return 'n/a'
    return NAME.get(x,x)
rows=list(csv.DictReader(open(f'{A}/tables/c1_argmax_vs_landing.csv')))
print('| Model | Task | Draw and event | Banned | Kind | Attempted not banned (labels) | Correct not banned | Argmax of gain (neutral) | Argmax of residual (neutral) | Argmax of implied mass |')
print('|-|-|-|-|-|-|-|-|-|-|')
for r in rows:
    if not r['banned'] or '+' in r['banned']: continue
    m='Qwen3-8B' if 'Qwen' in r['model'] else 'Llama-3.1-8B'
    task='Grid' if r['task']=='t1' else 'Shortest path'
    ev=r['event'].split('|')[0]+' '+r['event'].split('|')[2]
    ac=ast.literal_eval(r['attempted_counts']); cc=ast.literal_eval(r['correct_nonbanned_counts'])
    banned=r['banned']
    ac2={k:v for k,v in ac.items() if k!=banned}
    s=', '.join(f'{nm(k)} {v}' for k,v in sorted(ac2.items(), key=lambda kv:-kv[1]))
    c=', '.join(f'{nm(k)} {v}' for k,v in sorted(cc.items(), key=lambda kv:-kv[1])) or 'none'
    kind={'modal':'modal','absent-mode (sham)':'absent (sham)'}.get(r['ban_kind'],r['ban_kind'])
    def hit(a,h):
        if a in ('',None): return 'n/a'
        return nm(a)+(' (hit)' if h=='True' else '')
    print(f"| {m} | {task} | {ev} | {nm(banned)} | {kind} | {s} | {c} | {hit(r['argmax_Gbar_neutral'],r['hit_Gbar_neutral'])} | {hit(r['argmax_s_neutral'],r['hit_s_neutral'])} | {hit(r['argmax_mass'],r['hit_mass'])} |")
