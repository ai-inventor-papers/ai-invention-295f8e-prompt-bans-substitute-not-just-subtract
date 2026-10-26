def solve(nums):
    def sort_count(a):
        if len(a) <= 1:
            return a, 0
        mid = len(a) // 2
        left, x = sort_count(a[:mid])
        right, y = sort_count(a[mid:])
        merged, inv, i, j = [], x + y, 0, 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i]); i += 1
            else:
                merged.append(right[j]); j += 1
                inv += 1
        merged += left[i:]
        merged += right[j:]
        return merged, inv
    return sort_count(list(nums))[1]
