"""鉴权与用户管理路由。

权限矩阵：
    POST /api/auth/register   访客自助注册为普通用户（受 allow_register 开关控制）
    POST /api/auth/login      任意已注册账号登录，返回令牌
    GET  /api/auth/me         当前登录用户信息
    GET  /api/admin/users     仅管理员：用户清单
    POST /api/admin/users/role 仅管理员：调整角色
    GET  /api/admin/audit     仅管理员：审计日志
"""

from __future__ import annotations   # 类型注解延迟求值

from fastapi import APIRouter, Depends   # 路由容器与依赖注入
from pydantic import BaseModel, Field    # 请求体模型

from app.auth.deps import get_current_user, require_role   # 鉴权依赖
from app.auth.security import issue_token                  # 令牌签发
from app.auth.store import ADMIN, USER, store              # 台账与角色常量
from app.core.config import config                         # 注册开关配置
from app.core.exceptions import BizError   # 业务异常
from app.core.response import ok                           # 统一成功结构

router = APIRouter(prefix="/api", tags=["鉴权与管理"])   # 统一 /api 前缀，auth 与 admin 分组挂在其下


class RegisterRequest(BaseModel):
    """注册请求体。"""

    username: str = Field(..., description="用户名，字母开头，3–20 位")
    password: str = Field(..., min_length=6, description="密码，至少 6 位")
    display_name: str = Field("", description="显示名，可选")


class LoginRequest(BaseModel):
    """登录请求体。"""

    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class RoleRequest(BaseModel):
    """角色调整请求体（管理员）。"""

    role: str = Field(..., description="目标角色：admin / user")


@router.post("/auth/register")
async def register(payload: RegisterRequest) -> dict:
    """注册普通用户。

    入参：RegisterRequest。
    出参：统一结构，data 为脱敏用户信息。
    失败行为：关闭自助注册、用户名非法或重复转 fail 响应。
    """
    if not config.auth.allow_register:
        raise BizError("FORBIDDEN", "当前未开放自助注册，请联系管理员开通")
    user = store.create_user(
        username=payload.username,
        password=payload.password,
        role=USER,
        display_name=payload.display_name,
    )
    return ok(user)


@router.post("/auth/login")
async def login(payload: LoginRequest) -> dict:
    """账号密码登录。

    入参：LoginRequest。
    出参：统一结构，data 含令牌与脱敏用户信息。
    失败行为：账号或密码错误抛 BizError("UNAUTHORIZED")。
    """
    user = store.authenticate(payload.username, payload.password)
    if not user:
        raise BizError("UNAUTHORIZED", "用户名或密码错误")
    token = issue_token(user["username"], user["role"])
    store.audit(user["username"], "login", "登录成功")
    return ok({"token": token, "user": user})


@router.get("/auth/me")
async def me(current: dict = Depends(get_current_user)) -> dict:
    """返回当前登录用户信息。

    入参：依赖注入的当前用户。
    出参：统一结构，data 为脱敏用户信息。
    """
    return ok(current)


@router.get("/admin/users")
async def list_users(_: dict = Depends(require_role(ADMIN))) -> dict:
    """用户清单（仅管理员）。"""
    return ok({"users": store.list_users()})


@router.post("/admin/users/{username}/role")
async def change_role_by_name(username: str, payload: RoleRequest, operator: dict = Depends(require_role(ADMIN))) -> dict:
    """调整指定用户角色（仅管理员）。

    入参：username 目标用户；payload.role 新角色；operator 操作管理员。
    出参：更新后的脱敏用户。
    失败行为：用户不存在或角色非法转 fail 响应。
    """
    if username == operator["username"]:
        raise ValidationBizError("不允许调整自己的角色")
    user = store.set_role(username, payload.role)
    store.audit(operator["username"], "set_role", f"将 {username} 调整为 {payload.role}")
    return ok(user)


@router.get("/admin/audit")
async def list_audit(_: dict = Depends(require_role(ADMIN))) -> dict:
    """审计日志（仅管理员）。"""
    return ok({"records": store.list_audit()})
