def solve(n):
    ans = []
    for i in range(n + 1):
        c = 0
        x = i
        while x:
            x &= x - 1
            c += 1
        ans.append(c)
    return ans
