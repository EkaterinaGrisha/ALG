import sys

MOD = 10 ** 9 + 7


def main():
    n, k = map(int, sys.stdin.read().split())
    m = n - 1

    fact = [1] * (k + 1)
    for i in range(1, k + 1):
        fact[i] = fact[i - 1] * i % MOD
    inv_fact = [1] * (k + 1)
    inv_fact[k] = pow(fact[k], MOD - 2, MOD)
    for i in range(k, 0, -1):
        inv_fact[i - 1] = inv_fact[i] * i % MOD

    # При фиксированной ch1 схожести с остальными — m независимых Bin(k, 1/2).
    # E[max] = sum_{t=0}^{k-1} P(max > t) = k - sum_{t=0}^{k-1} F(t)^m,
    # где F(t) = P(X <= t) = (C(k,0) + ... + C(k,t)) / 2^k.
    inv_2k = pow(pow(2, k, MOD), MOD - 2, MOD)
    fk = fact[k]
    prefix = 0
    total = 0
    for t in range(k):
        prefix = (prefix + fk * inv_fact[t] % MOD * inv_fact[k - t]) % MOD
        total += pow(prefix * inv_2k % MOD, m, MOD)

    print((k - total) % MOD)


main()
