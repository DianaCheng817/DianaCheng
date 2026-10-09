# 0929 作业①：在阿里云百炼上创建智能体（FlowAgent 1.0 版）—— 完整指南

> 学号：f25011102 ｜ 日期：2026-10-02 ｜ 设计目标：**开源微专业学习助手**（FlowAgent 1.0 版，即"智能体编排应用"）

本指南把"在百炼上创建一个 FlowAgent 智能体"拆成 6 步，照着做即可完成，并拿到 ②③ 作业所需的 APP_ID。

## 第 1 步：开通百炼 + 拿 API-KEY（5 分钟）

1. 打开 https://bailian.console.aliyun.com/ ，用**阿里云账号**登录（没有就注册一个，新用户有免费额度）。
2. 首次进入按提示**开通百炼服务**（选"开通"即可，按量计费，学习用量几乎不花钱）。
3. 右上角头像 → **密钥管理 / API-KEY** → 创建新的 API-KEY，形如 `sk-xxxxxxxx`，**先复制保存**（只显示一次）。

## 第 2 步：创建智能体应用（FlowAgent 1.0 版）

1. 左侧菜单选 **智能体应用**（或"智能体"）→ 点击 **创建应用**。
2. 应用模式选择 **Flow Agent（流程编排 / 1.0 版）**——这是老的画布式工作流版本，用节点拖拽搭建流程。
3. 给应用起名：`开源微专业学习助手`，随便填个描述。

## 第 3 步：编排流程（画布拖节点）

按下面 5 个节点搭流程，从上到下连接：

```
[开始] 接收用户问题
   ↓
[大模型①] 意图理解与规划
   系统提示词：判断问题类型，决定是否需要联网（输出：需要/不需要 + 关键搜索词）
   ↓
[条件判断] 是否需要联网？        ← 条件节点
   ├─ 是 → [工具：网页搜索] 用关键词调百炼内置"网页搜索"工具，拿到最新资料
   └─ 否 → （跳过工具）
   ↓
[大模型②] 综合回答
   系统提示词：结合用户问题（+搜索结果）给出结构清晰、带出处的回答
   ↓
[结束] 返回回答
```

**大模型①（意图理解）System Prompt：**
```
你是流程规划器。用户会给出一个问题，请只输出一行 JSON：
{"need_search": true/false, "keywords": "搜索关键词"}
当问题涉及最新资讯、时事、具体数据、开源项目动态时 need_search 为 true，否则为 false。
```

**大模型②（综合回答）System Prompt：**
```
你是"开源微专业学习助手"，帮助计算机专业学生理解开源技术（模型、框架、Agent、工具）。
要求：
1. 回答结构清晰，用列表/小标题组织；
2. 如果提供了搜索结果，优先引用其中的事实，并标注来源；
3. 面向初学者，避免堆砌名词；必要时给出"一句话类比"；
4. 不确定的信息要明说"这一点我不确定"。
```

> 提示：大模型节点默认模型建议选 `qwen-plus`（便宜够用）；"网页搜索"工具在节点面板的"工具"里拖入，**无需写代码**。

## 第 4 步：在线测试

右上角 **预览/测试**：输入"阿里云百炼和 ModelScope 有什么区别？" → 应看到流程：大模型①规划 → 条件判断→ 网页搜索 → 大模型②综合回答。多测 2~3 个问题，不满意就改 Prompt 再测。

## 第 5 步：发布 + 拿 APP_ID

1. 测试满意后点击 **发布**（记得选"正式发布/新版本"）。
2. 回到 **应用管理** 列表页，在应用卡片上复制 **APP_ID**（形如 `4xxx-xxxx-xxxx-xxxx`，这就是 ②③ 作业要用的 ID）。

## 第 6 步：调用验证（发布成功即证明"创建+发布"完成）

```bash
# curl 验证（把 APP_ID 和 API-KEY 换成你自己的）
curl -X POST "https://dashscope.aliyuncs.com/api/v1/apps/你的APP_ID/completion" \
  -H "Authorization: Bearer sk-你的API-KEY" \
  -H "Content-Type: application/json" \
  -d '{"input":{"messages":[{"role":"user","content":"ModelScope是什么？"}]}}'
```

返回 JSON 里的 `output.text` 就是智能体的回答 → **创建、发布、调用全链路打通 ✅**

---

## 完成后（②③ 作业的衔接）

- ② 作业（streamlit 网页调用）：把上面这个 APP_ID 填进 `streamlit_app/app.py` 即可，见下一份文件。
- ③ 作业（ai-agent-book 设计思想）：本智能体采用"意图规划 → 工具检索 → 综合回答"的流程，
  对应《深入理解 AI Agent》的 `Agent = LLM + 上下文 + 工具` 公式，详细分析见 `02_智能体设计思想_ai-agent-book分析.md`。

---

## 附录（2026-10-03 实际执行）：新版 Managed Agent 与本文档的差异

> 实际创建时百炼控制台已升级为 **Managed Agent 平台**（顶部标签"Managed Agent"），
> 不再有本文档描述的"FlowAgent 画布"。以下记录实际完成的方式，供复盘/答辩参考。

| 项目 | 实际值 |
|---|---|
| 智能体名称 | 开源微专业学习助手 |
| 智能体 ID | `agent_01M3YJ2YF9HAR31432K3M9FQWJ` |
| 模型档位 | `auto`（自动档，页面只有"自动/均衡/性能/经济"四档，无具体模型名） |
| 系统提示词 | "你是开源微专业学习助手，专门解答开源、Git、Ollama、本地大模型部署、Agent智能体相关问题。回答简洁清晰，适合学生学习。" |
| 内置工具 | bash / read / write / edit / glob / grep / web_search / web_fetch（全开） |
| 业务空间 ID | `ws-d4370xpielcmheki`（地域 华北2·北京） |
| 会话 ID | `sesn_01M40A0J66E3XH3F7S7GSFSSVZ` |
| 部署 | 新版流程中"发布"改名"部署"，创建"部署"卡片即完成对外提供 |

**新版调用方式（与本文档第 6 步的旧接口不同）**——AgentStudio 会话接口：
1. `POST https://{业务空间ID}.cn-beijing.maas.aliyuncs.com/api/v1/agentstudio/sessions/{会话ID}/events`
   body：`{"input":[{"role":"user","type":"message","content":[{"type":"text","text":"问题"}]}]}`
2. 订阅 `GET .../sessions/{会话ID}/events/stream`（SSE），收到 `message` 事件的 `text` 即回复。

> 备注：旧接口 `/api/v1/apps/{APP_ID}/completion` 对 `agent_` 前缀的新版智能体返回 403，
> Responses 兼容接口（`/api/v2/apps/agent/{APP_ID}/compatible-mode/v1/responses`）返回 500，
> 均不适用；只有上面的 AgentStudio 会话接口实测可用（2026-10-03 验证，网页"测试连接"绿色 ✅）。
