def solve(s):
    pairs = {"(": ")", "[": "]", "{": "}"}
    n = len(s)

    def seq(i):
        while i < n and s[i] in pairs:
            j = seq(i + 1)
            if j < 0 or j >= n or s[j] != pairs[s[i]]:
                return -1
            i = j + 1
        return i

    return seq(0) == n
