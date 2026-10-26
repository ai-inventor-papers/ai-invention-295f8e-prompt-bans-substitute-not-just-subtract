import json, sys, collections, statistics as st
# usage: python3 -I base_checks.py <path to the base-model artifact (gen_art_experiment_50)>
P=sys.argv[1]
b1=json.load(open(P+'/results/b1_summary.json'))
for u,uv in b1['units'].items():
    for f,fv in uv['forks'].items():
        c=fv[fv['primary_mode']]
        print('B1',f,fv['primary_mode'],'gain',round(sum(c['gain'])/len(c['gain']),3),'pD instr',round(c['pD_instr_mean'],3),'pD base',round(c['pD_base_mean'],3),
              'base mass unmapped',round(c['base_mass_unmapped'],3),'JS ratio',round(fv['phrasing']['ratio_fork_vs_matched'],2))
rs=json.load(open(P+'/results/random_sets.json'))
s=json.load(open(P+'/results/b2_summary.json'))
for u in ('B3','T10'):
    U=s['units'][u]
    print('B2',u,'gap',round(U['gap_mean'],2),'fork stack share',round(U['arms']['FSTACK']['share'],2),'mean of per-prompt ratios',round(U['arms']['FSTACK']['share_mean_of_ratios'],2))
    for fam in ('R','Rpure'):
        sets=rs[u][fam]['sets']
        dist=collections.Counter(len(set(map(str,x))) for x in sets)
        n=U['null_'+fam]
        print('   null',fam,'median',round(n['median'],2),'p',round(n['empirical_p_upper'],3),'sets by number of distinct components',dict(sorted(dist.items())))
    print('   null Rscaled median',round(U['null_Rscaled']['median'],2),'p',round(U['null_Rscaled']['empirical_p_upper'],3))
b3=json.load(open(P+'/results/b3_summary.json'))
rows=[json.loads(l) for l in open(P+'/results/b3_heldout_rows.jsonl')]
for k in ('aligned|ablate|mlp|L0|H-1|COND','aligned|steer|mlp|L0|H-1|COND'):
    d=b3['per_node'][k]['d_per_prompt']
    sides=[r['side'] for r in rows]
    by=collections.defaultdict(list)
    for x,sd in zip(d,sides): by[sd].append(x)
    print('B3',k,'mean',round(st.mean(d),2),{sd:[round(x,2) for x in v] for sd,v in by.items()})
