"""A8 checker: the boolean answer (bools or 0/1 ints accepted)."""


def check(kwargs, expected, output):
    return isinstance(output, (bool, int)) and output in (0, 1, True, False) and bool(output) == bool(expected)
