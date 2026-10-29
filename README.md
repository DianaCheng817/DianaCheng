# DianaCheng

成御萌（学号 f25011102）的课程作业与练习仓库，收录开源微专业课程作业、模型调用实验、算子实现以及个人简历网页。

## 目录结构

| 目录 / 文件 | 内容说明 |
| --- | --- |
| `成御萌的简历.html` | 个人简历网页（HTML + CSS 手写，单文件可离线打开） |
| `0915课程作业网页.html` | 课程作业网页（HTML 基础练习） |
| `0922_ollama/` | 本地大模型 Ollama 实验：模型下载与调用记录、不同调用方式的对比、外部工具（外挂）接入思路，含 `call_ollama_demo.py` 示例 |
| `0929_假期作业_小龙虾/` | 假期作业：一个可运行的 Agent 小项目，包含 `main.py`、`main_bailian.py`（百炼版）、`agent.md`、`skill.md` 与依赖清单 |
| `0929_百炼智能体/` | 阿里云百炼平台智能体作业：FlowAgent 创建指南、智能体设计思想分析（基于 ai-agent-book）、`streamlit_app` 演示界面与调用校验脚本 |
| `周四第二次作业/` | Gelu 算子实现：`gelu_kernel.cpp` 手写 kernel + `verify_gelu.py` 数值校验 |
| `周四第三次作业/` | 开源合规与许可证检测分析报告（Word 文档）及其扫描原始产物 |
| `周四第三次作业/扫描工作/` | ScanCode 扫描 Apache commons-lang 生成的完整报告：`scan-report.html`、`scan-report.json`、前端资源目录与校验 PDF |

## 技术栈

- Python（Ollama / 百炼 API 调用、Streamlit 界面、NumPy 数值校验）
- C++（算子 kernel 实现）
- HTML / CSS（简历与作业网页）

## 运行说明

各子目录均为独立作业，具体运行方式见目录内各自的 `README.md` 或 `提交内容.txt`。Python 项目一般执行：

```bash
pip install -r requirements.txt
python main.py
```

## 作者

成御萌 · f25011102
