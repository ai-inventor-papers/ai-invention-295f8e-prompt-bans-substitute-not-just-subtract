TASK = {
    "T1": "grid", "T2": "shortest path", "T03": "kth smallest", "T04": "substring search", "T05": "two sum",
    "T06": "find duplicate", "T08": "Fibonacci", "T10": "connected components", "T11": "longest increasing subsequence",
    "T13": "merge intervals", "T14": "top-k frequent", "R1": "nonoverlapping intervals", "R2": "cycle detection",
    "R3": "topological order", "R6": "first and last position",
    "A1": "majority element", "A2": "maximum block sum", "A3": "trapped rain water", "A4": "count primes",
    "A5": "longest common prefix", "A6": "number of islands", "A7": "longest mirrored substring",
    "A8": "jump game", "A9": "median of two sorted lists",
    "B1": "missing number", "B2": "single number", "B3": "minimum spanning tree weight", "B4": "integer square root",
    "B5": "all subsets", "B6": "valid anagram", "B7": "count inversions",
}
ALG = {
    "full_sort": "full sort", "quickselect": "quickselect", "size_k_heap": "size-k heap", "heapify_pop": "heapify and pop",
    "counting_sort": "counting sort", "median_of_medians": "median of medians", "union_find": "union find", "dfs": "DFS",
    "bfs": "BFS", "label_propagation": "label propagation", "dijkstra": "Dijkstra", "bf_spfa": "Bellman-Ford/SPFA",
    "floyd": "Floyd-Warshall", "floyd_warshall": "Floyd-Warshall", "dial": "Dial", "bidir_dijkstra": "bidirectional Dijkstra",
    "hash_map": "hash map", "brute_force": "brute force", "sort_two_pointers": "sort and two pointers",
    "sort_binary_search": "sort and binary search", "two_pointers": "two pointers", "hash_set": "hash set",
    "index_marking": "index marking", "sort_adjacent": "sort and adjacent check", "floyd_cycle": "Floyd cycle detection",
    "binary_search_values": "binary search on values", "builtin": "built-in find", "naive": "naive", "kmp": "KMP",
    "rabin_karp": "Rabin-Karp", "z_algorithm": "Z algorithm", "horspool": "Boyer-Moore-Horspool",
    "memo_recursion": "memoised recursion", "iteration": "iteration", "matrix_power": "matrix power",
    "fast_doubling": "fast doubling", "quadratic_dp": "quadratic DP", "patience_bisect": "patience sorting with bisect",
    "fenwick": "Fenwick tree", "sort_sweep": "sort and sweep", "interval_tree": "interval tree", "heap": "heap",
    "sort_by_count": "sort by count", "bucket_sort": "bucket sort", "quickselect_counts": "quickselect on counts",
    "greedy_end": "greedy by end", "dp_bisect": "DP with bisect", "dag_longest_path": "DAG longest path",
    "kahn": "Kahn", "dfs_postorder": "DFS postorder", "source_removal": "source removal", "layering": "topological layering",
    "binary_search": "binary search", "bisect_module": "bisect module", "exponential_search": "exponential search",
    "linear_scan": "linear scan", "binary_expand": "binary expand", "dfs_parent": "DFS with parent",
    "bfs_parent": "BFS with parent", "edge_count": "edge count", "other": "other", "disputed": "disputed",
    "astar_gbfs": "A*", "bibfs": "bidirectional BFS", "iddfs": "IDDFS", "dijkstra_unit": "unit weight Dijkstra",
    "boyer_moore_vote": "Boyer-Moore vote", "hash_count": "hash count", "sort_middle": "sort and take middle",
    "divide_conquer": "divide and conquer", "randomized_verify": "randomised verify", "bit_count": "bit count",
    "library_mode": "library mode", "kadane": "Kadane", "prefix_min": "prefix minimum", "segment_tree": "segment tree",
    "prefix_suffix_max": "prefix and suffix maxima", "monotonic_stack": "monotonic stack", "peak_split": "peak split",
    "eratosthenes": "Eratosthenes sieve", "trial_division": "trial division", "linear_sieve": "linear sieve",
    "segmented_sieve": "segmented sieve", "sundaram": "Sundaram sieve", "atkin": "Atkin sieve",
    "horizontal_scan": "horizontal scan", "vertical_scan": "vertical scan", "sort_ends": "sort and compare ends",
    "binary_search_length": "binary search on length", "trie": "trie", "library_commonprefix": "library common prefix",
    "expand_center": "expand around centre", "dp_table": "DP table", "manacher": "Manacher",
    "greedy": "greedy", "dp": "DP", "bfs_indices": "BFS over indices", "merge_two_pointers": "merge with two pointers",
    "partition_binary_search": "partition binary search", "heap_merge": "heap merge", "concat_sort": "concatenate and sort",
    "arithmetic_sum": "arithmetic sum", "xor_fold": "XOR fold", "kruskal": "Kruskal", "prim_heap": "Prim with heap",
    "float_sqrt": "floating-point sqrt", "backtracking": "backtracking", "iterative_doubling": "iterative doubling",
    "sort_compare": "sort and compare", "merge_sort_count": "merge sort count",
    "sorted_insertion_bisect": "sorted insertion with bisect", "fenwick_tree": "Fenwick tree", "newton": "Newton",
    "dfs_flood": "DFS flood", "bfs_flood": "BFS flood",
}
def alg(x):
    if x is None:
        return "none"
    return ALG.get(x, x.replace("_", " "))
def task(x):
    return TASK.get(x, x)
def comp(d, n=None):
    items = sorted(d.items(), key=lambda kv: -kv[1])
    if n:
        items = items[:n]
    return ", ".join(f"{alg(k)} {v}" for k, v in items) if items else "none"
