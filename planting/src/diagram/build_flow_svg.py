"""现状流程图渲染器：读取 src/data/process-model.json，输出 docs/assets/current-state-flow.svg。

不依赖任何第三方库，生成的 SVG 可直接在浏览器 / VS Code / GitHub 中查看。
用法：python src/diagram/build_flow_svg.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "src", "data", "process-model.json")
OUT = os.path.join(ROOT, "docs", "assets", "current-state-flow.svg")

# 画布与栅格
W = 1730
MARGIN = 40
LANE_X, LANE_W = 40, 230
MAIN_X, MAIN_W = 300, 340
EXC_X, EXC_W = 700, 540
HUM_X, HUM_W = 1280, 410
TOP = 158
NODE_GAP = 26
EXC_GAP = 18

# 配色
C_BG = "#ffffff"
C_INK = "#1f2328"
C_MUTED = "#59636f"
C_LINE = "#d8dee4"
C_GREEN = "#2f6d4f"
C_GREEN_BG = "#f3f8f4"
C_ORANGE = "#b05a2b"
C_ORANGE_BG = "#fdf5ef"
C_GOLD = "#8a6d3b"
C_GOLD_BG = "#fdf9ef"
C_BLUE = "#2f5e73"
C_BLUE_BG = "#f2f7fa"


def esc(s):
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def char_w(ch, fs):
    """粗略字宽：CJK 按 1em，拉丁与数字按 0.55em。"""
    return fs if ord(ch) > 0x2e7f else fs * 0.55


def wrap(text, max_w, fs):
    """按字宽贪婪换行；英数字母数字串（如 f12、90、12%）不拆开。"""
    import re

    tokens = re.findall(r"[A-Za-z0-9%\./]+|\s|.", text)
    lines, cur, width = [], "", 0.0
    for tok in tokens:
        tw = sum(char_w(c, fs) for c in tok)
        if cur and width + tw > max_w:
            lines.append(cur)
            cur, width = "", 0.0
            if tok == " ":
                continue
        if tw > max_w:
            for ch in tok:
                cw_ = char_w(ch, fs)
                if cur and width + cw_ > max_w:
                    lines.append(cur)
                    cur, width = "", 0.0
                cur += ch
                width += cw_
            continue
        cur += tok
        width += tw
    if cur:
        lines.append(cur)

    # 避免行首出现右括号/标点、行尾出现左括号
    for i in range(1, len(lines)):
        if lines[i][:1] in "）)，。、；：":
            lines[i - 1] += lines[i][:1]
            lines[i] = lines[i][1:]
    for i in range(len(lines) - 1):
        if lines[i].endswith("（"):
            lines[i + 1] = "（" + lines[i + 1]
            lines[i] = lines[i][:-1]
    lines = [l.rstrip() for l in lines if l.strip()]
    return lines or [""]


def text(x, y, s, fs, fill=C_INK, weight="400", anchor="start", family="'Microsoft YaHei', 'PingFang SC', 'Noto Sans CJK SC', sans-serif"):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{fs}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}" font-family="{family}">{esc(s)}</text>'
    )


def node_height(n, w, fs_title=16.5, fs_field=12.5, label_w=58):
    inner = w - 36
    h = 14
    h += len(wrap(f'{n["id"]} · {n["title"]}', inner, fs_title)) * 23
    h += 6
    for _, val in n["fields"]:
        h += len(wrap(val, inner - label_w, fs_field)) * 18 + 3
    h += 20
    return max(h, 96)


def build():
    with open(DATA, encoding="utf-8") as f:
        model = json.load(f)

    main = model["mainFlow"]
    exc = model["exceptions"]
    hum = model["humanJudgements"]
    bots = model["bottlenecks"]

    # 主流程纵向排布
    ys = []
    y = TOP
    for n in main:
        ys.append(y)
        y += node_height(n, MAIN_W) + NODE_GAP
    main_bottom = y - NODE_GAP

    # 异常卡片纵向排布
    eys = []
    y = TOP
    for e in exc:
        eys.append(y)
        y += node_height(e, EXC_W) + EXC_GAP
    exc_bottom = y - EXC_GAP

    # 人工判断面板高度
    hum_lines = []
    for jid, title, desc in hum:
        hum_lines.append((jid, title, wrap(f"{title} —— {desc}", HUM_W - 72, 12.5)))
    hum_h = 54 + sum(len(l) * 18 + 10 for _, _, l in hum_lines)

    side_bottom = max(exc_bottom, TOP + hum_h)
    content_bottom = max(main_bottom, side_bottom)

    band_y = content_bottom + 46
    band_w = (1690 - 40 - 3 * 20) / 4
    band_heights = []
    for b in bots:
        lines = len(wrap(b["detail"], band_w - 32, 12)) + len(wrap("责任人：" + b["owner"], band_w - 32, 12))
        band_heights.append(34 + 12 + lines * 17 + 22)
    band_h = max(band_heights)
    legend_y = band_y + band_h + 56
    H = legend_y + 24

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">')
    out.append(f'<title>种植灌溉与农事记录 · 现状流程图</title>')
    out.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{C_BG}"/>')

    # 头部
    out.append(text(MARGIN, 52, "种植灌溉与农事记录 · 现状流程图（As-Is）", 30, C_INK, "700"))
    out.append(text(MARGIN, 80, "禾丰种植合作社 · 六角色访谈还原：触发 → 输入 → 交接 → 人工判断 → 输出 → 异常路径", 14, C_MUTED))
    out.append(text(MARGIN, 106, "资料：FDE 训练中心「项目练习 1」现场调研报告（任务 2）；事实编号 f00–f55；节点时限均未实测，瓶颈排序为待验证假设", 12, C_MUTED))

    # 列标题
    out.append(text(LANE_X, TOP - 22, "岗位 / 泳道", 13, C_MUTED, "600"))
    out.append(text(MAIN_X, TOP - 22, "主流程（f01 六步）", 13, C_GREEN, "600"))
    out.append(text(EXC_X, TOP - 22, "异常路径与转人工", 13, C_ORANGE, "600"))
    out.append(text(HUM_X, TOP - 22, "只能由人完成的判断", 13, C_BLUE, "600"))

    # 主流程节点
    for idx, n in enumerate(main):
        yy = ys[idx]
        h = node_height(n, MAIN_W)
        out.append(f'<rect x="{MAIN_X}" y="{yy}" width="{MAIN_W}" height="{h}" rx="10" fill="{C_GREEN_BG}" stroke="{C_GREEN}" stroke-width="1.2"/>')
        out.append(f'<rect x="{MAIN_X}" y="{yy}" width="6" height="{h}" rx="3" fill="{C_GREEN}"/>')
        cy = yy + 26
        for line in wrap(f'{n["id"]} · {n["title"]}', MAIN_W - 36, 16.5):
            out.append(text(MAIN_X + 20, cy, line, 16.5, C_INK, "700"))
            cy += 23
        cy += 4
        for label, val in n["fields"]:
            first = True
            for line in wrap(val, MAIN_W - 36 - 58, 12.5):
                if first:
                    out.append(text(MAIN_X + 20, cy, label, 12.5, C_GREEN, "600"))
                    first = False
                out.append(text(MAIN_X + 78, cy, line, 12.5, C_MUTED))
                cy += 18
            cy += 3
        out.append(text(MAIN_X + 20, yy + h - 14, "证据 " + " ".join(n["refs"]), 10.5, C_GREEN))
        # 泳道标签
        lane_h = min(h, 54)
        out.append(f'<rect x="{LANE_X}" y="{yy + (h - lane_h) // 2}" width="{LANE_W}" height="{lane_h}" rx="8" fill="#eef2ee" stroke="{C_LINE}"/>')
        out.append(text(LANE_X + LANE_W / 2, yy + (h - lane_h) // 2 + 22, n["lane"], 13.5, C_GREEN, "600", "middle"))
        out.append(text(LANE_X + LANE_W / 2, yy + (h - lane_h) // 2 + 38, n["laneNote"], 10.5, C_MUTED, "400", "middle"))

    # 主流程箭头
    for i in range(len(main) - 1):
        y1 = ys[i] + node_height(main[i], MAIN_W)
        y2 = ys[i + 1]
        out.append(f'<line x1="{MAIN_X + MAIN_W / 2}" y1="{y1}" x2="{MAIN_X + MAIN_W / 2}" y2="{y2}" stroke="{C_GREEN}" stroke-width="1.6"/>')
        out.append(f'<path d="M{MAIN_X + MAIN_W / 2 - 5},{y2 - 6} L{MAIN_X + MAIN_W / 2},{y2} L{MAIN_X + MAIN_W / 2 + 5},{y2 - 6}" fill="none" stroke="{C_GREEN}" stroke-width="1.6"/>')

    # 异常卡片 + 连接线
    idx_of = {n["id"]: i for i, n in enumerate(main)}
    for k, e in enumerate(exc):
        ey = eys[k]
        eh = node_height(e, EXC_W)
        src = idx_of[e["from"]]
        n_y = ys[src] + node_height(main[src], MAIN_W) / 2
        e_y = ey + eh / 2
        elbow = 660 + k * 8
        out.append(
            f'<path d="M{MAIN_X + MAIN_W},{n_y:.1f} L{elbow},{n_y:.1f} L{elbow},{e_y:.1f} L{EXC_X - 4},{e_y:.1f}" '
            f'fill="none" stroke="{C_ORANGE}" stroke-width="1.3" stroke-dasharray="6 4"/>'
        )
        out.append(f'<path d="M{EXC_X - 10},{e_y - 5} L{EXC_X - 2},{e_y} L{EXC_X - 10},{e_y + 5}" fill="none" stroke="{C_ORANGE}" stroke-width="1.3"/>')

        out.append(f'<rect x="{EXC_X}" y="{ey}" width="{EXC_W}" height="{eh}" rx="10" fill="{C_ORANGE_BG}" stroke="{C_ORANGE}" stroke-width="1.2" stroke-dasharray="6 4"/>')
        cy = ey + 26
        for line in wrap(f'{e["id"]} · {e["title"]}', EXC_W - 36, 15.5):
            out.append(text(EXC_X + 18, cy, line, 15.5, C_INK, "700"))
            cy += 22
        cy += 2
        for label, val in e["fields"]:
            out.append(text(EXC_X + 18, cy, label, 11.5, C_ORANGE, "600"))
            for line in wrap(val, EXC_W - 36 - 58, 12):
                out.append(text(EXC_X + 76, cy, line, 12, C_MUTED))
                cy += 17
            cy += 3
        out.append(text(EXC_X + 18, ey + eh - 14, "证据 " + " ".join(e["refs"]), 10.5, C_ORANGE))

    # 人工判断面板
    out.append(f'<rect x="{HUM_X}" y="{TOP}" width="{HUM_W}" height="{hum_h}" rx="10" fill="{C_BLUE_BG}" stroke="{C_BLUE}" stroke-width="1.2"/>')
    out.append(text(HUM_X + 18, TOP + 30, "系统不能替代的五类判断", 15.5, C_INK, "700"))
    cy = TOP + 58
    for jid, title, lines in hum_lines:
        out.append(f'<rect x="{HUM_X + 16}" y="{cy - 13}" width="26" height="18" rx="4" fill="{C_BLUE}"/>')
        out.append(text(HUM_X + 29, cy, jid, 10.5, "#ffffff", "700", "middle"))
        for line in lines:
            out.append(text(HUM_X + 50, cy, line, 12.5, C_MUTED))
            cy += 18
        cy += 10

    # 瓶颈带
    out.append(text(MARGIN, band_y - 14, "瓶颈与责任人（量化基线待样本验证）", 14, C_GOLD, "700"))
    for k, b in enumerate(bots):
        bx = MARGIN + k * (band_w + 20)
        by = band_y
        bh = band_heights[k]
        out.append(f'<rect x="{bx}" y="{by}" width="{band_w}" height="{bh}" rx="8" fill="{C_GOLD_BG}" stroke="{C_GOLD}" stroke-width="1"/>')
        out.append(f'<rect x="{bx}" y="{by}" width="{band_w}" height="4" rx="2" fill="{C_GOLD}"/>')
        cy = by + 30
        out.append(text(bx + 16, cy, f'{b["id"]} · {b["title"]}', 13.5, C_INK, "700"))
        cy += 22
        for line in wrap(b["detail"], band_w - 32, 12):
            out.append(text(bx + 16, cy, line, 12, C_MUTED))
            cy += 17
        cy += 3
        out.append(text(bx + 16, cy, "责任人：" + b["owner"], 12, C_GOLD, "600"))
        cy += 16
        out.append(text(bx + 16, cy, b["status"] + " · " + " ".join(b["refs"]), 11, C_MUTED))

    # 图例
    out.append(f'<line x1="{MARGIN}" y1="{legend_y}" x2="{MARGIN + 34}" y2="{legend_y}" stroke="{C_GREEN}" stroke-width="2"/>')
    out.append(text(MARGIN + 42, legend_y + 4, "主流程（六步）", 11.5, C_MUTED))
    out.append(f'<line x1="{MARGIN + 170}" y1="{legend_y}" x2="{MARGIN + 204}" y2="{legend_y}" stroke="{C_ORANGE}" stroke-width="1.5" stroke-dasharray="6 4"/>')
    out.append(text(MARGIN + 212, legend_y + 4, "异常路径 / 转人工", 11.5, C_MUTED))
    out.append(f'<rect x="{MARGIN + 350}" y="{legend_y - 6}" width="16" height="12" rx="3" fill="{C_GOLD}"/>')
    out.append(text(MARGIN + 374, legend_y + 4, "瓶颈与责任人", 11.5, C_MUTED))
    out.append(f'<rect x="{MARGIN + 500}" y="{legend_y - 6}" width="16" height="12" rx="3" fill="{C_BLUE}"/>')
    out.append(text(MARGIN + 524, legend_y + 4, "必须人工完成的判断", 11.5, C_MUTED))
    out.append(text(W - MARGIN, legend_y + 4, "合成训练案例 · 不代表真实授权、业务执行或客户验收", 11, C_MUTED, "400", "end"))

    out.append("</svg>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    return len(main), len(exc), len(hum), len(bots), W, H


if __name__ == "__main__":
    if not os.path.exists(DATA):
        sys.exit("缺少数据文件：%s" % DATA)
    result = build()
    print("生成完成：%s" % OUT)
    print("主流程 %d / 异常 %d / 人工判断 %d / 瓶颈 %d / 画布 %dx%d" % result)
