def solve(tasks, n):
    counts = [0] * 26
    for t in tasks:
        counts[ord(t) - 65] += 1
    time = 0
    while True:
        counts.sort(reverse=True)
        if counts[0] == 0:
            return time
        used = 0
        for i in range(min(n + 1, 26)):
            if counts[i] == 0:
                break
            counts[i] -= 1
            used += 1
        time += n + 1 if any(counts) else used
