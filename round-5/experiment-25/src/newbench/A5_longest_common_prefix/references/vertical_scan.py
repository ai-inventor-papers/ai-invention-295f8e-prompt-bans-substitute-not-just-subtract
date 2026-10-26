def solve(strs):
    first = strs[0]
    for i in range(len(first)):
        c = first[i]
        for s in strs[1:]:
            if i >= len(s) or s[i] != c:
                return first[:i]
    return first
