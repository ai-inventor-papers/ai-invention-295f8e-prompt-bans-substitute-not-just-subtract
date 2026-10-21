"""A7 checker (order-free): the output must be a substring of s that reads the same both ways and has the maximum
length (the expected answer's length)."""


def check(kwargs, expected, output):
    s = kwargs["s"]
    return isinstance(output, str) and len(output) == len(expected) and output == output[::-1] and output in s
