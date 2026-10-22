"""A3 checker: exact integer answer (unique by the spec)."""


def check(kwargs, expected, output):
    return isinstance(output, int) and not isinstance(output, bool) and output == expected
