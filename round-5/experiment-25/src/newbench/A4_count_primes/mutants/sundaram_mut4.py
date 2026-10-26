def solve(n):
    k = (n - 2) // 2
    marked = [False] * (k + 1)
    for i in range(1, k + 1):
        for j in range(i, k + 1):
            if i + j + 2 * i * j > k:
                break
            marked[i + j + 2 * i * j] = True
    return sum(1 for m in range(1, k + 1) if not marked[m])
