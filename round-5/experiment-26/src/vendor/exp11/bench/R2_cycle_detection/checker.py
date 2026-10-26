"""Order-free checker for R2_cycle_detection (copy of bench/common/checkers.py)."""

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _pairs(x):
    try:
        return [[int(a), int(b)] for a, b in x]
    except (TypeError, ValueError):
        return None


def check_bool(kwargs, expected, output):
    return isinstance(output, (bool, int)) and bool(output) == expected


check = check_bool
