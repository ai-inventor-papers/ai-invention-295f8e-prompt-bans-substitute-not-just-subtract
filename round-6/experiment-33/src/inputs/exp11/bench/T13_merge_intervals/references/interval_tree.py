import random


class Node:
    __slots__ = ("start", "end", "max_end", "left", "right", "alive")

    def __init__(self, start, end):
        self.start, self.end, self.max_end = start, end, end
        self.left = self.right = None
        self.alive = True


def insert(root, node):
    if root is None:
        return node
    cur = root
    while True:
        if node.end > cur.max_end:
            cur.max_end = node.end
        if node.start < cur.start:
            if cur.left is None:
                cur.left = node
                return root
            cur = cur.left
        else:
            if cur.right is None:
                cur.right = node
                return root
            cur = cur.right


def find_overlap(root, s, e):
    stack = [root] if root else []
    while stack:
        node = stack.pop()
        if node is None or node.max_end < s:
            continue
        if node.alive and node.start <= e and node.end >= s:
            return node
        stack.append(node.left)
        if node.start <= e:
            stack.append(node.right)
    return None


def solve(intervals):
    order = [list(iv) for iv in intervals]
    random.shuffle(order)
    root = None
    for s, e in order:
        hit = find_overlap(root, s, e)
        while hit is not None:
            hit.alive = False
            s, e = min(s, hit.start), max(e, hit.end)
            hit = find_overlap(root, s, e)
        root = insert(root, Node(s, e))
    out = []
    stack, node = [], root
    while stack or node:
        while node:
            stack.append(node)
            node = node.left
        node = stack.pop()
        if node.alive:
            out.append([node.start, node.end])
        node = node.right
    return out
