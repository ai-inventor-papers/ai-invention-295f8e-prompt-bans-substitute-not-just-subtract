import json, signal, sys, time, copy
sys.path.insert(0, sys.argv[1])
import cand, ref, checker
data = json.load(open(sys.argv[1] + '/cases.json'))
class TO(Exception): pass
def h(*a): raise TO()
signal.signal(signal.SIGALRM, h)
res = {'hidden_pass': 0, 'hidden_n': 0, 'extra_pass': 0, 'extra_n': 0, 'fail': []}
for c in data['tests']:
    res['hidden_n'] += 1
    signal.setitimer(signal.ITIMER_REAL, float(c.get('limit', 1.0)))
    try:
        out = cand.solve(**copy.deepcopy(c['kwargs']))
        signal.setitimer(signal.ITIMER_REAL, 0)
        ok = checker.check(c['kwargs'], c['expected'], out)
    except BaseException as e:
        signal.setitimer(signal.ITIMER_REAL, 0)
        ok = False
    res['hidden_pass'] += int(bool(ok))
    if not ok: res['fail'].append(c['case_id'])
for kw in data['extra']:
    res['extra_n'] += 1
    exp = ref.solve(**copy.deepcopy(kw))
    signal.setitimer(signal.ITIMER_REAL, 5.0)
    try:
        out = cand.solve(**copy.deepcopy(kw))
        signal.setitimer(signal.ITIMER_REAL, 0)
        ok = checker.check(kw, exp, out)
    except BaseException:
        signal.setitimer(signal.ITIMER_REAL, 0)
        ok = False
    res['extra_pass'] += int(bool(ok))
print(json.dumps(res))
