"""Executor's manual pass, round 2 (the 22 programs added by the long-form arms).  Applied before round 1 (later
rounds are more specific for the new programs; overlapping rules give the same class)."""

RULES = [
    (lambda t, c: t == "T2" and "stack" in c and ".pop()" in c, "CATALOGUE VARIANT", None,
     "Depth-first exploration with a LIFO stack that re-pushes a node whenever its distance improves and prunes "
     "entries worse than the best known distance: a generic label-correcting shortest-path search (the Bellman-Ford/"
     "SPFA family with a stack instead of a FIFO queue). Correct on hidden tests and 3/3 extra inputs; nearest known "
     "solutions are Mercury network-delay-time programs. Known method, not novel."),
    (lambda t, c: t == "T03" and "sorted(" in c and ("while left" in c or "while low" in c), "CATALOGUE VARIANT", None,
     "Counts every value, sorts the distinct values and binary-searches the cumulative counts (or recomputes them per "
     "probe): counting-sort selection with a binary search over prefix sums of the counts. A hybrid of two textbook "
     "steps; correct on hidden tests and 3/3 extra inputs. Not novel."),
    (lambda t, c: t == "T03" and "sorted(" in c and ".keys()" in c, "LABELLER MISS", "counting_sort",
     "Counts every value (Counter/defaultdict/dict), walks the distinct values in sorted order accumulating counts "
     "until k is covered: the catalogue's counting-sort mechanism with a sparse map. Correct on hidden tests and 3/3 "
     "extra inputs; nearest known solutions include KodCode counting-sort programs. Not novel."),
    (lambda t, c: t == "T04" and "needle_freq" in c, "LABELLER MISS", "naive",
     "Slides a window over the haystack, rejects windows whose character histogram differs from the needle's, then "
     "compares the window with the needle: the naive sliding-window comparison behind a count filter (slower than plain "
     "naive). Correct on hidden tests and 3/3 extra inputs. Not novel."),
    (lambda t, c: t == "T06" and "bitset" in c, "LABELLER MISS", "hash_set",
     "Keeps a bit-vector of seen values and returns the first value whose bit is already set: the hash-set-of-seen-"
     "values mechanism with an integer bitset as the set. Correct on hidden tests and 3/3 extra inputs. Not novel."),
]
