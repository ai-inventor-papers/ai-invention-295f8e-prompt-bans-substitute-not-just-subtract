def solve(nums):
    cand, cnt = nums[0], 0
    for x in nums:
        cnt += 1 if x == cand else -1
    return cand
