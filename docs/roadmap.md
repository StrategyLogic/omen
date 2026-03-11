# Roadmap

本文档描述 Omen 作为开源战略推演项目的阶段目标。

## Direction

Omen 的首要目标不是做一个大而全的平台，而是建立一个可信的推演闭环：

- 有清晰的场景输入
- 有明确的能力空间建模
- 有受约束的战略主体
- 有可解释的模拟输出
- 有可回放的结果与反事实分析

## Phase 0 — Foundation

目标：建立最小可行框架与公开叙事。

### Deliverables

- 项目 README
- `docs/` 文档目录
- case template
- 首个 show case
- 基础目录约定
- 统一命名规范

### Exit Criteria

- 外部读者能理解 Omen 是什么
- 新场景可以按模板扩展
- 项目展示结构清晰可迭代

## Phase 1 — Single Battle MVP

目标：围绕单一强场景打通最小推演闭环。

### Scope

- 场景：Ontology / Database / AI Memory
- 能力空间：12 个左右核心维度
- 主体类型：数据库、AI Memory、应用层、生态/资本
- 动作集合：研发、降价、结盟、并购、开源、防守

### Deliverables

- 场景定义格式
- 能力维度定义
- 主体状态模型
- 单轮与多轮模拟流程
- 基础结果面板
- 推演日志与检查点记录

### Exit Criteria

- 能跑出至少 3 条有差异的路径
- 能解释关键分叉为何发生
- 能输出替代 / 融合 / 共存三类结果

## Phase 2 — Explanation & Counterfactuals

目标：让结果从“可看”升级为“可解释”。

### Deliverables

- 关键事件高亮
- 因果链条生成
- 驱动因子排序
- 反事实分析接口
- 场景结果对比视图

### Exit Criteria

- 每个关键结果都能回溯到输入和动作
- 用户可查看“如果不发生某事件”的替代结果
- 报告不止给结论，还能给路径解释

## Phase 3 — Scenario System

目标：从单案例扩展到可复用的场景系统。

### Deliverables

- 多案例目录结构
- 通用场景 schema
- 参数化场景加载器
- 案例间对比框架
- 场景版本管理规则

### Candidate Cases

- Vector Database vs AI Memory
- Workflow Agents vs Vertical SaaS
- Open Models vs Closed APIs
- Data Governance vs AI-native Knowledge Systems

### Exit Criteria

- 至少 3 个案例共享同一套基础推演骨架
- 新案例接入成本显著下降
- README 可以公开展示多个 case

## Phase 4 — Strategy Workbench

目标：把 Omen 从 demo engine 提升为战略工作台。

### Deliverables

- 可配置实验面板
- 参数扫描
- 蒙特卡洛批量模拟
- 场景快照与回放
- 结果导出能力

### Exit Criteria

- 用户可以自行配置输入并运行实验
- 同一场景可批量跑不同参数组合
- 结果可导出为结构化报告

## Phase 5 — Ecosystem & Contributions

目标：建立面向社区的扩展机制。

### Deliverables

- 贡献指南
- 案例提交流程
- 场景评审标准
- 文档完善计划
- 示例数据和测试基线

### Exit Criteria

- 外部贡献者可以独立新增 case
- 社区能复用模板构建相邻场景
- 项目具备稳定的演化节奏

## Near-term Priorities

当前最优先的事项是：

1. 固化首个 case 的输入结构
2. 定义能力空间 schema
3. 定义 strategist agent 的状态与动作模型
4. 设计单轮 / 多轮模拟接口
5. 设计结果解释与回放格式

## Non-goals (Current Stage)

当前阶段暂不追求：

- 通用社会模拟
- 全行业统一模型
- 海量实时数据接入
- 企业级权限与协作系统
- 大而全的可视化平台

## Guiding Principle

每一个新阶段都应回答同一个问题：

> 它是否让 Omen 更接近一个可解释、可回溯、可扩展的战略推演引擎？
