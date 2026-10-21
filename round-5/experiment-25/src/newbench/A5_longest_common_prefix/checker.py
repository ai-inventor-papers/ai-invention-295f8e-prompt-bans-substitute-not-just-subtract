"""A5 checker: exact string answer (unique by the spec)."""


def check(kwargs, expected, output):
    return isinstance(output, str) and output == expected
