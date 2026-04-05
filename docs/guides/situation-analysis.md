# Situation Analysis 使用指南（重点：`--url`）

本指南面向使用者，介绍如何通过 `omen analyze situation --url` 把一篇网页报道快速转换为：

1. 可归档复用的 Situation Case（结构化原始材料）
2. 可继续推演的 Situation Artifact（JSON）
3. 面向阅读的 Strategic Situation Brief（Markdown）

下文使用你提供的样本 URL：

- `https://www.theregister.com/2026/03/30/sap_reltio/`

---

## 1. 什么时候用 `--url`

当你的输入是在线报道、新闻分析、博客文章时，`--url` 最省事。

你不需要先手工写 `cases/situations/*.md`，命令会自动完成：

- 抓取网页正文文本
- 保存原始文本到 `data/ingest/source/`
- 生成结构化 Case 到 `cases/situations/`
- 继续执行 situation analyze 流程，输出 JSON + Brief 到 `data/scenarios/<pack_id>/`

---

## 2. 一键分析命令

```bash
omen analyze situation --url "https://www.theregister.com/2026/03/30/sap_reltio/"
```

如果不显式指定 `--pack-id`，系统会按 case 名推导默认包名。

本样本实际生成在：

- `cases/situations/sap_reltio_acquisition.md`
- `data/scenarios/sap_v1/sap_reltio_acquisition_situation.json`
- `data/scenarios/sap_v1/sap_reltio_acquisition_situation.md`
- `data/scenarios/sap_v1/sap_reltio_acquisition_generation.json`

---

## 3. 你会得到什么

### 3.1 Case（归档材料）

`cases/situations/sap_reltio_acquisition.md` 是“结构化存档”，重点是保留来源事实，不直接做策略结论。

你可以看到它包含：

- The Story
- Core Facts
- Existing Data and Research Findings
- Direct Quotes
- Difficulties, Risks & Controversies
- Unknowns / Open Questions

样本摘录（来自已生成 case）：

> SAP is to acquire master data management and data integration specialist Reltio.

> Research from DSAG in December found that 83 percent of its members were only slightly familiar with BDC or not familiar with it at all.

这类 case 适合作为团队后续复盘、评审、再建模的输入基线。

### 3.2 Situation Artifact（机器可读）

`data/scenarios/sap_v1/sap_reltio_acquisition_situation.json` 是后续场景分解与模拟的输入。

关键字段：

- `context`: 当前局面、核心问题、决策点、约束、已知未知
- `signals`: 结构化信号
- `uncertainty_space`: 不确定性与置信度
- `source_meta` / `source_trace`: 来源追踪

样本里你可以直接看到：

- `pack_id: "sap_v1"`
- `confidence_risk: 0.55`
- `known_unknowns` 聚焦在“能否提升 BDC 采纳”“客户对战略转向反应”等问题

### 3.3 Strategic Situation Brief（人可读）

`data/scenarios/sap_v1/sap_reltio_acquisition_situation.md` 适合直接给业务方或项目组讨论。

样本摘录（来自已生成 brief）：

> SAP is acquiring Reltio to pivot its Business Data Cloud (BDC) strategy from sharing SAP data externally to also ingesting and harmonizing non-SAP data for its AI platform.

> The risk confidence score ($C_{risk}$) of 0.55 indicates the strategy is not ready for a full-scale commitment.

这说明 Brief 会把事实汇总成“当前状态 -> 决策问题 -> 风险置信度”的决策阅读格式。

---

## 4. 与 `--doc` 的关系

- `--url`: 适合“在线内容即输入”，自动抓取并自动生成 case
- `--doc`: 适合“你已经准备好本地 case 文档”

二者互斥，不要同时传。

---

## 5. 下一步：从 Situation 到 Scenario

拿到 situation artifact 后，执行场景分解：

```bash
omen scenario --situation data/scenarios/sap_v1/sap_reltio_acquisition_situation.json
```

随后可继续：

```bash
omen simulate --scenario data/scenarios/sap_v1/sap_reltio_acquisition.json
```

这样你就完成了从“网页信息”到“可模拟场景”的完整链路。

---

## 6. 常见问题

### Q1：`--url` 失败怎么办？

先检查：

- URL 是否可公开访问
- 页面是否有可提取正文（而非纯脚本渲染空壳）
- 网络与超时环境

### Q2：为什么我得到的 case 看起来“很保守”？

这是设计目标。case 阶段是“结构化存档”，不是“策略结论”，重点是忠实保留来源证据与不确定项。

### Q3：如何复用已有产物？

- 人读 brief：直接看 `*_situation.md`
- 机器流程：使用 `*_situation.json` 继续 `omen scenario` / `omen simulate`
- 审计追踪：查看 `*_generation.json`
