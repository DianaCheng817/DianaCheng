"""统一响应结构模块。

所有对外接口必须返回 {"ok", "data", "error"} 三字段结构，不允许例外。
"""

from __future__ import annotations   # 类型注解延迟求值

from typing import Any, Generic, TypeVar   # Generic/TypeVar 用于给响应模型加泛型标注

from pydantic import BaseModel   # 用 pydantic 做字段校验与文档生成

T = TypeVar("T")   # 泛型占位符，代表任意业务载荷类型


class ErrorBody(BaseModel):
    """错误体：code 为机器可读错误码，msg 为人类可读说明。"""

    code: str = ""   # 错误码，约定大写下划线风格，如 KG_NOT_FOUND
    msg: str = ""    # 错误说明，直接展示给调用方


class ApiResponse(BaseModel):
    """对外统一响应模型（仅用于 OpenAPI 文档展示，实际返回字典）。"""

    ok: bool          # 业务是否成功，成败只看这个字段，不看 HTTP 状态码
    data: Any = None  # 成功时的业务载荷；失败时可放校验报告等上下文
    error: ErrorBody  # 失败时的错误信息，成功时为空值对象


def ok(data: Any = None) -> dict:
    """构造成功响应。

    入参：
        data: 任意可 JSON 序列化的业务载荷。
    出参：
        统一字典结构，ok=True，error 为空值对象。
    失败行为：
        不抛异常；data 若不可序列化，由 FastAPI 序列化层报错。
    """
    return {"ok": True, "data": data, "error": {"code": "", "msg": ""}}   # 三字段恒定存在，调用方无需判空


def fail(code: str, msg: str, data: Any = None) -> dict:
    """构造失败响应。

    入参：
        code: 机器可读错误码，约定为大写下划线风格，如 "KG_NOT_FOUND"。
        msg: 面向用户的错误说明。
        data: 可选的失败上下文（如校验报告）。
    出参：
        统一字典结构，ok=False。
    失败行为：
        不抛异常。
    """
    return {"ok": False, "data": data, "error": {"code": code, "msg": msg}}   # 失败也保持同一结构，避免调用方分支处理
