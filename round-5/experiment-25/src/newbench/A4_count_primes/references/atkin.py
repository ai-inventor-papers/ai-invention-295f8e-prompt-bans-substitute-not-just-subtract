def solve(n):
    if n < 3:
        return 0
    limit = n - 1
    sieve = [False] * (limit + 1)
    x = 1
    while x * x <= limit:
        y = 1
        while y * y <= limit:
            m = 4 * x * x + y * y
            if m <= limit and (m % 12 == 1 or m % 12 == 5):
                sieve[m] = not sieve[m]
            m = 3 * x * x + y * y
            if m <= limit and m % 12 == 7:
                sieve[m] = not sieve[m]
            m = 3 * x * x - y * y
            if x > y and m <= limit and m % 12 == 11:
                sieve[m] = not sieve[m]
            y += 1
        x += 1
    r = 5
    while r * r <= limit:
        if sieve[r]:
            for i in range(r * r, limit + 1, r * r):
                sieve[i] = False
        r += 1
    count = (2 <= limit) + (3 <= limit)
    for a in range(5, limit + 1):
        if sieve[a]:
            count += 1
    return count
