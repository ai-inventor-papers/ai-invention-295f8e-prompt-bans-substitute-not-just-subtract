"""Order-free checker for R6_first_last_position (copy of bench/common/checkers.py)."""

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _pairs(x):
    try:
        return [[int(a), int(b)] for a, b in x]
    except (TypeError, ValueError):
        return None


def check_first_last(kwargs, expected, output):
    return isinstance(output, (list, tuple)) and len(output) == 2 and all(_is_int(v) for v in output) and \
        list(output) == expected


check = check_first_last
