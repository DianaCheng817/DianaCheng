"""FastAPI 应用入口。

启动顺序：
    1. 加载 config.yaml（import 时已完成）；
    2. 加载 / 构建知识图谱；
    3. 注册路由与异常处理器。
"""

from __future__ import annotations   # 类型注解延迟求值

from contextlib import asynccontextmanager   # 把生成器包装成异步上下文管理器（lifespan 用）
from collections.abc import AsyncIterator    # 标注 lifespan 的产出类型
from pathlib import Path                     # 静态页面目录定位

from fastapi import FastAPI                  # Web 框架本体
from fastapi.responses import FileResponse   # 根路径返回前端单页
from fastapi.staticfiles import StaticFiles  # 静态资源挂载

from app.api.auth_routes import router as auth_router                 # 鉴权与用户管理路由
from app.api.chat_routes import router as chat_router                 # 问答与检索路由
from app.api.routes import router                                     # 全部业务路由
from app.auth.store import store                                      # 用户台账单例
from app.core.config import PROJECT_ROOT, config                      # 全局配置单例
from app.core.exceptions import BizError, biz_exception_handler, global_exception_handler  # 统一异常出口
from app.core.logger import get_logger                                # 统一日志入口
from app.kg.graph import kg                                           # 知识图谱单例
from app.rag.retriever import retriever                               # RAG 检索器单例

logger = get_logger(__name__)   # 绑定本模块日志器，输出带模块名前缀


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期钩子。

    入参：app 当前 FastAPI 实例。
    出参：异步上下文管理器。
    失败行为：图谱/台账加载失败时抛出，服务不启动（避免带空知识库运行）。
    """
    logger.info("启动 %s v%s", config.app.name, config.app.version)   # 记录启动信息，便于排查
    kg.load()                                                        # 加载图谱：文件存在则读盘，缺失则用种子数据重建
    logger.info("知识图谱就绪：%d 节点", kg.graph.number_of_nodes())    # 打印节点数，确认没有空库
    retriever.build()                                                # 构建 RAG 检索索引（事实块 + 文档块）
    store.init_admin()                                               # 首次启动初始化管理员账号
    yield                                                            # 交还控制权，服务在此期间对外提供接口
    logger.info("服务停止")                                           # 关闭阶段记录，便于确认进程已退出


app = FastAPI(                                        # 创建应用实例
    title="种植灌溉与农事记录 · 调研智能体",            # 文档标题（/docs 页面可见）
    description="基于访谈证据知识图谱 + RAG 检索 + 多通道 LLM + Harness 合规校验的 FDE 调研助手",  # 接口说明
    version=config.app.version,                       # 版本号与配置保持一致
    lifespan=lifespan,                                # 挂载生命周期钩子，确保图谱先就绪
)

# 异常处理器：业务异常走显式错误码，其他走兜底
app.add_exception_handler(BizError, biz_exception_handler)      # 可预期的业务错误，返回 ok=false
app.add_exception_handler(Exception, global_exception_handler)  # 未预期异常，也要保持统一返回结构

# 路由注册
app.include_router(router)            # 知识图谱 / 关卡生成 / Harness 业务路由
app.include_router(auth_router)       # 注册、登录、用户管理、审计
app.include_router(chat_router)       # RAG 检索与问答

# 前端静态页面：static 目录挂载到 /static，根路径返回单页
_STATIC_DIR = PROJECT_ROOT / "app" / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """返回前端单页入口。"""
    return FileResponse(_STATIC_DIR / "index.html")
