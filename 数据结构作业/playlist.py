# -*- coding: utf-8 -*-
"""
校园音乐 App - "我的歌单" 顺序表实现 + 完整计时/计数
接口统一：get(i) / insert(i, song) / remove(i) / indexOf(name) / size() / showAll()
复杂度：
  - get(i)        : O(1)  数组下标直读
  - insert(i,song): O(n)  在位置 i 插入要把 i..n-1 全部后移一位，搬移 n-i 个元素
  - remove(i)     : O(n)  把 i+1..n-1 全部前移一位，搬移 n-1-i 个元素
  - indexOf(name) : O(n)  顺序扫描，最坏（目标在末尾/不存在）要扫 n 次
  - size()        : O(1)
  - showAll()     : O(n)
所有结果文件（CSV / 日志 / 十万条数据）均输出到本脚本所在目录，
不依赖写死的绝对路径，整个文件夹拷到任何电脑都能直接跑。
"""

import time
import random
import csv
import os
import sys
from datetime import datetime

# 输出目录 = 脚本所在目录（不再写死 D:\playlist_test）
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


class MyPlaylist:
    def __init__(self):
        self._songs = []
        self.move_count = 0   # 元素搬移计数器：每次搬一个元素 +1

    # ---------- 接口 ----------
    def get(self, i):
        if i < 0 or i >= len(self._songs):
            raise IndexError(f"越界：get({i})，当前 {len(self._songs)} 首")
        return self._songs[i]

    def insert(self, i, song):
        n = len(self._songs)
        if i < 0 or i > n:
            raise IndexError(f"越界：insert({i})，当前 {n} 首（合法 0..{n}）")
        self._songs.append(None)          # 先扩一个坑
        for j in range(n, i, -1):         # 从尾往头搬
            self._songs[j] = self._songs[j-1]
            self.move_count += 1
        self._songs[i] = song

    def remove(self, i):
        n = len(self._songs)
        if i < 0 or i >= n:
            raise IndexError(f"越界：remove({i})，当前 {n} 首")
        song = self._songs[i]
        for j in range(i, n-1):           # 从头到尾搬
            self._songs[j] = self._songs[j+1]
            self.move_count += 1
        self._songs.pop()
        return song

    def indexOf(self, name):
        for idx, s in enumerate(self._songs):
            if s == name:
                return idx
        return -1

    def size(self):
        return len(self._songs)

    def showAll(self):
        return list(self._songs)


def make_name(i):
    return f"Song_{i:06d}"


def build(n):
    pl = MyPlaylist()
    for i in range(n):
        pl._songs.append(make_name(i))
    return pl


def write_songs_file(n=100000):
    """生成 n 条歌名原始数据文件，与报告中"十万条真实数据"对应。"""
    path = os.path.join(OUT_DIR, f"songs_{n}.txt")
    with open(path, "w", encoding="utf-8") as f:
        for i in range(n):
            f.write(make_name(i) + "\n")
    return path


# ---------- 表 1 ----------
def table1(n):
    res = {"n": n}

    # get(i)：随机位置
    pl = build(n)
    k = min(2000, n)
    t0 = time.perf_counter()
    for _ in range(k):
        pl.get(random.randint(0, n-1))
    res["get"] = (time.perf_counter()-t0)/k*1e6

    # insert（中间）：在 n/2 插入再删掉恢复
    t0 = time.perf_counter()
    for _ in range(k):
        pos = n // 2
        pl.insert(pos, "TMP")
        pl.remove(pos)
    res["insert_mid"] = (time.perf_counter()-t0)/k*1e6

    # remove（中间）
    t0 = time.perf_counter()
    for _ in range(k):
        pos = n // 2
        pl.insert(pos, "TMP")
        pl.remove(pos)
    res["remove_mid"] = (time.perf_counter()-t0)/k*1e6

    # indexOf（最坏：目标在末尾）
    t0 = time.perf_counter()
    for _ in range(k):
        pl.indexOf(make_name(n-1))
    res["indexOf_worst"] = (time.perf_counter()-t0)/k*1e6

    # insert（尾部追加）
    t0 = time.perf_counter()
    for _ in range(k):
        pl.insert(n, "TMP")
        pl.remove(n)   # 删掉刚加在末尾的
    res["insert_tail"] = (time.perf_counter()-t0)/k*1e6

    return res


# ---------- 表 2 ----------
def table2(n):
    pl = build(n)
    k = min(500, n)
    out = {"n": n}

    # 头：位置 0
    t0 = time.perf_counter()
    for _ in range(k):
        pl.insert(0, "TMP"); pl.remove(0)
    out["head"] = (time.perf_counter()-t0)/k*1e6

    # 中：位置 n/2
    t0 = time.perf_counter()
    for _ in range(k):
        p = n//2
        pl.insert(p, "TMP"); pl.remove(p)
    out["mid"] = (time.perf_counter()-t0)/k*1e6

    # 尾：位置 n
    t0 = time.perf_counter()
    for _ in range(k):
        pl.insert(n, "TMP"); pl.remove(n)
    out["tail"] = (time.perf_counter()-t0)/k*1e6

    out["head_over_mid"] = out["head"] / out["mid"] if out["mid"] else 0
    return out


# ---------- 表 3 ----------
def table3(n):
    """数 move_count：插入时真实搬移了几个元素"""
    out = {"n": n}
    pl = build(n)

    # 插在第 1 位（位置 0）：应搬 n 个
    pl.move_count = 0
    pl.insert(0, "TMP")
    out["at_first"] = pl.move_count
    pl.remove(0)

    # 插在末尾（位置 n）：应搬 0 个
    pl.move_count = 0
    pl.insert(n, "TMP")
    out["at_last"] = pl.move_count
    pl.remove(n)

    # 所有位置平均：均匀采样 0..n，只统计 insert 的搬移次数
    positions = list(range(0, n+1, max(1, n//50)))   # 采样最多 51 个位置
    total = 0
    for p in positions:
        pl.move_count = 0
        pl.insert(p, "TMP")      # 只数 insert 搬了几个
        total += pl.move_count
        pl.remove(p)
    out["avg_move"] = total / len(positions)
    out["n_over_2"] = n / 2
    return out


# ---------- 边界 + 功能自测（与报告"原型的功能自测"表一一对应） ----------
def selftest():
    cases = []

    # 1. get：歌单 5 首，取下标 2
    pl = build(5)
    v = pl.get(2)
    cases.append(("get", "歌单 5 首，调用 get(2)", "返回下标 2 的歌曲名",
                  v, "是" if v == "Song_000002" else "否"))

    # 2. insert：长度 5，在位置 2 插入
    pl = build(5)
    pl.insert(2, "NewSong")
    ok = pl.size() == 6 and pl.get(2) == "NewSong"
    cases.append(("insert", "长度 5，在位置 2 插入 NewSong", "长度变 6，位置 2 = NewSong",
                  f"长度 = {pl.size()}，get(2)={pl.get(2)}", "是" if ok else "否"))

    # 3. remove：长度 5，删下标 1
    pl = build(5)
    s = pl.remove(1)
    ok = pl.size() == 4 and s == "Song_000001"
    cases.append(("remove", "长度 5，调用 remove(1)", "删除下标 1，长度变 4",
                  f"删除了 {s}，长度 = {pl.size()}", "是" if ok else "否"))

    # 4. indexOf：找最后一首
    pl = build(5)
    idx = pl.indexOf("Song_000004")
    cases.append(("indexOf", "5 首歌，找最后一首 Song_000004", "返回下标 4",
                  f"返回下标 = {idx}", "是" if idx == 4 else "否"))

    # 5. 边界：空歌单上删除
    pl = MyPlaylist()
    try:
        pl.remove(0)
        cases.append(("边界：空歌单上删除", "空歌单调用 remove(0)", "抛出越界异常",
                      "未抛异常", "否"))
    except IndexError as e:
        cases.append(("边界：空歌单上删除", "空歌单调用 remove(0)", "抛出越界异常",
                      f"抛出 IndexError：{e}", "是"))

    # 6. 边界：越界位置
    pl = build(5)
    try:
        pl.get(10)
        cases.append(("边界：越界位置", "长度 5，调用 get(10)", "抛出越界异常",
                      "未抛异常", "否"))
    except IndexError:
        cases.append(("边界：越界位置", "长度 5，调用 get(10)", "抛出越界异常",
                      "抛出 IndexError", "是"))

    # 7. 边界：插入位置为 length+1（合法尾部追加）
    pl = build(5)
    pl.insert(5, "TailSong")
    ok = pl.size() == 6 and pl.get(5) == "TailSong"
    cases.append(("边界：插入位置为 length + 1", "长度 5，insert(5, TailSong)", "合法尾部追加成功",
                  f"长度 = {pl.size()}，get(5)={pl.get(5)}", "是" if ok else "否"))

    # 8. 边界：负数下标
    pl = build(5)
    try:
        pl.get(-1)
        cases.append(("边界：负数下标", "长度 5，调用 get(-1)", "抛出越界异常",
                      "未抛异常", "否"))
    except IndexError:
        cases.append(("边界：负数下标", "长度 5，调用 get(-1)", "抛出越界异常",
                      "抛出 IndexError", "是"))

    return cases


class Tee:
    """同时输出到控制台和日志文件"""
    def __init__(self, *files):
        self.files = files

    def write(self, s):
        for f in self.files:
            f.write(s)

    def flush(self):
        for f in self.files:
            f.flush()


def main():
    random.seed(42)
    ns = [100, 1000, 10000, 100000]

    log_path = os.path.join(OUT_DIR, "运行日志_playlist.txt")
    log_f = open(log_path, "w", encoding="utf-8")
    sys.stdout = Tee(sys.__stdout__, log_f)

    print("=== 顺序表歌单作业：完整运行日志 ===")
    print("运行时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("数据规模：n = 100 / 1000 / 10000 / 100000（共十万条，程序自动生成）")
    print("输出目录：", OUT_DIR)
    print()

    # 生成 10 万条原始数据文件
    p = write_songs_file(100000)
    print(f"已生成原始数据文件：{os.path.basename(p)}（100000 条歌名）")
    print()

    print("=== 表 1：四种操作单次耗时 (μs) ===")
    t1 = []
    for n in ns:
        r = table1(n)
        t1.append(r)
        print(f"n={n:>6}  get={r['get']:>8.2f}  ins(mid)={r['insert_mid']:>8.2f}  "
              f"del(mid)={r['remove_mid']:>8.2f}  idx(worst)={r['indexOf_worst']:>9.2f}  "
              f"ins(tail)={r['insert_tail']:>8.2f}")

    print("\n=== 表 2：插入位置影响 (μs) ===")
    t2 = []
    for n in ns:
        r = table2(n)
        t2.append(r)
        print(f"n={n:>6}  head={r['head']:>8.2f}  mid={r['mid']:>8.2f}  tail={r['tail']:>8.2f}  "
              f"head/mid={r['head_over_mid']:.2f}")

    print("\n=== 表 3：元素搬移次数 ===")
    t3 = []
    for n in ns:
        r = table3(n)
        t3.append(r)
        print(f"n={n:>6}  at_first={r['at_first']:>6}  at_last={r['at_last']:>4}  "
              f"avg={r['avg_move']:>8.1f}  n/2={r['n_over_2']:>8.1f}")

    print("\n=== 功能与边界自测（对应报告自测表）===")
    cases = selftest()
    for c in cases:
        print(f"  [{c[4]}] {c[0]:<20} {c[1]}  ->  {c[3]}")

    print("\n运行结束时间：", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    # 写 CSV
    with open(os.path.join(OUT_DIR, "table1.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["n", "get(us)", "insert_mid(us)", "remove_mid(us)", "indexOf_worst(us)", "insert_tail(us)"])
        for r in t1:
            w.writerow([r["n"], round(r["get"],1), round(r["insert_mid"],1),
                        round(r["remove_mid"],1), round(r["indexOf_worst"],1), round(r["insert_tail"],1)])

    with open(os.path.join(OUT_DIR, "table2.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["n", "head(us)", "mid(us)", "tail(us)", "head/mid"])
        for r in t2:
            w.writerow([r["n"], round(r["head"],1), round(r["mid"],1), round(r["tail"],1), round(r["head_over_mid"],2)])

    with open(os.path.join(OUT_DIR, "table3.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["n", "insert_at_first(elements moved)", "insert_at_last(elements moved)",
                    "avg_move_count", "n/2"])
        for r in t3:
            w.writerow([r["n"], r["at_first"], r["at_last"], round(r["avg_move"],1), r["n_over_2"]])

    with open(os.path.join(OUT_DIR, "selftest.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["接口", "测试用例", "预期结果", "实际结果", "是否通过"])
        for c in cases:
            w.writerow(c)

    sys.stdout = sys.__stdout__
    log_f.close()
    print(f"完成。表1/表2/表3/自测 CSV 与运行日志已写入：{OUT_DIR}")


if __name__ == "__main__":
    main()
