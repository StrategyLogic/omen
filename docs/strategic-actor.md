# Strategic Actor（战略行动者）

## 概述

**Strategic Actor（战略行动者）**是 Omen 的核心抽象，用于描述并分析复杂战略博弈中的关键主体。

在开源版本中，Strategic Actor 能把非结构化案例资料（人物、组织、历史事件等）转成结构化产物，并提供可校验、可视化、可复现的分析流程。

## 核心价值

- 从文本到结构化：将案例文档转为本体与时间线数据。
- 可校验：对产物进行确定性校验，输出明确 `pass/fail` 与字段级错误。
- 可视化：基于本地产物渲染图谱与时间线，便于人工复核。

## 术语说明

- `Strategic Actor`：产品与文档中使用的概念名（战略行动者）。
- `actor`：CLI 和文件契约中的技术标识。

## 输入文档如何准备

### 1) 放置目录

将案例文档放到：`cases/actors/`

示例：`cases/actors/elon-musk.md`

### 2) 文档建议结构

建议包含以下内容（不强制模板）：

- 主体背景：身份、角色、关键阶段
- 关键事件：按时间列出里程碑/决策事件
- 外部环境：市场、竞争、政策、技术等约束
- 结果线索：阶段性结果与可观察证据

### 3) 命名建议

- 文件名建议使用小写-kebab 形式，例如：`jack-ma.md`。
- `--doc jack-ma` 会解析到 `cases/actors/jack-ma.md`。

## 运行方式

### 环境准备

```bash
cp config/llm.example.toml config/llm.toml
# 编辑 config/llm.toml，填入你的模型配置
```

### 基础分析

```bash
# 分析 cases/actors/elon-musk.md
omen analyze actor --doc elon-musk
```

### 常用参数

- `--output-dir`：输出目录，默认 `output/actors`
- `--year` / `--date`：状态快照时间点（用于历史时点分析）

### 产物校验

```bash
omen validate actor --doc elon-musk
```

## 生成物说明（Artifacts）

分析完成后，会在 `output/actors/<actor_id>/` 下生成：

- `strategy_ontology.json`
	- 战略上下文与结构化语义主文件。
- `actor_ontology.json`
	- 行动者本体数据（角色、事件、查询骨架等）。
- `analyze_status.json`
	- 状态快照，包含时间线与图谱数据。
- `analyze_persona.json`
	- 人物画像分析结果（叙事、关键特质等）。
- `generation.json`
	- 本次生成元数据与校验信息（是否复用、校验问题等）。

## 指标说明

### A. 状态快照指标（`analyze_status.json -> summary`）

- `timeline_event_count`：时间线事件数量
- `strategic_event_count`：战略相关事件数量
- `actor_node_count`：图谱节点数量
- `actor_edge_count`：图谱边数量

这些指标用于快速判断案例信息密度、图谱连通规模与可解释材料是否充分。

### B. 人物画像指标（`analyze_persona.json -> persona_insight`）

- `narrative`：人物画像叙事文本
- `key_traits[]`：关键特质列表（含证据摘要）
- `consistency_score`：画像一致性评分（范围 $[0,1]$）

### C. 校验指标（`omen validate actor` 输出）

- `status`：`pass` 或 `fail`
- `errors[]`：字段级错误明细
- `warnings[]`：非阻断告警
- `target_artifact` / `schema_version`：目标文件与版本信息

## 当前能力边界

Strategic Actor 当前聚焦于本地可复现的输入与分析闭环：

- 本体生成
- 状态快照
- 人物画像
- 图谱/时间线可视化
- 结构化校验

如需深层因果解释或更复杂推演，请在此基础上接入更高层流程。
