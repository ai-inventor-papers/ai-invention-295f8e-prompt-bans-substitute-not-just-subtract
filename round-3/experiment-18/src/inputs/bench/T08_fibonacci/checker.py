"""Order-free checker for T08_fibonacci (copy of bench/common/checkers.py)."""

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _pairs(x):
    try:
        return [[int(a), int(b)] for a, b in x]
    except (TypeError, ValueError):
        return None


def check_scalar_int(kwargs, expected, output):
    return _is_int(output) and output == expected


check = check_scalar_int
