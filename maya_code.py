import sys


def main():
    data = sys.stdin.buffer.read().split()
    n = int(data[0])
    q = int(data[1])
    words = data[2:2 + n]
    pos = 2 + n

    # ---------- Бор Ахо-Корасик: G[u*26 + c] — ребёнок u по букве c (0 — нет) ----------
    total = 0
    for w in words:
        total += len(w)
    G = [0] * (26 * (total + 1))
    pnode = [0] * (total + 1)  # родитель вершины
    pchar = [0] * (total + 1)  # буква на ребре от родителя
    depth = [0] * (total + 1)
    node_of = [0] * n
    nodes = 1
    for j in range(n):
        u = 0
        for ch in words[j]:
            c = ch - 65
            idx = u * 26 + c
            v = G[idx]
            if v == 0:
                v = nodes
                nodes += 1
                G[idx] = v
                pnode[v] = u
                pchar[v] = c
                depth[v] = depth[u] + 1
            u = v
        node_of[j] = u
    del words

    # Терминальные вершины бора нумеруем компактно: 0..T-1
    term = [-1] * nodes
    term_node = []
    for j in range(n):
        u = node_of[j]
        if term[u] < 0:
            term[u] = len(term_node)
            term_node.append(u)
    T = len(term_node)
    word_of_term = [[] for _ in range(T)]  # племена, чьё слово кончается в терминале

    # Вершины в порядке возрастания глубины (сортировка подсчётом).
    maxd = 0
    for v in range(nodes):
        if depth[v] > maxd:
            maxd = depth[v]
    start = [0] * (maxd + 2)
    for v in range(nodes):
        start[depth[v] + 1] += 1
    for d in range(maxd + 1):
        start[d + 1] += start[d]
    order = [0] * nodes
    for v in range(nodes):
        d = depth[v]
        order[start[d]] = v
        start[d] += 1
    del start, depth

    # Суффиксные ссылки (подъём по ссылкам, амортизированно O(сумма |s|)) и
    # wl[x] — ближайший терминал среди x и его суффиксных предков (-1, если нет).
    fail = [0] * nodes
    wl = [-1] * nodes
    for t in range(1, nodes):
        v = order[t]
        p = pnode[v]
        if p == 0:
            f = 0
        else:
            c = pchar[v]
            f = fail[p]
            while f and G[f * 26 + c] == 0:
                f = fail[f]
            f = G[f * 26 + c]
        fail[v] = f
        tv = term[v]
        wl[v] = tv if tv >= 0 else wl[f]
    del order, pnode, pchar

    # Сжатое дерево суффиксных ссылок только по терминалам
    cpar = [0] * T
    for k in range(T):
        cpar[k] = wl[fail[term_node[k]]]

    # ---------- Дерево племён: эйлеров обход (tin, tout = max tin в поддереве) ----------
    deg = [0] * (n + 1)
    eu = [0] * (n - 1)
    ev = [0] * (n - 1)
    for i in range(n - 1):
        a = int(data[pos]) - 1
        b = int(data[pos + 1]) - 1
        pos += 2
        eu[i] = a
        ev[i] = b
        deg[a + 1] += 1
        deg[b + 1] += 1
    for i in range(n):
        deg[i + 1] += deg[i]
    adj = [0] * (2 * (n - 1))
    fill = deg[:]
    for i in range(n - 1):
        a = eu[i]
        b = ev[i]
        adj[fill[a]] = b
        fill[a] += 1
        adj[fill[b]] = a
        fill[b] += 1

    tin = [0] * n
    tout = [0] * n
    visited = [False] * n
    stack = [0]
    visited[0] = True
    timer = 0
    while stack:
        u = stack[-1]
        if u >= 0:
            stack[-1] = ~u
            tin[u] = timer
            timer += 1
            for e in range(deg[u], deg[u + 1]):
                v = adj[e]
                if not visited[v]:
                    visited[v] = True
                    stack.append(v)
        else:
            stack.pop()
            u = ~u
            tout[u] = timer - 1

    for j in range(n):
        word_of_term[term[node_of[j]]].append(tin[j] + 1)

    # ---------- Тексты запросов: прогон по автомату ----------
    # Для запроса i и терминала k считаем, сколько позиций текста имеют wl = k.
    qv = [0] * q
    bucket_q = [[] for _ in range(T)]
    bucket_c = [[] for _ in range(T)]
    cnt = [0] * T
    touched = []
    for i in range(q):
        qv[i] = int(data[pos]) - 1
        text = data[pos + 1]
        pos += 2
        x = 0
        for ch in text:
            c = ch - 65
            while x and G[x * 26 + c] == 0:
                x = fail[x]
            x = G[x * 26 + c]
            w = wl[x]
            if w >= 0:
                if cnt[w] == 0:
                    touched.append(w)
                cnt[w] += 1
        for w in touched:
            bucket_q[w].append(i)
            bucket_c[w].append(cnt[w])
            cnt[w] = 0
        touched.clear()
    del data, G, fail, wl

    # ---------- DFS по сжатому дереву ссылок + Фенвик по tin племён ----------
    # В момент обработки терминала k в Фенвике отмечены ровно племена, чьи слова
    # являются суффиксами строки k (т.е. встречаются, заканчиваясь в этой позиции).
    head = [-1] * (T + 1)  # T — фиктивный корень
    nxt = [-1] * T
    for k in range(T):
        p = cpar[k]
        if p < 0:
            p = T
        nxt[k] = head[p]
        head[p] = k

    bit = [0] * (n + 1)
    ans = [0] * q
    stack = []
    k = head[T]
    while k != -1:
        stack.append(k)
        k = nxt[k]
    while stack:
        k = stack.pop()
        if k >= 0:
            for i in word_of_term[k]:
                while i <= n:
                    bit[i] += 1
                    i += i & -i
            bq = bucket_q[k]
            bc = bucket_c[k]
            for t in range(len(bq)):
                qi = bq[t]
                v = qv[qi]
                s = 0
                i = tout[v] + 1
                while i > 0:
                    s += bit[i]
                    i -= i & -i
                i = tin[v]
                while i > 0:
                    s -= bit[i]
                    i -= i & -i
                ans[qi] += bc[t] * s
            stack.append(~k)
            c = head[k]
            while c != -1:
                stack.append(c)
                c = nxt[c]
        else:
            k = ~k
            for i in word_of_term[k]:
                while i <= n:
                    bit[i] -= 1
                    i += i & -i

    sys.stdout.write("\n".join(map(str, ans)))
    sys.stdout.write("\n")


main()
