"""Order-free validity checkers, one per task (stdlib only; loaded by the sandbox runner by file path).

check(kwargs, expected, output) -> bool.  kwargs is a fresh copy of the case input.
"""


def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _pairs(x):
    try:
        return [[int(a), int(b)] for a, b in x]
    except (TypeError, ValueError):
        return None


def check_scalar_int(kwargs, expected, output):
    return _is_int(output) and output == expected


def check_two_sum(kwargs, expected, output):
    if not isinstance(output, (list, tuple)) or len(output) != 2 or not all(_is_int(v) for v in output):
        return False
    return sorted(output) == sorted(expected)


def check_merge(kwargs, expected, output):
    if not isinstance(output, (list, tuple)):
        return False
    p = _pairs(output)
    return p is not None and sorted(p) == expected


def check_topk(kwargs, expected, output):
    if not isinstance(output, (list, tuple)) or not all(_is_int(v) for v in output):
        return False
    return len(output) == len(expected) and sorted(output) == sorted(expected)


def check_bool(kwargs, expected, output):
    return isinstance(output, (bool, int)) and bool(output) == expected


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


def check_first_last(kwargs, expected, output):
    return isinstance(output, (list, tuple)) and len(output) == 2 and all(_is_int(v) for v in output) and \
        list(output) == expected


CHECK = {
    "T03": check_scalar_int, "T04": check_scalar_int, "T05": check_two_sum, "T06": check_scalar_int,
    "T08": check_scalar_int, "T10": check_scalar_int, "T11": check_scalar_int, "T13": check_merge,
    "T14": check_topk, "R1": check_scalar_int, "R2": check_bool, "R3": check_topo, "R6": check_first_last,
}
