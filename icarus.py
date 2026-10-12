import sys


def ask(h):
    sys.stdout.write(f"{h}\n")
    sys.stdout.flush()
    r = sys.stdin.readline().strip()
    if r != "ok" and r != "wet":
        # «fail» (или конец ввода) — нужно немедленно завершиться
        sys.exit(0)
    return r == "ok"


def main():
    # Удвоение: если h < N, то 2h < 2N < M, значит следующий запрос безопасен.
    prev = 0
    h = 1
    while not ask(h):
        prev = h
        h *= 2
    # N в (prev, h], и h <= M — бинпоиск внутри безопасен.
    lo, hi = prev + 1, h
    while lo < hi:
        mid = (lo + hi) // 2
        if ask(mid):
            hi = mid
        else:
            lo = mid + 1
    sys.stdout.write(f"! {lo}\n")
    sys.stdout.flush()


main()
