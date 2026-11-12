"""HTTP 路由定义。

约定：
    1. 所有接口返回统一结构，成功用 ok()，业务异常由全局处理器转 fail()；
    2. 路径统一挂在 /api 下，/health 单独放在根路径便于探活；
    3. 写操作必须携带人工确认标记，不提供默认放行。
"""

from __future__ import annotations   # 类型注解延迟求值

from fastapi import APIRouter, Query   # 路由容器与查询参数校验
from pydantic import BaseModel, Field  # 请求体模型与字段说明

from app.core.config import config              # 健康检查要回显服务名与版本
from app.core.response import ok                # 成功响应统一构造
from app.harness.checker import run_checks      # 文本合规校验入口
from app.kg.graph import kg                     # 知识图谱单例
from app.llm.ollama_client import ollama        # 模型状态查询
from app.services.stage import stage_service    # 关卡生成服务

router = APIRouter()   # 路由容器，最终在 app/main.py 挂载


# ------------------------------------------------------------------
# 请求模型
# ------------------------------------------------------------------
class GenerateRequest(BaseModel):
    """关卡生成请求。"""

    task_key: str = Field(..., description="任务键，如 opportunity:1")                    # 必填，决定走哪套任务骨架
    extra_question: str = Field("", description="追加要求，可为空")                        # 可选，用户临时补充的写作要求
    force_template: bool = Field(False, description="是否强制走模板引擎（离线 / 对照测试用）")  # 跳过模型直接出模板


class NewFactRequest(BaseModel):
    """新增事实请求。"""

    evidence_id: str = Field(..., description="证据编号，形如 f59")                 # 必填，且不允许与已有编号重复
    role: str = Field(..., description="口述角色，必须是六个已访谈角色之一")         # 必填，服务端还会二次校验白名单
    category: str = Field(..., description="事实类型")                             # 必填，如现状/异常/边界
    text: str = Field(..., description="事实正文")                                 # 必填，事实内容
    confirmed: bool = Field(False, description="人工确认标记，必须显式为 true")     # 默认 false，必须显式确认才写入


class HarnessRequest(BaseModel):
    """校验请求。"""

    text: str = Field(..., description="待校验文本")   # 必填，单段文本即可校验


# ------------------------------------------------------------------
# 健康检查
# ------------------------------------------------------------------
@router.get("/health")
async def health() -> dict:
    """服务健康检查。

    入参：无。
    出参：统一结构，data 含服务名、版本、图谱规模与模型状态。
    失败行为：模型探测失败不影响本接口可用性。
    """
    return ok({                                  # 统一成功结构
        "service": config.app.name,              # 服务名，便于确认起的是哪个服务
        "version": config.app.version,           # 版本号
        "knowledgeGraph": kg.stats(),            # 图谱规模，空库能立刻看出来
        "llm": ollama.describe(),                # 模型接入状态，含在线与否
    })


# ------------------------------------------------------------------
# 知识库
# ------------------------------------------------------------------
@router.get("/api/kg/stats")
async def kg_stats() -> dict:
    """返回知识图谱规模统计。

    入参：无。
    出参：统一结构，data 为节点数、边数与按类型计数。
    失败行为：不抛异常。
    """
    return ok(kg.stats())   # 只读接口，直接回传统计


@router.get("/api/kg/roles")
async def kg_roles() -> dict:
    """列出六个访谈角色。

    入参：无。
    出参：统一结构，data 为角色列表。
    失败行为：不抛异常。
    """
    return ok(kg.list_roles())   # 按种子数据固定顺序返回，便于前端稳定展示


@router.get("/api/kg/roles/{name}/facts")
async def kg_role_facts(name: str) -> dict:
    """取某角色口述的全部事实。

    入参：name 角色姓名（路径参数）。
    出参：统一结构，data 为事实列表；角色不存在时 data 为空列表。
    失败行为：不抛异常。
    """
    return ok({"role": name, "facts": kg.facts_by_role(name)})   # 角色名回显，便于核对查的是谁


@router.get("/api/kg/facts/{evidence_id}")
async def kg_fact(evidence_id: str) -> dict:
    """按证据编号取单条事实。

    入参：evidence_id 形如 f12（路径参数）。
    出参：统一结构，data 为事实属性。
    失败行为：编号不存在时由 NotFoundError 转为 fail 响应。
    """
    return ok(kg.get_fact(evidence_id))   # 越界编号由图谱层抛 NotFoundError


@router.get("/api/kg/search")
async def kg_search(
    q: str = Query(..., description="检索关键词"),                            # 必填，空值会被校验拦住
    limit: int = Query(20, ge=1, le=100, description="返回条数上限"),          # 下限 1 上限 100，防止拉全库
) -> dict:
    """全文检索事实。

    入参：q 关键词；limit 上限。
    出参：统一结构，data 含命中条数与结果列表。
    失败行为：q 为空时抛 ValidationBizError，转为 fail 响应。
    """
    hits = kg.search(q, limit)                                              # 执行检索
    return ok({"keyword": q, "count": len(hits), "facts": hits})            # 带条数便于前端分页判断


@router.get("/api/kg/evidence")
async def kg_evidence() -> dict:
    """导出全部证据索引。

    入参：无。
    出参：统一结构，data 为 证据编号 -> 正文 的字典。
    失败行为：不抛异常。
    """
    evidence = kg.evidence_index()                                    # 取编号到正文的索引
    return ok({"count": len(evidence), "evidence": evidence})          # 条数与正文一起返回


@router.get("/api/kg/opportunities")
async def kg_opportunities() -> dict:
    """返回业务机会清单 O1–O4。

    入参：无。
    出参：统一结构，data 为机会节点列表。
    失败行为：不抛异常。
    """
    return ok(kg.list_by_type("opportunity"))   # 按类型筛选，避免把规则、指标混进来


@router.get("/api/kg/metrics")
async def kg_metrics() -> dict:
    """返回指标基线卡 I1–I6。

    入参：无。
    出参：统一结构，data 为指标节点列表。
    失败行为：不抛异常。
    """
    return ok(kg.list_by_type("metric"))   # 仅指标类型


@router.post("/api/kg/facts")
async def kg_add_fact(payload: NewFactRequest) -> dict:
    """人工确认后新增一条事实。

    入参：NewFactRequest，confirmed 必须为 true。
    出参：统一结构，data 为写入后的事实。
    失败行为：未确认、编号非法或重复、角色非法均转 fail 响应。
    """
    fact = kg.add_fact(                    # 调图谱层写入，所有校验都在那里再做一遍
        evidence_id=payload.evidence_id,   # 证据编号
        role=payload.role,                 # 口述人
        category=payload.category,         # 类型
        text=payload.text,                 # 正文
        confirmed=payload.confirmed,       # 人工确认标记，false 会被直接拒绝
    )
    return ok(fact)                        # 返回写入后的节点属性


# ------------------------------------------------------------------
# 关卡生成
# ------------------------------------------------------------------
@router.get("/api/tasks")
async def list_tasks() -> dict:
    """列出全部关卡任务。

    入参：无。
    出参：统一结构，data 为任务摘要列表。
    失败行为：不抛异常。
    """
    return ok(stage_service.list_tasks())   # 六个任务键与标题


@router.post("/api/generate")
async def generate(payload: GenerateRequest) -> dict:
    """生成指定关卡答卷。

    入参：GenerateRequest。
    出参：统一结构，data 含正文、来源与 Harness 报告。
    失败行为：任务不存在转 fail 响应；模型失败自动降级，不抛异常。
    """
    return ok(stage_service.generate(       # 生成逻辑全部在 service 层
        task_key=payload.task_key,          # 任务键
        extra_question=payload.extra_question,   # 追加要求
        force_template=payload.force_template,   # 是否跳过模型
    ))


# ------------------------------------------------------------------
# Harness
# ------------------------------------------------------------------
@router.post("/api/harness/check")
async def harness_check(payload: HarnessRequest) -> dict:
    """对给定文本执行 Harness 合规校验。

    入参：HarnessRequest。
    出参：统一结构，data 为校验报告。
    失败行为：不抛异常，校验不通过通过 passed=False 表达。
    """
    return ok(run_checks(payload.text))   # 直接返回完整报告，由 passed 字段表达结论
