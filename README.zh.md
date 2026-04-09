<div align="center">
<h1>OmenAI</h1>
<strong><p>战略推演引擎 － 分析、模拟、解释</p></strong>
<p><a href="README.md">English</a> | 中文</p>

![Codecov](https://img.shields.io/codecov/c/github/StrategyLogic/omen) [![Package](https://img.shields.io/github/actions/workflow/status/StrategyLogic/omen/package.yml)](https://img.shields.io/github/actions/workflow/status/StrategyLogic/omen/package.yml) ![License](https://img.shields.io/pypi/l/omenai) ![Downloads](https://img.shields.io/pepy/dt/omenai) ![PyPI Version](https://img.shields.io/pypi/v/omenai)

</div>

[**Omen**](https://github.com/StrategyLogic/omen) （中文：爻）是基于**可解释AI**的战略推演引擎。它以**本体论建模**理解战略世界中的现象与本质，以**反事实分析**模拟决策情景中的已知与未知，为决策者生成可验证、可追溯和可解释的战略洞察。

[核心概念](docs/concepts.md) | [快速开始](docs/quick-start.md) | [案例模板](docs/case-template.md) | [项目路线图](docs/roadmap.md)

## 💡 Omen 做什么？

> 模拟征兆，揭示混沌。

与传统的预测模型不同，Omen 是面向复杂战略推演的引擎，它不局限在*单一确定的未来*，而是生成可解释、可回放、可比较的未来分叉路径。通过拆解复杂系统中的因果链条与逻辑关联，精准捕捉微弱征兆、关键分叉点与演化轨迹，让创始人、产品战略家、技术领袖与投资分析师清晰理解：

*   🔄 **替代逻辑**：哪项技术会在什么临界条件下替代另一项？
*   🛡️ **能力演化**：哪些核心能力会先被增强，哪些将长期共存？
*   🏆 **策略胜率**：哪类策略组合更容易赢得市场、资本与开发者生态？
*   ⏳ **时间窗口**：何时是自研、结盟、并购或收缩的最佳时机？

通过可解释的逻辑推演，Omen 致力于揭示技术演进如何重塑市场格局，让每一次战略决策可计算、可模拟、可验证、可追溯。

## ✨ 核心功能

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
git clone https://github.com/StrategyLogic/omen.git
cd omen
pip install --upgrade pip setuptools wheel
pip install -e .
```

### 运行示例
```bash
# 第一步：内置案例情势分析
omen analyze situation --doc sap_reltio_acquisition --pack-id sap
# 第二步：从情势生成情景规划
omen scenario --situation sap
```

### 查看结果

**战略主体画像 UI**

```bash
streamlit run app/strategic_actor.py
```
然后打开 `http://localhost:8501`，选择 `cases/actors/` 中的一个案例，查看画像叙事、图谱和时间线。

**战略情势简报**

在执行 `omen analyze situation` 后，阅读生成的简报：
```bash
# 简报示例路径
data/scenarios/sap/situation.md
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

## 📖 许可证

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