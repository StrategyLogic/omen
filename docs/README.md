# Docs

这个目录用于沉淀 Omen 的核心概念、方法论和项目演进计划。

## 推荐阅读路径

1. 从 [Quick Start](quick-start.md) 跑通最小推演闭环
2. 阅读 [Core Concepts](concepts.md) 理解术语与边界
3. 阅读 [Ontology Input](ontology.md) 理解战场输入结构
4. 阅读 [Precision Guide](precision.md) 理解精度评估与门禁
5. 阅读 [Ingest Workspace](ingest.md) 理解数据摄取目录与流程
6. 参考 [Roadmap](roadmap.md) 查看阶段演进

## Documents

- [Core Concepts](concepts.md)
- [Case Template](case-template.md)
- [Roadmap](roadmap.md)
- [Quick Start](quick-start.md)
- [Precision Guide](precision.md)
- [Ingest Workspace](ingest.md)

## Core Concepts

后续建议围绕以下概念持续扩展文档：

- **Capability Space**：将技术竞争拆解为可比较、可演化的能力维度
- **Strategic Actor**：在资源约束下做有限动作选择的战略主体
- **Strategy Ontology**：case-by-case 的战场设定输入（`meta`/`tbox`/`abox`/`reasoning_profile`）
- **Simulation Kernel**：结合规则、计算模型与 LLM 决策推进多轮演化
- **Counterfactual Analysis**：通过反事实回放解释关键分叉和策略影响
- **Show Case**：用单一强场景验证推演能力与解释能力

## Naming Conventions

- `cases/` 下的案例文件必须使用**场景名称**命名，而不是通用名。
- 使用小写英文文件名，必要时用连字符连接。
- 示例：`ontology.md`、`vector-memory.md`、`workflow-agents.md`
- 不使用：`case.md`、`demo.md`、`example.md`
