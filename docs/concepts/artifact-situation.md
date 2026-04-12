# 情势工件

> **情势工件**（Situation Artifacts）在 Omen 中承担前置定义层职责：把原始材料转成高质量、可复用的战略问题空间表达。

在 Omen 的资产体系中，Artifacts 与 Ontology 有不同的定义：

- Ontology 结构稳定、内聚性强，负责概念语义与关系建模。
- Artifacts 结构松散、关联性强，负责阶段性产出与流程衔接。

**如何构建**：情势工件由 Omen 情势分析自动生成，由情势案例、情势简报和情势模型三类生成物组成，分别对应不同的工作阶段和使用场景。生成过程勿须或仅需少量人工参与。

## 设计哲学

**情境**（Situation）是 Omen 诞生起就定义的核心概念，代表一个特定的现象及其演化，Omen 用其建模战略问题空间。

情势工件的设计完美匹配 Omen **人类决策优先**的设计哲学：机器负责把复杂现实信息压缩为可审计的简报，人类负责对意义、价值与行动方向做最终裁决。

## 核心价值

情势工件的生成贯穿“事件源收集 -> 案例研究 -> 战略分析 -> 机器输入对象”全流程：

- **战略方法融合**：把战略分析中的关键问题、约束、目标与未知统一为稳定字段，避免只停留在叙事摘要。
- **情势简报可读性**：问题定义层直接产出 Situation Brief，供战略决策者阅读和审计，避免只有机器可消费对象而“空跑”。
- **标准输入层**：把非结构化文档转成结构化资产，支持复用、版本化管理和跨团队协作。
- **前置信息资产**：为后续战略流程提供清晰边界与一致语义，降低下游重复解释成本。
- **启发式增强**：通过“未知识别 + 假说补全 + 稳定识别”提升一致性，减少随机漂移。

从而把原始材料转换为可阅读、可审计和可计算的战略资产。

## 工件体系

情势工件包含三个生成物，按顺序衔接：

1. 情势案例（Situation Case）
2. 情势简报（Situation Brief）
3. 情势模型（Situation Model）

### 情势案例

质量标准：高保真还原。

情势案例来自事件源（文档、URL）输入后的高保真案例整理，目标是保留事实叙事、语气风格与上下文完整性。

它回答：原始材料里“发生了什么”。

### 情势简报

质量标准：人类可读、可审计。

情势简报从情势案例提炼战略问题定义，面向决策者审阅，强调可读和可审计。

它回答：当前“要解决什么战略问题”。

### 情势模型

质量标准：机器可读、可计算。

情势模型在情势简报基础上完成结构化增强，形成系统可消费的标准 JSON，对接后续流程。

它回答：当前“系统基于哪些结构化情势对象继续工作”。

## 模型架构

情势模型由三部分组成：

1. `context`：问题上下文
2. `uncertainty_space`：不确定性空间
3. `source_meta` / `source_trace`：信息溯源

### 问题上下文

`context` 用来结构化描述“当前要解决的战略问题是什么”。典型字段包括：

- `title`
- `core_question`
- `current_state`
- `core_dilemma`
- `key_decision_point`
- `target_outcomes`
- `hard_constraints`
- `known_unknowns`

这一部分与 Situation Brief 的核心内容保持一致：

- 对人：可直接阅读、讨论、审计。
- 对系统：提供稳定的问题边界与语义上下文。

### 不确定性空间

`uncertainty_space` 用来描述“哪些未知仍在影响判断，以及当前分析可用性如何”。常见字段包括：

- `overall_confidence`
- `confidence_risk`
- `confidence_overall`
- `assumptions_explicit`
- `high_leverage_unknowns`
- `metrics`

这一部分让情势分析不只给一个分数，而是给出“为什么是这个分数”的结构化依据。

### 信息溯源

`source_meta` 与 `source_trace` 提供模型版本信息与生成过程 `hash-linked` 追溯，例如：

- `source_path`
- `generated_at`
- `pack_id`
- `pack_version`
- `actor_ref`

其中，`actor_ref` 关联到战略行动者本体（Strategic Actor Ontology），让情势分析与战略主体之间形成互动和闭环。

#### 示例片段

Omen 在分析过程中自动将 `sap` 案例与主体关联：

```
"actor_ref": "../output/actors/sap/actor_ontology.json"
```

这一部分保证情势分析的结果是真正可关联、可追踪、可复核的模型，而不是一份机器打印出的、散乱的日志行。

## 启发式建模

Omen 在情势工件构建中广泛采用启发式（heuristics）建模思想：让每个结构化概念都对应一组稳定化动作，从而降低与大语言模型（LLM）交互中的随机性和不确定性。

### 已知的未知

Omen 将 `known_unknowns` 定义为“已经识别到、但尚未被证据充分解释”的关键空白。

关键能力：在情势分析阶段优先提炼关键未知，避免认知空白被叙事文本掩盖。

战略价值：

- 明确哪些问题仍待验证。
- 区分事实、判断和假设。
- 给后续验证活动提供清晰边界。

#### 示例片段

摘自 SAP 收购 Reltio 的[情势模型](../../sample/data/scenarios/sap/situation.json)：

```json
"known_unknowns": [
  "Whether the move will successfully boost adoption of SAP's Business Data Cloud",
  "How customers will respond to SAP's sales messaging given the negative migration findings",
  "The timeline for integrating Reltio's capabilities into SAP's AI platform"
]
```

### 假说补全

Omen 将 `assumptions_explicit` 定义为针对关键未知给出的可检验假说。

关键能力：在情势增强阶段使用 LLM 生成未知项对应假说，并结合覆盖度与质量信号更新置信度表达。

战略价值：

- 从风险感知推进到可验证状态。
- 让置信度提升具备结构化依据。

#### 示例片段

摘自 SAP 收购 Reltio 的[情势模型](../../sample/data/scenarios/sap/situation.json)：

```json
"assumptions_explicit": [
  {
    "target_unknown": "Whether the move will successfully boost adoption of SAP's Business Data Cloud",
    "assumption_text": "The acquisition ... is a necessary but not sufficient condition for overcoming BDC's adoption barriers.",
    "quality_score": 0.8,
    "coverage_type": "partial"
  }
]
```

### 战略主体识别

在将情势分析关联到 `StrategicActor` 时，Omen 采用启发式评分来稳定候选识别算法，避免反复向大模型提问“谁是 StrategicActor”导致答案漂移。

战略价值：

- 同输入下识别结果更稳定。
- 降低模型随机性导致的角色幻觉。
- 为后续主体建模建立一致起点。

#### 代码片段

```python
if actor_type == "strategicactor":
  score += 100
if "founder/ceo/top_management" in role:
  score += 60
if "founder/ceo/strategic" in actor_id:
  score += 40
```

## 文档边界

本文档只说明情势工件（Situation Artifacts）的概念与设计，未展开以下内容：

- 情景规划
- 推理链路
- 流程执行逻辑

### 参考样例
- [情势案例：SAP 收购 Reltio](../../cases/situations/sap_reltio_acquisition.md)
- [情势简报：SAP 收购 Reltio](../../sample/data/scenarios/sap/situation.md)
- [情势模型：SAP 收购 Reltio](../../sample/data/scenarios/sap/situation.json)

## 相关文档

- [设计哲学](../philosophy.md)
- [战略主体](../concepts/strategic-actor.md)