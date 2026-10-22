import heapq


def solve(grid, start, goal):
    rows, cols = len(grid), len(grid[0])
    if grid[start[0]][start[1]] == '#' or grid[goal[0]][goal[1]] == '#':
        return []
    if start == goal:
        return [start]

    def manh(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    g = [{start: 0}, {goal: 0}]
    parent = [{start: None}, {goal: None}]
    target = [goal, start]
    heaps = [[(manh(start, goal), 0, start)], [(manh(goal, start), 0, goal)]]
    closed = [set(), set()]
    best = 1 << 30
    meet = None
    while heaps[0] and heaps[1]:
        # stop when neither frontier can improve the best meeting cost
        if best <= max(heaps[0][0][0], heaps[1][0][0]):
            break
        side = 0 if heaps[0][0][0] <= heaps[1][0][0] else 1
        f, gc, cell = heapq.heappop(heaps[side])
        if cell in closed[side] or gc > g[side].get(cell, 1 << 30):
            continue
        closed[side].add(cell)
        other = 1 - side
        if cell in g[other] and gc + g[other][cell] < best:
            best = gc + g[other][cell]
            meet = cell
        r, c = cell
        for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] == '.':
                ng = gc + 1
                if ng < g[side].get((nr, nc), 1 << 30):
                    g[side][(nr, nc)] = ng
                    parent[side][(nr, nc)] = cell
                    heapq.heappush(heaps[side], (ng + manh((nr, nc), target[side]), ng, (nr, nc)))
                    if (nr, nc) in g[other] and ng + g[other][(nr, nc)] < best:
                        best = ng + g[other][(nr, nc)]
                        meet = (nr, nc)
    if meet is None:
        return []
    left = []
    node = meet
    while node is not None:
        left.append(node)
        node = parent[0][node]
    left.reverse()
    node = parent[1][meet]
    while node is not None:
        left.append(node)
        node = parent[1][node]
    return left
