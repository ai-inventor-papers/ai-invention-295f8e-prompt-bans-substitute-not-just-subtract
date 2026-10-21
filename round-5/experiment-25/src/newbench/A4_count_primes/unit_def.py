"""A4 count primes below n: references, mutants, baselines, generator, probes."""
import json
import random

REFERENCES = {
    "eratosthenes": '''
def solve(n):
    if n < 3:
        return 0
    is_p = [True] * n
    is_p[0] = is_p[1] = False
    i = 2
    while i * i < n:
        if is_p[i]:
            for j in range(i * i, n, i):
                is_p[j] = False
        i += 1
    return sum(is_p)
''',
    "trial_division": '''
def solve(n):
    primes = []
    for m in range(2, n):
        ok = True
        for p in primes:
            if p * p > m:
                break
            if m % p == 0:
                ok = False
                break
        if ok:
            primes.append(m)
    return len(primes)
''',
    "linear_sieve": '''
def solve(n):
    if n < 3:
        return 0
    comp = [False] * n
    primes = []
    for i in range(2, n):
        if not comp[i]:
            primes.append(i)
        for p in primes:
            if i * p >= n:
                break
            comp[i * p] = True
            if i % p == 0:
                break
    return len(primes)
''',
    "segmented_sieve": '''
def solve(n):
    if n < 3:
        return 0
    r = int(n ** 0.5) + 1
    small = [True] * (r + 1)
    small[0] = small[1] = False
    for i in range(2, int(r ** 0.5) + 1):
        if small[i]:
            for j in range(i * i, r + 1, i):
                small[j] = False
    base = [i for i in range(2, r + 1) if small[i]]
    count = 0
    seg = max(r, 64)
    lo = 2
    while lo < n:
        hi = min(lo + seg, n)
        block = [True] * (hi - lo)
        for p in base:
            start = max(p * p, ((lo + p - 1) // p) * p)
            for j in range(start, hi, p):
                block[j - lo] = False
        count += sum(block)
        lo = hi
    return count
''',
    "sundaram": '''
def solve(n):
    if n < 3:
        return 0
    k = (n - 2) // 2
    marked = [False] * (k + 1)
    i = 1
    while i + i + 2 * i * i <= k:
        j = i
        while i + j + 2 * i * j <= k:
            marked[i + j + 2 * i * j] = True
            j += 1
        i += 1
    count = 1
    for m in range(1, k + 1):
        if not marked[m] and 2 * m + 1 < n:
            count += 1
    return count
''',
    "atkin": '''
def solve(n):
    if n < 3:
        return 0
    limit = n - 1
    sieve = [False] * (limit + 1)
    x = 1
    while x * x <= limit:
        y = 1
        while y * y <= limit:
            m = 4 * x * x + y * y
            if m <= limit and (m % 12 == 1 or m % 12 == 5):
                sieve[m] = not sieve[m]
            m = 3 * x * x + y * y
            if m <= limit and m % 12 == 7:
                sieve[m] = not sieve[m]
            m = 3 * x * x - y * y
            if x > y and m <= limit and m % 12 == 11:
                sieve[m] = not sieve[m]
            y += 1
        x += 1
    r = 5
    while r * r <= limit:
        if sieve[r]:
            for i in range(r * r, limit + 1, r * r):
                sieve[i] = False
        r += 1
    count = (2 <= limit) + (3 <= limit)
    for a in range(5, limit + 1):
        if sieve[a]:
            count += 1
    return count
''',
}

MUTANTS = [
    ("eratosthenes", '''
def solve(n):
    if n < 3:
        return 0
    is_p = [True] * n
    is_p[0] = is_p[1] = False
    i = 2
    while i * i < n:
        if is_p[i]:
            for j in range(i * i + i, n, i):
                is_p[j] = False
        i += 1
    return sum(is_p)
'''),
    ("trial_division", '''
def solve(n):
    count = 0
    for m in range(2, n):
        if all(m % d for d in range(2, int(m ** 0.5))):
            count += 1
    return count
'''),
    ("linear_sieve", '''
def solve(n):
    comp = [False] * max(n, 2)
    primes = []
    for i in range(2, n):
        if not comp[i]:
            primes.append(i)
        for p in primes:
            if i * p >= n:
                break
            comp[i * p] = True
    return len(primes) + 1
'''),
    ("segmented_sieve", '''
def solve(n):
    return sum(1 for m in range(2, n) if m % 2 and m % 3 and m % 5) + 3
'''),
    ("sundaram", '''
def solve(n):
    k = (n - 2) // 2
    marked = [False] * (k + 1)
    for i in range(1, k + 1):
        for j in range(i, k + 1):
            if i + j + 2 * i * j > k:
                break
            marked[i + j + 2 * i * j] = True
    return sum(1 for m in range(1, k + 1) if not marked[m])
'''),
    ("atkin", '''
def solve(n):
    return max(0, n // 3)
'''),
]

BASELINES = [("naive_quadratic", '''
def solve(n):
    count = 0
    for m in range(2, n):
        ok = True
        for d in range(2, m):
            if m % d == 0:
                ok = False
        if ok:
            count += 1
    return count
''', "fail")]

VARIANTS = {
    "erat_slice": ("eratosthenes", '''
def solve(n):
    if n < 3:
        return 0
    sieve = [1] * n
    sieve[0] = sieve[1] = 0
    for i in range(2, int(n ** 0.5) + 1):
        if sieve[i]:
            sieve[i * i::i] = [0] * len(range(i * i, n, i))
    return sum(sieve)
'''),
    "erat_bytearray": ("eratosthenes", '''
def solve(n):
    if n <= 2:
        return 0
    s = bytearray([1]) * n
    s[0] = s[1] = 0
    i = 2
    while i * i < n:
        if s[i]:
            s[i * i:n:i] = bytearray(len(range(i * i, n, i)))
        i += 1
    return sum(s)
'''),
    "trial_6k": ("trial_division", '''
def is_prime(m):
    if m < 2:
        return False
    if m < 4:
        return True
    if m % 2 == 0 or m % 3 == 0:
        return False
    i = 5
    while i * i <= m:
        if m % i == 0 or m % (i + 2) == 0:
            return False
        i += 6
    return True


def solve(n):
    return sum(1 for m in range(n) if is_prime(m))
'''),
    "trial_sqrt": ("trial_division", '''
import math


def solve(n):
    c = 0
    for m in range(2, n):
        for d in range(2, math.isqrt(m) + 1):
            if m % d == 0:
                break
        else:
            c += 1
    return c
'''),
}


def gen_cases(rng: random.Random) -> list:
    out = []
    edge = [0, 1, 2, 3, 4, 5, 10, 11, 12, 13, 100, 1000, 49999, 49998]
    for i, e in enumerate(edge):
        out.append({"case_id": f"gen:edge:{i}", "kind": "edge", "kwargs": {"n": e}})
    for i in range(12):
        out.append({"case_id": f"gen:rand:{i}", "kind": "random", "kwargs": {"n": rng.randint(5, 50000)}})
    for i, e in enumerate([50000, 49999, 49997, 47000, 45000, 48611]):
        out.append({"case_id": f"gen:stress:{i}", "kind": "stress", "kwargs": {"n": e}})
    return out


def lc_ok(kwargs, expected) -> bool:
    n = kwargs.get("n")
    return isinstance(n, int) and 0 <= n <= 50000


MAX_LC = 30
PROBES = [{"name": "n5k", "kwargs_json": json.dumps({"n": 5000}), "wrap": {}, "trace_ops": True},
          {"name": "n50k", "kwargs_json": json.dumps({"n": 50000}), "wrap": {}}]
