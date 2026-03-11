# Omen（爻）

> **Simulate the Signs. Reveal the Chaos.<br/>
模拟征兆，揭示混沌。**

Omen 是一个开源的战略推演引擎，用多智能体、能力建模与反事实分析，演算技术如何重构市场。

它聚焦的不是“预测一个确定未来”，而是生成**可解释、可回放、可比较**的未来分叉路径，帮助研究者、产品团队、技术战略团队和投资判断者理解：

- 哪项技术会在什么条件下替代另一项技术
- 哪些能力会先被侵蚀，哪些能力会长期共存
- 哪类策略更容易赢得市场、资本与开发者生态
- 哪个时间窗口适合自研、结盟、并购或收缩

## Positioning & Boundary

Omen 的定位是“现象模拟器”：负责显现征兆与路径，而不直接给出确定性答案。

- Omen（开源）负责 **Reveal**：显现复杂系统中的征兆与分叉

这意味着 Omen 项目对外保持明确边界：

- 展示项目全貌与核心概念
- 输出条件化判断与可解释路径
- 不输出“保证命中”的预测结论

Protocol: [Omen Project Protocol](PROTOCOL.md)

## Why Omen

技术竞争很少是线性演进。

真实世界中的技术演化通常由多种力量共同驱动：能力提升、成本下降、迁移摩擦、组织惯性、资本流向、生态锁定、标准推进，以及开发者采用行为。这些因素叠加后，市场往往不会平滑变化，而会在某个阈值附近发生加速替代、结构重组，或长期共存。

Omen 试图把这个过程从“观点讨论”变成“条件推演”：

- 将技术竞争表示为能力空间
- 将市场主体表示为战略智能体
- 将外部变化表示为可注入事件
- 将结果表示为多路径演化与反事实解释

## What Omen Does

Omen 的核心能力包括：

- **技术能力建模**：把复杂技术栈拆成可比较的能力维度
- **战略主体模拟**：让不同类型主体在约束条件下持续博弈
- **市场演化推演**：模拟采用率、份额、成本、现金流和生态变化
- **替代临界点识别**：发现“何时替代发生、为何发生”
- **反事实分析**：回答“如果没有某个事件/动作，会发生什么”
- **结果解释**：输出关键转折点、因果链条和策略含义

## Core Principles

Omen 的设计遵循以下原则：

- **可回溯**：每轮模拟都记录输入、动作、状态变化与解释
- **可解释**：重要结论都必须能说明关键驱动因素
- **有限行动空间**：智能体在明确定义的动作集合内行动，而不是自由聊天
- **硬约束优先**：技术、经济、政策等底层条件优先于叙事性变量
- **多路径输出**：系统默认生成多条可能路径，而不是单一结论

## How It Works

Omen 采用分层结构：

1. **Signal Layer**
   - 接入技术、市场、资本、标准与生态信号
2. **Tech Space Layer**
   - 将信号转为技术对象、能力维度、替代关系与风险因子
3. **Strategist Agent Layer**
   - 为各类主体定义目标、资源、约束和动作空间
4. **Simulation Kernel**
   - 结合规则、数学模型与 LLM 决策推进多轮演化
5. **Explanation Layer**
   - 输出关键分叉、反事实、因果链与行动建议

## Typical Outputs

一次完整推演通常会输出：

- 替代是否发生
- 替代发生的时间窗口
- 哪些变量是关键驱动因素
- 哪些主体率先受损或获益
- 哪种策略组合更有效
- 在哪些条件下会走向替代、融合或长期共存

## Show Cases

- [Ontology 战场：Database vs AI Memory](cases/ontology.md)

后续可以在 `cases/` 目录持续增加更多演示场景，例如：

- Agent Infrastructure vs Workflow Platforms
- Vertical AI vs General AI Stack
- Open Source Models vs Closed Commercial APIs
- Data Governance vs AI-native Knowledge Systems

## Open Source Scope

Omen 的开源版本将围绕“强场景 + 可运行推演内核”展开，优先交付：

- 标准化场景定义格式
- 技术能力空间定义
- 基础战略智能体
- 推演引擎与检查点机制
- 结果解释与回放面板
- 示例数据与默认参数

## Development Environment

- Language: **Python**
- Version: **3.12**

## Docs

- [Docs Index](docs/README.md)
- [Core Concepts](docs/concepts.md)
- [Case Template](docs/case-template.md)
- [Roadmap](docs/roadmap.md)
- [Project Protocol](PROTOCOL.md)

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).

## Ownership

Omen is developed and maintained by **[StrategyLogic®](https://www.strategylogic.ai)**.
The official project repository is [StrategyLogic/omen](https://github.com/StrategyLogic/omen),
and the organization profile is [github.com/StrategyLogic](https://github.com/StrategyLogic).
For trademark and ownership details, see [NOTICE](NOTICE.md).


## Planned Architecture

当前推荐的工程方向：

- **控制流**：LangGraph
- **计算流**：Python 规则引擎 + 经济/扩散/博弈模型
- **决策流**：LLM 驱动的 Strategist Agents
- **实验层**：多场景并行、参数扫描、蒙特卡洛模拟
- **展示层**：用于呈现路径树、生态位地图和关键事件的 Web UI

## Audience

Omen 面向以下用户：

- 技术战略团队
- 产品与平台负责人
- AI 基础设施研究者
- 开源生态观察者
- 投资与行业分析团队

## Project Status

当前项目处于早期构建阶段，重点是定义：

- 场景模型
- 能力空间
- 智能体动作系统
- 推演与解释闭环

## Vision

Omen 希望成为一个开放的战略推演工作台：

- 不是输出唯一答案
- 而是帮助人们系统地理解未来如何分叉
- 理解哪些条件塑造结果
- 理解哪些行动可以改变路径

如果你对技术演化、市场替代、战略建模或多智能体推演感兴趣，欢迎关注这个项目。