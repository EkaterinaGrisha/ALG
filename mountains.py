import sys


def main():
    data = sys.stdin.buffer.read().split()
    t = int(data[0])
    pos = 1
    out = []
    for _ in range(t):
        n = int(data[pos])
        pos += 1
        h = list(map(int, data[pos:pos + n]))
        pos += n

        # inc[i] — длина строго возрастающего отрезка, заканчивающегося в i
        inc = [1] * n
        for i in range(1, n):
            if h[i] > h[i - 1]:
                inc[i] = inc[i - 1] + 1

        # dec[i] — длина строго убывающего отрезка, начинающегося в i
        dec = [1] * n
        for i in range(n - 2, -1, -1):
            if h[i] > h[i + 1]:
                dec[i] = dec[i + 1] + 1

        # Вершина горки однозначна (строгий максимум): для вершины i
        # левый край выбирается (inc[i] - 1) способами, правый — (dec[i] - 1).
        # Если i не вершина, один из множителей равен 0.
        ans = 0
        for i in range(n):
            ans += (inc[i] - 1) * (dec[i] - 1)
        out.append(ans)

    sys.stdout.write("\n".join(map(str, out)) + "\n")


main()
