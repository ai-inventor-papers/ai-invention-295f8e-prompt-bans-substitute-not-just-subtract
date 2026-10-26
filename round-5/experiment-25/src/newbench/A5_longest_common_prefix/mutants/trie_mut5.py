def solve(strs):
    root = {}
    for s in strs:
        node = root
        for ch in s:
            node = node.setdefault(ch, {})
    out = []
    node = root
    while len(node) == 1:
        ch = next(iter(node))
        out.append(ch)
        node = node[ch]
    return "".join(out)
