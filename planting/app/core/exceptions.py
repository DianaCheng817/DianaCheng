"""业务异常定义与全局异常处理器。

设计要点：HTTP 状态码恒为 200，成败由响应体里的 ok 字段表达，
这样调用方只需要判断一层语义，不必同时处理 HTTP 层和业务层错误。
"""

from __future__ import annotations   # 类型注解延迟求值

from fastapi import Request                       # 处理器需要读取请求方法与路径用于日志
from fastapi.responses import JSONResponse        # 直接返回 JSON，绕过默认异常响应格式

from app.core.config import config                # 读取 debug 开关，决定是否暴露异常细节
from app.core.logger import logger                # 统一日志出口
from app.core.response import fail                # 复用统一失败结构


class BizError(Exception):
    """可预期的业务异常，携带错误码，避免把内部细节暴露给调用方。"""

    def __init__(self, code: str, msg: str, data: object = None) -> None:
        super().__init__(msg)   # 让 Exception 自身也持有文案，便于堆栈阅读
        self.code = code        # 机器可读错误码
        self.msg = msg          # 人类可读说明
        self.data = data        # 可选上下文（如 Harness 报告）


class NotFoundError(BizError):
    """查询目标不存在（如 f99 这类越界证据编号、不存在的角色）。"""

    def __init__(self, msg: str, data: object = None) -> None:
        super().__init__("NOT_FOUND", msg, data)   # 固定错误码，调用方按码分支即可


class ValidationBizError(BizError):
    """入参校验失败（缺字段、类型不对、任务键不存在）。"""

    def __init__(self, msg: str, data: object = None) -> None:
        super().__init__("VALIDATION_ERROR", msg, data)   # 固定错误码


class HarnessBlockedError(BizError):
    """Harness 合规校验未通过，输出被阻断。"""

    def __init__(self, msg: str, data: object = None) -> None:
        super().__init__("HARNESS_BLOCKED", msg, data)   # 固定错误码，data 内带命中规则明细


async def biz_exception_handler(request: Request, exc: BizError) -> JSONResponse:
    """业务异常处理器。

    入参：request 当前请求；exc 业务异常实例。
    出参：统一结构的 JSONResponse，HTTP 状态码固定 200（由 ok 字段表达成败）。
    失败行为：自身不抛异常。
    """
    logger.warning("业务异常 %s %s -> %s", request.method, request.url.path, exc.code)   # 记录方法与路径，便于定位调用方
    return JSONResponse(status_code=200, content=fail(exc.code, exc.msg, exc.data))      # 把异常翻译成统一失败结构


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """未预期异常兜底处理器。

    入参：request 当前请求；exc 任意异常。
    出参：统一结构的 JSONResponse。
    失败行为：自身不抛异常；debug 模式下附加异常类型便于定位，生产模式只给通用提示。
    """
    logger.exception("未处理异常 %s %s", request.method, request.url.path)   # exception 会带上完整堆栈
    # 安全考量：未预期异常可能包含路径、SQL、内部变量，默认不返回给调用方
    detail = f"{type(exc).__name__}: {exc}" if config.app.debug else "服务内部错误，请查看服务端日志"
    return JSONResponse(                                       # 返回统一结构，保持契约一致
        status_code=200,                                        # 与业务异常一致，恒为 200
        content=fail("INTERNAL_ERROR", detail),                 # 错误码固定为 INTERNAL_ERROR
    )
