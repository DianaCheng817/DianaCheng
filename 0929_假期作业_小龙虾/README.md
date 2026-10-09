# 【假期作业】实现视频代码：20 行代码彻底搞懂小龙虾（OpenClaw）

- 视频：【闪客】20 行代码彻底搞懂小龙虾！男女老少都看得懂哟~
  https://www.bilibili.com/video/BV19hwTzwETF/
- 说明：本目录完整复现了视频中从"大模型 API 调用"到"20 行 Agent 核心"的代码演进，
  最终核心就是 `main.py`（约 20 行）+ 两份提示词文件（`agent.md` / `skill.md`）。

---

## 一、视频到底讲了什么（一句话总结）

> **"小龙虾"（OpenClaw）的本质 = 大模型 + 上下文（提示词）+ 工具（命令执行）。**
> 视频用 20 行代码证明：所谓 Agent 的"智能"，绝大部分来自你喂给它的提示词和工具规则，
> 而不是模型本身。视频最后用电影《机械公敌》抛出思考：当 Agent 能执行电脑上所有操作时，
> 谁来约束它？（这也是 OpenClaw 类工具强调权限/沙箱的原因）

## 二、代码演进（视频里的 6 步，本目录已全部实现）

| 步骤 | 文件 | 实现内容 | 关键点 |
|---|---|---|---|
| step0 | 视频演示 | 调 API，问一句"你是谁" | 通过程序和大模型对话 |
| step1 | 视频演示 | 死循环持续对话 | 一问一答，但**无记忆**（1+1 问完再问"再加1呢"会答错）|
| step2 | 视频演示 | 维护 messages 历史 | 有了**记忆**，能理解上下文 |
| step3 | 视频演示 | 系统提示词约定"命令：/完成："格式 | 让模型"会干活"而不是只会聊天 |
| step4 | 视频演示 | 解析"命令："并 os.popen 执行，把结果回喂模型 | **Agent 循环**：思考→执行→再思考→结束 |
| 最终 | **main.py** | agent.md + skill.md 拼进系统提示词 | 20 行代码 = 一个能干活的小龙虾 |

## 三、运行方法

### 方式 A：原版（OpenRouter，与视频一致）
1. 安装依赖：`pip install -r requirements.txt`
2. 注册 OpenRouter（https://openrouter.ai/）获取 API Key，并设置：
   - `setx OPENROUTER_API_KEY "你的key"`（Windows，需重开终端生效）
   - 可选：`setx MODEL "openai/gpt-4o"`（默认 openai/gpt-4o，可换成其他模型名）
3. 运行：`python main.py`
4. 试几个需求，例如：
   - `创建 hello.txt，内容是 hello world`
   - `查看当前目录有哪些文件`
   - `把 https://www.bilibili.com/video/BVxxxx/ 下载下来`（需已装 yt-dlp）

### 方式 B：国内直连（阿里云百炼兼容接口，推荐在国内网络使用）
1. `pip install openai`
2. 开通阿里云百炼（https://bailian.console.aliyun.com/），创建 API-KEY：
   - `setx BAILIAN_API_KEY "sk-xxx"`
3. 运行：`python main_bailian.py`

> 注意：Agent 会真实执行模型输出的 shell 命令，**请只在自己可信的目录中运行，
> 不要喂给它危险指令**（视频里也演示了"killaperson"这种反例）。作业展示用途完全够用。

## 四、文件清单

| 文件 | 说明 |
|---|---|
| main.py | 20 行核心 Agent（OpenRouter 版，与视频一致）|
| main_bailian.py | 同一 Agent 的百炼兼容接口版（国内可直连）|
| agent.md | 系统提示词：约定"命令：/完成："两种输出格式 |
| skill.md | 技能说明书：新闻查询 / 文件操作 / B站视频下载等 |
| requirements.txt | Python 依赖 |
| README.md | 本说明 |

## 五、提交到作业表格的链接建议

把本目录推送到自己的 GitCode/GitHub 仓库（例如 `gitcode.com/DianaCheng/f25011102-hw`），
再把仓库地址填到作业表 0929 页的"假期作业"一栏即可。
