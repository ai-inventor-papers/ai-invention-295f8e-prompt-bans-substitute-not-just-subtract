def solve(strs):
    primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101]
    groups = {}
    for w in strs:
        key = 1
        for ch in w:
            key *= primes[ord(ch) - 97]
        groups.setdefault(key, []).append(w)
    return list(groups.values())
