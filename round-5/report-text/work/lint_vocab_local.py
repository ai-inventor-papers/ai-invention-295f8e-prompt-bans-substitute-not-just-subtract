"""Run the pipeline's vocabulary lint on the draft and attribute each flag to old or new text."""
import importlib.util, json, sys
from pathlib import Path

REL = Path('aii_pipeline/src/aii_pipeline/utils/prose_lint.py')
LINT = next(p / REL for p in Path(__file__).resolve().parents if (p / REL).is_file())
spec = importlib.util.spec_from_file_location('prose_lint', LINT)
pl = importlib.util.module_from_spec(spec); sys.modules['prose_lint'] = pl; spec.loader.exec_module(pl)

ROOT = Path(__file__).resolve().parents[1]
terms = json.loads((ROOT / 'domain_terms.json').read_text())


def flagged(text):
    body = pl.strip_latex(text)
    known, blob = pl._known_vocabulary(terms, None)
    out = {}
    for sentence, window in pl._sentence_windows(body):
        cands = [(m, m) for m in pl.HYPHEN_COMPOUND_RE.findall(sentence)]
        cands += [(m, f'"{m}"') for m in pl.QUOTED_COINAGE_RE.findall(sentence)]
        for raw, shown in cands:
            key = pl._fold(raw)
            if ' ' not in key and '-' not in key:
                continue
            spaced = key.replace('-', ' ')
            if key in pl._HYPHEN_ALLOW or {key, spaced} & known:
                continue
            if key in blob or spaced in blob:
                continue
            if pl._is_defined(window, key):
                continue
            out.setdefault(key, []).append(sentence[:140])
    return out


if __name__ == '__main__':
    draft = (ROOT / 'paper_draft.md').read_text()
    old = (ROOT / 'work' / 'paper_draft_before_iter5.md').read_text()
    issues = pl.lint_vocabulary(draft, terms)
    for i in issues:
        print('ISSUE:', i[:600]); print()
    f_new, f_old = flagged(draft), flagged(old)
    codes_new = sorted(set(pl.BARE_CODE_RE.findall(pl.strip_latex(draft))))
    codes_old = sorted(set(pl.BARE_CODE_RE.findall(pl.strip_latex(old))))
    print('codes now', codes_new, '| codes in old draft', codes_old)
    intro = {k: v for k, v in f_new.items() if k not in f_old}
    print('flagged now', len(f_new), '| flagged in old draft', len(f_old), '| introduced', len(intro))
    if '-v' in sys.argv:
        for k in sorted(intro):
            print(f'{k!r:45s} x{len(intro[k])} :: {intro[k][0]}')
