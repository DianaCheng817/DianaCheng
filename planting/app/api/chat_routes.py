"""问答与 RAG 检索路由。

权限矩阵：
    GET  /api/rag/search  公开：召回证据块预览（访客可浏览）
    POST /api/chat        登录用户（admin/user）：发起 RAG 问答
"""

from __future__ import annotations   # 类型注解延迟求值

from fastapi import APIRouter, Depends, Query   # 路由、依赖、查询参数
from pydantic import BaseModel, Field           # 请求体模型

from app.auth.deps import require_role          # 角色校验依赖
from app.auth.store import ADMIN, USER          # 角色常量
from app.core.response import ok                # 统一成功结构
from app.rag.retriever import retriever         # 检索器单例
from app.services.chat import chat_service      # 问答服务单例

router = APIRouter(prefix="/api", tags=["问答与检索"])   # 统一 /api 前缀


class ChatRequest(BaseModel):
    """问答请求体。"""

    question: str = Field(..., description="用户问题")
    force_template: bool = Field(False, description="强制走证据模板（离线/对照测试用）")


@router.get("/rag/search")
async def rag_search(
    q: str = Query(..., description="检索关键词"),
    limit: int = Query(5, ge=1, le=20, description="返回条数上限"),
) -> dict:
    """召回与关键词相关的证据块（公开预览）。

    入参：q 关键词；limit 条数上限。
    出参：统一结构，data 含命中条数与证据块列表。
    """
    hits = retriever.retrieve(q, top_k=limit)
    return ok({"keyword": q, "count": len(hits), "chunks": hits})


@router.post("/chat")
async def chat(payload: ChatRequest, current: dict = Depends(require_role(ADMIN, USER))) -> dict:
    """发起 RAG 问答。

    入参：ChatRequest；current 登录用户（依赖注入）。
    出参：统一结构，data 含回答、来源证据、模型通道与 Harness 报告。
    失败行为：问题为空由服务层转 fail；模型失败自动降级模板。
    """
    result = chat_service.answer(payload.question, force_template=payload.force_template)
    result["operator"] = current["username"]   # 记录提问人，便于审计追溯
    return ok(result)
