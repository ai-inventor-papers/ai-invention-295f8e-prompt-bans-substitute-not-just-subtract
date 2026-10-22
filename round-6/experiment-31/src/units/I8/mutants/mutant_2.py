def solve(nums):
    want = 1
    for v in sorted(nums):
        if v == want:
            want += 1
    return want if want > 1 else 2
