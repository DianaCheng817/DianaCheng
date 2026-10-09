# -*- coding: utf-8 -*-
"""
【可选变体】用 阿里云百炼（DashScope）兼容接口 运行同一个"20行小龙虾 Agent"
与视频代码逻辑一致，只是把 OpenRouter 换成了国内可直连的百炼兼容接口。

使用前：
1. 开通阿里云百炼，获取 API-KEY（https://bailian.console.aliyun.com/）
2. 设置环境变量：setx BAILIAN_API_KEY "sk-xxx"
3. 可选：setx MODEL "qwen-plus"（默认 qwen-plus）
"""
import os
import re
from openai import OpenAI

# 百炼 OpenAI 兼容模式地址
client = OpenAI(
    api_key=os.getenv("BAILIAN_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 与视频 main.py 相同的核心逻辑
agentmd = open("agent.md", "r", encoding="utf-8").read()
skillmd = open("skill.md", "r", encoding="utf-8").read()
messages = [{"role": "system", "content": agentmd + skillmd}]

while True:
    user_input = input("[请输入] ")
    messages.append({"role": "user", "content": user_input})
    while True:
        response = client.chat.completions.create(
            model=os.getenv("MODEL", "qwen-plus"),
            messages=messages,
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        print(f"[AI]回复: {reply}\n")

        m = re.search(r"命令[：:]\s*([^\n]+)", reply)
        if m is None:
            break

        command_result = os.popen(m.group(1).strip()).read()
        print(f"[执行]执行完毕: {command_result}\n")
        messages.append(
            {"role": "user", "content": f"执行完毕: {command_result}"}
        )
