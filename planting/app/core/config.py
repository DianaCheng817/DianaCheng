"""全局配置加载模块。

职责：从项目根目录的 config.yaml 读取所有可调参数，并提供进程内单例。
设计约束：密钥、模型地址、文件路径一律不进代码，只进 yaml 或环境变量。
"""

from __future__ import annotations   # 类型注解延迟求值，避免循环导入

import os                               # 读取环境变量，用于覆盖 yaml 中的敏感配置
from pathlib import Path   # 用面向对象方式处理跨平台路径
from typing import Any     # 标注 yaml 解析后的原始字典类型

import yaml                        # 读取 yaml 配置，不引入额外中间件
from pydantic import BaseModel, Field   # 定义配置模型并做类型校验


class AppMeta(BaseModel):
    """应用元信息。"""

    name: str = "planting-irrigation-agent"   # 服务名，用于日志前缀
    version: str = "1.0.0"                    # 版本号
    debug: bool = False                       # 是否输出调试级日志


class ServiceConfig(BaseModel):
    """HTTP 服务配置。"""

    host: str = "127.0.0.1"   # 监听地址，默认只绑本机
    port: int = 8000          # 监听端口
    reload: bool = False      # 是否热重载（仅调试用）


class OllamaConfig(BaseModel):
    """本地大模型（Ollama）接入配置。"""

    enabled: bool = True                             # 是否启用本地模型；关闭后直接走模板引擎
    base_url: str = "http://127.0.0.1:11434"         # Ollama 服务地址（可改 yaml，不写死在代码里）
    model_name: str = "qwen3:0.6b"                   # 模型名，必须与 ollama list 完全一致
    timeout: int = 120                               # 单次请求超时秒数
    temperature: float = 0.2                         # 采样温度，越低越贴事实
    num_predict: int = 2048                          # 最大生成 token
    fallback_to_template: bool = True                # 模型不可用时是否降级为模板引擎


class KnowledgeGraphConfig(BaseModel):
    """知识图谱配置。"""

    persist_path: str = "./kg_store/irrigation_kg.json"   # 持久化路径（相对项目根）
    seed_on_startup: bool = True                          # 文件缺失时是否用种子数据初始化
    evidence_total: int = 36                              # 合法证据条目总数
    evidence_max_index: int = 55                          # 证据编号索引上界，超出即判非法


class HarnessConfig(BaseModel):
    """Harness 合规校验配置，全部为可调词表。"""

    forbidden_keywords: list[str] = Field(default_factory=list)          # 禁止的方案型表述（如自动开阀）
    banned_roles: list[str] = Field(default_factory=list)                # 访谈中不存在的角色
    banned_entities: list[str] = Field(default_factory=list)             # 未经确认的实体编号
    banned_numbers: list[str] = Field(default_factory=list)              # 自创数值区间
    required_boundary_markers: list[str] = Field(default_factory=list)   # 必须出现的边界声明
    verification_markers: list[str] = Field(default_factory=list)        # 数值必须带的验证标注
    allowed_roles: list[str] = Field(default_factory=list)               # 六个合法角色
    block_on_fail: bool = True                                           # 未通过时是否阻断输出


class DocsConfig(BaseModel):
    """文档产出路径配置，保证代码与文档同源。"""

    tech_solution_md: str = "./docs/06-技术方案.md"       # 技术方案 Markdown 路径
    tech_solution_docx: str = "./docs/06-技术方案.docx"   # 技术方案 Word 路径
    prompt_md: str = "./docs/07-智能体提示词.md"          # 提示词文档路径


class AuthConfig(BaseModel):
    """鉴权与分层权限配置。"""

    jwt_secret: str = ""                    # 令牌签名密钥，空值时回落到环境变量 JWT_SECRET
    token_expire_hours: int = 12            # 登录令牌有效期（小时）
    admin_username: str = ""                # 初始管理员账号，空值读环境变量 ADMIN_USERNAME
    admin_password: str = ""                # 初始管理员密码，空值读环境变量 ADMIN_PASSWORD
    allow_register: bool = True             # 是否开放自助注册为普通用户
    users_path: str = "./data/users.json"   # 用户台账持久化路径


class RemoteLlmConfig(BaseModel):
    """兼容 OpenAI 协议的远程模型配置（云端部署通道）。"""

    enabled: bool = False                   # 是否启用远程模型通道
    base_url: str = ""                      # 远程接口地址，空值读环境变量 REMOTE_LLM_BASE_URL
    api_key: str = ""                       # 接口密钥，空值读环境变量 OPENAI_API_KEY
    model_name: str = ""                    # 远程模型名，空值读环境变量 REMOTE_LLM_MODEL
    timeout: int = 60                       # 单次生成超时（秒）
    temperature: float = 0.2                # 采样温度
    max_tokens: int = 2048                  # 单次最大生成 token


class RagConfig(BaseModel):
    """RAG 检索配置。"""

    top_k: int = 5                  # 单次问答注入的证据块上限
    doc_chunk_chars: int = 300      # 文档切块目标字符长度
    docs_dir: str = "./docs"        # 参与检索的调研文档目录


class AppConfig(BaseModel):
    """聚合配置对象，是 config.yaml 的内存映射。"""

    app: AppMeta                           # 应用元信息段
    service: ServiceConfig                 # 服务段
    ollama: OllamaConfig                   # 本地模型段
    knowledge_graph: KnowledgeGraphConfig   # 图谱段
    harness: HarnessConfig                 # 合规校验段
    docs: DocsConfig                       # 文档路径段
    auth: AuthConfig = Field(default_factory=AuthConfig)          # 鉴权段
    remote_llm: RemoteLlmConfig = Field(default_factory=RemoteLlmConfig)   # 远程模型段
    rag: RagConfig = Field(default_factory=RagConfig)             # RAG 段


# 项目根目录 = 本文件所在目录的上两级（app/core/config.py -> app/core -> app -> 根）
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]   # resolve 消解符号链接后再取父目录
# 配置文件固定放在项目根目录
CONFIG_PATH: Path = PROJECT_ROOT / "config.yaml"           # 拼出唯一配置入口


def _apply_env_overrides(raw: dict[str, Any]) -> dict[str, Any]:
    """用环境变量覆盖 yaml 中的敏感配置，密钥不入库。

    入参：yaml 解析出的原始字典。
    出参：补充/覆盖后的字典；环境变量未设置时保留 yaml 值。
    失败行为：不抛异常，缺省环境变量视为未配置。
    """
    # 鉴权段：密钥与初始管理员账号优先取环境变量
    auth = raw.setdefault("auth", {})
    auth["jwt_secret"] = os.getenv("JWT_SECRET", auth.get("jwt_secret", ""))
    auth["admin_username"] = os.getenv("ADMIN_USERNAME", auth.get("admin_username", ""))
    auth["admin_password"] = os.getenv("ADMIN_PASSWORD", auth.get("admin_password", ""))

    # 远程模型段：地址、密钥、模型名优先取环境变量
    remote = raw.setdefault("remote_llm", {})
    remote["base_url"] = os.getenv("REMOTE_LLM_BASE_URL", remote.get("base_url", ""))
    remote["api_key"] = os.getenv("OPENAI_API_KEY", remote.get("api_key", ""))
    remote["model_name"] = os.getenv("REMOTE_LLM_MODEL", remote.get("model_name", ""))

    # 本地 Ollama 段：地址与模型名支持环境变量覆盖（调试用）
    ollama = raw.setdefault("ollama", {})
    if os.getenv("OLLAMA_ENABLED") is not None:
        ollama["enabled"] = os.getenv("OLLAMA_ENABLED").lower() in ("1", "true", "yes")
    ollama["base_url"] = os.getenv("OLLAMA_BASE_URL", ollama.get("base_url", ""))
    ollama["model_name"] = os.getenv("OLLAMA_MODEL", ollama.get("model_name", ""))
    return raw


def load_config(path: Path | None = None) -> AppConfig:
    """读取并解析配置文件。

    入参：
        path: 配置文件绝对路径；传 None 时使用项目根目录的 config.yaml。
    出参：
        AppConfig 实例，字段缺省时使用模型默认值。
    失败行为：
        文件不存在抛 FileNotFoundError；yaml 语法错误抛 yaml.YAMLError；
        字段类型不匹配抛 pydantic.ValidationError。三者均由调用方或启动流程兜底。
    """
    target = path or CONFIG_PATH              # 未传路径时回落到默认位置
    if not target.exists():                   # 显式判空，避免后续 open 抛出更难理解的异常
        # 配置缺失属于部署错误，必须显式中断，不能静默用默认值继续跑
        raise FileNotFoundError(f"配置文件不存在：{target}")

    with open(target, "r", encoding="utf-8") as fp:   # 固定 UTF-8，防止中文键值乱码
        raw: dict[str, Any] = yaml.safe_load(fp) or {}  # safe_load 禁止任意对象构造，空文件回落到 {}

    raw = _apply_env_overrides(raw)           # 环境变量覆盖敏感字段，密钥不写进仓库
    return AppConfig(**raw)                   # pydantic 负责类型校验与缺省填充


# 进程内单例：避免每次请求都读磁盘
config: AppConfig = load_config()   # import 阶段完成一次加载


def reload_config() -> AppConfig:
    """重新从磁盘加载配置，用于修改 yaml 后不重启服务。

    入参：无。
    出参：新的 AppConfig 实例，并覆盖全局单例。
    失败行为：与 load_config 相同，抛出后全局单例保持旧值。
    """
    global config        # 声明要用模块级变量，否则会创建局部变量
    config = load_config()   # 只有解析成功才覆盖，失败时旧配置继续可用
    return config            # 便于调用方立即使用新值
