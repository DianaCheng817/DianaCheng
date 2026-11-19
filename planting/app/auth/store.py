"""用户台账与审计记录（JSON 文件持久化，MVP 不引入数据库）。

角色约定：
    admin  管理员（SaaS 视角）：用户管理、规则与图谱维护、查看审计日志
    user   注册用户：浏览 Wiki、发起问答与生成任务
    guest  访客：不入库，仅可浏览公开 Wiki 内容

安全约束：
    台账只存 PBKDF2 哈希，不存明文密码；用户对外返回时剔除 password_hash 字段。
"""

from __future__ import annotations   # 类型注解延迟求值

import json                         # 台账与审计记录序列化
import re                           # 用户名合法性校验
import time                         # 时间戳
from pathlib import Path            # 路径解析
from typing import Any              # 字典类型标注

from app.core.config import PROJECT_ROOT, config   # 读取台账路径配置
from app.core.exceptions import BizError, ValidationBizError   # 业务异常
from app.core.logger import get_logger             # 统一日志出口
from app.auth.security import hash_password, verify_password   # 密码哈希与校验

logger = get_logger(__name__)   # 绑定本模块日志器

ADMIN = "admin"     # 管理员角色常量
USER = "user"       # 注册用户角色常量
GUEST = "guest"     # 访客角色常量（不入库）
VALID_ROLES = {ADMIN, USER}

# 用户名：字母开头，允许字母数字下划线，3–20 位
_USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,19}$")


class UserStore:
    """用户台账门面：加载、校验、写入与审计留痕。"""

    def __init__(self) -> None:
        """初始化空台账，持久化路径在构造时解析固定。"""
        self._users: list[dict[str, Any]] = []
        self._path = self._resolve_path(config.auth.users_path)
        self._audit_path = self._path.parent / "audit.json"

    @staticmethod
    def _resolve_path(raw: str) -> Path:
        """把配置中的相对路径解析为项目根下的绝对路径。"""
        path = Path(raw)
        return path if path.is_absolute() else (PROJECT_ROOT / path).resolve()

    # ---------------- 持久化 ----------------
    def _load(self) -> None:
        """从磁盘读取台账；文件缺失时保持空列表。

        失败行为：文件损坏抛 BizError("STORE_CORRUPT")，避免带病运行。
        """
        if not self._path.exists():
            self._users = []
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._users = data.get("users", [])
        except (json.JSONDecodeError, OSError) as exc:
            raise BizError("STORE_CORRUPT", f"用户台账损坏：{exc}") from exc

    def _save(self) -> None:
        """把台账写回磁盘，目录不存在则创建。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"users": self._users}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def init_admin(self) -> None:
        """首次启动初始化管理员账号。

        入参：无。
        出参：无；台账中已存在 admin 时直接返回。
        失败行为：配置未给账号密码时使用演示默认值并告警，提示上线前修改。
        """
        self._load()
        if any(u["role"] == ADMIN for u in self._users):
            return
        username = config.auth.admin_username or "admin"
        password = config.auth.admin_password or "admin123"
        if not config.auth.admin_password:
            logger.warning("未配置 ADMIN_PASSWORD，使用演示默认管理员密码，上线前必须修改")
        self._users.append({
            "username": username,
            "password_hash": hash_password(password),
            "role": ADMIN,
            "display_name": "管理员",
            "created_at": int(time.time()),
        })
        self._save()
        logger.info("初始化管理员账号：%s", username)

    # ---------------- 查询 ----------------
    def _find(self, username: str) -> dict[str, Any] | None:
        """按用户名查找台账记录。"""
        for user in self._users:
            if user["username"] == username:
                return user
        return None

    def authenticate(self, username: str, password: str) -> dict[str, Any] | None:
        """校验账号密码。

        入参：username 用户名；password 明文密码。
        出参：校验通过返回脱敏用户字典，失败返回 None。
        """
        record = self._find(username)
        if not record or not verify_password(password, record["password_hash"]):
            return None
        return self._public(record)

    def get_user(self, username: str) -> dict[str, Any] | None:
        """按用户名取脱敏用户信息。"""
        record = self._find(username)
        return self._public(record) if record else None

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        """剔除密码哈希，只保留对外可返回的字段。"""
        return {
            "username": record["username"],
            "role": record["role"],
            "display_name": record.get("display_name", record["username"]),
            "created_at": record.get("created_at", 0),
        }

    def list_users(self) -> list[dict[str, Any]]:
        """列出全部脱敏用户（管理员接口用）。"""
        return [self._public(u) for u in self._users]

    # ---------------- 写入 ----------------
    def create_user(self, username: str, password: str, role: str, display_name: str = "") -> dict[str, Any]:
        """注册新用户。

        入参：username 用户名；password 明文；role 角色；display_name 显示名。
        出参：新建的脱敏用户字典。
        失败行为：用户名非法、已存在、角色非法或密码过短抛 ValidationBizError。
        """
        if not _USERNAME_PATTERN.match(username):
            raise ValidationBizError("用户名需以字母开头，含字母/数字/下划线，3–20 位")
        if len(password) < 6:
            raise ValidationBizError("密码长度至少 6 位")
        if role not in VALID_ROLES:
            raise ValidationBizError(f"角色必须是 {sorted(VALID_ROLES)}")
        if self._find(username):
            raise ValidationBizError("用户名已存在")
        record = {
            "username": username,
            "password_hash": hash_password(password),
            "role": role,
            "display_name": display_name or username,
            "created_at": int(time.time()),
        }
        self._users.append(record)
        self._save()
        self.audit(username, "register", f"注册为 {role}")
        return self._public(record)

    def set_role(self, username: str, role: str) -> dict[str, Any]:
        """调整用户角色（管理员操作）。

        入参：username 目标用户；role 新角色。
        出参：更新后的脱敏用户。
        失败行为：用户不存在或角色非法抛业务异常。
        """
        if role not in VALID_ROLES:
            raise ValidationBizError(f"角色必须是 {sorted(VALID_ROLES)}")
        record = self._find(username)
        if not record:
            raise BizError("NOT_FOUND", f"用户不存在：{username}")
        record["role"] = role
        self._save()
        return self._public(record)

    # ---------------- 审计 ----------------
    def audit(self, username: str, action: str, detail: str = "") -> None:
        """追加一条审计记录。

        入参：username 操作人；action 动作标识；detail 补充说明。
        出参：无；审计文件写入失败只记日志，不阻断主流程。
        """
        entry = {
            "time": int(time.time()),
            "username": username,
            "action": action,
            "detail": detail,
        }
        try:
            self._audit_path.parent.mkdir(parents=True, exist_ok=True)
            history: list[dict[str, Any]] = []
            if self._audit_path.exists():
                history = json.loads(self._audit_path.read_text(encoding="utf-8"))
            history.append(entry)
            self._audit_path.write_text(
                json.dumps(history[-500:], ensure_ascii=False, indent=2),   # 仅保留最近 500 条
                encoding="utf-8",
            )
        except OSError as exc:
            logger.warning("审计记录写入失败：%s", exc)

    def list_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        """读取最近审计记录（管理员接口用）。"""
        if not self._audit_path.exists():
            return []
        try:
            history = json.loads(self._audit_path.read_text(encoding="utf-8"))
            return history[-limit:][::-1]
        except (json.JSONDecodeError, OSError):
            return []


# 进程内单例
store = UserStore()
