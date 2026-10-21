def solve(n):
    primes = []
    for m in range(2, n):
        ok = True
        for p in primes:
            if p * p > m:
                break
            if m % p == 0:
                ok = False
                break
        if ok:
            primes.append(m)
    return len(primes)
