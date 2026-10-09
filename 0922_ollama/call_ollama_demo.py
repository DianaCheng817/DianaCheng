# -*- coding: utf-8 -*-
"""
Ollama 模型调用演示脚本（0922 作业配套）
覆盖两种调用方式：
  1) Ollama 原生 API（/api/generate、/api/chat）
  2) OpenAI 兼容接口（/v1/chat/completions）

前置条件：本机已安装并启动 Ollama（默认监听 127.0.0.1:11434）
运行：python call_ollama_demo.py
"""
import json
import urllib.request

BASE = "http://127.0.0.1:11434"
MODEL = "qwen3:0.6b"          # 改成你本机已下载的模型名，如 qwen2.5:0.5b


def post(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    print("=" * 50)
    print("1. Ollama 原生 API：/api/generate（一问一答）")
    r = post("/api/generate", {"model": MODEL, "prompt": "用一句话介绍你自己", "stream": False})
    print("回复：", r["response"])
    print(f"耗时：{r['total_duration'] / 1e6:.0f} ms，生成 {r['eval_count']} 个 token\n")

    print("=" * 50)
    print("2. Ollama 原生 API：/api/chat（多轮对话）")
    messages = [
        {"role": "user", "content": "1+1等于几？"},
        {"role": "assistant", "content": "等于2。"},
        {"role": "user", "content": "那再加1呢？"},
    ]
    r2 = post("/api/chat", {"model": MODEL, "messages": messages, "stream": False})
    print("回复：", r2["message"]["content"])
    print(f"耗时：{r2['total_duration'] / 1e6:.0f} ms\n")

    print("=" * 50)
    print("3. OpenAI 兼容接口：/v1/chat/completions")
    print("（Ollama 内置了 OpenAI 兼容层，任何 OpenAI SDK 改一下 base_url 就能用）")
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": "你好！"}],
        "stream": False,
    }
    r3 = post("/v1/chat/completions", payload)
    print("回复：", r3["choices"][0]["message"]["content"])
    print("usage：", r3.get("usage"))


if __name__ == "__main__":
    main()
