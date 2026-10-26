import os
from pathlib import Path
# Artifact folder: set EVAL5_DIR; defaults to the sibling folder art_aRTQM6CQ0Dre of the published repository.
ART = Path(os.environ.get('EVAL5_DIR', str(Path(__file__).resolve().parents[2] / 'art_aRTQM6CQ0Dre')))
import csv, math, random
rows=list(csv.DictReader(open(str(ART / 'tables/movability_units.csv'))))
core=[r for r in rows if r['core13']=='True']
def rank(x):
    s=sorted(range(len(x)),key=lambda i:x[i]); r=[0]*len(x); i=0
    while i<len(x):
        j=i
        while j+1<len(x) and x[s[j+1]]==x[s[i]]: j+=1
        for k in range(i,j+1): r[s[k]]=(i+j)/2+1
        i=j+1
    return r
def spear(a,b):
    ra,rb=rank(a),rank(b); n=len(a); ma=sum(ra)/n; mb=sum(rb)/n
    num=sum((x-ma)*(y-mb) for x,y in zip(ra,rb)); den=math.sqrt(sum((x-ma)**2 for x in ra)*sum((y-mb)**2 for y in rb))
    return num/den
beta=[float(r['beta']) for r in core]; E=[float(r['E']) for r in core]
bc=[float(r['beta_correct_only']) for r in core]
print('n',len(core),'rho',round(spear(beta,E),3),'rho correct-only beta',round(spear(bc,E),3))
for k in ['R1_opening_margin','R4_novelty_excess','R7_twin_modal_share','K','R6_runtime_merit']:
    print(k, round(spear([float(r[k]) for r in core],E),3))
# Bonett-Wright CI
r=spear(beta,E); n=len(core)
z=math.atanh(r); se=math.sqrt((1+r*r/2)/(n-3))
print('BW', round(math.tanh(z-1.96*se),2), round(math.tanh(z+1.96*se),2))
# permutation p one-sided
random.seed(0); cnt=0; N=20000
for _ in range(N):
    e=E[:]; random.shuffle(e)
    if spear(beta,e)>=r-1e-12: cnt+=1
print('perm p',cnt/N)
# power at true rho 0.6 via sampling bivariate normal then... approximate
