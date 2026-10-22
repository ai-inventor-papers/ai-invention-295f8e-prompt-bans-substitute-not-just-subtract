def solve(citations):
    a = sorted(citations, reverse=True)
    h = 0
    for i, c in enumerate(a):
        if c >= i + 1:
            h = i + 1
        else:
            break
    return h
