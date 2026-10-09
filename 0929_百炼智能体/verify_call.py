# -*- coding: utf-8 -*-
"""验证 app.py 同款 SSE 读取逻辑（POST 消息 + 读流到拿到回复）"""
import json
import os
import urllib.error
import urllib.request

key = os.environ["BAILIAN_API_KEY"]
base = "https://ws-d4370xpielcmheki.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio"
sid = "sesn_01M40A0J66E3XH3F7S7GSFSSVZ"

# 1) 发消息（与 app.py 相同）
payload = {
    "input": [
        {"role": "user", "type": "message",
         "content": [{"type": "text", "text": "你好，请用一句话介绍你自己"}]}
    ]
}
req = urllib.request.Request(
    f"{base}/sessions/{sid}/events",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=60) as resp:
    resp.read()
print("消息已发送", flush=True)

# 2) SSE 读取（与 app.py 相同逻辑）
texts = []
sreq = urllib.request.Request(
    f"{base}/sessions/{sid}/events/stream",
    headers={"Authorization": f"Bearer {key}", "Accept": "text/event-stream"},
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
                break
        elif t == "session_status":
            if (obj.get("session_status") or obj.get("status")) in ("idle", "terminated"):
                break
print("回复:", "".join(texts))
print("SSE 提前断开: OK")
