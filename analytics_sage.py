import csv
import math
import re
import sys
from datetime import date

T0, R0, DM0 = 365.0, 10.0, 1000.0
NAMES = "ABCD"


def norm(s):
    return (s or "").strip().lower().replace("ё", "е")


def phase_code(s):
    s = norm(s)
    if "прин" in s:
        return 0          # принятие заказа
    if "эскиз" in s:
        return 1          # эскиз
    if "обт" in s or "черн" in s:
        return 2          # черновой обтёс
    if "детал" in s:
        return 3          # детализация
    if "шлиф" in s or "полир" in s:
        return 4          # шлифовка и полировка
    return -1


def activity_code(s):
    s = norm(s)
    if "постан" in s:
        return "set"      # постановка задачи
    if "демонстр" in s:
        return "demo"     # демонстрация
    return "work"         # работа


def to_float(s):
    s = (s or "").strip().replace(",", ".")
    try:
        v = float(s)
        return 0.0 if math.isnan(v) else v
    except ValueError:
        return 0.0


def to_day(s):
    return date.fromisoformat((s or "").strip()[:10]).toordinal()


# ---------- парный t-тест: scipy, а если его нет — своя реализация ----------
def betacf(a, b, x):
    # непрерывная дробь для неполной бета-функции (метод Ленца)
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return h


def betainc(a, b, x):
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1.0 - x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbt) * betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * betacf(b, a, 1.0 - x) / b


def paired_ttest_p(y, y_mod):
    try:
        from scipy.stats import ttest_rel
        return float(ttest_rel(y, y_mod)[1])
    except ImportError:
        pass
    d = [u - v for u, v in zip(y, y_mod)]
    n = len(d)
    if n < 2:
        return float("nan")
    mean = sum(d) / n
    var = sum((x - mean) ** 2 for x in d) / (n - 1)
    if var == 0.0:
        return float("nan") if mean == 0.0 else 0.0
    t = mean / math.sqrt(var / n)
    df = n - 1
    return betainc(df / 2.0, 0.5, df / (df + t * t))


# ---------- чтение и подготовка данных (потоково, по одной строке) ----------
NUM = re.compile(r"[-+]?(?:\d+(?:[.,]\d*)?|[.,]\d+)(?:[eE][-+]?\d+)?")


def read_input():
    stream = iter(sys.stdin)
    line = ""
    for line in stream:
        if line.strip():
            break
    coefs = [float(x.replace(",", ".")) for x in NUM.findall(line)][:4]
    header_line = ""
    for header_line in stream:
        if header_line.strip():
            break
    delim = max([",", "\t", ";", "|"], key=header_line.count)
    header = [norm(h) for h in next(csv.reader([header_line], delimiter=delim))]
    return coefs, header, split_rows(stream, delim)


def split_rows(stream, delim):
    # быстрый путь: строка без кавычек режется обычным split, иначе — модулем csv
    for ln in stream:
        if '"' in ln:
            yield next(csv.reader([ln], delimiter=delim))
        else:
            s = ln.rstrip("\r\n")
            if s and not s.isspace():
                yield s.split(delim)


def build_features(header, rows):
    def col(name):
        for k, h in enumerate(header):
            if h == name:
                return k
        for k, h in enumerate(header):
            if name in h:
                return k
        raise KeyError(name)

    c_day, c_ord, c_ph = col("day"), col("order_id"), col("phase")
    c_act, c_res, c_pay = col("activity"), col("res"), col("pay")
    need = max(c_day, c_ord, c_ph, c_act, c_res, c_pay) + 1

    ph_cache, act_cache, day_cache = {}, {}, {}
    # по заказу: [min_day, max_day, done, s_min, s_max, remakes, pre_day, pre_pay, fin_pay]
    orders = {}
    remake_seen = set()      # дубликаты демонстраций-переделок не считаем дважды
    for r in rows:
        if len(r) < need:
            r = r + [""] * (need - len(r))
        ds = r[c_day]
        day = day_cache.get(ds)
        if day is None:
            try:
                day = to_day(ds)
            except ValueError:
                continue
            day_cache[ds] = day
        ph = ph_cache.get(r[c_ph])
        if ph is None:
            ph = ph_cache[r[c_ph]] = phase_code(r[c_ph])
        act = act_cache.get(r[c_act])
        if act is None:
            act = act_cache[r[c_act]] = activity_code(r[c_act])
        oid = r[c_ord].strip()
        o = orders.get(oid)
        if o is None:
            o = orders[oid] = [day, day, False, None, None, 0, None, 0.0, None]
        if day < o[0]:
            o[0] = day
        if day > o[1]:
            o[1] = day
        if (act != "demo" and act != "set") or ph not in (1, 4):
            if ph == 1:
                if o[3] is None or day < o[3]:
                    o[3] = day
                if o[4] is None or day > o[4]:
                    o[4] = day
            continue
        res = norm(r[c_res])
        if ph == 4:
            if act == "demo" and res == "success":
                o[2] = True
            continue
        # фаза эскиза
        if o[3] is None or day < o[3]:
            o[3] = day
        if o[4] is None or day > o[4]:
            o[4] = day
        if act == "set":
            if o[6] is None or day < o[6]:
                o[6] = day
                o[7] = to_float(r[c_pay])
        elif res == "remake":
            key = (oid, day)
            if key not in remake_seen:
                remake_seen.add(key)
                o[5] += 1
        elif res == "success":
            o[8] = to_float(r[c_pay])

    X, y = [], []
    for o in orders.values():
        if not o[2] or o[3] is None:
            continue                         # прерванные и брошенные заказы не берём
        T = o[1] - o[0]
        T1 = o[4] - o[3]
        dM = (o[8] if o[8] is not None else 0.0) - o[7]
        X.append((1.0, T1 / T0, o[5] / R0, dM / DM0))
        y.append(T / T0)
    return X, y


def main():
    coefs, header, rows = read_input()
    X, y = build_features(header, rows)

    y_mod = [sum(c * x for c, x in zip(coefs, row)) for row in X]
    p = paired_ttest_p(y, y_mod)
    if not (p < 0.1):                        # p >= 0.1 (или nan: прогноз совпал идеально)
        print("YES")
        return

    # Ошибочен ровно один коэффициент: для каждого подбираем значение,
    # минимизирующее MSE при остальных фиксированных (МНК по одной переменной),
    # и выбираем тот, у которого MSE получается наименьшей.
    best = None
    for k in range(4):
        num = den = 0.0
        for row, yy, pm in zip(X, y, y_mod):
            xk = row[k]
            r = yy - (pm - coefs[k] * xk)    # что должен объяснить коэффициент k
            num += xk * r
            den += xk * xk
        if den == 0.0:
            continue
        val = num / den
        new = coefs[:]
        new[k] = val
        mse = sum((yy - sum(c * x for c, x in zip(new, row))) ** 2 for row, yy in zip(X, y)) / len(y)
        ok_sum = abs(sum(new)) <= 10 + 1e-9  # гарантия условия для верных коэффициентов
        cand = (not ok_sum, mse, k, val)
        if best is None or cand < best:
            best = cand
    _, _, k, val = best
    print("%s %.10f" % (NAMES[k], val))  # без округления до 3 знаков


if __name__ == "__main__":
    main()
