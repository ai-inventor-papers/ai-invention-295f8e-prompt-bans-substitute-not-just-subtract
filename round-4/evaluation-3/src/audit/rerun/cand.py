def solve(nums, k):
    """
    Returns the k-th smallest value in the list nums.

    :param nums: A list of integers.
    :type nums: list[int]
    :param k: The index of the value to find (1-indexed).
    :type k: int
    :return: The k-th smallest value in nums.
    :rtype: int
    """

    def count_less(v):
        # Count how many values in nums are less than v
        return sum(1 for x in nums if x < v)

    # Sort the values to find the k-th smallest
    values = sorted(set(nums))  # Remove duplicates to avoid false count

    # Use binary search to find the k-th smallest value
    low, high = 0, len(values) - 1
    while low < high:
        mid = (low + high + 1) // 2  # +1 to round up in case of equal counts
        if count_less(values[mid]) < k:
            low = mid
        else:
            high = mid - 1

    return values[low]
