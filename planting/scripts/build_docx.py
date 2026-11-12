"""技术方案 Markdown 转 Word。

用途：把 docs/06-技术方案.md 转成 docs/06-技术方案.docx，
      保证 md 与 docx 内容一致，避免两份文档各改各的。

支持的 Markdown 子集：
    标题（# / ## / ###）、普通段落、无序列表、有序列表、表格、代码块、引用块、加粗。

用法：
    python scripts/build_docx.py
    python scripts/build_docx.py --src docs/06-技术方案.md --dst docs/06-技术方案.docx

失败行为：源文件缺失抛 FileNotFoundError；目标目录不可写抛 OSError。
"""

from __future__ import annotations   # 类型注解延迟求值

import argparse   # 解析 --src / --dst
import re         # 识别标题、列表、分割线
import sys        # 修改导入路径与退出码
from pathlib import Path   # 处理路径

from docx import Document                          # Word 文档对象
from docx.enum.table import WD_TABLE_ALIGNMENT     # 表格对齐方式
from docx.enum.text import WD_ALIGN_PARAGRAPH      # 段落对齐方式
from docx.oxml.ns import qn                        # 设置中文字体所需的命名空间
from docx.shared import Pt, RGBColor               # 字号与颜色

ROOT = Path(__file__).resolve().parents[1]   # 项目根目录
if str(ROOT) not in sys.path:                # 避免重复插入
    sys.path.insert(0, str(ROOT))            # 让脚本能独立导入

# 中文正文字体与字号
BODY_FONT = "宋体"          # 正文中文字体
BODY_SIZE = Pt(10.5)        # 正文字号（五号）
CODE_FONT = "Consolas"      # 代码等宽字体
CODE_SIZE = Pt(9)           # 代码字号


def _set_run_font(run, font_name: str, size: Pt, bold: bool = False, color: RGBColor | None = None) -> None:
    """设置 run 的中英文字体、字号、加粗与颜色。

    入参：
        run: python-docx 的 Run 对象。
        font_name: 字体名，中文走 eastAsia 属性。
        size: 字号。
        bold: 是否加粗。
        color: 可选颜色。
    出参：无。
    失败行为：不抛异常。
    """
    run.font.name = font_name                              # 设置西文字体名
    run.font.size = size                                   # 设置字号
    run.bold = bold                                        # 设置加粗
    if color is not None:                                  # 只有传了颜色才设置，避免覆盖默认黑
        run.font.color.rgb = color                         # 设置颜色
    # 中文字体必须单独设置 eastAsia，否则 Word 会退回默认宋体以外的字体
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)   # 直接写底层 XML 属性，这是 python-docx 的已知约束


def _add_rich_text(paragraph, text: str, font_name: str = BODY_FONT, size: Pt = BODY_SIZE) -> None:
    """把含 **加粗** 与 `代码` 标记的文本写入段落。

    入参：
        paragraph: 目标段落。
        text: 原始文本。
        font_name / size: 基础字体与字号。
    出参：无。
    失败行为：不抛异常。
    """
    # 先按行内代码切分，再按加粗切分，保证两种标记可以共存
    for chunk in re.split(r"(`[^`]+`)", text):                                # 用反引号切分
        if chunk.startswith("`") and chunk.endswith("`") and len(chunk) > 2:  # 命中行内代码
            run = paragraph.add_run(chunk[1:-1])                              # 去掉两侧反引号
            _set_run_font(run, CODE_FONT, CODE_SIZE)                          # 用等宽字体
            continue                                                          # 处理下一个片段

        for sub in re.split(r"(\*\*[^*]+\*\*)", chunk):                       # 再用双星号切分
            if sub.startswith("**") and sub.endswith("**") and len(sub) > 4:   # 命中加粗
                run = paragraph.add_run(sub[2:-2])                             # 去掉两侧星号
                _set_run_font(run, font_name, size, bold=True)                 # 加粗写入
            elif sub:                                                          # 普通文本
                run = paragraph.add_run(sub)                                   # 原样写入
                _set_run_font(run, font_name, size)                            # 常规字体


def _style_document(doc: Document) -> None:
    """设置正文默认样式。

    入参：doc Document 实例。
    出参：无。
    失败行为：不抛异常。
    """
    normal = doc.styles["Normal"]                                            # 取默认正文样式
    normal.font.name = BODY_FONT                                             # 西文字体
    normal.font.size = BODY_SIZE                                             # 字号
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)               # 中文字体单独设置
    normal.paragraph_format.line_spacing = 1.4                               # 1.4 倍行距，便于阅读
    normal.paragraph_format.space_after = Pt(4)                              # 段后 4 磅，避免过挤


def _parse_table_row(line: str) -> list[str]:
    """解析一行 Markdown 表格。

    入参：line 形如 "| a | b |"。
    出参：单元格文本列表。
    失败行为：不抛异常，空行返回空列表。
    """
    line = line.strip()                                            # 去掉首尾空白
    if not line.startswith("|"):                                   # 不是表格行
        return []                                                  # 返回空
    cells = [cell.strip() for cell in line.strip("|").split("|")]   # 去掉两侧竖线后按竖线切分
    return cells                                                   # 返回单元格列表


def _is_separator_row(cells: list[str]) -> bool:
    """判断是否为表格分隔行（|---|）。

    入参：cells 单元格列表。
    出参：布尔值。
    失败行为：不抛异常。
    """
    return bool(cells) and all(re.fullmatch(r"[-: ]+", cell or "-") for cell in cells)   # 每个单元格都只由横线/冒号/空格组成


def convert(src: Path, dst: Path) -> None:
    """执行转换。

    入参：
        src: Markdown 源文件路径。
        dst: 目标 docx 路径（已存在则覆盖）。
    出参：无。
    失败行为：源文件缺失抛 FileNotFoundError；写盘失败抛 OSError。
    """
    if not src.exists():                                    # 源文件必须存在
        raise FileNotFoundError(f"源文件不存在：{src}")

    lines = src.read_text(encoding="utf-8").splitlines()    # 按 UTF-8 读取，避免中文乱码
    doc = Document()                                        # 新建空文档
    _style_document(doc)                                    # 先定默认样式

    i = 0                  # 当前行游标
    total = len(lines)     # 总行数
    while i < total:                                   # 逐行解析
        line = lines[i]                                # 取当前行
        stripped = line.strip()                        # 去空白后的内容

        # 空行直接跳过
        if not stripped:                               # 空行
            i += 1                                     # 推进游标
            continue                                   # 不产生段落

        # 代码块
        if stripped.startswith("```"):                       # 代码块起始
            i += 1                                           # 跳过起始行
            code_lines: list[str] = []                       # 收集代码行
            while i < total and not lines[i].strip().startswith("```"):   # 直到遇到结束标记
                code_lines.append(lines[i])                  # 收一行
                i += 1                                       # 推进
            i += 1  # 跳过结束标记
            para = doc.add_paragraph()                                    # 代码用一个段落承载
            para.paragraph_format.left_indent = Pt(12)                    # 左缩进，视觉上区分
            run = para.add_run("\n".join(code_lines))                     # 合并成多行文本
            _set_run_font(run, CODE_FONT, CODE_SIZE)                      # 等宽字体
            para.paragraph_format.line_spacing = 1.1                      # 代码行距略小
            continue                                                      # 处理下一行

        # 表格
        if stripped.startswith("|"):                                    # 表格行
            rows: list[list[str]] = []                                  # 收集全部行
            while i < total and lines[i].strip().startswith("|"):        # 连续表格行
                cells = _parse_table_row(lines[i])                       # 解析单行
                if cells and not _is_separator_row(cells):               # 跳过 |---| 分隔行
                    rows.append(cells)                                   # 收集有效行
                i += 1                                                   # 推进
            if rows:                                                     # 有数据才建表
                cols = max(len(row) for row in rows)                     # 按最宽行定列数
                table = doc.add_table(rows=0, cols=cols)                 # 先建空表
                table.style = "Table Grid"                               # 带边框
                table.alignment = WD_TABLE_ALIGNMENT.CENTER              # 居中
                for r_index, row in enumerate(rows):                     # 逐行填充
                    cells = table.add_row().cells                        # 新增一行
                    for c_index in range(cols):                          # 逐列填充
                        text = row[c_index] if c_index < len(row) else ""   # 缺列补空
                        cell_para = cells[c_index].paragraphs[0]          # 取单元格首个段落
                        _add_rich_text(cell_para, text, size=Pt(9))       # 表格字号略小
                        # 表头加粗
                        if r_index == 0:                                  # 第一行为表头
                            for run in cell_para.runs:                    # 遍历该单元格所有 run
                                run.bold = True                           # 加粗
                doc.add_paragraph()                                       # 表后补空段，避免与下文粘连
            continue                                                      # 处理下一行

        # 标题
        heading = re.match(r"^(#{1,6})\s+(.*)$", stripped)                # 匹配 # 开头的标题
        if heading:                                                       # 命中标题
            level = len(heading.group(1))                                 # 井号个数即层级
            text = heading.group(2).strip()                               # 标题文本
            h = doc.add_heading(level=min(level, 4))                      # Word 最多用 4 级标题样式
            _add_rich_text(h, text, font_name="黑体", size=Pt(18 - level * 2))   # 层级越高字号越大
            if h.runs:                                                    # 有内容才设色
                h.runs[0].font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)      # 深蓝标题色
            i += 1                                                        # 推进
            continue                                                      # 处理下一行

        # 引用块
        if stripped.startswith(">"):                                      # 引用块
            para = doc.add_paragraph()                                    # 新建段落
            para.paragraph_format.left_indent = Pt(14)                     # 左缩进
            _add_rich_text(para, stripped.lstrip("> "), size=Pt(9.5))      # 去掉 > 后写入
            for run in para.runs:                                          # 遍历 run 设色
                run.font.color.rgb = RGBColor(0x55, 0x55, 0x55)            # 灰色，与正文区分
            i += 1                                                         # 推进
            continue                                                       # 处理下一行

        # 无序列表
        if re.match(r"^[-*+]\s+", stripped):                               # - / * / + 开头
            para = doc.add_paragraph(style="List Bullet")                  # 用内置项目符号样式
            _add_rich_text(para, re.sub(r"^[-*+]\s+", "", stripped))       # 去掉标记后写入
            i += 1                                                         # 推进
            continue                                                       # 处理下一行

        # 有序列表
        if re.match(r"^\d+[.、]\s+", stripped):                            # 数字加 . 或 、开头
            para = doc.add_paragraph(style="List Number")                  # 用内置编号样式
            _add_rich_text(para, re.sub(r"^\d+[.、]\s+", "", stripped))    # 去掉标记后写入
            i += 1                                                         # 推进
            continue                                                       # 处理下一行

        # 水平分割线
        if re.fullmatch(r"-{3,}", stripped):                               # 三个以上横线
            para = doc.add_paragraph()                                     # 新建段落
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER                     # 居中
            run = para.add_run("—" * 30)                                   # 用全角破折号画线
            _set_run_font(run, BODY_FONT, Pt(8), color=RGBColor(0xAA, 0xAA, 0xAA))   # 浅灰细线
            i += 1                                                         # 推进
            continue                                                       # 处理下一行

        # 普通段落
        para = doc.add_paragraph()                    # 新建段落
        _add_rich_text(para, stripped)                # 处理加粗与行内代码后写入
        i += 1                                        # 推进游标

    dst.parent.mkdir(parents=True, exist_ok=True)   # 目标目录不存在则创建
    doc.save(str(dst))                              # 保存文档
    print(f"已生成：{dst}")                          # 输出结果路径，便于确认


def main() -> int:
    """命令行入口。

    入参：--src / --dst，均可选。
    出参：退出码 0。
    失败行为：异常向上抛，由进程以非 0 退出。
    """
    parser = argparse.ArgumentParser(description="技术方案 Markdown 转 Word")          # 参数解析器
    parser.add_argument("--src", default=str(ROOT / "docs" / "06-技术方案.md"))          # 默认源文件
    parser.add_argument("--dst", default=str(ROOT / "docs" / "06-技术方案.docx"))        # 默认目标文件
    args = parser.parse_args()                                                          # 解析

    convert(Path(args.src), Path(args.dst))   # 执行转换
    return 0                                  # 正常退出


if __name__ == "__main__":     # 直接运行时才执行
    sys.exit(main())           # 用返回值作为退出码
