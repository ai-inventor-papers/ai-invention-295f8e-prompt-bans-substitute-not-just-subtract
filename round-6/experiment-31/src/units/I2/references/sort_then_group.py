def solve(strs):
    order = sorted(range(len(strs)), key=lambda i: "".join(sorted(strs[i])))
    out = []
    prev = None
    for i in order:
        sig = "".join(sorted(strs[i]))
        if sig != prev:
            out.append([])
            prev = sig
        out[-1].append(strs[i])
    return out
