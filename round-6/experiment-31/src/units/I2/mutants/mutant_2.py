def solve(strs):
    groups = {}
    for w in strs:
        key = "".join(sorted(w))
        groups[key] = [w]
    return list(groups.values())
