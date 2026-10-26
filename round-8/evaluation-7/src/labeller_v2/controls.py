"""Executor-written validation controls for the dictionary-form counting-sort extension (STEP A2 iii-iv).

Two positive controls (they must become counting_sort) and three negative controls (they must keep their class).
The two positives double as the 'constructed dictionary-form counting sorts' of the judge gate (STEP A4); they are
executor-constructed because the bench holds no independent exemplar of that form (a declared partial departure)."""

POSITIVE = {
    "pos_counter_cumulative": (
        "counting_sort",
        "from collections import Counter\n\n"
        "def solve(nums, k):\n"
        "    cnt = Counter(nums)\n"
        "    seen = 0\n"
        "    for v in sorted(cnt):\n"
        "        seen += cnt[v]\n"
        "        if seen >= k:\n"
        "            return v\n",
    ),
    "pos_dict_items_expand": (
        "counting_sort",
        "def solve(nums, k):\n"
        "    freq = {}\n"
        "    for x in nums:\n"
        "        freq[x] = freq.get(x, 0) + 1\n"
        "    out = []\n"
        "    for v, c in sorted(freq.items()):\n"
        "        out.extend([v] * c)\n"
        "    return out[k - 1]\n",
    ),
}

NEGATIVE = {
    # a dict used only as a memo, then a full sort of the input: must stay full_sort
    "neg_memo_then_full_sort": (
        "full_sort",
        "def solve(nums, k):\n"
        "    memo = {}\n"
        "    for x in nums:\n"
        "        if x not in memo:\n"
        "            memo[x] = abs(x)\n"
        "    return sorted(nums)[k - 1]\n",
    ),
    # value buckets of fixed width, recursing into the bucket that holds rank k: must stay other (no bucket class)
    "neg_bucket_select": (
        "other",
        "def solve(nums, k):\n"
        "    vals, lo, span = nums, -10000, 20001\n"
        "    while True:\n"
        "        width = max(1, span // 50)\n"
        "        nb = span // width + 1\n"
        "        buckets = [[] for _ in range(nb)]\n"
        "        for x in vals:\n"
        "            buckets[(x - lo) // width].append(x)\n"
        "        for i, b in enumerate(buckets):\n"
        "            if k <= len(b):\n"
        "                vals, lo = b, lo + i * width\n"
        "                break\n"
        "            k -= len(b)\n"
        "        if width == 1:\n"
        "            return vals[0]\n"
        "        span = width\n",
    ),
    # a heap over the (value, count) items of a Counter: must stay a heap class
    "neg_heap_over_counter": (
        "heapify_pop",
        "import heapq\n"
        "from collections import Counter\n\n"
        "def solve(nums, k):\n"
        "    items = list(Counter(nums).items())\n"
        "    heapq.heapify(items)\n"
        "    while True:\n"
        "        v, c = heapq.heappop(items)\n"
        "        if k <= c:\n"
        "            return v\n"
        "        k -= c\n",
    ),
}
