"""Order-free checker for T05_two_sum (copy of bench/common/checkers.py)."""

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _pairs(x):
    try:
        return [[int(a), int(b)] for a, b in x]
    except (TypeError, ValueError):
        return None


def check_two_sum(kwargs, expected, output):
    if not isinstance(output, (list, tuple)) or len(output) != 2 or not all(_is_int(v) for v in output):
        return False
    return sorted(output) == sorted(expected)


check = check_two_sum
