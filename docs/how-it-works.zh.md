# 🛠️ 工作原理

Omen 采用分层架构，确保推演的透明度与可干预性：

```mermaid
graph TD
    A[信号层<br/>Signal Layer] -->|技术/市场/资本/标准信号 | B(技术空间层<br/>Tech Space Layer)
    B -->|能力维度/替代关系/风险因子 | C(战略主体层<br/>Strategic Actor Layer)
    C -->|目标/资源/动作空间 | D(推演内核<br/>Simulation Kernel)
    D -->|规则+数学模型+LLM 决策 | E(解释层<br/>Explanation Layer)
    E -->|分叉路径/反事实/因果链 | F[用户洞察<br/>User Insights]
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style D fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#bfb,stroke:#333,stroke-width:2px
```

1.  **信号层**：接入多维度的宏观与微观信号。
2.  **技术空间层**：将信号转化为结构化的技术对象与关系图谱。
3.  **战略主体层**：为各类主体定义明确的动作空间，而非自由聊天。
4.  **推演内核**：结合硬约束规则、经济/扩散模型与 LLM 决策逻辑，推进多轮演化。
5.  **解释层**：提取关键分叉点，生成人类可读的推演报告。