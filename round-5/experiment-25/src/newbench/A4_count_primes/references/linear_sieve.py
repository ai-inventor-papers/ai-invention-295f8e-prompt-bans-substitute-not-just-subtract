def solve(n):
    if n < 3:
        return 0
    comp = [False] * n
    primes = []
    for i in range(2, n):
        if not comp[i]:
            primes.append(i)
        for p in primes:
            if i * p >= n:
                break
            comp[i * p] = True
            if i % p == 0:
                break
    return len(primes)
