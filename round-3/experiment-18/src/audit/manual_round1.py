"""Executor's manual pass, round 1 (the 30 programs of the first audit pool).  Each entry: final class, catalogue
label if a labeller miss, one-paragraph justification.  Classes follow the plan's definitions verbatim."""

MISS_CS = ("LABELLER MISS", "counting_sort",
           "Counts the occurrences of every value in a dict, then walks the distinct values in increasing order "
           "(sorted keys) subtracting counts until k is covered: the catalogue's counting-sort mechanism (count every "
           "value, walk the counts in value order) with a sparse dict instead of a range array. Passes the hidden tests "
           "and 3/3 extra random inputs; nearest known solutions are generic heap/k-th-smallest programs (similarity "
           "<= 0.38), nearest reference counting_sort. Not novel.")

RULES = [
    # (predicate on (task, code), final_class, catalogue_label, justification)
    (lambda t, c: t == "T03" and ".get(" in c and "sorted(" in c and ".keys()" in c, *MISS_CS),
    (lambda t, c: t == "T03" and "sorted(set(nums))" in c and ".count(" in c, "LABELLER MISS", "counting_sort",
     "Walks the sorted distinct values and accumulates list.count(value) until k is covered: counting over the value "
     "order (counting-sort mechanism) with a quadratic count. Correct on hidden and 3/3 extra inputs. Not novel."),
    (lambda t, c: t == "T03" and "nums.count = lambda" in c, "DEGENERATE", None,
     "Monkey-patches list methods with self-referential lambdas and fails every test; no algorithm."),
    (lambda t, c: t == "T06" and "nums.index(x)" in c and "enumerate" in c, "DEGENERATE", None,
     "Keeps elements whose index differs from their first occurrence (list.index inside a comprehension): a quadratic "
     "brute-force pairwise check that only passes because n is small. Not a catalogue method; degenerate by the "
     "class definition."),
    (lambda t, c: t == "T06" and "nums.count(" in c, "DEGENERATE", None,
     "Filters by list.count (quadratic brute force), sometimes followed by a broken neighbour comparison; fails or "
     "only passes on small inputs."),
    (lambda t, c: t == "T06" and "^=" in c, "DEGENERATE", None,
     "XOR of all values: an arithmetic trick that is wrong whenever the duplicate repeats or values are missing; "
     "fails the hidden tests."),
    (lambda t, c: t == "T06" and "expected" in c and "sum" in c, "CATALOGUE VARIANT", None,
     "Sum minus n(n+1)/2: the textbook arithmetic trick for exactly one duplicated value; wrong when the duplicate "
     "repeats (allowed by this spec), so it fails. Known method, not novel."),
    (lambda t, c: t == "T06", "DEGENERATE", None,
     "Adjacent comparison without sorting / sentinel loops: no valid duplicate-finding mechanism; fails."),
    (lambda t, c: t == "T1", "LABELLER MISS", "dfs",
     "Extends a single path list as a stack with a visited set and backtracks: depth-first search; fails the tests."),
    (lambda t, c: t == "T2" and "deque" in c, "CATALOGUE VARIANT", None,
     "Breadth-first search with visited flags on a weighted graph (a known, incorrect method for weighted shortest "
     "paths); fails the tests."),
    (lambda t, c: t == "T04" and "suffix automaton" in c.lower(), "CATALOGUE VARIANT", None,
     "Builds a suffix automaton of the needle and scans the haystack: a known string-matching structure outside the "
     "T04 catalogue; buggy (fails hidden tests, 1/3 extra). Known method, not novel."),
]
