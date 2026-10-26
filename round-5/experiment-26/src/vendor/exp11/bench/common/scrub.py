"""Name scrubbing of forced programs (tokenize-based, position-exact edits).

* user-defined identifiers (functions, classes, parameters, assigned names, user attributes) whose sub-words
  contain an alias of ANY catalogue mode (global lexicon) are renamed (kmp_table -> table1, bfs -> helper1);
  API names (heapq.heappush, bisect, deque, ...) are never touched;
* comments and docstrings that name an alias are removed (a docstring that is the only statement becomes pass);
* the result must compile; scrub is idempotent; residual aliases are counted.
"""

from __future__ import annotations

import ast
import builtins
import io
import keyword
import re
import tokenize

from .catalogue import TASKS

STOP = {"a", "an", "the", "of", "with", "and", "on", "in", "by", "to", "for", "over", "sorting", "sort", "sorted",
        "search", "binary", "count", "counts", "set", "map", "table", "tree", "list", "array", "value", "values",
        "loop", "double", "single", "full", "find", "index", "operator", "built", "in", "first", "per", "test",
        "range", "o", "n", "n2", "2", "seen", "of", "most", "common", "path", "graph"}


def _words(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", s.lower())


def _build_lexicon():
    seqs = set()
    phrases = set()
    for t, c in TASKS.items():
        for m, al in c["aliases"].items():
            for a in al:
                w = [x for x in _words(a)]
                if not w:
                    continue
                phrases.add(" ".join(w))
                if len(w) == 1 and w[0] not in STOP:
                    seqs.add(tuple(w))
                elif len(w) > 1:
                    seqs.add(tuple(w))
        for m, (disp, _) in c["modes"].items():
            w = [x for x in _words(disp) if x not in ("a", "an", "the")]
            if w:
                phrases.add(" ".join(w))
    phrases = {p for p in phrases if p not in STOP and len(p) >= 2}
    return seqs, phrases


ALIAS_SEQS, ALIAS_PHRASES = _build_lexicon()
# substring matching only for distinctive algorithm tokens (exact sub-word matching covers the rest)
SUBSTR_ALIASES = {"quickselect", "heap", "memo", "kmp", "fenwick", "horspool", "bfs", "dfs", "dsu", "unionfind",
                  "kahn", "indegree", "tortoise", "floyd", "tails", "bucket", "lps", "rabin", "karp", "knuth"}
PROTECTED = {"solve"} | {a.strip() for c in TASKS.values()
                         for a in c["signature"].split("(", 1)[1].rstrip(")").split(",")}
PHRASE_RE = re.compile(r"(?<![a-z0-9])(" + "|".join(sorted((re.escape(p).replace(r"\ ", r"[\s_\-]+") for p in ALIAS_PHRASES),
                                                            key=len, reverse=True)) + r")(?![a-z0-9])")


def subwords(name: str) -> list[str]:
    parts = []
    for chunk in name.split("_"):
        parts += re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+", chunk)
    return [p.lower() for p in parts if p]


def name_has_alias(name: str) -> bool:
    sw = subwords(name)
    for seq in ALIAS_SEQS:
        k = len(seq)
        for i in range(len(sw) - k + 1):
            if tuple(sw[i:i + k]) == seq:
                return True
    low = name.lower()
    return any(a in low for a in SUBSTR_ALIASES)


def text_has_alias(text: str) -> bool:
    return PHRASE_RE.search(text.lower()) is not None


def _defined_names(tree: ast.AST) -> tuple[set[str], set[str], set[str]]:
    funcs, others, attrs = set(), set(), set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs.add(node.name)
            for a in node.args.args + node.args.kwonlyargs + node.args.posonlyargs:
                others.add(a.arg)
            if node.args.vararg:
                others.add(node.args.vararg.arg)
            if node.args.kwarg:
                others.add(node.args.kwarg.arg)
        elif isinstance(node, ast.ClassDef):
            funcs.add(node.name)
        elif isinstance(node, ast.Lambda):
            for a in node.args.args:
                others.add(a.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            others.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            attrs.add(node.attr)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            others.update(node.names)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            others.add(node.name)
    for node in ast.walk(tree):  # names introduced by imports are API names, never renamed
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                nm = (a.asname or a.name).split(".")[0]
                funcs.discard(nm)
                others.discard(nm)
    return funcs, others, attrs


def _docstring_spans(tree: ast.AST) -> list[tuple[int, int, bool]]:
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                if text_has_alias(first.value.value):
                    spans.append((first.lineno, first.end_lineno, len(node.body) == 1))
    return spans


def scrub_code(code: str) -> tuple[str, dict]:
    info = {"renamed": {}, "comments_removed": 0, "docstrings_removed": 0, "ok": True, "error": None}
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        info.update(ok=False, error=f"syntax: {e}")
        return code, info
    lines = code.split("\n")
    # 1) docstrings naming an alias
    spans = _docstring_spans(tree)
    for lo, hi, only in sorted(spans, reverse=True):
        indent = re.match(r"\s*", lines[lo - 1]).group(0)
        lines[lo - 1:hi] = [indent + "pass"] if only else []
        info["docstrings_removed"] += 1
    code = "\n".join(lines)
    tree = ast.parse(code)
    funcs, others, attrs = _defined_names(tree)
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
    used |= funcs | others | attrs | set(dir(builtins)) | set(keyword.kwlist)
    rename = {}
    for nm in sorted(funcs | others | attrs):
        if nm in PROTECTED or not name_has_alias(nm):
            continue
        rest = [w for w in subwords(nm) if not any(w in s for s in ALIAS_SEQS) and w not in SUBSTR_ALIASES
                and not any(a in w for a in SUBSTR_ALIASES)]
        base = "_".join(rest) if rest else ("helper" if nm in funcs else "var")
        if not base.isidentifier() or keyword.iskeyword(base):
            base = "var"
        i = 1
        while f"{base}{i}" in used:
            i += 1
        rename[nm] = f"{base}{i}"
        used.add(rename[nm])
    info["renamed"] = rename
    # 2) token edits: renames + alias comments
    edits = []
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError) as e:
        info.update(ok=False, error=f"tokenize: {e}")
        return code, info
    prev = None
    for tok in toks:
        if tok.type == tokenize.NAME and tok.string in rename:
            is_attr = prev is not None and prev.type == tokenize.OP and prev.string == "."
            if (not is_attr) or tok.string in attrs:
                edits.append((tok.start[0], tok.start[1], tok.end[1], rename[tok.string]))
        elif tok.type == tokenize.COMMENT and text_has_alias(tok.string):
            edits.append((tok.start[0], tok.start[1], tok.end[1], ""))
            info["comments_removed"] += 1
        if tok.type not in (tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT):
            prev = tok
    lines = code.split("\n")
    for row, c0, c1, rep in sorted(edits, key=lambda e: (e[0], -e[1])):
        ln = lines[row - 1]
        lines[row - 1] = ln[:c0] + rep + ln[c1:]
        if rep == "":
            lines[row - 1] = lines[row - 1].rstrip()
    out = "\n".join(l for i, l in enumerate(lines) if not (l.strip() == "" and code.split("\n")[i].strip().startswith("#")))
    try:
        compile(out, "<scrubbed>", "exec")
    except SyntaxError as e:
        info.update(ok=False, error=f"scrubbed does not compile: {e}")
    return out, info


def residual_aliases(code: str) -> int:
    """Alias mentions left in user-defined identifiers, comments or docstrings/strings."""
    n = 0
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return -1
    funcs, others, attrs = _defined_names(tree)
    n += sum(1 for nm in funcs | others | attrs if nm not in PROTECTED and name_has_alias(nm))
    try:
        for tok in tokenize.generate_tokens(io.StringIO(code).readline):
            if tok.type == tokenize.COMMENT and text_has_alias(tok.string):
                n += 1
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return -1
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
            f = node.body[0]
            if isinstance(f, ast.Expr) and isinstance(f.value, ast.Constant) and isinstance(f.value.value, str) \
                    and text_has_alias(f.value.value):
                n += 1
    return n


def scrub_response(text: str, code: str) -> tuple[str, str, dict]:
    """Return (scrubbed response text, scrubbed code, info): the code block is replaced by its scrubbed version,
    alias phrases in any prose around it are removed."""
    s_code, info = scrub_code(code)
    i = text.find(code)
    if i < 0:
        return text, s_code, dict(info, ok=False, error="code not found in response")
    pre, post = text[:i], text[i + len(code):]
    pre = PHRASE_RE.sub("", pre.lower()) if text_has_alias(pre) else pre
    post = PHRASE_RE.sub("", post.lower()) if text_has_alias(post) else post
    return pre + s_code + post, s_code, info
