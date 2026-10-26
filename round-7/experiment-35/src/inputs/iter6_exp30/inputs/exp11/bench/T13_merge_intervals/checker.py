"""Order-free checker for T13_merge_intervals (copy of bench/common/checkers.py)."""

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _pairs(x):
    try:
        return [[int(a), int(b)] for a, b in x]
    except (TypeError, ValueError):
        return None


def check_merge(kwargs, expected, output):
    if not isinstance(output, (list, tuple)):
        return False
    p = _pairs(output)
    return p is not None and sorted(p) == expected


check = check_merge
