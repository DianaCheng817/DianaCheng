# -*- coding: utf-8 -*-
"""
0929 作业②：发布智能体并在本地生成 streamlit 网页来调用它
============================================================
在阿里云百炼 Managed Agent 平台创建并部署"开源微专业学习助手"后，
通过 AgentStudio API 会话接口调用它（发送消息 + SSE 接收回复）。

运行：
    pip install streamlit
    streamlit run app.py
浏览器打开 http://localhost:8501 即可对话。
"""
import json
import os
import urllib.error
import urllib.request

import streamlit as st

# 应用配置：优先读环境变量，也可在左侧边栏手动填
DEFAULT_WORKSPACE_ID = os.getenv("BAILIAN_WORKSPACE_ID", "ws-d4370xpielcmheki")   # 百炼业务空间 ID
DEFAULT_SESSION_ID = os.getenv("BAILIAN_SESSION_ID", "sesn_01M40A0J66E3XH3F7S7GSFSSVZ")  # 智能体会话 ID
DEFAULT_API_KEY = os.getenv("BAILIAN_API_KEY", "")

# ---------- 调用百炼应用 ----------
# 注意：streamlit 每次交互都会从上到下重新执行整个脚本，
# 函数必须定义在"侧边栏按钮"之前，否则点测试连接会报 call_agent 未定义。
# Managed Agent 通过 AgentStudio 会话接口调用：
# ① POST https://{业务空间ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio/sessions/{会话ID}/events 发送消息
# ② 订阅 SSE .../sessions/{会话ID}/events/stream 接收回复
def call_agent(session_id: str, api_key: str, user_text: str, history=None) -> str:
    """调用百炼 Managed Agent 会话（发消息 + SSE 读回复）"""
    base = f"https://{DEFAULT_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
    payload = {
        "input": [
            {"role": "user", "type": "message",
             "content": [{"type": "text", "text": user_text}]}
        ]
    }
    # 1) 发送消息
    req = urllib.request.Request(
        f"{base}/sessions/{session_id}/events",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()

    # 2) SSE 流式接收回复
    texts = []
    sreq = urllib.request.Request(
        f"{base}/sessions/{session_id}/events/stream",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "text/event-stream"},
    )
    with urllib.request.urlopen(sreq, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[5:].strip())
            except Exception:
                continue
            t = obj.get("type")
            if t == "message" and obj.get("role") != "user":
                for block in (obj.get("content") or []):
                    if block.get("type") == "text" and block.get("text"):
                        texts.append(block["text"])
                if texts:
                    break  # 已拿到回复，主动断开 SSE
            elif t == "session_status":
                if (obj.get("session_status") or obj.get("status")) in ("idle", "terminated"):
                    break
    return "\n".join(texts) if texts else "（智能体未返回文本）"

st.set_page_config(page_title="开源微专业学习助手", page_icon="🦞")
st.title("🦞 开源微专业学习助手")
st.caption("基于阿里云百炼 FlowAgent 智能体应用（0929 作业）")

# ---------- 左侧边栏：配置 ----------
with st.sidebar:
    st.header("⚙️ 连接配置")
    session_id = st.text_input("会话ID（sesn_...）", value=DEFAULT_SESSION_ID)
    api_key = st.text_input("API-KEY（sk-...）", value=DEFAULT_API_KEY, type="password")
    if st.button("测试连接"):
        if not session_id or not api_key:
            st.warning("请先填写 会话ID 和 API-KEY")
        else:
            with st.spinner("正在测试…"):
                try:
                    resp = call_agent(session_id, api_key, "你好，请用一句话介绍你自己")
                    st.success(f"连接成功 ✅\n{resp}")
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8", errors="replace")
                    st.error(f"连接失败 ❌ HTTP {e.code}\n{body[:500]}")
                except Exception as e:
                    st.error(f"连接失败 ❌\n{e}")
    st.divider()
    st.caption("提示：也可以先设置环境变量\nBAILIAN_WORKSPACE_ID / BAILIAN_SESSION_ID / BAILIAN_API_KEY\n再运行本网页，就不用每次填写。")

# ---------- 调用百炼应用 ----------
# Managed Agent 通过 AgentStudio 会话接口调用：
# ① POST .../sessions/{会话ID}/events 发送消息
# ② 订阅 SSE .../sessions/{会话ID}/events/stream 接收回复
def call_agent(session_id: str, api_key: str, user_text: str, history=None) -> str:
    """调用百炼 Managed Agent 会话（发消息 + SSE 读回复）"""
    base = f"https://{DEFAULT_WORKSPACE_ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
    payload = {
        "input": [
            {"role": "user", "type": "message",
             "content": [{"type": "text", "text": user_text}]}
        ]
    }
    # 1) 发送消息
    req = urllib.request.Request(
        f"{base}/sessions/{session_id}/events",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()

    # 2) SSE 流式接收回复
    texts = []
    sreq = urllib.request.Request(
        f"{base}/sessions/{session_id}/events/stream",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "text/event-stream"},
    )
    with urllib.request.urlopen(sreq, timeout=120) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            try:
                obj = json.loads(line[5:].strip())
            except Exception:
                continue
            t = obj.get("type")
            if t == "message" and obj.get("role") != "user":
                for block in (obj.get("content") or []):
                    if block.get("type") == "text" and block.get("text"):
                        texts.append(block["text"])
                if texts:
                    break  # 已拿到回复，主动断开 SSE
            elif t == "session_status":
                if (obj.get("session_status") or obj.get("status")) in ("idle", "terminated"):
                    break
    return "\n".join(texts) if texts else "（智能体未返回文本）"

# ---------- 聊天区 ----------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好！我是开源微专业学习助手，可以帮你梳理开源模型、框架、Agent、Skill 等知识，也可以联网查最新资讯。你想问什么？"}
    ]

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

if prompt := st.chat_input("输入你的问题，例如：Ollama 和 vLLM 有什么区别？"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    if not session_id or not api_key:
        st.error("请先在左侧边栏填写 会话ID 和 API-KEY")
    else:
        with st.chat_message("assistant"):
            with st.spinner("智能体思考中…"):
                try:
                    reply = call_agent(
                        session_id, api_key, prompt,
                        history=st.session_state.messages[:-1],
                    )
                except Exception as e:
                    reply = f"调用出错：{e}\n\n请检查 会话ID / API-KEY 是否正确。"
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})
