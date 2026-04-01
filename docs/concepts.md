# 核心概念

本文档阐述 Omen 的核心概念，用于统一术语、约束实现边界，并支撑场景扩展。

## 1 Strategic Simulation

**定义**

战略推演是对“技术能力、市场主体、资源约束、外部事件”在时间维度上的联动演化建模。

**目标**

- 不是给出唯一结论
- 而是输出条件化路径和策略含义

**结果形态**

- 多路径演化
- 条件触发点
- 可解释结论

## 2 Capability Space

**定义**

能力空间是对技术竞争对象的可计算表示：把抽象技术优势拆解为可比较、可演化的能力维度。

**作用**

- 让“技术路线对比”从叙述转为建模
- 让替代与融合能够被量化观察

**典型维度**

- 语义检索、语义推理、上下文加载
- 一致性、吞吐/延迟、成本效率
- 开发者体验、迁移摩擦、生态兼容

## 3 Strategy Ontology

**定义**

[战略本体](ontology.md) 是“设定战场”阶段的结构化输入，嵌入在场景文件中，用于把概念、关系和规则以可验证形式交给推演引擎。
**最小结构**

- `meta`：案例元数据（`version`、`case_id`、`domain`）
- `tbox`：概念、语义关系、公理规则
- `abox`：参与方实例、能力映射、约束与事件
- `reasoning_profile`：激活/传播/反事实规则引用

**设计约束**

- `Competition` 属于 `game` 类概念
- 关系名必须是语义谓词（如 `has_capability`、`competes_with`）
- 本体输入服务于当前 case，不扩展为通用本体平台

**交付物**

| Case | Strategy Ontology 文件 | 状态 | 说明 |
|---|---|---|---|
| ontology-battlefield | `data/scenarios/ontology.json` | ✅ 完成 | 内嵌 `meta`/`tbox`/`abox`/`reasoning_profile` |

### 3.1 Strategic Actor

**定义**

`Strategic Actor` 是代表战略主体（厂商、应用团队、资本/生态等）的行动单元。

**关键属性**

- 目标函数（增长、利润、防守、生态扩张等）
- 资源约束（预算、研发能力、时间）
- 风险偏好（激进/稳健）
- 可执行动作集合（研发、降价、结盟、并购、开源、防守）

**边界**

- 不是自由聊天体
- 必须在有限动作空间内行动

更多细节请参考 [战略行动者概念文档](concepts/strategic-actor.md)。

## 4 State

**定义**

`State` 是每一轮推演的全局状态快照，包含市场、能力、主体与外生事件信息。

**最小组成**

- 时间步
- 主体状态（资金、能力、份额、策略）
- 市场状态（需求结构、采用率）
- 约束条件（政策、标准、成本）

**要求**

- 可序列化
- 可比较
- 可回放

## 5 Action Space

**定义**

动作空间是每类主体在当前状态下可执行的离散或参数化动作集合。

**目的**

- 控制模拟可解释性
- 保证跨场景结果可比较

**示例动作**

- `invest_rnd`
- `cut_price`
- `form_alliance`
- `acquire_capability`
- `open_source_module`

## 6 Simulation Kernel

**定义**

`Simulation Kernel` 是推演执行核心，负责将状态、动作和规则推进为下一轮状态。

**三种流**

1. **规则流**：硬约束、门槛触发、事件合法性
2. **计算流**：采用率、份额、成本、现金流更新
3. **决策流**：在边界内生成动作选择与解释

**设计原则**

- 先规则与计算，再策略解释
- 避免让关键数值完全由自然语言生成

## 7 Emergence (Constrained)

**定义**

`Emergence` 指多主体互动产生的系统级结果（如加速替代、生态重组、长期共存）。

**Omen 的约束式涌现**

- 允许涌现
- 但必须发生在可审计约束内

**反模式**

- 用随机叙事替代机制解释
- 仅依赖角色对话推动关键结论

## 8 Counterfactual Analysis

**定义**

反事实分析是在保持其他条件不变时，修改一个变量或动作并重跑路径，比较结果差异。

**常见问题**

- 去掉某次融资会怎样
- 降低某项能力增长速度会怎样
- 将并购策略改为结盟会怎样

**价值**

- 提高解释可信度
- 识别真正关键驱动因子

## 9 Explainability

**定义**

可解释性是将“结果”映射回“输入—动作—状态变化”的因果链条。

**输出要求**

- 关键拐点
- 主要驱动因子排序
- 关键动作影响
- 路径分叉原因

## 10 Show Case

**定义**

`Show Case` 是用于公开展示的单一强场景，要求问题具体、主体清晰、输出可验证。

**规范**

- 文件放在 `cases/`
- 文件名必须是场景名（如 `ontology.md`）
- 不使用 `case.md` 这类泛名

## 11 Path Types

Omen 默认输出多种路径类型：

- **Most Likely Path**：最可能路径
- **High Risk Path**：高风险路径
- **High Upside Path**：高收益路径
- **Black Swan Path**：低概率高影响路径

## 12 Decision Output

推演输出应是可执行的“条件化判断”，而非绝对预测。

**推荐格式**

- 在什么条件下发生什么
- 哪些变量触发了拐点
- 哪种策略组合更优
- 下一步动作建议是什么

## 13 Non-goals

当前阶段不追求：

- 通用社会模拟
- 全行业统一模型
- 无约束自由对话驱动模拟

## 14 Terminology Policy

项目文档统一使用以下术语：

- 战略推演（Strategic Simulation）
- 条件化判断（Conditional Judgment）
- 能力空间（Capability Space）
- 战略主体（Strategic Actor）
- 反事实分析（Counterfactual Analysis）

避免使用会误导为确定性预测的表达。

## 15 Precision & Ingest Terms

为保持外部文档一致性，新增以下统一术语：

- **Precision Evaluation**：用于度量重复性、方向正确性、证据链完整性
- **Precision Gate**：基于阈值的通过/未通过判定
- **Ingest Workspace**：`data/ingest/` 下的标准目录（`sources/extracted/knowledge/graph`）

相关文档：

- [精度评估](precision.md)
- [数据摄取](ingest.md)