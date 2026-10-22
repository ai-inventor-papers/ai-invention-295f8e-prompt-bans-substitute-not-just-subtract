def solve(nums):
    want = 1
    for v in sorted(nums):
        if v == want:
            want += 1
        elif v > want:
            break
    return want
