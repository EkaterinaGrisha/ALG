"""D. Торговый план Великого хирфета: расчёт плана продаж на 1572 год по манускрипту.

Запуск: python3 analytics_plan.py data.xlsx > answer.txt
Строка ответа: <товар> <месяц 1..12> <плановая цена> <количество>
"""
import math
import sys
from collections import defaultdict

import pandas as pd

INFL = 1.07          # годовая инфляция 7%
LAST_YEAR = 1571     # максимальный month — декабрь 1571
PLAN_YEAR = 1572
YEARS = (1569, 1570, 1571)   # только 3 последних года


def load(path):
    df = pd.read_excel(path, dtype={"name": str})
    df = df.rename(columns=lambda c: str(c).strip().lower())
    df["name"] = df["name"].astype(str).str.strip()
    df["month"] = df["month"].astype(int)
    df["price"] = df["price"].astype(float)
    last = df["month"].max()                     # декабрь 1571
    df["year"] = LAST_YEAR - (last - df["month"]) // 12
    df["cal"] = 12 - (last - df["month"]) % 12   # 1 = январь, ..., 12 = декабрь
    return df


def plan(df):
    # Распродажа: цена < 50% средней цены товара в этом же месяце (по всем продажам).
    mean_all = df.groupby(["name", "month"])["price"].transform("mean")
    df = df.assign(sale=df["price"] < 0.5 * mean_all)

    start = df.groupby("name")["month"].min()    # товар продаётся с первого месяца продаж
    last = df["month"].max()
    sold_last_year = set(df.loc[df["year"] == LAST_YEAR, "name"])

    rows = []
    for name in sorted(sold_last_year):          # без продаж в 1571 — исключаем
        g = df[df["name"] == name]
        for cal in range(1, 13):
            volumes = []      # расчётный объём рынка по годам (с инфляцией)
            prices = []       # цены без распродаж (с инфляцией)
            for year in YEARS:
                month = last - (LAST_YEAR - year) * 12 - (12 - cal)
                if month < start[name]:
                    continue                     # товар ещё не продавался — год не учитываем
                k = INFL ** (PLAN_YEAR - year)
                cur = g[g["month"] == month]
                full = cur[~cur["sale"]]
                n_all = len(cur)                 # все продажи, включая распродажи
                avg = full["price"].mean() if len(full) else 0.0
                volumes.append(avg * n_all * k)  # нет продаж -> объём 0
                prices.extend((full["price"] * k).tolist())

            volume = sum(volumes) / len(volumes) if volumes else 0.0

            # Плановая цена: наименьшая цена множества, которая >= 90% его цен.
            price = 0
            if prices:
                prices.sort()
                n = len(prices)
                idx = (9 * n + 9) // 10 - 1      # наименьший k: k >= 0.9 * n
                price = int(math.floor(prices[idx] + 1e-9))

            share = 0.02 * cal                   # январь 2%, ..., декабрь 24%
            qty = 0
            if price > 0 and volume > 0:
                qty = int(math.ceil(share * volume / price - 1e-9))
            rows.append((name, cal, price, qty))
    return rows


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data.xlsx"
    for name, cal, price, qty in plan(load(path)):
        print(name, cal, price, qty)


if __name__ == "__main__":
    main()
