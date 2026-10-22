def solve(strs):
    groups = {}
    for w in strs:
        cnt = [0] * 26
        for ch in w:
            cnt[ord(ch) - ord("a")] += 1
        groups.setdefault(tuple(cnt), []).append(w)
    return list(groups.values())
