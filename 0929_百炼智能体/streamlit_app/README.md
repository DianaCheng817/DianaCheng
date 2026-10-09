# streamlit 网页调用百炼智能体 —— 使用说明

## 这是什么
0929 作业②要求：**发布智能体并在本地生成一个 streamlit 网页来调用它**。
本目录的 `app.py` 就是那个网页——它通过百炼 **Managed Agent（托管智能体）** 的
AgentStudio 会话接口调用"开源微专业学习助手"，聊天式交互。
✅ 2026-10-03 已在百炼实测调用成功（网页侧"测试连接"绿色通过、对话正常回复）。

## 已配置好的参数（在 app.py 顶部常量，也可在网页侧边栏改）
- 业务空间 ID：`ws-d4370xpielcmheki`（地域：华北2·北京）
- 会话 ID：`sesn_01M40A0J66E3XH3F7S7GSFSSVZ`（绑定智能体 `agent_01M3YJ2YF9HAR31432K3M9FQWJ`）
- API-KEY：在网页侧边栏手动填写（`sk-` 开头）

## 运行步骤（3 步）

```bash
# 1. 装依赖（Python 3.9+）
pip install -r requirements.txt

# 2. 提供 API-KEY（二选一）
#    方式A：环境变量（setx 后需重开终端生效）
setx BAILIAN_API_KEY "sk-你的API-KEY"
#    方式B：直接在网页左侧边栏粘贴（推荐，改完立即生效）

# 3. 启动
streamlit run app.py
```

浏览器打开 `http://localhost:8501`，即可对话：
- 问："Ollama 和 vLLM 有什么区别？"
- 问："今天有哪些开源 AI 新闻？"（智能体配置了 web_search 工具，会自动联网检索）

## 效果演示要点（截图给老师看）
1. 网页标题"开源微专业学习助手"（证明是 streamlit）；
2. 侧边栏有会话ID / API-KEY 配置；
3. 点"测试连接"出现绿色"连接成功 ✅"+ 智能体自我介绍；
4. 对话得到智能体回答（证明调用成功）。

## 技术说明
- 调用百炼 **Managed Agent** 的 AgentStudio 会话接口（官方文档 2026-09-20 版）：
  1. `POST https://{业务空间ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio/sessions/{会话ID}/events` 发送用户消息；
  2. 订阅 `.../sessions/{会话ID}/events/stream`（SSE）接收回复，读到 `message` 文本即返回。
- 只依赖 streamlit + Python 标准库 urllib，无需安装 dashscope SDK。
- 接口参考：阿里云帮助中心《Managed Agents API 总览》《Managed Agents 快速开始》。
