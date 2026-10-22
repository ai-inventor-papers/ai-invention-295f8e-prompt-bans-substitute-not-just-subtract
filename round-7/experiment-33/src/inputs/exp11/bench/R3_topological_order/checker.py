"""Order-free checker for R3_topological_order (copy of bench/common/checkers.py)."""

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _pairs(x):
    try:
        return [[int(a), int(b)] for a, b in x]
    except (TypeError, ValueError):
        return None


def check_topo(kwargs, expected, output):
    if not isinstance(output, (list, tuple)):
        return False
    n = kwargs["n"]
    if expected == []:
        return len(output) == 0
    if len(output) != n or not all(_is_int(v) for v in output) or sorted(output) != list(range(n)):
        return False
    pos = {v: i for i, v in enumerate(output)}
    return all(pos[b] < pos[a] for a, b in kwargs["prerequisites"])


check = check_topo
