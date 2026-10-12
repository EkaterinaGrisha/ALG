import sys
from math import gcd


def lcm(x, y):
    return x // gcd(x, y) * y


def main():
    data = sys.stdin.read().split()
    a, b, c, n = int(data[0]), int(data[1]), int(data[2]), int(data[3])

    LIMIT = 10 ** 18
    lab = lcm(a, b)
    lac = lcm(a, c)
    lbc = lcm(b, c)
    labc = lcm(lab, c)

    # Сколько чисел от 1 до x делятся ровно на два из трёх (формула включений-исключений)
    def count(x):
        return x // lab + x // lac + x // lbc - 3 * (x // labc)

    if count(LIMIT) < n:
        print(-1)
        return

    lo, hi = 1, LIMIT
    while lo < hi:
        mid = (lo + hi) // 2
        if count(mid) >= n:
            hi = mid
        else:
            lo = mid + 1
    print(lo)


main()
