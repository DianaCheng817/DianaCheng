# src 说明

这里是文档的「可复现部分」：原始导出、结构化数据、渲染脚本与自检脚本。
`docs/` 里所有图表和数字都从这里来，改数据 → 重跑脚本 → 文档图自动更新。

```
src/
├── raw/                      导出报告原件（不改动，作为溯源）
│   ├── 种植灌溉与农事记录-业务挖掘报告.md
│   └── 种植灌溉与农事记录-现场调研报告.md
├── data/
│   └── process-model.json    现状流程模型：6 个主流程节点 + 5 条异常路径 + 4 个瓶颈 + 5 类人工判断
├── diagram/
│   └── build_flow_svg.py     读取 process-model.json，渲染 docs/assets/current-state-flow.svg
└── tools/
    └── check_docs.py         文档自检：证据编号是否越界、图片是否缺失、SVG 是否可解析
```

## 常用命令

```powershell
# 生成 / 更新现状流程图
python src\diagram\build_flow_svg.py

# 提交前自检（证据编号、图片引用、SVG 格式）
python src\tools\check_docs.py
```

## 为什么 raw 不做改动

两份导出报告是平台生成的原始记录（含学员填写内容、评分与标准参考答案）。
文档里引用的事实编号（`f00`–`f55`）都以它为出处，因此保留原件、不在原件上编辑，
修订只发生在 `docs/`。这样任何一条结论都能回溯到原始记录。

## 数据文件的字段约定

`process-model.json`：

| 字段 | 含义 |
| --- | --- |
| `mainFlow[]` | 主流程节点：`id`、`lane`（岗位泳道）、`fields`（输入/动作/输出/系统）、`refs`（证据编号） |
| `exceptions[]` | 异常路径：`from`（挂在哪个主流程节点）、`fields`（触发/动作/接手/留痕）、`refs` |
| `humanJudgements[]` | 只能由人完成的判断，格式 `[编号, 判断, 说明]` |
| `bottlenecks[]` | 瓶颈：`owner`（责任人）、`status`（基线状态）、`refs` |
