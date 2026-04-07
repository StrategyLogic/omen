# 🛠️ How It Works

Omen adopts a layered architecture to ensure the transparency and intervenability of reasoning:

```mermaid
graph TD
    A[Signal Layer] -->|Tech/Market/Capital/Standard Signals | B(Tech Space Layer)
    B -->|Capability Dimensions/Substitution Relations/Risk Factors | C(Strategic Actor Layer)
    C -->|Goals/Resources/Action Space | D(Simulation Kernel)
    D -->|Rules+Math Models+LLM Decisions | E(Explanation Layer)
    E -->|Branching Paths/Counterfactuals/Causal Chains | F[User Insights]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
```

*   **Signal Layer**: Accesses multi-dimensional macro and micro signals.
*   **Tech Space Layer**: Transforms signals into structured technical objects and relationship graphs.
*   **Strategic Actor Layer**: Defines clear Action Spaces for various entities, rather than free-form chatting.
*   **Simulation Kernel**: Combines hard constraint rules, economic/diffusion models, and LLM decision logic to advance multi-round evolution.
*   **Explanation Layer**: Extracts key branching points and generates human-readable reasoning reports.