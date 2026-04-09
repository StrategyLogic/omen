# 战略主体

> **战略主体**（Strategic Actor）是 Omen 的核心抽象，用于描述并分析复杂战略博弈中的关键行动者。
  
Omen 提供可校验、可重复运行的自动化流程，能够从非结构化案例资料（人物、组织、历史事件等）中提取结构化战略主体，并输出图谱、时间线和画像结果，支持后续推演与复核。

## 核心价值

- **本体建模**：将人物、组织、事件映射到统一战略行动者语义层与本体，降低后续推演建模成本。
- **标准输入层**：把文本输入转化为结构化模型与状态快照，便于版本管理、回放和比较。
- **数据源**：战略主体产物直接作为图谱、时间线、画像和校验流程的统一数据源。
- **工程化**：全流程可本地运行、可重复执行，并提供确定性校验结果用于自动化门禁。

## 本体结构

`actor_ontology` 是战略主体的本体模型。它围绕核心的行动者承载“谁参与、发生了什么、彼此如何影响”，核心架构：

- `actors[]` 每个元素代表一个参与者，分为两类：`Actor`（参与者）和 `StrategicActor`（行动者）。
- `products[]` 定义了相关的产品或技术资产，如 `product`、`platform`、`tool` 等。
- `influences[]` 定义了参与者基于事件之间的关系，如 `builds`、`competes_with`、`participates_in`、`affects` 等。
- `events[]` 记录了案例中的事实事件。

### 设计优势

- 分层清晰：参与者、关系、事件三层可分别演化。
- 事实与语义解耦：事实层可追溯，语义层可推理。
- 面向工程落地：字段稳定，便于校验、回放、可视化。

## 关键概念

### 参与者

`Actor` 表示参与者，构成了战略互动网络中的角色。位于 `actor_ontology.actors[]`，通过 `type: Actor` 区分，例如客户、团队、潜在用户等。

`Actor` 字段：

- `id`：参与者唯一标识
- `name`：参与者名称
- `role`：参与者角色（如 customer/team）
- `profile`：兴趣、影响力、对战略行动者的对齐程度等

**示例片段**

```json
{
  "id": "actor-customer-pilot",
  "name": "10-person pilot team customer",
  "type": "Actor",
  "role": "customer",
  "profile": {
    "interest": "Improve R&D team standard, discover root causes, establish performance quantification standards.",
    "influence_level": "Medium (provided validation feedback)",
    "alignment_with_strategic_actor": "High (appreciated data-driven insights over subjective experience)"
  }
}
```

### 行动者

`StrategicActor` 是战略互动网络中的核心战略主体，位于 `actor_ontology.actors[]` 中，通过 `type: StrategicActor` 区分。

通过结构化 `profile` 深入描述行动者的背景、决策风格、价值主张和不可妥协约束等信息，这部分反映了“战略行动者是谁、如何决策、坚持什么”。

`profile` 字段：

- `background_facts`：背景事实（经历、轨迹、关键经验）
- `strategic_style.decision_style`：决策风格
- `strategic_style.value_proposition`：价值主张
- `strategic_style.decision_preferences`：决策偏好
- `strategic_style.non_negotiables`：不可妥协约束

**示例片段**

```json
{
  "id": "actor-founder-1",
  "name": "Chen Jiaxing",
  "type": "StrategicActor",
  "role": "founder",
  "profile": {
    "background_facts": {
      "key_experiences": [
        "1.5 years of exploration, development, and validation before launch"
      ]
    },
    "strategic_style": {
      "decision_style": "Data-driven, feedback-oriented",
      "value_proposition": "Replace process-driven tools with data-driven insights to achieve effective R&D management without disrupting developer focus.",
      "decision_preferences": [
        "Free community version to drive adoption",
        "Focus on product and technology, avoid distractions from non-product opinions",
        "Use own product for internal management"
      ],
      "non_negotiables": [
        "No manual task status updates required from developers",
        "No reliance on maturity models or industry standards for evaluation",
        "No process gates that sacrifice speed"
      ]
    }
  }
}
```

### 影响关系层

`influences[]` 描述“主体-主体/主体-事件/事件-产品”之间的关系，是图谱渲染与关系推断的输入层。

字段：

- `source` / `target`：关系起点与终点
- `type`：关系类型（如 `builds`、`competes_with`、`participates_in`、`affects`）
- `description`：关系解释

**示例片段**

```json
[
  {
    "source": "actor-founder-1",
    "target": "product-x-developer",
    "type": "builds",
    "description": "Founder/lead actor builds and steers the core product asset."
  },
  {
    "source": "competitor-process-tools",
    "target": "actor-founder-1",
    "type": "influences",
    "description": "Competitor market presence influences founder strategic decisions."
  },
  {
    "source": "product-x-developer",
    "target": "competitor-process-tools",
    "type": "competes_with",
    "description": "Core product competes with traditional solutions."
  },
  {
    "source": "chen-jiaxing-1",
    "target": "product-x-developer",
    "type": "affects",
    "description": "Strategic decision affects the core product lifecycle."
  }
]
```

### 事件层

`events[]` 是案例中的事实事件序列，强调“可回溯事实”。

字段：

- `id` / `name` / `type`：事件标识、名称和类型（如 `launch`、`pivot`、`funding_round`）
- `date`：事件发生时间（格式 `YYYY-MM`）
- `description`：事件描述
- `actors_involved[]`：事件的参与者列表
- `evidence_refs[]`：事件描述中引用的原始证据（文章、演讲、访谈等）
- `is_strategy_related`：是否与战略相关

**示例片段**

```json
{
  "id": "chen-jiaxing-1",
  "name": "X-Developer Platform Launch",
  "type": "launch",
  "date": "2019-10",
  "description": "X-Developer platform launched after 1.5 years of exploration, development, and validation; free community version offered to help companies get started quickly.",
  "actors_involved": ["actor-founder-1"],
  "evidence_refs": [
    "# 从流程驱动到数据驱动,打造你的高效研发团队",
    "2019年10月24日",
    "经过一年半的探索、开发与验证,我们推出了一款研发效能分析与改进的平台:X-Developer,并提供了免费的社区版帮助企业快速起步。"
  ],
  "is_strategy_related": true
}
```

### 与 Strategy.events 的差异

`actor_ontology` 与 `strategy_ontology` 中都存在事件概念，但侧重点不同：

- `actor_ontology.events`：围绕 `StrategicActor` 的事实层事件。偏“案例记录”，包含时间、证据、参与方，用于时间线与状态快照。
- `strategy_ontology`：侧重“战略建模”的事件概念，偏“语义层事件”。通常存在于概念层/关系层（如 `PlatformLaunch`、`TeamAdoption`），用于表达机制与推理关系。

可以理解为：前者回答“发生了什么”，后者回答“为什么这类事件在战略上有意义”。

**示例片段**

```json
// strategy_ontology.json
"events": [
	{
		"name": "PlatformLaunch",
		"description": "Event of launching a platform after exploration and validation.",
		"category": "launch",
		"confidence": 1.0
	}
]
```

## 战略画像

战略画像是对 `StrategicActor` 的深度分析结果，对“决策风格-事件证据-战略行为”的综合归纳，用于：

- 对外展示：快速说明该主体的战略人格
- 内部复核：检查叙事与证据是否一致
- 后续推演：作为上层解释与模拟的输入线索

输出文件为 `analyze_persona.json`，核心架构 `persona_insight` 说明：

- `narrative`：行动者画像叙事
- `key_traits[]`：关键特质与证据摘要
- `consistency_score`：画像一致性评分 $[0,1]$

**示例片段**

```json
{
  "persona_insight": {
    "narrative": "Chen Jiaxing emerges as a pragmatic, product-centric innovator whose strategic profile is defined by a deep-seated belief in empirical validation and developer-centric efficiency. The foundational 1.5-year period of exploration, development, and validation before launch is not merely a background fact but a core expression of his data-driven and feedback-oriented decision style...",
    "key_traits": [
      {
        "trait": "Empirically-Driven Innovator",
        "evidence_summary": "Invested 1.5 years in exploration and validation before launch, ensuring the product is rooted in data and real feedback, not assumptions."
      },
      {
        "trait": "Developer-Centric Pragmatist",
        "evidence_summary": "Non-negotiables explicitly forbid manual status updates and process gates that sacrifice speed, protecting developer focus as a core tenet."
      },
      {
        "trait": "Product-Led Strategist",
        "evidence_summary": "Decision preferences emphasize focusing on product/tech and using their own product internally; launch strategy uses a free version to drive organic adoption."
      }
    ],
    "consistency_score": 0.95
  }
}
```

## 战略状态快照

战略状态快照是某一时刻的事实层数据，生成物是 `analyze_status.json`，包含事件清单和关系描述，用于时间线和图谱的可视化展示。

核心结构：

- `timeline[]`：事件时间线，每个事件包含 `time`、`name`、`event`、`description`、`evidence`、`strategic` 等字段
- `actor_graph`：图谱节点和边，包含 `nodes[]` 和 `edges[]`

**示例片段**

```json
{
  "timeline": [
    {
      "id": "chen-jiaxing-1",
      "time": "2019-10",
      "name": "X-Developer Platform Launch",
      "event": "launch",
      "description": "X-Developer platform launched after 1.5 years of exploration, development, and validation; free community version offered...",
      "strategic": true
    }
  ],
  "actor_graph": {
    "nodes": [
      {
        "id": "actor-founder-1",
        "label": "Chen Jiaxing",
        "node_type": "strategic_actor",
        "role": "founder"
      },
      {
        "id": "product-x-developer",
        "label": "X-Developer",
        "node_type": "product"
      }
    ],
    "edges": [
      {
        "source": "actor-founder-1",
        "target": "product-x-developer",
        "label": "builds",
        "weight": 1.0
      }
    ]
  },
  "summary": {
    "timeline_event_count": 3,
    "actor_node_count": 9,
    "actor_edge_count": 12
  }
}
```

## 内置案例

仓库内置案例（`cases/actors/`）：

| 案例文件 | 说明 |
|----------|------|
| `chen-jiaxing.md` | X-Developer 创始人，数据驱动研发效能平台 |
| `elon-musk.md` | 特斯拉/SpaceX 创始人，多产业颠覆者 |
| `jack-ma.md` | 阿里巴巴创始人，电商生态构建者 |
| `jeff-bezos.md` | 亚马逊创始人，长期主义与飞轮效应 |
| `shenda.md` | 盛大集团创始人，多元化经营与平台转型案例 |
| `steve-jobs.md` | 苹果创始人，产品哲学与创新驱动 |

### 如何使用

> 如果你尚未安装 Omen，请先阅读[快速指南（LLM）](../quick-start-llm.md)，完成环境配置和模型接入。

**首次使用**：运行 CLI 生成一个简单案例：

```bash
omen analyze actor --doc chen-jiaxing
```

**检查输出**：查看生成的文件

```bash
ls output/actors/chen-jiaxing/
```

**启动 UI**：交互式探索图谱和时间线

```bash
streamlit run app/strategic_actor.py
```

**尝试其他案例**：如 `elon-musk` 或 `steve-jobs`

---

## 进阶指南

- [构建战略主体](../guides/build-strategic-actor.md)：从零开始构建自定义的战略行动者。