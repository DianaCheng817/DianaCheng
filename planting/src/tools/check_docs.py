"""文档自检：证据编号越界、图片引用缺失、SVG 可解析、JSON 可解析。

用法：python src/tools/check_docs.py
退出码 0 = 全部通过；1 = 有问题。
"""

import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(ROOT, "docs")

# 本案例允许出现的事实编号（36 条：f00–f05 / f10–f15 / f20–f25 / f30–f35 / f40–f45 / f50–f55）
GROUPS = [(0, 5, 5), (10, 15, 15), (20, 25, 25), (30, 35, 35), (40, 45, 45), (50, 55, 55)]
VALID_FACTS = {f"f{i:02d}" for lo, hi, _ in GROUPS for i in range(lo, hi + 1)}

problems = []
stats = {"docs": 0, "fact_refs": 0, "images": 0}


def iter_md():
    for name in sorted(os.listdir(DOCS)):
        if name.endswith(".md"):
            yield name, os.path.join(DOCS, name)


def check_facts(name, text):
    for m in re.finditer(r"`?(f\d{2})`?", text):
        fid = m.group(1)
        stats["fact_refs"] += 1
        if fid not in VALID_FACTS:
            line = text[: m.start()].count("\n") + 1
            problems.append(f"{name}:{line} 证据编号越界 -> {fid}")


def check_images(name, path, text):
    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
        target = m.group(1).strip()
        if target.startswith("http"):
            continue
        stats["images"] += 1
        full = os.path.normpath(os.path.join(os.path.dirname(path), target))
        if not os.path.exists(full):
            problems.append(f"{name} 引用的图片不存在 -> {target}")
        elif target.lower().endswith(".svg"):
            try:
                ET.parse(full)
            except ET.ParseError as e:
                problems.append(f"{name} 引用的 SVG 无法解析 -> {target}: {e}")


def main():
    if not os.path.isdir(DOCS):
        print("缺少 docs 目录")
        return 1

    for name, path in iter_md():
        stats["docs"] += 1
        with io.open(path, encoding="utf-8") as f:
            text = f.read()
        check_facts(name, text)
        check_images(name, path, text)

    # 数据文件与图
    data = os.path.join(ROOT, "src", "data", "process-model.json")
    try:
        with io.open(data, encoding="utf-8") as f:
            model = json.load(f)
        for key in ("mainFlow", "decisions", "exceptions", "humanJudgements", "bottlenecks"):
            if not model.get(key):
                problems.append(f"process-model.json 缺少 {key}")
        node_ids = {n["id"] for n in model["mainFlow"]}
        exc_ids = {e["id"] for e in model["exceptions"]}
        for n in model["mainFlow"]:
            for ref in n["refs"]:
                if ref not in VALID_FACTS:
                    problems.append(f"process-model.json 节点 {n['id']} 证据编号越界 -> {ref}")
        for e in model["exceptions"]:
            if e["from"] not in node_ids:
                problems.append(f"process-model.json 异常 {e['id']} 挂载节点不存在 -> {e['from']}")
        for d in model["decisions"]:
            if d["after"] not in node_ids:
                problems.append(f"process-model.json 判断 {d['id']} 挂在未知节点 -> {d['after']}")
            if d["failTarget"] != "APPROVAL" and d["failTarget"] not in exc_ids:
                problems.append(f"process-model.json 判断 {d['id']} 不通过分支落点不存在 -> {d['failTarget']}")
            if d["id"] not in {h[0] for h in model["humanJudgements"]}:
                problems.append(f"process-model.json 判断 {d['id']} 在判断口径面板中缺少对应条目")
    except Exception as e:
        problems.append(f"process-model.json 解析失败: {e}")

    svg = os.path.join(DOCS, "assets", "current-state-flow.svg")
    if not os.path.exists(svg):
        problems.append("缺少 docs/assets/current-state-flow.svg（先跑 python src/diagram/build_flow_svg.py）")
    else:
        try:
            ET.parse(svg)
        except ET.ParseError as e:
            problems.append(f"SVG 解析失败: {e}")

    print(f"文档 {stats['docs']} 份 / 证据引用 {stats['fact_refs']} 处 / 图片 {stats['images']} 处")
    if problems:
        print("发现问题：")
        for p in problems:
            print("  - " + p)
        return 1
    print("自检通过：证据编号均在 f00–f55 范围内，图片与 SVG 均可解析。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
