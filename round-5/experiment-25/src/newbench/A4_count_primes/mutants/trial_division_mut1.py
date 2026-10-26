def solve(n):
    count = 0
    for m in range(2, n):
        if all(m % d for d in range(2, int(m ** 0.5))):
            count += 1
    return count
