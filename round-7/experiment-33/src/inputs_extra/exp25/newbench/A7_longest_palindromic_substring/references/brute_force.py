def solve(s):
    n = len(s)
    for length in range(n, 0, -1):
        for i in range(n - length + 1):
            sub = s[i:i + length]
            if sub == sub[::-1]:
                return sub
    return s[:1]
