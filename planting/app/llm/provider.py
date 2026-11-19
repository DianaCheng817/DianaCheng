"""统一 LLM 门面：按优先级在本地 Ollama、远程兼容接口、模板降级之间切换。

通道优先级：
    1. 本地 Ollama（配置启用且探活就绪）；
    2. 兼容 OpenAI 协议的远程接口（云端部署用，配置启用且密钥齐全）；
    3. 都不可用时不抛给调用方，由上层问答服务回退证据模板。

设计要点：
    - 任何通道的网络/解析错误都收口为 RuntimeError，由上层决定降级；
    - 模型地址、密钥、模型名全部来自配置/环境变量，代码内不硬编码。
"""

from __future__ import annotations   # 类型注解延迟求值

from typing import Any             # 请求载荷与返回字典类型

import requests                    # HTTP 调用，复用现有依赖

from app.core.config import config          # 读取远程模型配置
from app.core.logger import get_logger      # 统一日志出口
from app.llm.ollama_client import ollama    # 本地 Ollama 客户端单例

logger = get_logger(__name__)   # 绑定本模块日志器


class LLMProvider:
    """模型调用门面，对外暴露 generate / describe 两个入口。"""

    def _remote_ready(self) -> bool:
        """判断远程兼容通道是否配置齐全且可用。

        入参：无。
        出参：布尔值；未启用、缺地址或缺密钥时返回 False。
        """
        remote = config.remote_llm
        return bool(remote.enabled and remote.base_url and remote.api_key and remote.model_name)

    def _generate_remote(self, system_prompt: str, user_prompt: str) -> str:
        """调用兼容 OpenAI 协议的 /chat/completions 接口。

        入参：system_prompt 系统约束；user_prompt 任务与证据。
        出参：模型返回纯文本。
        失败行为：HTTP 错误、超时、返回体缺字段抛 RuntimeError。
        """
        remote = config.remote_llm
        payload: dict[str, Any] = {
            "model": remote.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": remote.temperature,
            "max_tokens": remote.max_tokens,
            "stream": False,
        }
        resp = requests.post(
            f"{remote.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {remote.api_key}"},
            json=payload,
            timeout=remote.timeout,
        )
        resp.raise_for_status()
        body = resp.json()
        content = (body.get("choices") or [{}])[0].get("message", {}).get("content")
        if not content:
            raise RuntimeError("远程模型返回内容为空")
        return content.strip()

    def available_channel(self) -> str:
        """返回当前可用通道标识。

        入参：无。
        出参："ollama" / "remote" / "none"。
        """
        if ollama.is_available():
            return "ollama"
        if self._remote_ready():
            return "remote"
        return "none"

    def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, str]:
        """按优先级调用可用模型生成文本。

        入参：system_prompt 系统提示词；user_prompt 用户提示词。
        出参：二元组 (正文, 来源通道)。
        失败行为：无可用通道或调用失败抛 RuntimeError，由上层降级模板。
        """
        if ollama.is_available():
            return ollama.generate(system_prompt, user_prompt), "ollama"
        if self._remote_ready():
            try:
                return self._generate_remote(system_prompt, user_prompt), "remote"
            except (requests.RequestException, ValueError) as exc:
                raise RuntimeError(f"远程模型生成失败：{exc}") from exc
        raise RuntimeError("无可用模型通道（Ollama 与远程接口均不可用）")

    def describe(self) -> dict[str, Any]:
        """返回各通道接入状态，供 /health 展示。"""
        return {
            "channel": self.available_channel(),
            "ollama": ollama.describe(),
            "remote": {
                "enabled": config.remote_llm.enabled,
                "configured": self._remote_ready(),
                "baseUrl": config.remote_llm.base_url,
                "model": config.remote_llm.model_name,
            },
        }


# 进程内单例
provider = LLMProvider()
