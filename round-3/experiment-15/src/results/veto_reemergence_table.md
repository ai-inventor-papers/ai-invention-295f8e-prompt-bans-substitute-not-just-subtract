| event | round | vetoed n-grams (decoded) | A share after veto | hit rows | hits in code | re-emergence imports |
|---|--:|---|--:|--:|--:|---|
| T03|modal|full_sort | 1 | ',' | 0.20 | 50 | 1.00 | import heapq (1); import random (1) |
| T04|modal|naive | 1 | '1):\n' | 0.44 | 31 | 1.00 |  |
| T04|modal|naive | 2 | '1):\n' + '1):' | 0.42 | 31 | 1.00 |  |
| T04|modal|naive | 3 | '1):\n' + '1):' + ' if haystack[i' | 0.54 | 41 | 1.00 |  |
| T06|modal|hash_set | 1 | ' nums:\n       ' | 0.38 | 26 | 1.00 |  |
| T06|modal|hash_set | 2 | ' nums:\n       ' + ' [' | 0.26 | 28 | 1.00 |  |
| T06|modal|hash_set | 3 | ' nums:\n       ' + ' [' + '[num]' | 0.26 | 28 | 1.00 |  |
| T05|modal|hash_map | 1 | ' i]\n' | 0.93 | 45 | 0.93 | from typing import List (1); from collections import defaultdict (1) |
| T05|modal|hash_map | 2 | ' i]\n' + '[num' | 0.95 | 46 | 0.93 |  |
| T05|modal|hash_map | 3 | ' i]\n' + '[num' + '(num' | 0.92 | 47 | 0.94 | import bisect (1); from typing import List (1) |
| T10|modal|union_find | 1 | ' def find' | 0.59 | 31 | 1.00 |  |
| T10|modal|union_find | 2 | ' def find' + ' root' | 0.57 | 32 | 1.00 |  |
| T10|modal|union_find | 3 | ' def find' + ' root' + '    parent' | 0.23 | 32 | 1.00 |  |
| R1|modal|greedy_end | 1 | '.sort' | 0.60 | 46 | 1.00 | import unittest (1); import sys (1) |
| R1|modal|greedy_end | 2 | '.sort' + ' = sorted' | 0.48 | 49 | 1.00 |  |
| R1|modal|greedy_end | 3 | '.sort' + ' = sorted' + ' intervals =' | 0.33 | 49 | 1.00 |  |
| T08|modal|matrix_power | 1 | ' matrix' | 0.46 | 38 | 1.00 |  |
| T08|modal|matrix_power | 2 | ' matrix' + 'j' | 0.43 | 38 | 1.00 |  |
| T08|modal|matrix_power | 3 | ' matrix' + 'j' + '_matrices' | 0.28 | 38 | 1.00 |  |
| R3|modal|kahn | 1 | ' queue' | 0.98 | 46 | 1.00 | from collections import defaultdict, deque (44); from collections import deque, defaultdict (2); from collections import defaultdict (1) |
| R3|modal|kahn | 2 | ' queue' + '.p' | 0.96 | 50 | 1.00 | from collections import defaultdict, deque (41); from collections import deque, defaultdict (2); from itertools import count (1) |
| R3|modal|kahn | 3 | ' queue' + '.p' + ' deque([' | 0.96 | 50 | 1.00 | from collections import defaultdict, deque (43); from collections import deque, defaultdict (2); from collections import defaultdict (1) |
| T13|modal|sort_sweep | 1 | '\ndef solve' | 0.84 | 43 | 1.00 |  |
| T13|modal|sort_sweep | 2 | '\ndef solve' + 'intervals[' | 1.00 | 50 | 1.00 |  |
| T13|modal|sort_sweep | 3 | '\ndef solve' + 'intervals[' + '\ndef' | 0.88 | 50 | 1.00 | from typing import List (26); import itertools (2); import bisect (1) |
| R6|modal|binary_search | 1 | ' = 0,' | 0.98 | 39 | 1.00 |  |
| R6|modal|binary_search | 2 | ' = 0,' + ' right = ' | 0.96 | 39 | 1.00 |  |
| R6|modal|binary_search | 3 | ' = 0,' + ' right = ' + ' right = -' | 0.96 | 39 | 1.00 |  |
| T14|modal|heap | 1 | '(k' | 0.57 | 30 | 1.00 | from collections import Counter (26); import heapq (21); from heapq import nlargest (6) |
| T14|modal|heap | 2 | '(k' + ' heapq' | 0.02 | 35 | 1.00 | from collections import Counter (1); import bisect (1) |
| T11|modal|quadratic_dp | 1 | '[j] +' | 0.85 | 36 | 1.00 |  |
| T11|modal|quadratic_dp | 2 | '[j] +' + '  +' | 0.83 | 36 | 1.00 |  |
| T11|modal|quadratic_dp | 3 | '[j] +' + '  +' + '[j] ' | 0.80 | 36 | 1.00 |  |
| T14|present_minor|sort_by_count | 1 | ' [' | 0.37 | 150 | 1.00 | from collections import Counter (44); from typing import List (6); from operator import itemgetter (4) |
| T14|present_minor|sort_by_count | 2 | ' [' + '=True' | 0.34 | 158 | 1.00 | from collections import Counter (41); from typing import List (6); from operator import itemgetter (4) |
| T14|present_minor|sort_by_count | 3 | ' [' + '=True' + ' True' | 0.35 | 158 | 1.00 | from collections import Counter (44); from typing import List (6); from operator import itemgetter (5) |
| T03|present_minor|heapify_pop | 1 | ' {}\n   ' | 0.25 | 112 | 1.00 | import heapq (46); import bisect (3); from typing import List (1) |
| T03|present_minor|heapify_pop | 2 | ' {}\n   ' + '.items' | 0.10 | 112 | 1.00 | import heapq (15); import bisect (4) |
| T03|present_minor|quickselect | 1 | ' quick' | 0.12 | 24 | 1.00 | import random (7); import heapq (3); import bisect (1) |
| T04|present_minor|kmp | 1 | '                j' | 0.26 | 38 | 1.00 |  |
| T04|present_minor|kmp | 2 | '                j' + ':\n                    j' | 0.14 | 38 | 1.00 |  |
| T10|present_minor|dfs | 1 | ' dfs' | 0.17 | 62 | 1.00 | from collections import defaultdict (2); from typing import List (2) |
| T03|present_minor|size_k_heap | 1 | '.n' | 0.09 | 50 | 1.00 | import heapq (8); from typing import List (3); import random (1) |
