def solve(n):
    def mul(a, b):
        return [[a[0][0] * b[0][0] + a[0][1] * b[1][0], a[0][0] * b[0][1] + a[0][1] * b[1][1]],
                [a[1][0] * b[0][0] + a[1][1] * b[1][0], a[1][0] * b[0][1] + a[1][1] * b[1][1]]]

    result = [[1, 0], [0, 1]]
    m = [[1, 1], [1, 0]]
    while n:
        if n & 1:
            result = mul(result, m)
        m = mul(m, m)
        n >>= 1
    return result[0][1]
