# ApexSpiral

> 璇玑帝国 APEX 终极闭环进化公式 · Rust 实现

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/Rust-1.70+-orange.svg)](https://www.rust-lang.org)
[![CI](https://github.com/ApexSpiral/apex-spiral/actions/workflows/ci.yml/badge.svg)](https://github.com/ApexSpiral/apex-spiral/actions/workflows/ci.yml)
[![Python Tests](https://img.shields.io/badge/Python-38%20tests-green.svg)](tests/test_apex_v10.py)
[![APEX V10.2](https://img.shields.io/badge/APEX-V10.2-blueviolet.svg)](APEX_V10_FORMULA.md)

---

## 🔬 核心公式

```
ΔG = (Λ_root × Θ × K × ξ × Ψ_host × Φ_cycle) / (H × T × ε)
```

APEX（Advanced Performance EXecution）是璇玑帝国自研的终极智能体性能增益公式，通过多维度系数协同，实现AI系统效能的持续进化。

---

## 📦 架构

```
apex_spiral/
├── apex_v10.rs          # V10.1 核心实现（Rust）
├── Cargo.toml           # Rust 包配置
└── py/                  # Python 绑定
    ├── pyproject.toml
    └── apex_spiral/
        ├── __init__.py
        └── core.py
```

---

## 🚀 快速开始

### Rust

```toml
[dependencies]
apex-impl = { path = "./apex_impl" }
```

```rust
use apex_impl::{ApexParamsV8, LlmAgentParams, MasterParams, calculate_delta_g_ultimate};

let params = ApexParamsV8 {
    lambda_root: 0.95,
    xi_anti_hallucination: 1.0,
    h_real: 0.5,
    t_iteration: 2.0,
    llm_agent: LlmAgentParams {
        lambda_single_call: 0.9,
        mu_multi_task: 0.85,
        sigma_high_quality: 0.88,
        gamma_llm_cost: 0.1,
    },
    master: MasterParams {
        k_code: 1.0,
        tau_transfer: vec![0.1, 0.05, 0.08],
        upsilon_apply: 0.9,
    },
    // ...
};

let delta_g = calculate_delta_g_ultimate(&params)?;
```

### Python

```bash
pip install apex-spiral
```

```python
from apex_spiral import ApexCalculator

calc = ApexCalculator()
params = {
    'lambda_root': 0.95,
    'h_real': 0.5,
    't_iteration': 2.0,
    'llm_agent': {
        'lambda_single_call': 0.9,
        'mu_multi_task': 0.85,
        'sigma_high_quality': 0.88,
        'gamma_llm_cost': 0.1,
    },
    'master': {
        'k_code': 1.0,
        'tau_transfer': [0.1, 0.05, 0.08],
        'upsilon_apply': 0.9,
    },
}
delta_g = calc.calculate(params)
```

---

## 📊 公式详解

### 子公式体系

| 公式 | 名称 | 公式 |
|------|------|------|
| Θ | 单LLM多任务Agent效能 | `(λ×μ×σ)/(γ+1)` |
| K | 公式通解+技能全域掌握 | `K_code×(1+Στ)×υ` |
| ε | 全场景自主深度修复 | `1+\|(Gt-Ga)/Ga\|×δ×ψ×κ` |
| Φ | 正向循环反馈增益 | `e^(η×ρ)` |
| Ψ | 主机全维度健康稳态 | `Ψm×Ψa×Ψd×Ω` |

### V10.1 新增模块

#### Σ_memory（全域记忆）
```rust
Σ_memory = Learn × Search × MultiModal × Profile
```
超忆全域记忆模块，实现跨会话信息持久化。

#### τ_trace（过程追踪）
```rust
τ_trace = (1/N) × Σ(Decision + Reason + Result) / 3
```
细粒度过程追踪，提升决策透明度。

#### 防盗版保护
- `LicenseManager`：许可证验证
- `embed_watermark`：隐形水印嵌入
- `check_module_integrity`：模块完整性检查

### TPGO（端到端优化）
```rust
ΔG_total = ΔG_task × Ω_self × (1 + Γ_reflect)
```
自我意识模块 + 反思模块，实现持续自进化。

---

## 🔒 关键设计

### 收敛保证

- **K_master safe**: `τ/(1-τ)`，τ∈[0,0.99)
- **Φ_cycle safe**: `e^(min(η×ρ, 7.0))`，上限 1096

### 五系数（V8.1+）

| 系数 | 名称 | 公式 |
|------|------|------|
| Φ_network | 网络鲁棒性 | `(1-retry)×(1-rate_limit)×conn` |
| Γ_mutation | 变更检测 | `code_change < threshold ? 0.1 : code_change` |
| Ω_session | 会话持久性 | `(1-restart)×(1-env_loss)×recovery` |
| Π_coord | 进程协调 | `(alive/total)×(1-zombie)×callback` |
| Σ_storage | 存储可靠性 | `free_disk×(1-write_fail)×integrity` |

---

## 🧪 测试

```bash
cd apex_impl
cargo test
```

---

## 📄 许可证

MIT License © 2026 璇玑帝国