"""现状流程图渲染器：读取 src/data/process-model.json，输出 docs/assets/current-state-flow.svg。

主流程为泳道纵向链条，6 个主流程节点之间插入 5 个判定节点（菱形 J1–J5），
每个判定都画出「通过 / 不通过」两条出边及落点（异常卡片或外部审批），
这样图上能看到判断发生在哪一步、判断条件是什么、判断失败流向哪里。

不依赖任何第三方库。用法：python src/diagram/build_flow_svg.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "src", "data", "process-model.json")
OUT = os.path.join(ROOT, "docs", "assets", "current-state-flow.svg")

# 画布与栅格
W = 1780
MARGIN = 40
LANE_X, LANE_W = 40, 230
MAIN_X, MAIN_W = 300, 340
MAIN_CX = MAIN_X + MAIN_W / 2
EXC_X, EXC_W = 710, 540
HUM_X, HUM_W = 1285, 415
TOP = 176
NODE_GAP = 26
EXC_GAP = 18

# 判定节点
DIA_W, DIA_H = 232, 86
GAP_TO_DIA = 24
GAP_AFTER_DIA = 30
AP_BLOCK_W, AP_BLOCK_H = 134, 42

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


def arrow_down(x, y1, y2, color=C_GREEN, width=1.6):
    """竖线 + 下端箭头。"""
    return (
        f'<line x1="{x}" y1="{y1:.1f}" x2="{x}" y2="{y2 - 8:.1f}" stroke="{color}" stroke-width="{width}"/>'
        f'<path d="M{x - 5},{y2 - 9:.1f} L{x},{y2:.1f} L{x + 5},{y2 - 9:.1f}" fill="none" stroke="{color}" stroke-width="{width}"/>'
    )


def build():
    with open(DATA, encoding="utf-8") as f:
        model = json.load(f)

    main = model["mainFlow"]
    exc = model["exceptions"]
    hum = model["humanJudgements"]
    bots = model["bottlenecks"]
    decs = model.get("decisions", [])
    dec_after = {d["after"]: d for d in decs}

    # ---- 纵向排布：节点 → 判定菱形 → 下一节点 ----
    ys, dia_y, dia_h, ap_y = [], {}, {}, {}
    y = TOP
    for n in main:
        ys.append(y)
        y += node_height(n, MAIN_W)
        d = dec_after.get(n["id"])
        if d:
            y += GAP_TO_DIA
            dia_y[n["id"]] = y
            y += DIA_H
            if d["failTarget"] == "APPROVAL":
                ap_y[n["id"]] = y + 14
                y += 14 + AP_BLOCK_H + 26
            else:
                y += GAP_AFTER_DIA
        else:
            y += NODE_GAP
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
    hum_h = 76 + sum(len(l) * 18 + 10 for _, _, l in hum_lines)

    content_bottom = max(main_bottom, exc_bottom, TOP + hum_h)

    band_y = content_bottom + 46
    band_w = (W - 2 * MARGIN - 3 * 20) / 4
    band_heights = []
    for b in bots:
        lines = len(wrap(b["detail"], band_w - 32, 12)) + len(wrap("责任人：" + b["owner"], band_w - 32, 12))
        band_heights.append(34 + 12 + lines * 17 + 22)
    band_h = max(band_heights)
    legend_y = band_y + band_h + 56
    H = legend_y + 30

    out = []
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">')
    out.append('<title>种植灌溉与农事记录 · 现状流程图</title>')
    out.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{C_BG}"/>')

    # 头部
    out.append(text(MARGIN, 52, "种植灌溉与农事记录 · 现状流程图（As-Is）", 30, C_INK, "700"))
    out.append(text(MARGIN, 80, "禾丰种植合作社 · 六角色访谈还原：触发 → 输入 → 判断 → 交接 → 输出，判断失败转入异常路径", 14, C_MUTED))
    out.append(text(MARGIN, 106, "资料：FDE 训练中心「项目练习 1」现场调研报告（任务 2）；事实编号 f00–f55；节点时限均未实测", 12, C_MUTED))
    out.append(text(MARGIN, 126, "读图顺序：主干自上而下；菱形 J 为人工判断点，实线向下＝判断通过，虚线向右＝判断不通过（落点见「异常路径」列）", 12, C_BLUE))

    # 列标题
    out.append(text(LANE_X, TOP - 24, "岗位 / 泳道", 13, C_MUTED, "600"))
    out.append(text(MAIN_X, TOP - 24, "主流程（f01 六步）+ 判断点（J1–J5）", 13, C_GREEN, "600"))
    out.append(text(EXC_X, TOP - 24, "异常路径与转人工", 13, C_ORANGE, "600"))
    out.append(text(HUM_X, TOP - 24, "判断口径与依据", 13, C_BLUE, "600"))

    # ---- 主流程节点 + 泳道 ----
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

    # ---- 判定菱形 + 分支 ----
    for i, n in enumerate(main):
        d = dec_after.get(n["id"])
        if not d:
            continue
        dy = dia_y[n["id"]]
        dcy = dy + DIA_H / 2
        n_bottom = ys[i] + node_height(n, MAIN_W)
        # 进入菱形的箭头（无箭头，纯连接）
        out.append(f'<line x1="{MAIN_CX}" y1="{n_bottom:.1f}" x2="{MAIN_CX}" y2="{dy:.1f}" stroke="{C_GREEN}" stroke-width="1.6"/>')
        # 菱形
        out.append(
            f'<polygon points="{MAIN_CX:.1f},{dy:.1f} {MAIN_CX + DIA_W / 2:.1f},{dcy:.1f} '
            f'{MAIN_CX:.1f},{dy + DIA_H:.1f} {MAIN_CX - DIA_W / 2:.1f},{dcy:.1f}" '
            f'fill="{C_BLUE_BG}" stroke="{C_BLUE}" stroke-width="1.4"/>'
        )
        out.append(text(MAIN_CX, dcy - 4, d["id"], 11.5, C_BLUE, "700", "middle"))
        out.append(text(MAIN_CX, dcy + 14, d["q"], 11.5, C_INK, "600", "middle"))
        # 通过分支（实线向下）
        nxt_y = ys[i + 1] if i + 1 < len(main) else dy + DIA_H + GAP_AFTER_DIA
        out.append(arrow_down(MAIN_CX, dy + DIA_H, nxt_y))
        out.append(text(MAIN_CX - 10, dy + DIA_H + 20, d["passLabel"], 11.5, C_GREEN, "700", "end"))
        if d.get("passText"):
            if d["failTarget"] == "APPROVAL":
                # 审批块占据右侧空间，通过分支的说明改放左侧
                out.append(text(MAIN_CX - 24, dy + DIA_H + 20, d["passText"], 11, C_MUTED, "400", "end"))
            else:
                out.append(text(MAIN_CX + 10, dy + DIA_H + 20, d["passText"], 11, C_MUTED))
        # 不通过分支标签（菱形右侧）
        out.append(text(MAIN_CX + DIA_W / 2 + 8, dcy - 6, d["failLabel"], 11.5, C_ORANGE, "700"))

        if d["failTarget"] == "APPROVAL":
            # 外部审批：画一条向下的虚线到一个说明块
            by = ap_y[n["id"]]
            bx = MAIN_CX + 36
            out.append(
                f'<path d="M{MAIN_CX + DIA_W / 2:.1f},{dcy:.1f} L{bx + AP_BLOCK_W / 2:.1f},{dcy:.1f} '
                f'L{bx + AP_BLOCK_W / 2:.1f},{by - 6:.1f}" fill="none" stroke="{C_ORANGE}" stroke-width="1.3" stroke-dasharray="6 4"/>'
            )
            out.append(f'<path d="M{bx + AP_BLOCK_W / 2 - 5},{by - 8:.1f} L{bx + AP_BLOCK_W / 2:.1f},{by - 2:.1f} L{bx + AP_BLOCK_W / 2 + 5},{by - 8:.1f}" fill="none" stroke="{C_ORANGE}" stroke-width="1.3"/>')
            out.append(f'<rect x="{bx}" y="{by}" width="{AP_BLOCK_W}" height="{AP_BLOCK_H}" rx="6" fill="{C_ORANGE_BG}" stroke="{C_ORANGE}" stroke-width="1.2" stroke-dasharray="5 3"/>')
            out.append(text(bx + AP_BLOCK_W / 2, by + 18, "转审批人本人确认", 11.5, C_INK, "600", "middle"))
            out.append(text(bx + AP_BLOCK_W / 2, by + 34, "（f41，流程外）", 10.5, C_ORANGE, "400", "middle"))

    # ---- 异常卡片 + 来自判定节点的连接线 ----
    idx_of = {n["id"]: i for i, n in enumerate(main)}
    dec_by_target = {d["failTarget"]: d for d in decs}
    for k, e in enumerate(exc):
        ey = eys[k]
        eh = node_height(e, EXC_W)
        elbow = 652 + k * 9
        d = dec_by_target.get(e["id"])
        if d:
            src_id = d["after"]
            dcy = dia_y[src_id] + DIA_H / 2
            sx = MAIN_CX + DIA_W / 2
            e_y = ey + eh / 2
            out.append(
                f'<path d="M{sx:.1f},{dcy:.1f} L{elbow},{dcy:.1f} L{elbow},{e_y:.1f} L{EXC_X - 4},{e_y:.1f}" '
                f'fill="none" stroke="{C_ORANGE}" stroke-width="1.3" stroke-dasharray="6 4"/>'
            )
        else:
            # 无判定承接的异常（如系统不可用）挂在主流程节点上
            src = idx_of[e["from"]]
            n_y = ys[src] + node_height(main[src], MAIN_W) / 2
            e_y = ey + eh / 2
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

    # ---- 判断口径面板 ----
    out.append(f'<rect x="{HUM_X}" y="{TOP}" width="{HUM_W}" height="{hum_h}" rx="10" fill="{C_BLUE_BG}" stroke="{C_BLUE}" stroke-width="1.2"/>')
    out.append(text(HUM_X + 18, TOP + 30, "系统不能替代的五类判断", 15.5, C_INK, "700"))
    out.append(text(HUM_X + 18, TOP + 52, "对应图中菱形 J1–J5 的判定口径", 11.5, C_MUTED))
    cy = TOP + 78
    for jid, title, lines in hum_lines:
        out.append(f'<rect x="{HUM_X + 16}" y="{cy - 13}" width="26" height="18" rx="4" fill="{C_BLUE}"/>')
        out.append(text(HUM_X + 29, cy, jid, 10.5, "#ffffff", "700", "middle"))
        for line in lines:
            out.append(text(HUM_X + 50, cy, line, 12.5, C_MUTED))
            cy += 18
        cy += 10

    # ---- 瓶颈带 ----
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

    # ---- 图例 ----
    out.append(f'<line x1="{MARGIN}" y1="{legend_y}" x2="{MARGIN + 34}" y2="{legend_y}" stroke="{C_GREEN}" stroke-width="2"/>')
    out.append(text(MARGIN + 42, legend_y + 4, "主流程（六步）", 11.5, C_MUTED))
    out.append(
        f'<polygon points="{MARGIN + 190},{legend_y - 9} {MARGIN + 206},{legend_y} {MARGIN + 190},{legend_y + 9} '
        f'{MARGIN + 174},{legend_y}" fill="{C_BLUE_BG}" stroke="{C_BLUE}" stroke-width="1.2"/>'
    )
    out.append(text(MARGIN + 214, legend_y + 4, "人工判断点（实线＝通过，虚线＝不通过）", 11.5, C_MUTED))
    out.append(f'<line x1="{MARGIN + 470}" y1="{legend_y}" x2="{MARGIN + 504}" y2="{legend_y}" stroke="{C_ORANGE}" stroke-width="1.5" stroke-dasharray="6 4"/>')
    out.append(text(MARGIN + 512, legend_y + 4, "异常路径 / 转人工", 11.5, C_MUTED))
    out.append(f'<rect x="{MARGIN + 660}" y="{legend_y - 6}" width="16" height="12" rx="3" fill="{C_GOLD}"/>')
    out.append(text(MARGIN + 684, legend_y + 4, "瓶颈与责任人", 11.5, C_MUTED))
    out.append(text(W - MARGIN, legend_y + 4, "合成训练案例 · 不代表真实授权、业务执行或客户验收", 11, C_MUTED, "400", "end"))

    out.append("</svg>")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    return len(main), len(decs), len(exc), len(hum), len(bots), W, H


if __name__ == "__main__":
    if not os.path.exists(DATA):
        sys.exit("缺少数据文件：%s" % DATA)
    result = build()
    print("生成完成：%s" % OUT)
    print("主流程 %d / 判断点 %d / 异常 %d / 判断口径 %d / 瓶颈 %d / 画布 %dx%d" % result)
