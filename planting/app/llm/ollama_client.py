"""Ollama 本地模型适配层。

设计要点：
1. 只用标准 Ollama HTTP 接口（/api/tags 探活、/api/chat 生成），不引入额外 SDK；
2. 任何网络错误都降级为 TemplateFallback 信号，不让服务整体不可用；
3. 模型地址与名称全部来自 config.yaml。
"""

from __future__ import annotations   # 类型注解延迟求值

from typing import Any   # 标注请求载荷与返回字典的类型

import requests   # 只用标准库以外的 requests，不引入 ollama SDK

from app.core.config import config          # 模型地址与名称来自配置，禁止硬编码
from app.core.logger import get_logger      # 统一日志出口

logger = get_logger(__name__)   # 绑定本模块日志器


class OllamaClient:
    """Ollama HTTP 客户端。"""

    def __init__(self) -> None:
        """从配置读取地址、模型名与超时。"""
        self.base_url: str = config.ollama.base_url.rstrip("/")   # 去掉尾部斜杠，避免拼出双斜杠
        self.model: str = config.ollama.model_name                # 模型名，必须与 ollama list 完全一致
        self.timeout: int = config.ollama.timeout                 # 单次生成超时（秒）

    def is_available(self) -> bool:
        """探测 Ollama 服务是否可达且模型已就绪。

        入参：无。
        出参：布尔值，True 表示服务在线且模型已拉取。
        失败行为：不抛异常，任何异常都返回 False，由上层决定是否降级。
        """
        if not config.ollama.enabled:   # 配置里关掉本地模型时直接判不可用，省一次网络调用
            return False
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)   # 探活用短超时，避免拖慢启动
            resp.raise_for_status()                                        # 非 2xx 视为不可达
            tags = resp.json().get("models", [])                           # 取出已安装模型列表
            names = {item.get("name", "") for item in tags}                # 收成集合，便于精确匹配
            # 严格按名称匹配：配置写 qwen2.5:7b 就只认 qwen2.5:7b，
            # 不能因为装了 qwen2.5:0.5b 就误判可用——否则会调用到不存在的模型而静默降级。
            # 仅当配置里没写 tag 时，才退化为按基名匹配。
            if ":" in self.model:                                          # 配置里带了 tag，则要求全名一致
                ready = self.model in names                                # 全名命中才算就绪
            else:                                                          # 配置里没带 tag，允许任意 tag 的同名模型
                ready = any(n.split(":")[0] == self.model for n in names)   # 按基名比对
            if not ready:                                                  # 未就绪时给出可用列表，便于改配置
                logger.warning("Ollama 在线，但模型 %s 未拉取；可用模型：%s", self.model, sorted(names))
            return ready                                                   # 把结论返回给上层
        except (requests.RequestException, ValueError) as exc:              # 网络错误与 JSON 解析错误一并兜住
            logger.warning("Ollama 探活失败：%s", exc)                      # 只告警不抛异常，保证服务可用
            return False                                                    # 判不可用，触发模板降级

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """调用本地模型生成文本。

        入参：
            system_prompt: 系统提示词，约束模型身份与输出纪律。
            user_prompt: 用户提示词，携带证据与任务。
        出参：模型返回的纯文本。
        失败行为：
            HTTP 错误 / 超时 / 返回体缺字段统一抛 RuntimeError，
            由上层 StageService 捕获并降级为模板引擎。
        """
        payload: dict[str, Any] = {              # 组装 /api/chat 请求体
            "model": self.model,                 # 指定模型，与探活用的是同一个配置值
            "messages": [                        # 两段式消息：系统约束 + 用户任务
                {"role": "system", "content": system_prompt},   # 身份与纪律放在系统位，权重更高
                {"role": "user", "content": user_prompt},       # 证据与写作要求放用户位
            ],
            "stream": False,                     # 关闭流式，便于一次性做完 Harness 校验
            "options": {                                                    # 采样参数，压低随机性
                "temperature": config.ollama.temperature,                   # 温度来自配置
                "num_predict": config.ollama.num_predict,                   # 最大生成长度来自配置
            },
        }
        try:
            resp = requests.post(                # 调用本地模型
                f"{self.base_url}/api/chat",     # 标准 chat 接口
                json=payload,                    # 以 JSON 提交，避免编码问题
                timeout=self.timeout,            # 生成耗时长，用配置里的超时
            )
            resp.raise_for_status()   # 非 2xx 立即抛错，交给下方统一转 RuntimeError
            body = resp.json()        # 解析返回体
        except (requests.RequestException, ValueError) as exc:   # 网络与解析错误统一收口
            raise RuntimeError(f"Ollama 生成失败：{exc}") from exc   # 用 from 保留原始堆栈

        content = (body.get("message") or {}).get("content")   # 兼容 message 缺失的情况
        if not content:                                        # 空内容等同于失败，不能当成功返回
            raise RuntimeError("Ollama 返回内容为空")
        return content.strip()                                 # 去掉首尾空白，便于后续规则匹配

    def describe(self) -> dict[str, Any]:
        """返回当前模型接入状态，供 /health 展示。

        入参：无。
        出参：字典，含 baseUrl、model、enabled、available。
        失败行为：不抛异常。
        """
        return {
            "baseUrl": self.base_url,          # 便于确认连的是哪个 Ollama 实例
            "model": self.model,               # 便于确认模型名是否写错
            "enabled": config.ollama.enabled,  # 配置层开关
            "available": self.is_available(),  # 实时探活结果
        }


ollama = OllamaClient()   # 全局单例，避免每次请求都重新读配置
