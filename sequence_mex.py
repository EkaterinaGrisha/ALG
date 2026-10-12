import os
import sys
from math import comb
from bisect import bisect_left


def build(last, size):
    # Дерево минимумов: корень в 1, листья [size, 2*size) = last[0:size]
    level = last[:size]
    levels = [level]
    while len(level) > 1:
        level = list(map(min, level[::2], level[1::2]))
        levels.append(level)
    tree = [0]
    for lv in reversed(levels):
        tree += lv
    return tree


def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    a = list(map(int, data[1:n + 1]))
    q = int(data[n + 1])
    L = list(map(int, data[n + 2:n + 2 + 2 * q:2]))
    R = list(map(int, data[n + 3:n + 3 + 2 * q:2]))
    del data

    # Запросы: по возрастанию r, при равном r — по убыванию l.
    # Ключ: r (18 бит) | n - l (18 бит) | номер запроса (20 бит).
    keys = [(r << 38) | ((n - l) << 20) | k for k, l, r in zip(range(q), L, R)]
    del L, R
    keys.sort()
    M18 = (1 << 18) - 1
    M20 = (1 << 20) - 1
    ls = [n - ((key >> 20) & M18) for key in keys]  # l в порядке keys
    bounds = [bisect_left(keys, r << 38) for r in range(n + 2)]
    out = []
    oapp = out.append

    # Для каждого j значения AND(i..j), i <= j, образуют цепочку по вложению битов,
    # поэтому M — объединение n цепочек. Числа < 2^t с t//2 единичными битами —
    # антицепь размера C(t, t//2); если она больше n, то все числа < 2^t в M
    # попасть не могут, и MEX < 2^t. Значения >= 2^t на ответ не влияют.
    t = 1
    while comb(t, t // 2) <= n:
        t += 1
    if t < 6:
        t = 6
    LIM = 1 << t
    LOW = LIM - 1
    HIGH = ~LOW

    # Позиции нумеруются с 1. last[v] — наибольшее i, для которого AND(i..j) = v
    # при каком-то j <= r (0, если такого нет); для одного v оно не убывает с j.
    # v ∈ M(l, r) <=> last[v] >= l, ответ — наименьшее v с last[v] < l.
    last = [0] * LIM
    cur = 0      # MEX всех значений префикса: ответ любого запроса <= cur
    size = 64    # дерево минимумов по last[0:size], size > cur всегда
    tree = build(last, size)

    # AND(i..j) < LIM <=> i <= zh, где zh — наибольшее i, при котором в
    # AND(i..j) нет старших битов (0, если такого нет; zh не убывает с ростом j).
    # Окно [lo..j] с AND старших частей — очередь на двух стеках.
    fa = []      # агрегаты «передней» половины очереди
    bv = []      # элементы «задней» половины
    bagg = -1    # AND задней половины
    lo = 1
    zh_old = 0

    # Цепочка AND по младшим битам: позиции и значения по возрастанию;
    # poss[k] — наибольшее i, где достигается vals[k].
    vals = []
    poss = []
    for j in range(1, n + 1):
        x = a[j - 1]

        xh = x & HIGH
        bv.append(xh)
        bagg &= xh
        while lo <= j:
            if (fa[-1] & bagg) if fa else bagg:
                break
            if not fa:
                acc = -1
                for y in reversed(bv):
                    acc &= y
                    fa.append(acc)
                bv.clear()
                bagg = -1
            fa.pop()
            lo += 1
        zh = lo - 1

        xl = x & LOW
        k = len(vals) - 1
        tnv = [xl]
        tnp = [j]
        prev = xl
        while k >= 0:
            v = vals[k]
            w = v & xl
            if w == v:
                # v ⊆ x, а все значения ниже — подмаски v: они не меняются
                break
            if w != prev:
                tnv.append(w)
                tnp.append(poss[k])
                prev = w
            k -= 1
        if k >= 0 and vals[k] == prev:
            k -= 1
        c0 = k + 1   # vals[:c0] не изменились
        del vals[c0:]
        del poss[c0:]
        tnv.reverse()
        tnp.reverse()
        vals += tnv
        poss += tnp

        if zh:
            # Пары (vals[i], poss[i]) с poss[i] < zh и пара (vals[iv1], zh) —
            # это все различные AND(i..j) < LIM. Обрабатываем только новые:
            # изменившиеся (i >= c0) и ставшие видимыми (poss[i] >= zh_old).
            iv1 = bisect_left(poss, zh)
            i0 = bisect_left(poss, zh_old) if zh_old else 0
            if c0 < i0:
                i0 = c0
            i = i0
            while i <= iv1:
                v = vals[i]
                p = poss[i] if i < iv1 else zh
                if last[v] != p:
                    last[v] = p
                    if v < size:
                        node = v + size
                        tree[node] = p
                        node >>= 1
                        while node:
                            lc = tree[2 * node]
                            rc = tree[2 * node + 1]
                            mn = lc if lc < rc else rc
                            if tree[node] == mn:
                                break
                            tree[node] = mn
                            node >>= 1
                i += 1
            if last[cur]:
                cur += 1
                while last[cur]:
                    cur += 1
                if cur >= size:
                    while size <= cur:
                        size <<= 1
                    tree = build(last, size)
        zh_old = zh

        qs = bounds[j]
        qe = bounds[j + 1]
        if qs < qe:
            # Запросы с r = j идут по убыванию l, ответы не убывают:
            # ищем первое отсутствующее значение, начиная с предыдущего ответа.
            s = 0
            for l in ls[qs:qe]:
                node = s + size
                if tree[node] >= l:
                    while True:
                        while node & 1:
                            node >>= 1
                        node += 1
                        if tree[node] < l:
                            break
                    while node < size:
                        node <<= 1
                        if tree[node] >= l:
                            node += 1
                    s = node - size
                oapp(s)

    ans = [0] * q
    for key, v in zip(keys, out):
        ans[key & M20] = v
    sys.stdout.write("\n".join(map(str, ans)))
    sys.stdout.write("\n")
    sys.stdout.flush()
    os._exit(0)  # не тратим время на освобождение памяти при выходе


main()
