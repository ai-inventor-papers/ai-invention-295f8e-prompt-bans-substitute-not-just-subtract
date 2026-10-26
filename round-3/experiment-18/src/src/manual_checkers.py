"""Checkers for the manual pass (stdlib only; loaded by the bench sandbox runner)."""


def _t1(kw, exp, got):
    grid, s, g = kw["grid"], tuple(kw["start"]), tuple(kw["goal"])
    if not exp:
        return got == [] or got is None
    try:
        path = [tuple(p) for p in got]
    except TypeError:
        return False
    if not path or path[0] != s or path[-1] != g:
        return False
    R, C = len(grid), len(grid[0])
    for (a, b), (c, d) in zip(path, path[1:]):
        if abs(a - c) + abs(b - d) != 1:
            return False
    return all(0 <= r < R and 0 <= c < C and grid[r][c] == "." for r, c in path)


def _eq(kw, exp, got):
    return got == exp


CHECK = {"T1": _t1, "T2": _eq, "T03": _eq, "T04": _eq, "T06": _eq, "T10": _eq}
