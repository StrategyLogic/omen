<div align="center">
<h1>OmenAI</h1>
<strong><p>Strategic Reasoning Engine - Analyze, Simulate, Explain.</p></strong>
<p>English | <a href="README.zh.md">中文</a></p>

![Codecov](https://img.shields.io/codecov/c/github/StrategyLogic/omen) [![Package](https://img.shields.io/github/actions/workflow/status/StrategyLogic/omen/package.yml)](https://img.shields.io/github/actions/workflow/status/StrategyLogic/omen/package.yml) ![License](https://img.shields.io/pypi/l/omenai) ![Downloads](https://img.shields.io/pepy/dt/omenai) ![PyPI Version](https://img.shields.io/pypi/v/omenai)
</div>

[**Omen**](https://github.com/StrategyLogic/omen) (Chinese: 爻) is a strategic reasoning engine based on **Explainable AI**. It leverages **ontological modeling** to understand the phenomena and essence of the strategic world, and **counterfactual analysis** to simulate the known and unknown in decision-making scenarios, generating verifiable, comparable, and explainable decision support for decision-makers.

[Concepts](docs/concepts.md) | [Quick Start](docs/quick-start.md) |  [Case Templates](docs/case-template.md) | [Roadmap](docs/roadmap.md)

## ⭐ What Omen Does

> **Simulate the Signs. Reveal the Chaos.**

Unlike traditional predictive models, Omen is designed for complex strategic reasoning and does not promise to *predict a certain future*. Instead, it generates **interpretable, replayable, and comparable future branching paths**. Its core responsibility is to reveal faint omens, critical branching points, and evolutionary trajectories within complex systems, empowering founders, product strategists, technology leaders, and investment analysts to understand:

*   🔄 **Substitution Logic**: Which technology will replace another under what critical conditions?
*   🛡️ **Capability Evolution**: Which core capabilities will be enhanced first, and which will coexist long-term?
*   🏆 **Strategy Wins**: Which strategy combinations are more likely to win the market, capital, and developer ecosystem?
*   ⏳ **Time Windows**: When is the optimal timing for in-house development, alliances, M&A, or contraction?

## ✨ Core Features

| Feature Module | Description |
| :--- | :--- |
| 🧬 **Technology Capability Modeling** | Deconstructs complex tech stacks into quantifiable, comparable capability dimensions (e.g., latency, throughput, ease of use, ecosystem richness). |
| 🤖 **Strategic Agent Simulation** | Defines different types of market participants (startups, giants, open-source communities, regulators), endowing them with goals, resources, and constraints. |
| 📈 **Market Evolution Reasoning** | Simulates dynamic changes in adoption rates, market share, cost structures, cash flow, and ecosystems. |
| ⚡ **Critical Point Identification** | Automatically discovers key thresholds for "when substitution occurs" and "why it happens at this moment." |
| 🔮 **Counterfactual Analysis** | Answers "What would have happened if event X had not occurred, or if strategy Y had been adopted?" |
| 📖 **Result Explanation Engine** | Outputs key turning points, causal chain deductions, and strategic implications, rejecting black-box conclusions. |

### 📊 Typical Outputs

A complete reasoning session typically answers the following questions:
*   **Substitution?** Will the new technology completely replace the old one, or form a complement?
*   **Time Window?** When is the specific time window for substitution or turning points?
*   **Key Drivers?** Which variables (e.g., cost reduction speed, API compatibility) are the decisive factors?
*   **Winners and Losers?** Which entities suffer first, and which benefit unexpectedly?
*   **Strategy Effectiveness?** Under what circumstances is an "open ecosystem" superior to "vertical integration"?
*   **Endgame Form?** Does it move towards monopoly, oligarchic balance, or fragmented coexistence?

## 🚀 Quick Start

### Installation

Environment requirements: Python 3.12+ with `pip` package manager.

```bash
git clone https://github.com/StrategyLogic/omen.git
cd omen
pip install --upgrade pip setuptools wheel
pip install -e .
```

### Run Example
```bash
# Step 1. analyze situation from a built-in case
omen analyze situation --doc sap_reltio_acquisition --pack-id sap
# Step 2. generate scenario planning artifact from situation
omen scenario --situation sap
```

### View Results

**Strategic Actor Persona UI**

```bash
streamlit run app/strategic_actor.py
```

Then open `http://localhost:8501` and select a case from `cases/actors/` to view persona narrative, graph, and timeline.

**Strategic Situation Brief**

After `omen analyze situation`, read the generated brief:

```bash
# Example brief path
data/scenarios/sap/situation.md
```

Want to learn more? Read the [precision evaluation](docs/precision.md) document.

## 👥 Target Audience

Omen is built for the following roles:
*   Technology Strategy Teams
*   Product & Platform Leads
*   AI Infrastructure Researchers
*   Open Source Ecosystem Observers
*   Investors & Industry Analysts

## 🎬 Show Cases

We have built-in classic reasoning:
*   [🗺️ Ontology Games: Database vs AI Memory](cases/ontology.md)
*   [⚔️ Vector Database vs AI Memory](cases/vector-memory.md)   

More scenarios are under development (contributions welcome):
*   `Agent Infrastructure` vs `Workflow Platforms`
*   `Vertical AI` vs `General AI Stack`
*   `Open Source Models` vs `Closed Commercial APIs`
*   `Data Governance` vs `AI-Native Knowledge Systems`

## 📖 License

Omen is under [AGPL-3.0-or-later](LICENSE), the project is developed and maintained by **[StrategyLogic®](https://www.strategylogic.ai)**.

*Note: If you wish to use Omen in a closed-source environment or provide it as a SaaS service without open-sourcing your code, please contact us for a commercial license.*


## 🔮 Vision

Omen aims to become an **open strategic reasoning workstation**:
> It does not output a single answer, but helps people systematically understand **how the future branches**;
> Understand **which conditions shape the outcome**;
> Understand **which actions can change the path**.

If you are interested in technological evolution, market substitution, strategic modeling, or multi-agent reasoning, welcome to join us in interpreting the **omens** of this chaotic world together.

---
*Simulate the Signs. Reveal the Chaos.*