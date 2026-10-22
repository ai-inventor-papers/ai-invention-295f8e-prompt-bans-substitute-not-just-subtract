def solve(n):
    def step(x):
        s = 0
        while x:
            x, d = divmod(x, 10)
            s += d * d
        return s
    slow, fast = n, step(n)
    while fast != 1 and slow != fast:
        slow = step(slow)
        fast = step(step(fast))
    return fast == 1
