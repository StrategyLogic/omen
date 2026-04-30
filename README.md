<div align="center">
<h1>OmenAI</h1>
<strong><p>XAI-Powered Strategic Reasoning Engine</p></strong>
<p>English | <a href="README.zh.md">中文</a></p>

![Codecov](https://img.shields.io/codecov/c/github/StrategyLogic/omen) ![Package](https://img.shields.io/github/actions/workflow/status/StrategyLogic/omen/package.yml) ![License](https://img.shields.io/pypi/l/omenai) ![Downloads](https://img.shields.io/pepy/dt/omenai) ![PyPI Version](https://img.shields.io/pypi/v/omenai)
</div>

[**Omen**](https://github.com/StrategyLogic/omen) (Chinese: 爻) is an open-source strategic reasoning engine powered by **Explainable AI** (XAI). It combines ontological modeling of strategic phenomena with counterfactual analysis of uncertainty, delivering verifiable, traceable, and explainable insights for decision-makers.

[Concepts](docs/concepts.md) | [Quick Start](docs/quick-start.md) | [Case Templates](docs/case-template.md) | [Roadmap](docs/roadmap.md)

## 🪄 Capabilities

> Analyze, Simulate, Explain.

Omen **does not predict** the future. It is a reasoning engine **built for complexity**. By mapping causal chains and logical dependencies, it generates replayable, comparable branching paths, revealing weak signals, critical points, and evolving ecosystems, and helping decision-makers **gain clarity** in complexity:

*   🔄 **Substitution Logic**: Which technology will replace another under what critical conditions?
*   🛡️ **Capability Evolution**: Which core capabilities will be enhanced first, and which will coexist long-term?
*   🏆 **Strategy Wins**: Which strategy combinations are more likely to win the market, capital, and developer ecosystem?
*   ⏳ **Time Windows**: When is the optimal timing for in-house development, alliances, M&A, or contraction?

Through explainable reasoning chains, Omen reveals how technological evolution reshapes markets, helping strategic decisions **decode the omens** from the chaos.

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

---

## 🫧 Online Demo

If you are a:
- Strategy Consultant
- C-level Executive
- Industry Analyst
- Product Manager
- Other non-technical users

Want to quickly experience Omen without local installation? Please visit our online demo deployed on Streamlit Cloud.

You can explore the strategic reasoning flow directly online:

👉 [Explore Omen on Streamlit Cloud](https://omen-demo.streamlit.app/)

👉 [Explore Omen Pro on Streamlit Cloud](https://omen-pro.streamlit.app/)

---

## 🚀 Quick Start

If you are a:

- Data Scientist
- AI Researcher
- Strategy Analyst
- Other technical users

Want to run Omen in your local environment? Please follow the installation and running guide below.

### 🏗️ Installation

Environment requirements: Python 3.12+ with `pip` package manager.

```bash
git clone https://github.com/StrategyLogic/omen.git
cd omen
pip install --upgrade pip setuptools wheel
pip install -e .
```

### 🌰 Run Demo

If you want to quickly see Omen in action, a visualized sample case and its results are available in the `demo` directory. Run:

```bash
streamlit run demo/app/scenario_planning.py
```

Then open `http://localhost:8501` in your browser to explore the full strategic reasoning flow.

#### End-to-End Flow

![End-to-End Flow](docs/assets/images/streamlit-strategic-reason-flow.png)

#### More details

You can click on each panel on the page to inspect the full chain of outputs from source document to situation artifact, scenario artifact, simulation result, and explanation artifact.

![Scenario Planning](docs/assets/images/streamlit-scenario-planning.png)

---

## 🎵 Run Built-in Case

If you want to run a complete **Analyze - Simulate - Explain** workflow, we have prepared a built-in case simulating SAP's acquisition of Reltio in March 2026. 

The case document is `cases/situations/sap_reltio_acquisition.md`, and it can be run end-to-end with the following commands:

### Step 1. Analyze

Omen's Analyze module combines strategy methodology and the data pipeline, allowing you to generate strategic insights and machine input artifacts from the source document with a single command.

#### Situation Analysis

```bash
# analyze the built-in case and pack it as "sap" alias
omen analyze situation --doc sap_reltio_acquisition --pack-id sap
```

This step generates the Situation Artifact and creates a package named `sap` for consistent use in subsequent steps.

#### Scenario Planning

Omen `v0.1.9` provides deterministic A/B/C scenario planning capabilities.

- Scenario A: Offensive branch
- Scenario B: Defensive branch
- Scenario C: Confrontational branch

You can directly use the `sap` alias to locate the generated situation artifact from the previous step:

```bash
omen scenario --situation sap
```

This step generates the scenario pack artifact under `data/scenarios/sap/` for simulation.

### Step 2. Simulate

Omen's simulation engine can reason across different scenarios. Use the scenario pack generated in the previous step to run simulation:

```bash
omen simulate --scenario data/scenarios/sap/scenario_pack.json
```

This step generates reasoning traces and writes the deterministic result to `output/sap/result.json`.

### Step 3. Explain

Omen's explanation module interprets simulation outcomes and traces back key decision points and risk items (known unknowns) from the situation artifact to generate decision-ready insights and recommendations:

```bash
omen explain --pack-id sap
```

This step generates a structured explanation artifact at `output/sap/explanation.json`.

### Launch UI

The Streamlit application for visualizing the full strategic reasoning flow.

```bash
streamlit run app/scenario_planning.py
```

Then open `http://localhost:8501` in your browser to explore the results.

## 🎬 Showcase

### Strategic Actor Analyze

We have built-in samples of five strategic actors:

*  👤 [Elon Musk](cases/actors/elon-musk.md)
*  👤 [Jeff Bezos](cases/actors/jeff-bezos.md)
*  👤 [Steve Jobs](cases/actors/steve-jobs.md)
*  👤 [Jack Ma](cases/actors/jack-ma.md)
*  👤 [Chen Jiaxing (me)](cases/actors/chen-jiaxing.md)

Run the following command to build strategic actors and gain insights into their profiles, behavior patterns, and influence relationship graphs:

```bash
streamlit run app/strategic_actor.py
```

### Strategic Reasoning Cases

*  🧩 [Acquisition: SAP vs Reltio](cases/situations/sap_reltio_acquisition.md)
*  🗺️ [Ontology Games: Database vs AI Memory](cases/ontology.md)
*  ⚔️ [Vector Database vs AI Memory](cases/vector-memory.md)   

More scenarios are under development (contributions welcome):
*   `Agent Infrastructure` vs `Workflow Platforms`
*   `Vertical AI` vs `General AI Stack`
*   `Open Source Models` vs `Closed Commercial APIs`
*   `Data Governance` vs `AI-Native Knowledge Systems`

## 📃 License

Omen is under [AGPL-3.0-or-later](LICENSE), the project is developed and maintained by **[StrategyLogic®](https://www.strategylogic.ai)**.

*Note: If you wish to use Omen in a closed-source environment or provide it as a SaaS service without open-sourcing your code, please contact us for a commercial license.*


## 🌟 Vision

Omen aims to become an **open strategic reasoning workstation**:
> It does not output a single answer, but helps people systematically understand **how the future branches**;
> and understand **which conditions shape the outcome**;
> and understand **which actions can change the path**.

If you are interested in technological evolution, market substitution, strategic modeling, or multi-agent reasoning, you are welcome to join us in interpreting the **omens** of this chaotic world together.

---
*Simulate the Signs. Reveal the Chaos.*