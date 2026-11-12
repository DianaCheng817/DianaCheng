"""Harness 校验规则集。

每条规则只做一件事，输入输出统一为 RuleHit 列表，便于独立测试与增删。

规则设计依据（来自平台扣分点）：
    H1 响应结构      —— 所有接口必须返回 ok / data / error
    H2 证据编号      —— 只允许 f00–f55 且必须真实存在于知识库
    H3 角色错配      —— 只允许六个已访谈角色
    H4 虚构实体      —— 禁止出现未经访谈确认的地块、作物、E01/R01/R02 一类自造编号
    H5 方案越界      —— 禁止把「自动控制泵阀」当成方案提出（边界声明中的否定表述除外）
    H6 自创数值      —— 禁止出现未经样本验证的自造工时与频次区间
    H7 边界声明      —— 必须显式写明只读 / 不自动控制泵阀 / 观测解释与灌溉建议
    H8 数值验证标注  —— 出现量化指标时必须同时标注待样本验证等字样
"""

from __future__ import annotations   # 类型注解延迟求值

import re                                    # 正则用于编号、数值与位置定位
from dataclasses import dataclass, field     # 轻量结果对象，避免为一条校验结果建类
from typing import Any                        # 标注 check_envelope 的任意入参

from app.core.config import config   # 词表全部来自配置，改规则不需要改代码

# 否定词：用于区分「不自动控制泵阀」（合规声明）与「自动控制泵阀」（违规方案）
NEGATION_WORDS = ("不", "禁止", "不得", "严禁", "不做", "无", "非", "不自动")   # 覆盖常见的否定写法

# 量化数值的识别：数字 + 单位。
# 前置负向断言 (?<![A-Za-z0-9]) 用于排除「S2 天气核查」「I1 观测」这类编号，
# 否则流程编号会被误判成「2 天」这样的时间数值。
NUMERIC_PATTERN = re.compile(   # 预编译，H8 会逐句调用，避免重复构造
    r"(?<![A-Za-z0-9])\d+(?:\.\d+)?\s*(?:分钟|小时|天|次|个百分点|%|％|亩|个地块|万元|元)"
)


@dataclass
class RuleHit:
    """单条规则的校验结果。"""

    rule_id: str                     # 规则编号，如 H3
    rule_name: str                   # 规则中文名
    passed: bool                     # 是否通过
    severity: str = "block"          # block 阻断 / warn 告警
    detail: str = ""                 # 人类可读结论
    hits: list[str] = field(default_factory=list)   # 命中的具体内容，供调用方展示


def _near_negation(text: str, index: int, match_length: int = 0, back: int = 10, forward: int = 12) -> bool:
    """判断命中位置的前后是否出现否定词。

    中文里否定词可能出现在违禁词之前（不自动控制泵阀），也可能出现在之后
    （自动开阀不做），因此必须双向回看，否则会把合规的边界声明误判为违规方案。

    入参：
        text: 待检查全文。
        index: 命中词的起始下标。
        match_length: 命中词长度，用于确定向后看的起点。
        back: 向前回看的字符数。
        forward: 向后延伸的字符数。
    出参：
        True 表示上下文存在否定词，属于合规表述。
    失败行为：不抛异常。
    """
    start = max(0, index - back)                                   # 向前回看的起点，不能越过字符串头部
    end = min(len(text), index + match_length + forward)           # 向后延伸的终点，不能越过字符串尾部
    context = text[start:index] + text[index + match_length:end]   # 拼出前后文，命中词本身不参与判断
    return any(word in context for word in NEGATION_WORDS)          # 任一侧出现否定词即视为合规表述


def check_envelope(payload: Any) -> RuleHit:
    """H1：校验响应是否具备 ok / data / error 三字段。

    入参：payload 任意响应对象。
    出参：RuleHit 结果。
    失败行为：不抛异常。
    """
    if not isinstance(payload, dict):   # 非字典直接判失败，后续不可能取到字段
        return RuleHit("H1", "响应结构", False, "block", "响应不是字典结构")

    missing = [k for k in ("ok", "data", "error") if k not in payload]   # 逐个检查三字段是否齐备
    if missing:                                                           # 缺字段即视为破坏契约
        return RuleHit("H1", "响应结构", False, "block", f"缺少字段：{missing}", missing)

    if not isinstance(payload["error"], dict):   # error 必须是对象，不能是字符串或 None
        return RuleHit("H1", "响应结构", False, "block", "error 字段必须是对象")
    if "code" not in payload["error"] or "msg" not in payload["error"]:   # error 内部也必须含 code 与 msg
        return RuleHit("H1", "响应结构", False, "block", "error 必须含 code 与 msg")

    return RuleHit("H1", "响应结构", True, "block", "结构合规")   # 全部检查通过


def check_evidence_ids(text: str, valid_ids: set[str]) -> RuleHit:
    """H2：校验正文中出现的 fxx 证据编号是否合法。

    入参：
        text: 正文。
        valid_ids: 知识库中真实存在的证据编号集合。
    出参：RuleHit 结果，hits 为非法编号列表。
    失败行为：不抛异常。
    """
    found = set(re.findall(r"\bf(\d{2})\b", text))   # 提取所有形如 f12 的两位编号
    invalid: list[str] = []                          # 收集非法编号
    for idx in found:                                # 逐个判断
        node_id = f"f{idx}"                          # 还原成完整节点编号
        # 越界或不在知识库中，一律视为引用错误（防止模型自造 f99 这类编号）
        if int(idx) > config.knowledge_graph.evidence_max_index or node_id not in valid_ids:
            invalid.append(node_id)   # 记下非法编号，便于前端定位

    if invalid:   # 有非法编号即判失败
        return RuleHit("H2", "证据编号", False, "block", f"存在非法证据编号：{sorted(invalid)}", sorted(invalid))
    return RuleHit("H2", "证据编号", True, "block", f"引用编号全部合法，共 {len(found)} 个")   # 通过时回报引用数量


def check_roles(text: str) -> RuleHit:
    """H3：校验是否出现访谈中不存在的角色。

    入参：text 正文。
    出参：RuleHit 结果。
    失败行为：不抛异常。
    """
    hits = [role for role in config.harness.banned_roles if role in text]   # 逐个比对禁用角色词表
    if hits:                                                                # 命中即说明模型把未访谈角色写成了事实
        return RuleHit("H3", "角色错配", False, "block", f"出现未访谈角色：{hits}", hits)
    return RuleHit("H3", "角色错配", True, "block", "未出现未访谈角色")       # 通过


def check_entities(text: str) -> RuleHit:
    """H4：校验是否出现虚构地块、作物或自造编号（E01/R01/R02）。

    入参：text 正文。
    出参：RuleHit 结果。
    失败行为：不抛异常。
    """
    hits = [item for item in config.harness.banned_entities if item in text]   # 先按配置词表精确匹配
    # 单独兜一层正则：E 数字 / R 数字 + 两位，防止变体写法漏网
    hits.extend(re.findall(r"\b[ER]\d{2}\b", text))   # 正则覆盖未列入词表的同类编号
    hits = sorted(set(hits))                          # 去重排序，避免同一条重复计数
    if hits:                                          # 命中任一即判失败
        return RuleHit("H4", "虚构实体", False, "block", f"出现未经访谈确认的实体：{hits}", hits)
    return RuleHit("H4", "虚构实体", True, "block", "未出现虚构实体")   # 通过


def check_boundary_violation(text: str) -> RuleHit:
    """H5：校验是否把「自动控制泵阀」当成方案提出。

    入参：text 正文。
    出参：RuleHit 结果。
    失败行为：不抛异常。
    """
    violations: list[str] = []                                    # 收集违规关键词
    for keyword in config.harness.forbidden_keywords:             # 遍历禁用方案词表
        for match in re.finditer(re.escape(keyword), text):       # 转义后精确查找每个出现位置
            # 否定语境的「不自动控制泵阀」是必须保留的边界声明，不能误判为违规
            if not _near_negation(text, match.start(), len(keyword)):
                violations.append(keyword)   # 非否定语境才算真的越界

    if violations:   # 有越界表述即判失败
        return RuleHit(
            "H5", "方案越界", False, "block",
            f"把自动控制泵阀当作方案输出：{sorted(set(violations))}", sorted(set(violations)),
        )
    return RuleHit("H5", "方案越界", True, "block", "未越界到自动控制泵阀")   # 通过


def check_numbers(text: str) -> RuleHit:
    """H6：校验是否出现自造数值区间。

    入参：text 正文。
    出参：RuleHit 结果。
    失败行为：不抛异常。
    """
    hits = [item for item in config.harness.banned_numbers if item in text]   # 按禁用语料精确匹配
    if hits:                                                                  # 命中即说明这类数字没有访谈来源
        return RuleHit("H6", "自创数值", False, "block", f"出现未经样本验证的自造数值：{hits}", hits)
    return RuleHit("H6", "自创数值", True, "block", "未出现自造数值")          # 通过


def check_boundary_declaration(text: str) -> RuleHit:
    """H7：校验是否显式写明首期边界。

    入参：text 正文。
    出参：RuleHit 结果。
    失败行为：不抛异常。
    """
    markers = config.harness.required_boundary_markers                 # 三个必选边界表述
    found = [m for m in markers if m in text]                          # 看正文里出现了哪些
    if not found:                                                      # 一个都没有即判失败
        return RuleHit("H7", "边界声明", False, "block", f"未出现任何边界声明，需含其一：{markers}")
    return RuleHit("H7", "边界声明", True, "block", f"已声明边界：{found}")   # 通过时回报命中了哪几条


def check_verification_markers(text: str) -> RuleHit:
    """H8：校验量化数值是否带验证性标注。

    逐句扫描：句中出现「数字 + 单位」却没有任何验证标注，即视为把估算值写成事实。

    入参：text 正文。
    出参：RuleHit 结果，hits 为缺标注的句子。
    失败行为：不抛异常。
    """
    sentences = re.split(r"[。；;\n]", text)             # 按中文句号、分号、换行切句，标注一般跟在同一句内
    markers = config.harness.verification_markers        # 允许的标注词表，如「待样本验证」「访谈确认」
    offenders: list[str] = []                            # 收集缺标注的句子

    for sentence in sentences:                                        # 逐句扫描
        if not NUMERIC_PATTERN.search(sentence):                      # 不含量化数值就跳过，避免噪声
            continue                                                  # 进入下一句
        if not any(m in sentence for m in markers):                   # 含数值但没有任何标注词
            offenders.append(sentence.strip()[:60])                   # 截断到 60 字，避免报告过长

    if offenders:   # 有缺标注的句子即判失败（warn 级，不阻断但扣分）
        return RuleHit(
            "H8", "数值验证标注", False, "warn",
            f"{len(offenders)} 处数值缺少待样本验证标注", offenders,
        )
    return RuleHit("H8", "数值验证标注", True, "warn", "量化数值均带验证标注")   # 通过
