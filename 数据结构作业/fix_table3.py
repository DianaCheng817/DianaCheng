# -*- coding: utf-8 -*-
"""只重跑表3：插入位置 vs 搬移元素数（路径跟随脚本所在目录，可移植）"""
import csv, os, random
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playlist import MyPlaylist, build

OUT_DIR = os.path.dirname(os.path.abspath(__file__))

def table3(n):
    pl = build(n)
    out = {"n": n}

    pl.move_count = 0
    pl.insert(0, "TMP")
    out["at_first"] = pl.move_count
    pl.remove(0)

    pl.move_count = 0
    pl.insert(n, "TMP")
    out["at_last"] = pl.move_count
    pl.remove(n)

    total = 0
    positions = list(range(0, n+1, max(1, n//50)))   # 均匀采样 0..n
    for p in positions:
        pl.move_count = 0
        pl.insert(p, "TMP")
        total += pl.move_count
        pl.remove(p)
    out["avg_move"] = total / len(positions)
    out["n_over_2"] = n / 2
    return out

random.seed(42)
rows = []
for n in [100, 1000, 10000, 100000]:
    r = table3(n)
    rows.append(r)
    print(f"n={n:>6}  at_first={r['at_first']:>6}  at_last={r['at_last']:>4}  "
          f"avg={r['avg_move']:>8.1f}  n/2={r['n_over_2']:>8.1f}")

with open(os.path.join(OUT_DIR, "table3.csv"), "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["n", "insert_at_first(elements moved)", "insert_at_last(elements moved)",
                "avg_move_count", "n/2"])
    for r in rows:
        w.writerow([r["n"], r["at_first"], r["at_last"], round(r["avg_move"],1), r["n_over_2"]])
print("table3.csv 已更新（位于脚本所在目录）")
