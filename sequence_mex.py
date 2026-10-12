import sys
from math import comb


def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    a = list(map(int, data[1:n + 1]))
    q = int(data[n + 1])

    # Запросы группируем по правой границе (списки через head/nxt).
    head = [-1] * n
    nxt = [-1] * q
    ql = [0] * q
    idx = n + 2
    for k in range(q):
        r = int(data[idx + 1]) - 1
        ql[k] = int(data[idx]) - 1
        nxt[k] = head[r]
        head[r] = k
        idx += 2
    del data

    # Для каждого j значения AND(i..j), i <= j, образуют цепочку по вложению битов,
    # поэтому M — объединение n цепочек. Числа < 2^t с t//2 единичными битами —
    # антицепь размера C(t, t//2); если она больше n, то все числа < 2^t в M
    # попасть не могут, и MEX < 2^t. Значения >= 2^t на ответ не влияют.
    t = 1
    while comb(t, t // 2) <= n:
        t += 1
    size = 1 << t

    # Лист v дерева — last[v]: максимальное i, для которого AND(i..j) = v при
    # каком-то j <= текущего r (-1, если такого нет). Во внутренних узлах — минимум.
    # Тогда v ∈ M(l, r) <=> last[v] >= l, а ответ — самый левый лист с last < l.
    tree = [-1] * (2 * size)
    ans = [0] * q

    vals = []  # различные значения AND(i..j), от i = j влево
    poss = []  # для каждого — наибольшее i, на котором оно достигается
    for j in range(n):
        x = a[j]
        nv = [x]
        np_ = [j]
        prev = x
        for k in range(len(vals)):
            v = vals[k] & x
            if v != prev:
                nv.append(v)
                np_.append(poss[k])
                prev = v
        vals = nv
        poss = np_

        # Значения в цепочке убывают, поэтому малые (< size) — её хвост.
        k = len(nv) - 1
        while k >= 0:
            v = nv[k]
            if v >= size:
                break
            p = np_[k]
            node = v + size
            if tree[node] < p:
                tree[node] = p
                node >>= 1
                while node:
                    lc = tree[2 * node]
                    rc = tree[2 * node + 1]
                    m = lc if lc < rc else rc
                    if tree[node] == m:
                        break
                    tree[node] = m
                    node >>= 1
            k -= 1

        k = head[j]
        while k != -1:
            l = ql[k]
            node = 1
            while node < size:
                node <<= 1
                if tree[node] >= l:
                    node += 1
            ans[k] = node - size
            k = nxt[k]

    sys.stdout.write("\n".join(map(str, ans)))
    sys.stdout.write("\n")


main()
