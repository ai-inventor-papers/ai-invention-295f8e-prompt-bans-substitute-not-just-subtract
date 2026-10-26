def solve(strs):
    prefix = strs[0]
    for s in strs[1:2]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
    return prefix
