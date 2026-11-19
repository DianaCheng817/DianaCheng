# 种植灌溉与农事记录 · 业务挖掘与现场调研资料包

禾丰种植合作社的种植灌溉与农事记录场景，从「想上 AI」到「值得验证的业务需求」的完整调查材料。

- **案例**：灌溉计划与田间真实湿度（原创合成案例）
- **训练平台**：FDE 训练中心 · 集团专题项目 `agriculture-irrigation` · 项目练习 1
- **覆盖阶段**：01 业务挖掘（3 项任务，78 / 72 / 78）、02 现场调研（3 项任务，72 / 72 / 72）
- **资料性质**：合成训练案例，只读核对与人工交接，**不代表真实授权、业务执行或客户验收**

---

## 一句话结论

问题成立，但**不是**「上一套自动灌溉」：首期只做观测解释与灌溉建议、系统只读、异常不驱动执行；
真正要改善的是**异常读数的人工核验闭环**、**现场说明的随单交接**、**多套系统的口径治理**，
而这三件事目前都缺可验证的基线。

---

## 目录结构

```
planting/
├── README.md                      本文件：项目概览与索引
├── docs/                          五份交付文档
│   ├── 01-业务挖掘.md              业务机会、现状基线、立项与决策链
│   ├── 02-访谈记录.md              六角色 × 六问访谈记录、角色地图、矛盾陈述
│   ├── 03-现场调研分析.md          四来源收敛表、证据台账、问题清单
│   ├── 04-项目原有资料.md          客户简报、现状信息请求表、访谈问题库、利益相关者资料
│   ├── 05-现状流程图.md            六步主流程 + 5 个判断点（菱形）、异常路径、瓶颈责任人
│   └── assets/
│       └── current-state-flow.svg  现状流程图（由脚本生成）
└── src/                           可复现部分
    ├── README.md                   src 目录说明
    ├── raw/                        平台导出报告原件（溯源用，不改动）
    ├── data/process-model.json     流程模型数据（节点 / 异常 / 瓶颈）
    ├── diagram/build_flow_svg.py   SVG 渲染脚本（仅标准库）
    └── tools/check_docs.py         文档自检（证据编号、图片、SVG）
```

---

## 五份文档在回答什么

| 文档 | 回答的问题 | 核心交付 |
| --- | --- | --- |
| [01 业务挖掘](docs/01-业务挖掘.md) | 哪件真实事件触发了需求？维持现状损失什么？谁批预算、谁能否决？ | 业务机会清单 O1–O4、6 项指标基线卡、项目章程与利益相关者地图 |
| [02 访谈记录](docs/02-访谈记录.md) | 每个岗位怎么讲这件事？谁在什么系统里接手？哪里说法不一致？ | 6 个角色 × 6 问的记录（36 条事实）、角色地图、4 组矛盾对照 |
| [03 现场调研分析](docs/03-现场调研分析.md) | 四份材料是否互相支持？哪些结论还立不住？ | 四来源收敛表、36 条证据台账、P0/P1/P2 问题清单 |
| [04 项目原有资料](docs/04-项目原有资料.md) | 手上到底有哪些原始材料？还缺什么？ | 4 份案例资料全文 + 资料取得状态表 |
| [05 现状流程图](docs/05-现状流程图.md) | 现在的流程怎么走？谁在哪儿做判断、判断失败流向哪？瓶颈在谁手上？ | 现状流程图（SVG + Mermaid，含 5 个判断菱形与是/否分支）、节点表、异常路径表、判断口径表 |

---

## 关键结论速览

### 业务机会（详见 01）

| 编号 | 机会 | 真正要改善的业务结果 |
| --- | --- | --- |
| O1 | 异常读数识别与人工复核 | 异常提示落到具体地块与观测记录，复核签字后才算数，异常不驱动执行 |
| O2 | 现场说明随单交接 | 便签与群聊里的关键说明挂到业务编号上流转，接手人确认才闭环 |
| O3 | 数据口径治理 | 主编号、事件时间、版本、埋深、面积单位先对齐，歧义记录进人工修复队列 |
| O4 | 验收与反馈闭环 | 按岗位分别计时、固定分母，每周复测后再更新规则版本 |

### 现状基线（详见 01 / 03）

| 指标 | 现状 | 状态 |
| --- | --- | --- |
| 观测汇总工时 | 24 地块 / 每天 60 次观测，人工汇总约 90 分钟 | 单岗位口径，待样本验证 |
| 旱情识别时效 | 平均约 2 天 → 目标半天 | 目标已定，基期与口径未定 |
| 异常读数核验 | 全量人工核验，单次耗时未知 | 待采集 |
| 交接返工 | 便签 / 群聊传递，返工率未知 | 待采集 |
| 质控驳回频次 | 无质控台账 | 待验证假设，不得当基线 |

### 硬边界（全项目通用）

1. 首期只做**观测解释与灌溉建议**，不自动控制泵阀（`f05`、`f32`、`f52`）
2. 所有异常读数**不直接驱动执行**，全部人工核验（`f40`、`f42`）
3. 四类情况强制转人工：传感器拔出误判、资料缺依据、版本冲突、关键系统不可用（`f44`）
4. 交接五要素 + 接手人确认，仅发消息不算完成（`f23`）
5. 最终决定、对外承诺、资产变更须审批人本人确认，禁止借用账号（`f41`）
6. 审计保留六要素，可重建六步链（`f45`）

---

## 证据编号约定

正文里的 `f12`、`f23` 这类编号指**访谈事实编号**（`agriculture-irrigation-f00` … `f55`），共 36 条：

| 区间 | 角色 | 事实类型 |
| --- | --- | --- |
| `f00`–`f05` | 顾明岚 · 合作社负责人 | 业务目标、流程、验收、预算、决策、范围 |
| `f10`–`f15` | 林亦舟 · 田间技术员 | 现场故障样本、工作量、执行条件、复核 |
| `f20`–`f25` | 唐映秋 · 农事计划员 | 流程、资料、权限、交接、规则、升级 |
| `f30`–`f35` | 秦芮 · 农业物联工程师 | 系统、数据质量、读写能力、更新、故障兜底 |
| `f40`–`f45` | 傅景 · 农产品质控员 | 红线、权限、验收、留存、转人工、审计 |
| `f50`–`f55` | 叶书 · 基地经营代表 | 口径分歧、统计规则、范围、投诉、反馈闭环 |

**引用纪律**：只引编号，不用角色名代替事实；编号不存在即视为引用错误（由 `src/tools/check_docs.py` 自动校验）。

---

## 快速开始

```powershell
# 1. 重新生成现状流程图
python src\diagram\build_flow_svg.py

# 2. 提交前自检（证据编号越界、图片缺失、SVG 可解析）
python src\tools\check_docs.py
```

环境要求：Python 3.8+，仅用标准库，无需 pip 安装。

---

## 资料状态与后续

| 项 | 状态 |
| --- | --- |
| 业务挖掘（01 阶段） | 已完成，关卡通过 |
| 现场调研（02 阶段） | 已完成，关卡通过 |
| 需求定义及之后（03–09 阶段） | 未开始 |
| 原始业务凭证（单据、日志、制度原文） | 未取得，全部标注为待补 |

后续进入需求定义阶段前，必须先补上四个 P0 事项：用水计量口径与基期、异常核验签核人、三套系统权威源、交接时限与确认载体。

---

## 智能体服务（FastAPI + RAG + 知识图谱 + Harness + 分层权限）

资料包之外，本仓库提供一个**可运行、可公网访问的调研智能体 MVP**：把 36 条访谈事实与调研文档建成可检索知识库，
模型只能基于召回证据作答，返回前统一过 Harness 合规拦截；按管理员 / 注册用户 / 访客分层授权。

### MVP 构成

| 构成 | 实现 |
| --- | --- |
| ① FastAPI | `app/main.py` + `app/api/`，统一 `ok/data/error` 返回结构，`/docs` 可在线试调 |
| ② Harness | `app/harness/`，H2–H8 八条规则加权评分，未通过即阻断并回退证据模板 |
| ③ 知识库：RAG + LLM + Wiki | `app/rag/` 文档切块与召回；`app/llm/` 本地 Ollama / 远程兼容接口 / 模板降级三通道；`app/kg/` 知识图谱提供 Wiki 视角（角色、事实、机会、指标、流程） |
| ④ 分层权限 | `app/auth/`，管理员 admin（SaaS：用户管理、图谱维护、审计）、注册用户 user（问答与生成）、访客 guest（只读浏览 Wiki） |
| ⑤ 在线网址 | 容器化部署，托管平台注入 `PORT` 即可对外访问；见下文「部署上线」 |

### 目录结构（服务侧）

```
planting/
├── app/
│   ├── main.py               # FastAPI 入口，lifespan 加载图谱 / RAG 索引 / 初始化管理员
│   ├── api/
│   │   ├── routes.py         # 知识图谱、关卡生成、Harness 校验路由
│   │   ├── auth_routes.py    # 注册、登录、用户管理、角色调整、审计日志
│   │   └── chat_routes.py    # RAG 检索预览与问答接口
│   ├── core/                 # 配置、统一返回结构、异常、日志
│   ├── kg/                   # 知识图谱（networkx + JSON 持久化）
│   ├── rag/                  # 文档切块、词元打分检索（轻量本地方案）
│   ├── llm/                  # Ollama 客户端 + 统一模型门面（兼容 OpenAI 协议）
│   ├── harness/              # 合规规则与加权评分
│   ├── services/             # 提示词编排、关卡生成、RAG 问答服务
│   ├── auth/                 # 密码哈希、JWT 令牌、用户台账、鉴权依赖
│   └── static/index.html     # 前端单页（Wiki 浏览 / 问答 / 后台管理）
├── config.yaml               # 唯一配置源（模型地址、路径、规则词表、权限、RAG）
├── Dockerfile                # 容器化部署文件
├── .env.example              # 环境变量样例（密钥不入库）
└── scripts/verify.py         # 阶段验证脚本（离线 + --online 在线两组断言）
```

### 本地启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

- 前端页面：<http://127.0.0.1:8000/>
- 接口文档：<http://127.0.0.1:8000/docs>
- 健康检查：<http://127.0.0.1:8000/health>
- 模型名须与 `ollama list` 完全一致；本地无 Ollama 时自动降级模板引擎，服务不中断。

### 账号与权限矩阵

| 角色 | 能力 |
| --- | --- |
| 访客 guest | 浏览 Wiki（角色 / 事实 / 机会 / 指标）、检索预览、查看接口文档；不可问答与生成 |
| 注册用户 user | 访客全部能力 + 发起 RAG 问答、生成关卡答卷 |
| 管理员 admin | 用户全部能力 + 新增事实、用户管理、角色调整、查看审计日志 |

- 首次启动自动初始化管理员：账号取环境变量 `ADMIN_USERNAME`（缺省 `admin`），密码取 `ADMIN_PASSWORD`；
  未配置时使用演示密码 `admin123`，**上线前必须通过环境变量替换**。
- 自助注册受 `config.yaml` 的 `auth.allow_register` 开关控制；注册用户默认为 `user` 角色。

### 主要接口

| 方法 | 路径 | 权限 | 说明 |
| --- | --- | --- | --- |
| GET | `/health` | 公开 | 服务状态、图谱规模、模型通道 |
| GET | `/api/kg/roles` `/api/kg/facts/{id}` `/api/kg/opportunities` `/api/kg/metrics` | 公开 | Wiki 知识查询 |
| GET | `/api/kg/search` `/api/rag/search` | 公开 | 事实 / 文档块检索 |
| POST | `/api/auth/register` `/api/auth/login` | 公开 | 注册 / 登录，返回令牌 |
| GET | `/api/auth/me` | 登录 | 当前用户信息 |
| POST | `/api/chat` | user / admin | RAG 问答（检索 → 生成 → Harness → 兜底） |
| POST | `/api/generate` | user / admin | 生成指定关卡答卷 |
| POST | `/api/harness/check` | 公开 | 文本合规校验 |
| POST | `/api/kg/facts` | admin | 人工确认后新增事实 |
| GET | `/api/admin/users` `/api/admin/audit` | admin | 用户清单 / 审计日志 |
| POST | `/api/admin/users/{username}/role` | admin | 调整用户角色 |

### 配置与环境变量

所有密钥、模型地址只允许出现在 `config.yaml` 或环境变量，禁止硬编码进代码。敏感项优先取环境变量：

| 环境变量 | 作用 |
| --- | --- |
| `JWT_SECRET` | 登录令牌签名密钥，生产必须设置随机长字符串 |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | 初始管理员账号密码（仅首次写入台账） |
| `REMOTE_LLM_ENABLED` / `REMOTE_LLM_BASE_URL` / `OPENAI_API_KEY` / `REMOTE_LLM_MODEL` | 云端远程兼容模型通道 |
| `OLLAMA_ENABLED` / `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | 本地 Ollama 通道覆盖 |

样例见 `.env.example`。

### 部署上线

容器方式：

```bash
docker build -t planting-agent .
docker run -p 8000:8000 --env-file .env planting-agent
```

托管平台（Render / Railway 等）：
1. 推送本仓库后新建服务，构建命令 `pip install -r requirements.txt`，启动命令 `uvicorn app.main:app --host 0.0.0.0 --port ${PORT}`；
2. 在平台环境变量中配置 `JWT_SECRET`、`ADMIN_USERNAME`、`ADMIN_PASSWORD`，按需配置远程模型；
3. 平台分配的公网地址即 MVP 可访问网址；本地无 Ollama 时问答自动走证据模板，不影响服务可用性。

**Render 一键部署（推荐，本仓库已内置 `render.yaml` 蓝图）**：

1. 用 GitHub 账号登录 <https://render.com>，进入 Dashboard → New → **Blueprint**；
2. 授权 Render 访问 `DianaCheng817/DianaCheng`，选择包含 `planting/render.yaml` 的仓库；
3. Render 读取蓝图后自动创建名为 `planting-agent` 的免费 Web 服务（rootDir 为 `planting`）；
4. 在服务的 Environment 页补齐 `ADMIN_USERNAME`、`ADMIN_PASSWORD`（蓝图已自动注入随机 `JWT_SECRET`），按需配置远程模型；
5. 部署完成后，Render 分配形如 `https://planting-agent-xxxx.onrender.com` 的公网地址，即为 MVP 网址；
6. 打开该地址验证：首页 `/`、`/docs`、`/health`、Wiki 浏览、注册登录与问答链路。

**Railway 一键部署（备选，当前网络下 Railway 可达）**：

1. 用 GitHub / Google / 邮箱登录 <https://railway.com>；
2. New Project → **Deploy from GitHub repo** → 授权并选择 `DianaCheng817/DianaCheng`；
3. Railway 识别根目录后，把服务的 Root Directory 设为 `planting`，它会用 `Dockerfile` 自动构建；
4. 在服务的 Variables 页添加 `ADMIN_USERNAME`、`ADMIN_PASSWORD`、`JWT_SECRET`（随机长串）；
5. Settings → Networking → Generate Domain，生成形如 `https://xxx.railway.app` 的公网地址；
6. 打开该地址验证首页、`/docs`、`/health`、Wiki 与问答链路。

> 部署 prerequisite：需要一个 Render / Railway 平台账号并在网页完成 GitHub 授权。
> 账号授权属于平台侧人工操作，脚本无法代劳；未配置平台账号时，本地 `python run.py` 完全可用。
> 免费套餐首次部署有冷启动，首次访问可能等待 30–60 秒。

**正式公网 MVP 网址（永久固定，平台托管，已实测）**：

| 项目 | 内容 |
|---|---|
| 公网首页 | **https://planting-agent-production.up.railway.app/** |
| 接口文档 | https://planting-agent-production.up.railway.app/docs |
| 健康检查 | https://planting-agent-production.up.railway.app/health |
| 托管平台 | Railway（账号 evanlu122817@qq.com / DianaCheng817，项目 `planting-agent`，production 环境） |
| 部署方式 | 连接 GitHub 仓库 `DianaCheng817/DianaCheng` 的 `main` 分支，Root Directory = `planting`，NIXPACKS 构建，自动部署（push 即更新） |
| 实测结果 | 首页 / `/health` / `/docs` / `/openapi.json` 均 HTTP 200；注册→登录→问答（Harness 100 分、证据 f02/f40）→Wiki 溯源 f12→越权拦截，全链路公网实测通过 |
| 首页截图 | `screenshots/mvp-railway-permanent.png` |

> 该地址为平台分配的**永久固定域名**，不依赖本机进程，关机后老师仍可访问；代码 push 到仓库会自动重新部署。
> 关键修复：Railway 注入 `PORT` 环境变量，启动命令必须用 `sh -c 'exec uvicorn ... --port $PORT'` 做 shell 展开（见 `Dockerfile` 与 `scripts/expose_public.bat`）。
> 管理员默认账号：`admin` / `Planting@MVP2026`（密码由环境变量 `ADMIN_PASSWORD` 注入，可随时在 Railway Variables 修改）。

**备用：本地演示临时地址**（无需账号、随时可开）：

> `cloudflared tunnel --url http://127.0.0.1:8000 --protocol http2` 会生成形如
> `https://xxx.trycloudflare.com` 的临时地址，依赖本机服务与隧道进程运行，关机即失效，仅作离线演示兜底；
> 双击 `scripts\expose_public.bat` 可一键启动"本地服务 + 隧道"。**正式访问请用上方 Railway 固定网址。**

### 验证与产出

```powershell
python scripts\verify.py            # 离线验证：配置 / 图谱 / Harness / 关卡 / RAG / 鉴权 / 问答模板
python scripts\verify.py --online   # 在线验证：额外覆盖 HTTP 接口、权限拦截、登录与问答
python scripts\build_docx.py        # 技术方案 md -> docx
python src\tools\check_docs.py      # 原有文档自检（证据编号、图片、SVG）
```

### 设计取舍一句话

不做「更聪明的模型」，做「不会编造的流程」：检索只召回已归档证据，模型输出先过 Harness，
未通过即丢弃并改走证据模板，因此不合规内容永远不会到达调用方。

---

## 免责声明

本项目为 FDE 训练中心的合成训练案例，角色、企业、数字均为虚构。
文档中的一切损失金额、频次、耗时均为**待验证假设**，不得作为对真实客户的价值承诺或验收依据。
