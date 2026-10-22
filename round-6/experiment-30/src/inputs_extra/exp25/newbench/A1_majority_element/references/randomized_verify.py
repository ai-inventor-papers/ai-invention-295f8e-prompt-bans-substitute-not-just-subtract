import random


def solve(nums):
    n = len(nums)
    while True:
        c = random.choice(nums)
        if nums.count(c) > n // 2:
            return c
