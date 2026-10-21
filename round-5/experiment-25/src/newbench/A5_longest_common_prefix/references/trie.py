class TrieNode:
    def __init__(self):
        self.children = {}
        self.end = False


def solve(strs):
    root = TrieNode()
    for s in strs:
        node = root
        for ch in s:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.end = True
    out = []
    node = root
    while len(node.children) == 1 and not node.end:
        ch, nxt = next(iter(node.children.items()))
        out.append(ch)
        node = nxt
    return "".join(out)
