import os


def solve(strs):
    return os.path.commonprefix(strs[:2])
