def solve(n):
    comp = [False] * max(n, 2)
    primes = []
    for i in range(2, n):
        if not comp[i]:
            primes.append(i)
        for p in primes:
            if i * p >= n:
                break
            comp[i * p] = True
    return len(primes) + 1
