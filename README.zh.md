# OmenAI

**AI驱动的开源战略推演引擎。**

[![Package](https://img.shields.io/github/actions/workflow/status/StrategyLogic/omen/package.yml)](https://img.shields.io/github/actions/workflow/status/StrategyLogic/omen/package.yml) ![](https://img.shields.io/pypi/l/omenai) ![](https://img.shields.io/pepy/dt/omenai) ![](https://img.shields.io/pypi/v/omenai) ![](https://img.shields.io/github/stars/StrategyLogic/omen?style=social) 

> 模拟征兆，揭示混沌。

[**Omen**](https://github.com/StrategyLogic/omen) （中文：爻）是一个通过现象模拟进行战略推演的开源引擎。它利用**多智能体博弈论**、**能力空间建模**与**反事实分析**，演算技术演化如何重构市场格局。

[English version](README.md) | [官方仓库](https://github.com/StrategyLogic/omen) | [核心概念](docs/concepts.md) | [快速开始](docs/quick-start.md) | [案例模板](docs/case-template.md) | [项目路线图](docs/roadmap.md)

## 💡 Omen 具体做什么？

Omen 不承诺预测一个*确定的未来*，而是生成**可解释、可回放、可比较的未来分叉路径**。它的核心职责是揭示复杂系统中的微弱征兆、关键分叉点与演化轨迹，赋能创始人、产品战略家、技术领袖与投资分析师理解：

*   🔄 **替代逻辑**：哪项技术会在什么临界条件下替代另一项？
*   🛡️ **能力演化**：哪些核心能力会先被瓦解，哪些将长期共存？
*   🏆 **策略胜率**：哪类策略组合更容易赢得市场、资本与开发者生态？
*   ⏳ **时间窗口**：何时是自研、结盟、并购或收缩的最佳时机？

## ⚙️ 核心功能

| 功能模块 | 描述 |
| :--- | :--- |
| **🧬 技术能力建模** | 将复杂的技术栈拆解为可量化、可比较的能力维度（如：延迟、吞吐量、易用性、生态丰富度）。 |
| **🤖 战略主体模拟** | 定义不同类型的市场参与者（初创公司、巨头、开源社区、监管机构），赋予其目标、资源与约束。 |
| **📈 市场演化推演** | 模拟采用率、市场份额、成本结构、现金流及生态系统的动态变化。 |
| **⚡ 临界点识别** | 自动发现“替代何时发生”、“为何在此刻发生”的关键阈值。 |
| **🔮 反事实分析** | 回答“如果当时没有发生 X 事件，或者采取了 Y 策略，结局会有什么不同？” |
| **📖 结果解释引擎** | 输出关键转折点、因果链条推导及策略含义，拒绝黑盒结论。 |

### 📊 典型输出

一次完整的推演通常会回答以下问题：
*   **是否替代？** 新技术是否会完全取代旧技术，还是形成互补？
*   **时间窗口？** 替代或转折发生的具体时间窗口是何时？
*   **关键驱动？** 哪些变量（如成本下降速度、API 兼容性）是决定性因素？
*   **赢家与输家？** 哪些主体率先受损，哪些主体意外获益？
*   **策略有效性？** 在何种情境下，“开放生态”优于“垂直整合”？
*   **终局形态？** 走向垄断、寡头平衡还是碎片化共存？

## 🚀 快速开始

### 安装

运行环境要求：Python 3.12+ `pip` 包管理器。

```bash
pip install omenai
```

从源码安装：

```bash
git clone https://github.com/StrategyLogic/omen.git
cd omen
pip install --upgrade pip setuptools wheel
pip install -e .
```

### 运行示例
```bash
# 运行模拟
omen simulate --scenario data/scenarios/ontology.json

# 使用固定 seed 运行（可复现）
omen simulate --scenario data/scenarios/ontology.json --seed 42

# 生成解释报告
omen explain --input output/result.json

# 使用通用覆盖参数做对比
omen compare --scenario data/scenarios/ontology.json --overrides '{"user_overlap_threshold": 0.9}'

# 使用商业主参数入口（资金冲击）做对比
omen compare --scenario data/scenarios/ontology.json --budget-actor ai-memory --budget-delta 200

# 保留历史输出（时间戳后缀）
omen compare --scenario data/scenarios/ontology.json --budget-actor ai-memory --budget-delta 200 --incremental
```

### 查看运行结果

**本地文件保护**：输出的文件在项目根目录下的 `output/` 中，默认已在 `.gitignore` 排除，它不会被跟踪或误上传，避免你的数据被泄漏。

示例：`output/result.json` `output/explanation.json` `output/comparison.json`

每次运行模拟，*默认*覆盖上一次的运行结果；你可以通过添加 `--incremental` 参数生成带时间戳后缀的新文件，该参数对所有 `omen CLI` 命令有效。

```bash
# 不会覆盖上一次输出（输出文件自动加上时间戳后缀）
omen simulate --scenario data/scenarios/ontology.json --incremental
```

默认情况下，`simulate` 每次会使用随机 seed 扰动模拟结果；当你需要稳定地使用某次模拟结果时，如：注入不同的场景参数为同一次模拟结果进行对比，请显式传入固定的 `--seed` 值。

```bash
# 使用固定 seed 运行
omen compare --scenario data/scenarios/ontology.json --budget-actor ai-memory --budget-delta 200 --seed 42
# 两次不同的参数运行在同一次模拟结果上，以实现控制变量和可比性
omen compare --scenario data/scenarios/ontology.json --budget-actor ai-memory --budget-delta 300 --seed 42
```

想了解更多？阅读[精度评估](docs/precision.md)文档。

## 👥 适用人群

Omen 专为以下角色打造：
*   技术战略团队
*   产品与平台负责人
*   AI 基础设施研究者
*   开源生态观察者
*   投资与行业分析师

## 🎬 案例演示

我们已内置了经典推演：
*   [🗺️ 本体论博弈：数据库 vs AI 记忆](cases/ontology.md)
*   [⚔️ 向量数据库 vs AI 记忆](cases/vector-memory.md)

更多场景持续构建中（欢迎贡献）：
*   `智能体基础设施` vs `工作流平台`
*   `垂直领域 AI` vs `通用 AI 栈`
*   `开源模型` vs `闭源商业 API`
*   `数据治理` vs `AI 原生知识系统`

## 📦 许可证

Omen 采取[**AGPL-3.0-or-later**](LICENSE)许可证，由 **[StrategyLogic®](https://www.strategylogic.ai)** 开发与维护。

*注意：如果您希望在闭源环境中使用 Omen 或将其作为 SaaS 服务提供而不公开源码，请联系我们获取商业授权。*

## 🔮 愿景

Omen 希望成为一个**开放的战略推演工作台**：
> 它不输出唯一的答案，而是帮助人们系统地理解**未来如何分叉**；<br/>
> 理解**哪些条件塑造了结果**；<br/>
> 理解**哪些行动可以改变路径**。

如果你对技术演化、市场替代、战略建模或多智能体推演感兴趣，欢迎加入我们，共同解读这个混沌世界的*征兆*。

---
*模拟征兆，揭示混沌。*