"""鉴权 FastAPI 依赖：解析令牌、识别当前用户与角色。"""

from __future__ import annotations   # 类型注解延迟求值

from typing import Any             # 用户字典类型

from fastapi import Depends, Header   # 请求头读取与依赖注入

from app.auth.security import decode_token      # 令牌校验
from app.auth.store import GUEST, store         # 用户台账与访客角色常量
from app.core.exceptions import BizError        # 鉴权失败异常


def _parse_bearer(authorization: str | None) -> dict[str, Any] | None:
    """从 Authorization 头解析当前用户。

    入参：authorization 请求头原值（Bearer <token>）。
    出参：登录用户脱敏字典；未携带令牌返回 None；令牌无效抛 BizError。
    """
    if not authorization:
        return None
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise BizError("UNAUTHORIZED", "认证头格式应为 Bearer <token>")
    payload = decode_token(parts[1])
    user = store.get_user(payload.get("sub", ""))
    if not user:
        raise BizError("UNAUTHORIZED", "账号不存在或已被停用")
    return user


def get_optional_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """可选登录依赖：未登录返回访客身份，登录返回用户信息。

    供只读 Wiki 等访客可访问的接口使用。
    """
    user = _parse_bearer(authorization)
    return user if user else {"username": GUEST, "role": GUEST, "display_name": "访客"}


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """强制登录依赖：未登录或令牌无效抛 401 业务异常。"""
    user = _parse_bearer(authorization)
    if not user:
        raise BizError("UNAUTHORIZED", "请先登录")
    return user


def require_role(*roles: str):
    """角色校验依赖工厂。

    入参：roles 允许通过的角色列表（如 admin、user）。
    出参：FastAPI 依赖函数，校验当前用户角色在允许集合内。
    """

    def _checker(current: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if current["role"] not in roles:
            raise BizError("FORBIDDEN", f"当前角色 {current['role']} 无权访问该接口")
        return current

    return _checker
