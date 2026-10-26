"""A9 checker: a number within 1e-6 of the median."""


def check(kwargs, expected, output):
    return isinstance(output, (int, float)) and not isinstance(output, bool) and abs(output - expected) <= 1e-6
