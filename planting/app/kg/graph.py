"""知识图谱（知识库）核心模块。

采用 networkx 有向图承载四类实体与三类关系，并以 JSON（node-link 格式）持久化，
避免 pickle 跨 Python 版本失效的问题。

节点命名约定：
    role:<姓名>     角色节点
    fact:<fxx>      访谈事实节点
    metric:<Ix>     指标基线节点
    opp:<Ox>        业务机会节点
    rule:<Rx>       硬边界规则节点
    decision:<Dx>   决策链节点
    gap:<Gx>        待补事项节点
    flow:<Sx>       主流程节点

边类型：
    口述（role -> fact）
    支撑（fact -> metric）
    依据（fact -> opp / rule / decision）
    归属（gap -> role）
"""

from __future__ import annotations   # 类型注解延迟求值

import json               # 用标准 JSON 持久化，替代 pickle
from pathlib import Path  # 跨平台处理持久化路径
from typing import Any    # 标注节点属性字典的类型

import networkx as nx   # 图结构与 node-link 序列化

from app.core.config import PROJECT_ROOT, config                       # 读取持久化路径配置
from app.core.exceptions import BizError, NotFoundError, ValidationBizError   # 三类业务异常
from app.core.logger import get_logger                                 # 统一日志出口
from app.kg import seed                                                # 种子数据（36 条访谈事实）

logger = get_logger(__name__)   # 绑定本模块日志器


class KnowledgeGraph:
    """知识库门面类，封装图构建、持久化、检索与校验。"""

    def __init__(self) -> None:
        """初始化空图对象，真正的数据加载由 load() 触发。"""
        self.graph: nx.DiGraph = nx.DiGraph()                  # 有向图，边方向代表「口述 / 支撑 / 依据」
        self.persist_path: Path = self._resolve_persist_path()   # 启动时就把路径定死，避免运行中变

    @staticmethod
    def _resolve_persist_path() -> Path:
        """把配置中的相对路径解析为绝对路径。

        入参：无。
        出参：绝对路径 Path 对象。
        失败行为：不抛异常，路径不存在时由 mkdir 创建。
        """
        raw = Path(config.knowledge_graph.persist_path)                    # 配置里可能是相对路径
        return raw if raw.is_absolute() else (PROJECT_ROOT / raw).resolve()   # 相对路径一律相对项目根

    # ---------------- 构建 ----------------
    def build_from_seed(self) -> None:
        """使用内置种子数据重建整张图。

        入参：无。
        出参：无（原地重建 self.graph）。
        失败行为：种子数据字段缺失会抛 KeyError，属于开发期错误，不吞掉。
        """
        g = nx.DiGraph()   # 先建新图，构建成功后再整体替换，避免中途失败留下半张图

        # 角色节点
        for role in seed.ROLES:                    # 六个已访谈角色
            g.add_node(                            # 节点 id 用「类型:业务主键」，便于拼装
                f"role:{role['name']}",            # 如 role:顾明岚
                node_type="role",                  # 节点类型，供统计与筛选
                name=role["name"],                 # 姓名
                post=role["post"],                 # 岗位
                focus=role["focus"],               # 关注点
                authority=role["authority"],       # 权限
                veto=role["veto"],                 # 否决权
            )

        # 事实节点
        for fact in seed.FACTS:                                  # 36 条 f00–f55
            g.add_node(                                          # 一条事实一个节点
                f"fact:{fact['evidence_id']}",                   # 如 fact:f12
                node_type="fact",                                # 节点类型
                evidence_id=fact["evidence_id"],                 # 证据编号
                role=fact["role"],                               # 口述人
                category=fact["category"],                       # 事实类型（现状/边界/异常…）
                text=fact["text"],                               # 事实正文
                status=fact["status"],                           # 核实状态
            )
            # 口述关系：角色 -> 事实
            g.add_edge(f"role:{fact['role']}", f"fact:{fact['evidence_id']}", relation="口述")   # 建立归属边

        # 指标节点与支撑关系
        for metric in seed.METRICS:                        # I1–I6 指标基线
            node_id = f"metric:{metric['metric_id']}"      # 如 metric:I1
            g.add_node(node_id, node_type="metric", **metric)   # 指标自带字段较多，整体展开
            for ref in metric["refs"]:                     # 该指标依据哪些事实
                if g.has_node(f"fact:{ref}"):              # 事实节点存在才连边，避免悬空边
                    g.add_edge(f"fact:{ref}", node_id, relation="支撑")   # 事实支撑指标

        # 业务机会节点与依据关系
        for opp in seed.OPPORTUNITIES:                       # O1–O4 业务机会
            node_id = f"opp:{opp['opportunity_id']}"         # 如 opp:O1
            g.add_node(node_id, node_type="opportunity", **opp)   # 写入机会属性
            for ref in opp["refs"]:                          # 机会依据的事实
                if g.has_node(f"fact:{ref}"):                # 防悬空
                    g.add_edge(f"fact:{ref}", node_id, relation="依据")   # 事实是机会的依据

        # 规则节点
        for rule in seed.RULES:                              # R1–R6 硬边界
            node_id = f"rule:{rule['rule_id']}"              # 如 rule:R1
            g.add_node(node_id, node_type="rule", **rule)    # 写入规则属性
            for ref in rule["refs"]:                         # 规则来源事实
                if g.has_node(f"fact:{ref}"):                # 防悬空
                    g.add_edge(f"fact:{ref}", node_id, relation="依据")   # 事实是规则的依据

        # 决策链节点
        for item in seed.DECISIONS:                                    # 五步决策链
            node_id = f"decision:D{item['order']}"                     # 按顺序编号 D1–D5
            g.add_node(node_id, node_type="decision", **item)          # 写入决策属性
            for ref in item["refs"]:                                   # 决策依据事实
                if g.has_node(f"fact:{ref}"):                          # 防悬空
                    g.add_edge(f"fact:{ref}", node_id, relation="依据")   # 事实是决策依据

        # 待补事项节点
        for gap in seed.GAPS:                                   # G1–G9 待补事项
            node_id = f"gap:{gap['gap_id']}"                    # 如 gap:G1
            g.add_node(node_id, node_type="gap", **gap)         # 待补项暂不连边，仅作清单

        # 主流程节点
        for step in seed.MAIN_FLOW:                             # S1–S6 现状主流程
            node_id = f"flow:{step['step']}"                    # 如 flow:S1
            g.add_node(node_id, node_type="flow", **step)       # 写入流程步骤

        self.graph = g   # 整体替换，保证要么全成要么不动
        logger.info(     # 打印规模，便于确认没有漏建
            "知识图谱构建完成：%d 节点 / %d 边",
            self.graph.number_of_nodes(),   # 节点数
            self.graph.number_of_edges(),   # 边数
        )

    # ---------------- 持久化 ----------------
    def save(self) -> None:
        """把当前图写入磁盘 JSON。

        入参：无。
        出参：无。
        失败行为：目录不可写抛 OSError；序列化失败抛 TypeError。
        """
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)      # 目录不存在则创建，已存在不报错
        data = nx.node_link_data(self.graph, edges="edges")              # 转成 node-link 结构，指定边字段名
        with open(self.persist_path, "w", encoding="utf-8") as fp:       # 覆盖写，固定 UTF-8
            json.dump(data, fp, ensure_ascii=False, indent=2)            # 保留中文，缩进便于人读
        logger.info("知识图谱已持久化：%s", self.persist_path)            # 记录落盘位置

    def load(self) -> None:
        """从磁盘加载图；文件缺失时按配置决定是否用种子重建。

        入参：无。
        出参：无。
        失败行为：文件损坏抛 BizError("KG_CORRUPT")，避免带病运行。
        """
        if not self.persist_path.exists():                       # 首次启动或文件被删
            if config.knowledge_graph.seed_on_startup:           # 配置允许则自动重建
                self.build_from_seed()                           # 用种子数据建图
                self.save()                                      # 立即落盘，下次启动直接读
            return                                               # 未允许重建时保持空图，由上层感知

        try:
            with open(self.persist_path, "r", encoding="utf-8") as fp:   # 读盘
                raw = json.load(fp)                                       # 解析 JSON
            self.graph = nx.node_link_graph(raw, edges="edges")           # 还原为有向图
            logger.info(                                                  # 打印规模，确认加载完整
                "知识图谱加载完成：%d 节点 / %d 边",
                self.graph.number_of_nodes(),   # 节点数
                self.graph.number_of_edges(),   # 边数
            )
        except (json.JSONDecodeError, KeyError, ValueError) as exc:   # 三类可预期的损坏情形
            raise BizError("KG_CORRUPT", f"知识图谱文件损坏，请删除后重启以重建：{exc}")   # 显式中断，避免空库跑业务

    def reset(self) -> None:
        """强制用种子数据重建并覆盖磁盘文件。

        入参：无。
        出参：无。
        失败行为：同 build_from_seed / save。
        """
        self.build_from_seed()   # 重建内存图
        self.save()              # 覆盖磁盘文件

    # ---------------- 查询 ----------------
    def stats(self) -> dict[str, Any]:
        """返回图谱规模统计。

        入参：无。
        出参：按节点类型计数的字典，以及总节点数、总边数。
        失败行为：不抛异常。
        """
        counter: dict[str, int] = {}                                  # 类型计数器
        for _, attr in self.graph.nodes(data=True):                   # 遍历全部节点
            node_type = attr.get("node_type", "unknown")              # 无类型标记的归为 unknown
            counter[node_type] = counter.get(node_type, 0) + 1        # 累加
        return {
            "nodes": self.graph.number_of_nodes(),   # 节点总数
            "edges": self.graph.number_of_edges(),   # 边总数
            "byType": counter,                       # 按类型分布
            "persistPath": str(self.persist_path),   # 便于确认连的是哪个文件
        }

    def get_fact(self, evidence_id: str) -> dict[str, Any]:
        """按证据编号取单条事实。

        入参：evidence_id 形如 "f12" 或 "fact:f12"。
        出参：事实属性字典（含 evidence_id、role、category、text、status）。
        失败行为：编号不存在抛 NotFoundError。
        """
        node_id = evidence_id if evidence_id.startswith("fact:") else f"fact:{evidence_id}"   # 兼容两种写法
        if not self.graph.has_node(node_id):   # 查不到就明确报错，不返回空对象
            raise NotFoundError(f"证据编号不存在：{evidence_id}")
        return self.graph.nodes[node_id]       # 返回节点属性视图

    def get_role(self, name: str) -> dict[str, Any]:
        """按姓名取角色节点。

        入参：name 角色姓名，如 "顾明岚"。
        出参：角色属性字典。
        失败行为：不存在抛 NotFoundError。
        """
        node_id = f"role:{name}"                   # 拼节点 id
        if not self.graph.has_node(node_id):       # 防止拼错名字后静默返回空
            raise NotFoundError(f"角色不存在：{name}")
        return self.graph.nodes[node_id]           # 返回角色属性

    def list_roles(self) -> list[dict[str, Any]]:
        """列出全部角色节点。

        入参：无。
        出参：角色属性字典列表，顺序按种子数据固定。
        失败行为：不抛异常。
        """
        result = []                          # 结果容器
        for role in seed.ROLES:              # 按种子数据顺序遍历，保证输出顺序稳定
            node = self.get_role(role["name"])   # 逐个取节点
            result.append(node)                  # 收集
        return result                            # 返回固定顺序列表

    def facts_by_role(self, name: str) -> list[dict[str, Any]]:
        """取某角色口述的全部事实。

        入参：name 角色姓名。
        出参：事实属性字典列表。
        失败行为：角色不存在时返回空列表（不抛异常，便于上层聚合）。
        """
        node_id = f"role:{name}"                    # 拼角色节点 id
        if not self.graph.has_node(node_id):        # 角色不存在时返回空，不打断聚合
            return []
        return [                                                          # 只取类型为 fact 的后继节点
            self.graph.nodes[nbr]
            for nbr in self.graph.successors(node_id)                     # 沿着「口述」边的方向
            if self.graph.nodes[nbr].get("node_type") == "fact"           # 过滤掉非事实节点
        ]

    def search(self, keyword: str, limit: int = 20) -> list[dict[str, Any]]:
        """全文关键词检索事实节点。

        入参：
            keyword: 检索词，支持中文子串匹配。
            limit: 返回条数上限。
        出参：命中事实列表，附 hit 字段表示命中字段名。
        失败行为：keyword 为空抛 ValidationBizError。
        """
        if not keyword or not keyword.strip():   # 空关键词会匹配所有节点，必须拦住
            raise ValidationBizError("检索关键词不能为空")

        key = keyword.strip()                     # 去掉首尾空白，避免「 交接 」查不到
        hits: list[dict[str, Any]] = []           # 命中集合
        for node_id, attr in self.graph.nodes(data=True):   # 遍历全部节点
            if attr.get("node_type") != "fact":             # 只检索事实节点
                continue                                    # 其他类型直接跳过
            # 同时匹配正文、角色名与编号，便于按人 / 按号检索
            if key in attr.get("text", "") or key in attr.get("role", "") or key in attr.get("evidence_id", ""):
                hits.append(attr)                           # 命中即收集
            if len(hits) >= limit:                          # 达到上限提前结束，避免全图扫描
                break
        if not hits:                                        # 无命中返回空列表
            return []
        return hits                                         # 返回命中事实

    def related(self, node_id: str) -> list[dict[str, Any]]:
        """取某节点的直接关联节点（出边与入边各一遍）。

        入参：node_id 完整节点 id，如 "opp:O1"。
        出参：关联节点列表，含 id、node_type、relation、方向。
        失败行为：节点不存在抛 NotFoundError。
        """
        if not self.graph.has_node(node_id):   # 先确认节点存在
            raise NotFoundError(f"节点不存在：{node_id}")

        result: list[dict[str, Any]] = []                        # 结果容器
        for target in self.graph.successors(node_id):            # 出边方向：本节点 -> 后继
            result.append({                                      # 逐条记录关系
                "id": target,                                    # 对端节点 id
                "node_type": self.graph.nodes[target].get("node_type"),   # 对端类型
                "relation": self.graph.edges[node_id, target].get("relation"),   # 关系名
                "direction": "out",                              # 指出是出边
            })
        for source in self.graph.predecessors(node_id):          # 入边方向：前驱 -> 本节点
            result.append({                                      # 逐条记录关系
                "id": source,                                    # 对端节点 id
                "node_type": self.graph.nodes[source].get("node_type"),   # 对端类型
                "relation": self.graph.edges[source, node_id].get("relation"),   # 关系名
                "direction": "in",                               # 指出是入边
            })
        return result                                            # 出边在前、入边在后

    def list_by_type(self, node_type: str) -> list[dict[str, Any]]:
        """按节点类型批量取节点。

        入参：node_type 取 role / fact / metric / opportunity / rule / decision / gap / flow。
        出参：属性字典列表。
        失败行为：类型不存在时返回空列表。
        """
        return [
            {"id": node_id, **attr}                     # 把 id 一并带出，便于前端跳转
            for node_id, attr in self.graph.nodes(data=True)
            if attr.get("node_type") == node_type       # 只保留目标类型
        ]

    def evidence_index(self) -> dict[str, str]:
        """返回 证据编号 -> 事实正文 的索引，供提示词拼接使用。

        入参：无。
        出参：字典，键为 f00–f55，值为事实正文。
        失败行为：不抛异常。
        """
        return {
            attr["evidence_id"]: attr["text"]                        # 编号做键，正文做值
            for _, attr in self.graph.nodes(data=True)
            if attr.get("node_type") == "fact"                       # 只取事实节点
        }

    # ---------------- 写入（需人工确认） ----------------
    def add_fact(self, evidence_id: str, role: str, category: str, text: str, confirmed: bool) -> dict[str, Any]:
        """新增一条事实，必须由人工确认。

        入参：
            evidence_id: 新证据编号，格式 f + 两位数字，且不得重复。
            role: 口述角色，必须在六个合法角色内。
            category: 事实类型。
            text: 事实正文。
            confirmed: 人工确认标记，False 时直接拒绝写入。
        出参：写入后的事实属性。
        失败行为：未确认 / 编号非法 / 角色非法 / 编号重复均抛 ValidationBizError。
        """
        # 这是本服务唯一的写入口，必须强制人工确认：
        # 训练场景下大模型极易编造证据，未经确认的事实入库会污染后续所有检索结果，
        # 因此这里把 confirmed 作为硬闸门，且不允许通过接口默认值绕过。
        if not confirmed:   # 未携带人工确认标记
            raise ValidationBizError("新增事实必须携带 confirmed=true 的人工确认标记")

        if not (evidence_id.startswith("f") and evidence_id[1:].isdigit()):   # 校验编号格式
            raise ValidationBizError("证据编号必须形如 f59（f + 数字）")

        if role not in config.harness.allowed_roles:   # 角色白名单校验，防止编造口述人
            raise ValidationBizError(f"角色必须属于六个已访谈角色：{config.harness.allowed_roles}")

        node_id = f"fact:{evidence_id}"                       # 拼节点 id
        if self.graph.has_node(node_id):                      # 已存在则拒绝，禁止覆盖已有证据
            raise ValidationBizError(f"证据编号已存在，禁止覆盖：{evidence_id}")

        self.graph.add_node(                                  # 写入新事实节点
            node_id,
            node_type="fact",            # 类型固定
            evidence_id=evidence_id,     # 编号
            role=role,                   # 口述人
            category=category,           # 分类
            text=text,                   # 正文
            status="confirmed_fact",     # 标记为已人工确认，与种子数据区分
        )
        self.graph.add_edge(f"role:{role}", node_id, relation="口述")   # 补上归属边
        self.save()                                                     # 立即落盘，防止重启丢失
        logger.info("人工确认新增事实 %s，口述人 %s", evidence_id, role)   # 留痕，便于审计
        return self.graph.nodes[node_id]                                 # 返回写入后的属性


# 进程内单例，供路由与业务层共用
kg = KnowledgeGraph()   # 全局唯一实例，避免多处各建一张图
