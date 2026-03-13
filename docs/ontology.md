# Strategy Ontology 指南

> 本文档说明 Omen Strategy Ontology 设计理念、案例化建模方式，以及如何在推演流程中运行与验证。

战略本体论（Strategy Ontology）是 Omen 场景输入的核心组成部分。它定义了战略推演中的概念体系、关系网络和规则逻辑，是把“设定战场”这一步标准化的关键工具。

## 关键问题

在战略推演中，最常见的问题不是“算不出来”，而是“输入不清晰”：

- 概念口径不一致（同一个词在不同团队含义不同）
- 关系命名不语义化（难以追踪因果）
- 规则无法审计（解释只能停留在叙事层）

Strategy Ontology 的目标是把“设定战场”这一步标准化：先定义清楚**谁在竞争（Strategic Actor）**、**按什么机制竞争（Game）**、**什么条件触发变化（Rules）**，再进入模拟执行。

## 设计原则

Omen Strategy Ontology 并非一个通用的本体平台，而是**案例驱动**的战场定义规范。它的设计原则包括：

1. **基础定义**  
   战略核心概念（如 `Actor`、`Game`、`Capability`）作为基础抽象层明确定义，覆盖战略推理的核心需求。

2. **概念层次**  
   基于理论演化对战略核心概念进行继承关系定义，如经典战略理论中的 `Competition` 归类为博弈论中的 `game` 并定义为“静态博弈”，便于区分“对象”与“博弈机制”之间不同的抽象层次，以及与“动态博弈”的差异。

3. **谓词关系优先**
   关系名使用语义谓词（如 `has_capability`、`competes_with`），避免对象建模中常见的组合名词型（如 `actor_capability`）命名。

4. **案例继承与扩展**
   每个案例可以自定义概念、关系和规则，并根据需要进行扩展，形成独立的本体输入，但必须遵守基础定义的语义约束。

5. **可解释与可审计**
   解释输出必须可追踪到规则引用（`applied_axioms`、`rule_trace_references`）。

### 架构分层

Strategy Ontology Schema 包含 TBox/ABox + 推理配置：

- `meta`：版本与案例标识（`version`、`case_id`、`domain`）
- `tbox`：概念、关系、公理
- `abox`：案例实例（actors、capabilities、constraints、events）
- `reasoning_profile`：激活/传播/反事实规则引用
- `case_package`：用于声明可复用案例包（manifest、运行能力声明、必需工件）。

## 战略本体案例

[Ontology之战](cases/ontology.md)：`data/scenarios/ontology.json`

[向量 vs. 记忆](cases/vector-memory.md)：`data/scenarios/vector-memory.json`

### TBox 概念体系

```json
"tbox": {
  "concepts": [
    {
      "name": "DatabaseActor",
      "description": "传统数据库战略主体",
      "category": "actor"
    },
    {
      "name": "Competition",
      "description": "静态竞争关系",
      "category": "game"
    }
  ],
  "relations": [
    {
      "name": "has_capability",
      "source": "DatabaseActor",
      "target": "semantic",
      "description": "主体具备能力"
    }
  ],
  "axioms": [
    {
      "id": "AX-activation-overlap",
      "statement": "high overlap can activate competition",
      "type": "activation"
    },
    {
      "id": "AX-propagation-migration-friction",
      "statement": "migration friction suppresses replacement velocity",
      "type": "propagation"
    },
    {
      "id": "AX-counterfactual-budget-shock",
      "statement": "budget shock shifts actor capability window",
      "type": "counterfactual"
    }
  ]
}
```

### ABox 实例断言

```json
"abox": {
  "actors": [
    {
      "actor_id": "traditional-db",
      "actor_type": "DatabaseActor"
    }
  ],
  "capabilities": [
    {
      "actor_id": "traditional-db",
      "name": "semantic",
      "score": 0.42
    }
  ],
  "constraints": [
    {
      "name": "user_overlap_threshold",
      "value": 0.22
    }
  ]
}
```

### 推理规则

```json
"reasoning_profile": {
  "activation_rules": [{"rule_id": "AX-activation-overlap"}],
  "propagation_rules": [{"rule_id": "AX-propagation-migration-friction"}],
  "counterfactual_rules": [{"rule_id": "AX-counterfactual-budget-shock"}]
}
```

> 说明：`reasoning_profile` 中的 `rule_id` 必须在 `tbox.axioms.id` 中声明。


## 运行推演工作流

### 步骤 1：运行基线模拟

```bash
omen simulate --scenario data/scenarios/ontology.json
```

输出：`output/result.json`

验证点：

- 存在 `ontology_setup`
- `ontology_setup.meta.case_id == "ontology-battlefield"`

### 步骤 2：运行反事实对比

```bash
omen compare --scenario data/scenarios/ontology.json --overrides '{"user_overlap_threshold": 0.9}'
```

输出：`output/comparison.json`

验证点：

- `conditions[*].semantic_type` 存在
- `conditions[*].category` 存在

### 步骤 3：生成解释报告

```bash
omen explain --input output/result.json
```

输出：`output/explanation.json`

验证点：

- `applied_axioms` 存在
- `rule_trace_references` 存在

### 步骤 4：执行回归测试

```bash
python -m pytest -q
```

预期：全部测试通过。

## 🧩 开发说明

### 本体输入

`data/scenarios/ontology.json` 已内嵌本体定义（`meta`/`tbox`/`abox`/`reasoning_profile`），可直接使用：

```bash
omen simulate --scenario data/scenarios/ontology.json
omen compare --scenario data/scenarios/ontology.json --overrides '{"user_overlap_threshold": 0.9}'
```

启用后，输出会包含：

- compare 的语义条件对象（例如 `semantic_type`、`category`）
- explain 的规则追踪引用（例如 `rule_trace_references`）

### 本体复用

你也可以直接复用同一工作流运行[第二个案例](cases/vector-memory.md)：

```bash
omen simulate --scenario data/scenarios/vector-memory.json
omen explain --input output/result.json
omen compare --scenario data/scenarios/vector-memory.json --overrides '{"user_overlap_threshold": 0.85}'
```

预期输出仍保持一致：

- `output/result.json`（含 `scenario_id`、`outcome_class`、`timeline`）
- `output/explanation.json`（含 `branch_points`、`causal_chain`）
- `output/comparison.json`（含 `baseline_outcome_class`、`variation_outcome_class`、`conditions`、`deltas`）

## 案例扩展

基于现有案例创建新场景的推荐步骤：

1. **继承基础结构**：复制现有 ontology.json，保留 meta 结构
2. **调整 TBox**：根据新场景修改概念、关系
3. **实例化 ABox**：设置具体 actor 和能力分数
4. **验证约束**：运行 simulate --check-only 验证格式
5. **迭代优化**：根据推演结果调整参数

### 校验清单

下面这份清单帮助你检查自定义的 Strategy Ontology 输入是否符合规范：

- [ ] `meta.version` 已声明
- [ ] `meta.case_id` 唯一标识案例
- [ ] `Competition` 的 `category` 为 `game`
- [ ] `abox.capabilities.actor_id` 都能映射到 `abox.actors.actor_id`
- [ ] `score` 在 `[0,1]`
- [ ] `reasoning_profile.*.rule_id` 均可在 `tbox.axioms.id` 解析

### 常见错误与排查

- 规则引用错误：`reasoning_profile.*.rule_id` 未在 `tbox.axioms.id` 中声明
- Actor 映射错误：`abox.capabilities.actor_id` 未在 `abox.actors.actor_id` 中出现
- 关系命名错误：关系名未使用语义谓词（如 `has_capability`、`competes_with`）
- 概念分类错误：`Competition` 未标注为 `game`