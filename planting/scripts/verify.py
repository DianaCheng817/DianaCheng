"""阶段验证脚本（可直接运行）。

覆盖四类检查：
    1. 配置加载
    2. 知识图谱载入、检索、证据合法性
    3. Harness 规则（正样本必过、负样本必拦）
    4. 六个关卡任务的生成与合规评分

用法：
    python scripts/verify.py
    python scripts/verify.py --online      # 额外验证 HTTP 接口（需先启动服务）

失败行为：任一断言不通过，进程以退出码 1 结束。
"""

from __future__ import annotations   # 类型注解延迟求值

import argparse                     # 解析 --online 开关
import sys                          # 修改导入路径、设置退出码
from pathlib import Path            # 计算项目根目录

# 允许脚本从项目根目录被调用时正确导入 app 包
ROOT = Path(__file__).resolve().parents[1]   # scripts/verify.py 的上两级即项目根
if str(ROOT) not in sys.path:                # 避免重复插入
    sys.path.insert(0, str(ROOT))            # 插到最前，保证优先导入本地包

from app.core.config import config                      # noqa: E402  配置单例
from app.harness.checker import run_checks            # noqa: E402  Harness 入口
from app.kg.graph import kg                            # noqa: E402  知识图谱单例
from app.llm.ollama_client import ollama               # noqa: E402  模型状态
from app.services.stage import stage_service           # noqa: E402  关卡生成服务


class Checker:
    """极简断言收集器，记录通过与失败项。"""

    def __init__(self) -> None:
        """初始化计数器。"""
        self.passed = 0                    # 通过项计数
        self.failed = 0                    # 失败项计数
        self.failures: list[str] = []      # 失败明细，便于最后统一打印

    def expect(self, condition: bool, title: str, detail: str = "") -> None:
        """记录一次断言。

        入参：condition 断言结果；title 用例名；detail 失败时的补充信息。
        出参：无。
        失败行为：不抛异常，失败项写入列表。
        """
        if condition:                      # 断言成立
            self.passed += 1               # 通过计数 +1
            print(f"  [PASS] {title}")    # 即时输出，便于观察进度
        else:                              # 断言失败
            self.failed += 1                                             # 失败计数 +1
            self.failures.append(f"{title} {detail}")                    # 记入明细
            print(f"  [FAIL] {title} {detail}")                        # 即时输出失败原因


def check_config(c: Checker) -> None:
    """验证配置加载。

    入参：c 断言收集器。
    出参：无。
    失败行为：不抛异常。
    """
    print("\n[1] 配置加载")                                                     # 分组标题
    c.expect(config.app.name == "planting-irrigation-agent", "服务名读取正确")    # 服务名与 yaml 一致
    c.expect(len(config.harness.allowed_roles) == 6, "六个合法角色已配置")         # 角色白名单完整性
    c.expect(config.knowledge_graph.evidence_max_index == 55, "证据编号上界为 55")  # H2 的上界来源


def check_kg(c: Checker) -> None:
    """验证知识图谱。

    入参：c 断言收集器。
    出参：无。
    失败行为：不抛异常，异常由断言记录。
    """
    print("\n[2] 知识图谱")   # 分组标题
    kg.load()                 # 确保图谱已加载（幂等）
    stats = kg.stats()        # 取规模统计
    c.expect(stats["byType"].get("fact") == 36, "事实节点数为 36", f"实际 {stats['byType'].get('fact')}")           # 36 条事实
    c.expect(stats["byType"].get("role") == 6, "角色节点数为 6", f"实际 {stats['byType'].get('role')}")             # 六个角色
    c.expect(stats["byType"].get("metric") == 6, "指标节点数为 6", f"实际 {stats['byType'].get('metric')}")         # 六个指标
    c.expect(stats["byType"].get("opportunity") == 4, "业务机会节点数为 4", f"实际 {stats['byType'].get('opportunity')}")   # 四个机会

    fact = kg.get_fact("f12")                       # 取一条已知事实
    c.expect("90 分钟" in fact["text"], "f12 含 90 分钟事实")   # 校验正文内容未被误改

    hits = kg.search("传感器")                                              # 关键词检索
    c.expect(len(hits) >= 2, "按关键词检索到传感器相关事实", f"实际 {len(hits)} 条")   # 至少两条

    roles = kg.list_roles()                                 # 角色列表
    c.expect(len(roles) == 6, "角色列表返回 6 条")           # 数量正确
    c.expect(any(r["name"] == "傅景" and "否决" in r["veto"] for r in roles), "傅景具备否决权")   # 否决权是否保留

    facts = kg.facts_by_role("林亦舟")                                          # 按角色取事实
    c.expect(len(facts) == 6, "林亦舟口述事实 6 条", f"实际 {len(facts)}")        # 与访谈记录一致

    evidence = kg.evidence_index()                                              # 证据索引
    c.expect(len(evidence) == 36, "证据索引 36 条", f"实际 {len(evidence)}")      # 索引完整


def check_harness(c: Checker) -> None:
    """验证 Harness 规则。

    入参：c 断言收集器。
    出参：无。
    失败行为：不抛异常。
    """
    print("\n[3] Harness 规则")   # 分组标题

    # 正样本：边界声明 + 合法编号 + 数值带标注
    good = (                                                                         # 精心构造的合规文本
        "首期只做观测解释与灌溉建议，不自动控制泵阀，系统只读（f05、f32）。"              # 满足 H5/H7
        "24 个地块每天共 60 次观测，人工汇总约 90 分钟（f12，待样本验证）。"                # 满足 H8
    )
    report = run_checks(good)                                        # 执行校验
    c.expect(report["passed"], "正样本通过校验", str(report["suggestions"]))   # 必须全部通过
    c.expect(report["score"] == 100, "正样本满分", f"实际 {report['score']}")   # 归一化后应为 100

    # 负样本 1：把自动控制泵阀当方案
    bad_auto = "方案是自动控制泵阀，实现自动灌溉。"   # 故意越界
    r1 = run_checks(bad_auto)                        # 执行校验
    c.expect(not r1["passed"], "拦截自动控制泵阀方案")   # 必须判不通过
    c.expect(r1["blocked"], "违规内容被阻断")            # 且必须阻断

    # 负样本 2：未访谈角色
    bad_role = "交付给农户和台账管理员确认。"   # 两个禁用角色
    r2 = run_checks(bad_role)                   # 执行校验
    c.expect(not r2["passed"], "拦截未访谈角色")   # 必须判不通过

    # 负样本 3：虚构编号
    bad_id = "证据编号 E01 与 R01 已确认。"   # 自造编号
    r3 = run_checks(bad_id)                  # 执行校验
    c.expect(not r3["passed"], "拦截虚构证据编号")   # 必须判不通过

    # 负样本 4：非法证据编号
    bad_f = "见 f99 记录。"                    # 越界编号
    r4 = run_checks(bad_f)                    # 执行校验
    c.expect(not r4["passed"], "拦截越界证据编号 f99")   # 必须判不通过

    # 负样本 5：自创数值
    bad_num = "每次误判占用 25-40 分钟。"        # 禁用语料里的区间
    r5 = run_checks(bad_num)                    # 执行校验
    c.expect(not r5["passed"], "拦截自创数值区间")   # 必须判不通过

    # 负样本 6：缺边界声明
    bad_boundary = "建议增加传感器数量。"        # 没有任何边界表述
    r6 = run_checks(bad_boundary)               # 执行校验
    c.expect(not r6["passed"], "拦截缺少边界声明的输出")   # 必须判不通过


def check_generation(c: Checker) -> None:
    """验证六个关卡任务的模板生成与合规评分。

    入参：c 断言收集器。
    出参：无。
    失败行为：不抛异常。
    """
    print("\n[4] 关卡生成（模板引擎）")   # 分组标题
    tasks = stage_service.list_tasks()                                        # 取任务清单
    c.expect(len(tasks) == 6, "任务总数为 6", f"实际 {len(tasks)}")             # 六关齐全

    for task in tasks:                                                        # 逐关验证
        result = stage_service.generate(task["key"], force_template=True)    # 强制模板，排除模型波动
        report = result["harness"]                                            # 取校验报告
        c.expect(report["passed"], f"{task['key']} 通过 Harness", str(report["suggestions"]))   # 必须通过
        c.expect(report["score"] == 100, f"{task['key']} 合规满分", f"实际 {report['score']}")    # 必须满分
        c.expect(len(result["content"]) > 800, f"{task['key']} 正文非空", f"长度 {len(result['content'])}")   # 防止空模板


def check_online(c: Checker) -> None:
    """验证 HTTP 接口（需服务已启动）。

    入参：c 断言收集器。
    出参：无。
    失败行为：连接失败时记录为失败项，不抛异常。
    """
    print("\n[5] HTTP 接口（在线模式）")   # 分组标题
    import requests   # 延迟导入，离线模式不需要该依赖

    base = f"http://{config.service.host}:{config.service.port}"   # 用配置拼地址，不硬编码
    try:
        resp = requests.get(f"{base}/health", timeout=10).json()                          # 探活
        c.expect(resp.get("ok") is True, "/health 返回 ok")                                # 统一结构
        c.expect("knowledgeGraph" in resp.get("data", {}), "/health 含知识图谱信息")         # 返回体含统计

        resp2 = requests.get(f"{base}/api/kg/search", params={"q": "交接"}, timeout=10).json()   # 检索接口
        c.expect(resp2.get("ok") is True, "/api/kg/search 返回 ok")                              # 统一结构
        c.expect(resp2["data"]["count"] >= 1, "检索到交接相关事实")                                # 有命中

        resp3 = requests.post(                                       # 生成接口
            f"{base}/api/generate",
            json={"task_key": "opportunity:1", "force_template": True},   # 强制模板，避免依赖模型
            timeout=30,
        ).json()
        c.expect(resp3.get("ok") is True, "/api/generate 返回 ok")                  # 统一结构
        c.expect(resp3["data"]["harness"]["score"] == 100, "/api/generate 合规满分")   # 返回内容合规

        resp4 = requests.post(                                       # 校验接口
            f"{base}/api/harness/check",
            json={"text": "自动控制泵阀"},                             # 故意违规的文本
            timeout=10,
        ).json()
        c.expect(resp4["data"]["passed"] is False, "接口拦截违规文本")   # 必须判不通过
    except requests.RequestException as exc:                          # 服务没起或网络不通
        c.expect(False, "HTTP 接口连通", f"请先启动服务：{exc}")        # 记为失败项，不中断脚本


def main() -> int:
    """执行全部检查。

    入参：命令行参数 --online。
    出参：退出码，0 全通过，1 存在失败项。
    失败行为：不抛异常。
    """
    parser = argparse.ArgumentParser(description="阶段验证")                # 参数解析器
    parser.add_argument("--online", action="store_true", help="额外验证 HTTP 接口")   # 默认离线
    args = parser.parse_args()                                            # 解析结果

    c = Checker()                                       # 断言收集器
    print("=" * 60)                                     # 分隔线
    print("种植灌溉与农事记录 · 调研智能体 验证")        # 标题
    print("=" * 60)                                     # 分隔线
    print(f"Ollama 状态：{ollama.describe()}")           # 打印模型可用性，便于解释降级原因

    check_config(c)      # 第 1 组
    check_kg(c)          # 第 2 组
    check_harness(c)     # 第 3 组
    check_generation(c)  # 第 4 组
    if args.online:      # 仅在 --online 时执行
        check_online(c)  # 第 5 组

    print("\n" + "=" * 60)                              # 汇总分隔线
    print(f"通过 {c.passed} 项 / 失败 {c.failed} 项")     # 总数
    if c.failures:                                     # 有失败项
        print("失败明细：")                             # 标题
        for item in c.failures:                        # 逐条打印
            print(f"  - {item}")                       # 明细
        return 1                                       # 退出码 1
    print("全部检查通过")                                # 全通过
    return 0                                           # 退出码 0


if __name__ == "__main__":     # 直接运行时才执行
    sys.exit(main())           # 用返回值作为退出码
