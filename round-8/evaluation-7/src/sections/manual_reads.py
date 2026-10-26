"""The executor's manual reads (STEP A4), keyed by the first 12 hex digits of the program's sha256. One entry per
distinct program where the counted readers (rule, judge A, judge B) disagree, plus the fixed-seed 10-program sample
where they agree. Read on 2026-10-23 from tables/counting_sort_adjudication.csv and logs/manual_queue.txt, blind to
the cell's arm outcome counts (the cell name is visible in the queue file)."""

ATTEMPT_DIJKSTRA = ("dijkstra", "attempted Dijkstra with a binary heap; crashes because it iterates the edge list as "
                    "an adjacency list (edges[u] or 'for v, w in edges')")
DEGENERATE = ("other", "degenerate text after 'def solve(': repeated tokens, no executable algorithm")
ATTEMPT_DIAL = ("dial", "attempted Dial's algorithm (array of buckets indexed by distance); buggy bucket handling")

MANUAL = {
    # T03 (kth smallest)
    "a2e18e96e898": ("counting_sort", "dictionary form: dict counts, sorted keys walked until k is covered (sample)"),
    "6407f9c6e45f": ("counting_sort", "dict counts walked over the value range min..max, expanded to a list (sample)"),
    "ab79cb14e32d": ("counting_sort", "dictionary form: dict counts, sorted(count.keys()) walked with k -= count (sample)"),
    "5828ba352521": ("other", "binary search on the value range with a count of values <= mid; not quickselect "
                              "(no partition), a known technique outside the catalogue"),
    # T2 (shortest path), committed contrastive pilot cells, forced Dial and padding cells
    "62e9d8c3ace3": ATTEMPT_DIJKSTRA, "cbac861e3abd": ATTEMPT_DIJKSTRA, "b2095529d235": ATTEMPT_DIJKSTRA,
    "14f1254586d5": ATTEMPT_DIJKSTRA, "cc2749615776": ATTEMPT_DIJKSTRA, "6d5e893bbc90": ATTEMPT_DIJKSTRA,
    "4fc729783799": ATTEMPT_DIJKSTRA, "80acd5d4aefb": ATTEMPT_DIJKSTRA, "72e8bc9e9aff": ATTEMPT_DIJKSTRA,
    "e65767ec8f70": ATTEMPT_DIJKSTRA,
    "60814954b6e6": ("bf_spfa", "SPFA on a deque (re-queues a node whenever its distance improves; 0-weight edges go "
                                "to the front); passes"),
    "9fbdc6a902ab": DEGENERATE, "2be04393d45e": DEGENERATE, "b8faa7f27ccc": DEGENERATE, "3a60dd381ed2": DEGENERATE,
    "e74e2bf01c01": DEGENERATE, "6c3d36b1e4ab": DEGENERATE, "2b7586de326b": DEGENERATE, "c06ae865ed0b": DEGENERATE,
    "f194188f8ec1": ("other", "degenerate: the task statement echoed inside the signature, no algorithm"),
    "783ff4d847ab": DEGENERATE, "a4fde6b07641": DEGENERATE, "a3cb5214e3bd": DEGENERATE, "3351dc702a41": DEGENERATE,
    "630f36a9f515": DEGENERATE, "4b0f189026a0": DEGENERATE, "a019369cf3dd": DEGENERATE, "ab4b70de9c83": DEGENERATE,
    "c644cbe35996": DEGENERATE, "5f7d7639a716": DEGENERATE,
    "9ad202cd8075": ("other", "degenerate: the word 'dijkstra' appears once among repeated tokens, no algorithm"),
    "5c38f4bbf84a": DEGENERATE, "e758888d8ba3": DEGENERATE,
    "01ca75928259": ("other", "degenerate: imports heappush/heappop, then only repeated '(123)' tokens"),
    "ac29704be454": ("dijkstra", "Dijkstra with a binary heap over an adjacency list; passes (sample)"),
    "c10ebda23a13": ATTEMPT_DIAL, "4f7cdf8d094b": ATTEMPT_DIAL, "17359b6216c0": ATTEMPT_DIAL, "1d8329846c43": ATTEMPT_DIAL,
    "d05cdbddf65c": ATTEMPT_DIAL, "b082ac99653a": ATTEMPT_DIAL, "fcb4bcbcc9e3": ATTEMPT_DIAL, "54962abfdeba": ATTEMPT_DIAL,
    "b83b0be057a7": ("other", "FIFO queue with settle-on-first-pop (neither Dijkstra's priority order nor SPFA's "
                              "re-relaxation); crashes on list.popleft"),
}


def resolve(full_hashes: list[str]) -> dict[str, dict[str, str]]:
    """Map full sha256 -> {label, note} for every prefix above (each prefix must match exactly one hash)."""
    out = {}
    for pre, (lab, note) in MANUAL.items():
        hits = [h for h in full_hashes if h.startswith(pre)]
        if len(hits) != 1:
            raise ValueError(f"manual-read prefix {pre} matches {len(hits)} programs")
        out[hits[0]] = {"label": lab, "note": note}
    return out
