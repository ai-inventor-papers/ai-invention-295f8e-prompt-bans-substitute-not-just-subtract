_T = [0] * 256
for _i in range(1, 256):
    _T[_i] = _T[_i >> 1] + (_i & 1)


def solve(x):
    return _T[x & 255] + _T[(x >> 8) & 255] + _T[(x >> 16) & 255] + _T[(x >> 24) & 255]
