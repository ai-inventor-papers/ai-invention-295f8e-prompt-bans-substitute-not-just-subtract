def solve(x):
    ans = 0
    while x:
        x &= x - 1
        ans += 1
    return ans
