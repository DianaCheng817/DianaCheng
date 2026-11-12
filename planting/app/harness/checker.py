"""Harness 校验编排与评分。

对外只暴露 run_checks(text) 与 assert_pass(text) 两个入口。
评分采用固定权重，便于回归测试比对。
"""

from __future__ import annotations   # 类型注解延迟求值

from typing import Any   # 标注报告字典的类型

from app.core.config import config                    # 读取 block_on_fail 开关
from app.core.exceptions import HarnessBlockedError   # 未通过时抛出的业务异常
from app.core.logger import get_logger                # 统一日志出口
from app.harness import rules                         # 八条规则的实现
from app.harness.rules import RuleHit                 # 规则结果类型，用于类型标注

logger = get_logger(__name__)   # 绑定本模块日志器

# 各规则权重。
# H1（响应结构）不参与文本评分，它校验的是接口返回体，由 check_envelope 单独判定；
# 文本类规则 H2–H8 合计 90 分，最终得分按 90 归一化为 100 分制，便于横向比较。
WEIGHTS: dict[str, int] = {   # 权重字典，键为规则编号
    "H2": 15,   # 证据编号
    "H3": 15,   # 角色错配
    "H4": 10,   # 虚构实体
    "H5": 15,   # 方案越界
    "H6": 5,    # 自创数值
    "H7": 20,   # 边界声明（最关键，权重最高）
    "H8": 10,   # 数值验证标注
}

# 文本类规则权重总和，用于归一化
TEXT_WEIGHT_TOTAL = sum(WEIGHTS.values())   # 当前为 90，改权重后自动跟随

# 每条规则不通过时的修复建议
FIX_HINTS: dict[str, str] = {
    "H1": "对外返回必须使用 app/core/response.py 的 ok() / fail() 构造",   # 结构类修复
    "H2": "只允许引用知识库中真实存在的 f00–f55，禁止自造编号",              # 编号类修复
    "H3": "只能用顾明岚、林亦舟、唐映秋、秦芮、傅景、叶书六个角色",           # 角色类修复
    "H4": "删除未经访谈确认的地块、作物与 E01/R01/R02 类编号，或改为待验证假设",  # 实体类修复
    "H5": "把「自动控制泵阀」改为边界声明，如「不自动控制泵阀，只做观测解释与灌溉建议」",  # 越界类修复
    "H6": "删除自造工时与频次区间，改为「待样本验证」后由现场抽样给出",        # 数值类修复
    "H7": "补齐边界声明：只读 / 不自动控制泵阀 / 观测解释与灌溉建议",         # 边界类修复
    "H8": "每个量化数值后补「待样本验证」或「待采集」",                       # 标注类修复
}


def _gather_hits(text: str, valid_ids: set[str]) -> list[RuleHit]:
    """执行全部规则并汇总结果。

    入参：
        text: 待校验正文。
        valid_ids: 知识库中真实存在的证据编号集合。
    出参：RuleHit 列表，顺序固定。
    失败行为：单条规则内部异常会向上抛出，属开发期错误，不静默吞掉。
    """
    return [                                    # 顺序与 H2–H8 一致，便于报告对读
        rules.check_evidence_ids(text, valid_ids),        # H2 证据编号
        rules.check_roles(text),                          # H3 角色错配
        rules.check_entities(text),                       # H4 虚构实体
        rules.check_boundary_violation(text),             # H5 方案越界
        rules.check_numbers(text),                        # H6 自创数值
        rules.check_boundary_declaration(text),           # H7 边界声明
        rules.check_verification_markers(text),           # H8 数值验证标注
    ]


def run_checks(text: str) -> dict[str, Any]:
    """对一段文本执行完整合规校验。

    入参：
        text: 待校验文本（通常是智能体生成的答卷正文）。
    出参：
        字典：
            passed     总体是否通过（所有 block 级规则均通过）
            score      0–100 的合规得分
            results    逐条规则结果
            suggestions 未通过项对应的修复建议
            blocked    是否应阻断输出
    失败行为：不抛异常；text 为空时按「未通过」处理。
    """
    from app.kg.graph import kg   # 延迟导入，避免模块循环依赖（graph 也会反向引用 checker）

    # 图谱为空时先加载：否则任何 fxx 都会被判定为非法编号，造成大面积误报
    if kg.graph.number_of_nodes() == 0:   # 0 节点说明还没初始化
        kg.load()                          # 触发读盘或种子重建

    valid_ids = set(kg.evidence_index().keys())   # 合法编号集合，来自图谱而不是硬编码
    hits = _gather_hits(text or "", valid_ids)     # 空文本也要走完流程，交由各规则判定

    passed_all = all(hit.passed for hit in hits if hit.severity == "block")   # 只看阻断级规则
    raw_score = sum(WEIGHTS.get(hit.rule_id, 0) for hit in hits if hit.passed)  # 累加通过项权重
    # 归一化为百分制：H2–H8 合计 90 分，换算后满分仍为 100
    score = round(raw_score / TEXT_WEIGHT_TOTAL * 100) if TEXT_WEIGHT_TOTAL else 0   # 防止除零

    suggestions = [   # 只给未通过项配修复建议，通过的项不需要噪声
        {"ruleId": hit.rule_id, "ruleName": hit.rule_name, "hint": FIX_HINTS.get(hit.rule_id, "")}
        for hit in hits
        if not hit.passed   # 过滤条件放在末尾，读起来更像自然语言
    ]

    blocked = bool(config.harness.block_on_fail and not passed_all)   # 配置开关 + 结果共同决定是否阻断

    report = {   # 对外报告，字段名保持稳定，前端与验证脚本都依赖它
        "passed": passed_all,      # 总体结论
        "score": score,            # 百分制得分
        "blocked": blocked,        # 是否应阻断
        "results": [               # 逐条明细
            {
                "ruleId": hit.rule_id,        # 规则编号
                "ruleName": hit.rule_name,    # 规则名称
                "passed": hit.passed,         # 是否通过
                "severity": hit.severity,     # 阻断级别
                "detail": hit.detail,         # 结论说明
                "hits": hit.hits,             # 命中内容
            }
            for hit in hits   # 按原顺序输出，不排序
        ],
        "suggestions": suggestions,   # 修复建议
    }

    if not passed_all:   # 只在失败时告警，避免日志噪声
        logger.warning("Harness 未通过，得分 %d，命中 %d 条规则", score, len(suggestions))
    return report   # 返回完整报告


def assert_pass(text: str) -> dict[str, Any]:
    """校验并在未通过时抛业务异常。

    入参：text 待校验文本。
    出参：校验报告（必然通过）。
    失败行为：未通过且配置开启 block_on_fail 时抛 HarnessBlockedError，附带完整报告。
    """
    report = run_checks(text)   # 先拿到完整报告，异常里也要带明细
    if report["blocked"]:       # 阻断条件成立
        raise HarnessBlockedError(                                   # 抛出可被统一处理器捕获的业务异常
            f"生成内容未通过 Harness 校验，得分 {report['score']}",   # 文案带上得分，便于定位
            report,                                                   # 附完整报告，前端可展示命中项
        )
    return report   # 通过则原样返回
