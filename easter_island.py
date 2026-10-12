import sys


def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    # Строки и столбцы двигаются независимо: каждую координату нужно
    # превратить в перестановку 1..n. Оптимально сопоставить отсортированные
    # координаты с 1, 2, ..., n по порядку.
    r = sorted(map(int, data[1:2 * n + 1:2]))
    c = sorted(map(int, data[2:2 * n + 2:2]))
    ans = 0
    for i in range(n):
        ans += abs(r[i] - i - 1) + abs(c[i] - i - 1)
    print(ans)


main()
