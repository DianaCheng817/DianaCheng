# -*- coding: utf-8 -*-
"""
【闪客】20 行代码彻底搞懂小龙虾（OpenClaw）—— 视频代码复现（最终版 main.py）

核心思想：Agent = 大模型 + 上下文（agent.md / skill.md）+ 工具（命令执行）
运行方式：见 README.md，需要设置环境变量 OPENROUTER_API_KEY
"""
import os
import re
from openrouter import OpenRouter   # 导入 OpenRouter SDK

# 与大模型建立连接（API Key 从环境变量读取）
with OpenRouter(api_key=os.getenv("OPENROUTER_API_KEY")) as client:
    # 读取"系统提示词"(agent.md) 和 "技能说明"(skill.md)，
    # 拼进 system 消息 —— 这就是小龙虾"性格 + 技能"的来源
    agentmd = open("agent.md", "r", encoding="utf-8").read()
    skillmd = open("skill.md", "r", encoding="utf-8").read()
    messages = [{"role": "system", "content": agentmd + skillmd}]

    # 外层循环 —— 持续接收用户的输入
    while True:
        user_input = input("[请输入] ")
        messages.append({"role": "user", "content": user_input})

        # 内层循环 —— Agent 反复"思考→执行"，直到给出最终答复
        while True:
            # 把完整对话历史发给大模型，获得回复
            response = client.chat.completions.create(
                model=os.getenv("MODEL", "openai/gpt-4o"),
                messages=messages,
            )
            reply = response.choices[0].message.content
            messages.append({"role": "assistant", "content": reply})
            print(f"[AI]回复: {reply}\n")

            # 提取模型输出中的命令（兼容中文全角冒号，只取第一条命令行）
            # 没有命令 → 说明模型给出了"完成：XXX"总结，任务结束
            m = re.search(r"命令[：:]\s*([^\n]+)", reply)
            if m is None:
                break

            # 执行命令，把执行结果回传给模型，让它判断是否还需要继续
            command_result = os.popen(m.group(1).strip()).read()
            print(f"[执行]执行完毕: {command_result}\n")
            messages.append(
                {"role": "user", "content": f"执行完毕: {command_result}"}
            )
