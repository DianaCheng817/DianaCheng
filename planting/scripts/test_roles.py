# -*- coding: utf-8 -*-
"""三类身份权限边界实测（真实 HTTP 请求）。
覆盖：访客只读、注册用户、管理员；越权一律被统一无权限响应拦截。
"""
import json
import time
import uuid
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"
passed, failed = 0, 0


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def check(title, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("  [PASS]", title)
    else:
        failed += 1
        print("  [FAIL]", title, detail)


print("=" * 60)
print("三类身份权限边界实测")
print("=" * 60)

# ---- 访客（未登录）----
print("\n[访客 guest]")
_, wiki = call("GET", "/api/kg/roles")
check("访客可浏览 Wiki 角色列表", wiki.get("ok") is True)
_, kg = call("GET", "/api/kg/facts/f12")
check("访客可按编号溯源事实", kg.get("ok") is True)
_, health = call("GET", "/health")
check("访客可看健康检查", health.get("ok") is True)
_, chat_anon = call("POST", "/api/chat", {"question": "测试", "force_template": True})
check("访客问答被拦截", chat_anon.get("ok") is False)
_, admin_anon = call("GET", "/api/admin/users")
check("访客访问管理接口被拦截", admin_anon.get("ok") is False)

# ---- 注册用户 ----
print("\n[注册用户 user]")
uname = "u_" + uuid.uuid4().hex[:8]
pwd = "Test@12345"
_, reg = call("POST", "/api/auth/register", {"username": uname, "password": pwd, "role": "user"})
check("注册用户成功", reg.get("ok") is True, str(reg.get("error", ""))[:80])
_, login = call("POST", "/api/auth/login", {"username": uname, "password": pwd})
check("注册用户登录成功", login.get("ok") is True, str(login.get("error", ""))[:80])
utoken = login.get("data", {}).get("token", "") if login.get("ok") else ""
_, me = call("GET", "/api/auth/me", token=utoken)
check("注册用户角色为 user", me.get("data", {}).get("role") == "user", str(me.get("data", {}))[:80])
_, chat_user = call("POST", "/api/chat", {"question": "异常读数为什么人工核验", "force_template": True}, utoken)
check("注册用户可问答", chat_user.get("ok") is True, str(chat_user.get("error", ""))[:80])
_, admin_user = call("GET", "/api/admin/users", token=utoken)
check("注册用户访问管理接口被拦截（越权）", admin_user.get("ok") is False)
_, gen_user = call("POST", "/api/generate", {"task_key": "opportunity:1", "force_template": True}, utoken)
check("注册用户可生成任务", gen_user.get("ok") is True, str(gen_user.get("error", ""))[:80])

# ---- 管理员 ----
print("\n[管理员 admin]")
_, alogin = call("POST", "/api/auth/login", {"username": "admin", "password": "admin123"})
check("管理员登录成功", alogin.get("ok") is True, str(alogin.get("error", ""))[:80])
atoken = alogin.get("data", {}).get("token", "") if alogin.get("ok") else ""
_, users = call("GET", "/api/admin/users", token=atoken)
check("管理员可查看用户清单", users.get("ok") is True)
_, audit = call("GET", "/api/admin/audit", token=atoken)
check("管理员可查看审计日志", audit.get("ok") is True)
_, chat_admin = call("POST", "/api/chat", {"question": "测试", "force_template": True}, atoken)
check("管理员可问答", chat_admin.get("ok") is True)

print("\n" + "=" * 60)
print("通过 %d 项 / 失败 %d 项" % (passed, failed))
print("全部通过" if failed == 0 else "存在失败项")
