# 开源合规与许可证检测 —— 扫描原始产物

本目录存放《开源合规与许可证检测分析报告》（上一级目录的同名 docx）所使用的原始扫描结果，供复核使用。

## 扫描对象

Apache Commons Lang（Apache-2.0），通过 git 克隆官方仓库后使用 **ScanCode Toolkit** 全量扫描。第三方源码本身（约 10.3MB、846 个文件）**不上传到本仓库**，需要复现时执行：

```bash
git clone https://github.com/apache/commons-lang.git
scancode -clpieu --json-pp scan-report.json commons-lang
```

## 文件说明

| 文件 | 说明 |
| --- | --- |
| `scan-report.html` | 扫描结果的可视化报告，浏览器直接打开即可查看（含许可证分布图表、文件级明细） |
| `scan-report.json` | ScanCode 完整 JSON 输出，包含每个文件的许可证判定、版权信息、匹配规则与匹配分数（约 1.2MB） |
| `scan-report_files/` | HTML 报告依赖的前端静态资源（Bootstrap、D3、DataTables、Chart.js 等及其许可证文件） |
| `preview_check.pdf` | 报告渲染效果校验（第 1 次） |
| `preview_check2.pdf` | 报告渲染效果校验（第 2 次） |
| `preview_check3.pdf` | 报告渲染效果校验（第 3 次，最终版） |

## 结论摘要

扫描共覆盖 **781** 个文件，许可证判定分布如下：

| 判定结果 | 文件数 | 占比 |
| --- | --- | --- |
| `apache-2.0` | 695 | 89.0% |
| 未检出许可证声明 | 83 | 10.6% |
| `apache-2.0 AND (generic-cla AND apache-2.0)` | 2 | 0.3% |
| `apache-2.0 AND apache-1.1` | 1 | 0.1% |

主体为 Apache-2.0，另有 1 个文件同时含 apache-1.1 声明、2 个文件含 generic-cla 声明；未检出 GPL/AGPL 等强传染性许可证。详细分析见上一级目录的作业报告。
