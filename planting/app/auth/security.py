"""鉴权基础能力：密码哈希与自签 JWT（HS256，仅用标准库，不引入额外依赖）。

说明：
    - 密码使用 PBKDF2-HMAC-SHA256 加盐哈希，数据库/台账中只存哈希，不存明文；
    - JWT 手写 HS256 签发与校验，载荷含用户名、角色与过期时间；
    - 签名密钥优先取配置/环境变量 JWT_SECRET，未配置时进程内生成临时密钥（重启后旧令牌失效，仅适合本地演示）。
"""

from __future__ import annotations   # 类型注解延迟求值

import base64                       # base64url 编解码
import hashlib                      # PBKDF2 密码哈希
import hmac                         # HMAC 签名与比对
import json                         # 载荷序列化
import os                           # 生成临时随机密钥
import time                         # 令牌过期时间戳
from typing import Any              # 载荷字典类型

from app.core.config import config   # 读取密钥与有效期配置
from app.core.exceptions import BizError   # 鉴权失败统一转业务异常

# PBKDF2 迭代次数，演示环境够用即可
_PBKDF2_ITERATIONS = 120_000
# 单条哈希的盐长度（字节）
_SALT_BYTES = 16


def _b64url_encode(data: bytes) -> str:
    """base64url 编码（去掉填充 =）。

    入参：原始字节。
    出参：URL 安全的字符串。
    """
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(text: str) -> bytes:
    """base64url 解码（补回填充 =）。

    入参：URL 安全字符串。
    出参：原始字节。
    """
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def hash_password(password: str) -> str:
    """生成密码哈希。

    入参：password 明文密码。
    出参：字符串 "salt_hex:hash_hex"，可直接存入台账。
    失败行为：空密码由上层入参校验拦截，这里不重复判断。
    """
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验明文密码与台账哈希是否一致。

    入参：password 明文；stored 台账中的 "salt:hash" 字符串。
    出参：布尔值，一致为 True。
    失败行为：台账格式损坏时返回 False，不抛异常。
    """
    try:
        salt_hex, hash_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
        return hmac.compare_digest(digest.hex(), hash_hex)   # 恒定时间比对，防时序攻击
    except (ValueError, AttributeError):
        return False


def _secret() -> bytes:
    """取签名密钥。

    入参：无。
    出参：密钥字节；配置为空时用进程内临时密钥兜底。
    """
    secret = config.auth.jwt_secret
    if secret:
        return secret.encode("utf-8")
    # 未配置 JWT_SECRET 时生成进程级临时密钥；多实例/重启场景必须通过环境变量配置固定密钥
    if not hasattr(_secret, "_fallback"):
        _secret._fallback = os.urandom(32)   # type: ignore[attr-defined]
    return _secret._fallback                 # type: ignore[attr-defined]


def issue_token(username: str, role: str) -> str:
    """签发登录令牌。

    入参：username 用户名；role 角色（admin/user）。
    出参：JWT 字符串（header.payload.signature）。
    失败行为：配置异常不吞，由全局处理器兜底。
    """
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": username,                       # 主体用户名
        "role": role,                          # 角色，供权限校验直接读取
        "iat": now,                            # 签发时间
        "exp": now + config.auth.token_expire_hours * 3600,   # 过期时间
    }
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    signature = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url_encode(signature)}"


def decode_token(token: str) -> dict[str, Any]:
    """校验并解析令牌。

    入参：token JWT 字符串。
    出参：载荷字典（sub/role/exp/iat）。
    失败行为：签名无效、格式错误或已过期抛 BizError("UNAUTHORIZED")。
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise BizError("UNAUTHORIZED", "令牌格式错误")
    header_b64, payload_b64, signature_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
    actual = _b64url_decode(signature_b64)
    if not hmac.compare_digest(expected, actual):
        raise BizError("UNAUTHORIZED", "令牌签名无效")
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise BizError("UNAUTHORIZED", "令牌载荷损坏") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise BizError("UNAUTHORIZED", "登录已过期，请重新登录")
    return payload
