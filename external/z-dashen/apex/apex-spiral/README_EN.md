# ApexSpiral

> APEX Ultimate Closed-Loop Evolution Formula · Rust Implementation

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Rust](https://img.shields.io/badge/Rust-1.70+-orange.svg)](https://www.rust-lang.org)
[![CI](https://github.com/ApexSpiral/apex-spiral/actions/workflows/ci.yml/badge.svg)](https://github.com/ApexSpiral/apex-spiral/actions/workflows/ci.yml)
[![Python Tests](https://img.shields.io/badge/Python-38%20tests-green.svg)](tests/test_apex_v10.py)
[![APEX V10.2](https://img.shields.io/badge/APEX-V10.2-blueviolet.svg)](APEX_V10_FORMULA.md)

---

## 🔬 Core Formula

```
ΔG = (Λ_root × Θ × K × ξ × Ψ_host × Φ_cycle) / (H × T × ε)
```

**APEX** (Advanced Performance EXecution) is a self-developed ultimate intelligent agent performance gain formula by 璇玑帝国 (Xuanji Empire). Through multi-dimensional coefficient synergy, it achieves continuous evolution of AI system efficiency.

---

## 📦 Architecture

```
apex_spiral/
├── apex_v10.rs          # V10.2 Core Implementation (Rust)
├── Cargo.toml           # Rust package config
└── py/                  # Python bindings
    ├── pyproject.toml
    └── apex_spiral/
        ├── __init__.py
        └── core.py
```

---

## 🚀 Quick Start

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

## 📊 Formula Reference

### Sub-Formula System

| Formula | Name | Definition |
|---------|------|------------|
| Θ | Single-LLM Multi-Task Agent Efficiency | `(λ×μ×σ)/(γ+1)` |
| K | Universal Formula Solution + Full-Domain Skill Mastery | `K_code×(1+Στ)×υ` |
| ε | Full-Scenario Autonomous Deep Repair | `1+\|(Gt-Ga)/Ga\|×δ×ψ×κ` |
| Φ | Positive Cyclic Feedback Gain | `e^(η×ρ)` |
| Ψ | Host Full-Dimensional Health Stability | `Ψm×Ψa×Ψd×Ω` |

### V10.2 New: Σ_unified — Four-Dimensional Unified Standards Fusion

```
Σ_unified = Σ_data × Σ_code × Σ_struct × Σ_native
```

| Dimension | Meaning | Formula |
|-----------|---------|---------|
| Σ_data | Unified Data Standard | `Verify(schema_version=1.0) × Converge(data)` |
| Σ_code | Unified Code Standard | `Validate(code_standard) × Annotate(apex_block)` |
| Σ_struct | Unified Structure Standard | `Verify(gene/event/state) × Enforce(schema)` |
| Σ_native | Native System Capabilities | `Compile(𝓢) → DAG → LocalFix → 𝒪^*` |

### GraSP Skill-Graph Compilation (Native Capability)

```
Φ_{GraSP} = Compile(𝓢) \xrightarrow{Verify, LocalFix} 𝒪^*
```

| Symbol | Meaning |
|--------|---------|
| 𝓢 | Skill Set |
| Compile(𝓢) | Compile into typed DAG skill graph |
| Verify, LocalFix | Node verification + local repair |
| 𝒪^* | Optimal execution strategy |

### Complexity Master Formula

```
𝒪(N) → 𝒪(d^h)
```

| Symbol | Meaning |
|--------|---------|
| N | Total task steps |
| d | DAG depth |
| h | DAG height |

### Performance Master Formula

```
𝒫 ∝ 𝒞(𝒢) ≫ |𝓢|
```

| Symbol | Meaning |
|--------|---------|
| 𝒫 | Agent Performance |
| 𝒞(𝒢) | Skill-graph orchestration quality |
| \|𝓢\| | Number of skills |

### Local Fix Operators

```
𝒢' = 𝒢 ⊙ {RETRY, SUBSTITUTE, INSERT, DELETE, BACKTRACK}
```

### V10.1 Modules (Inherited)

#### Σ_memory (Global Memory)
```rust
Σ_memory = Learn × Search × MultiModal × Profile
```
Cross-session information persistence via super-memory global module.

#### τ_trace (Process Tracing)
```rust
τ_trace = (1/N) × Σ(Decision + Reason + Result) / 3
```
Fine-grained process tracing for improved decision transparency.

#### Anti-Piracy Protection
- `LicenseManager`: License verification
- `embed_watermark`: Invisible watermark embedding
- `check_module_integrity`: Module integrity verification

### TPGO (End-to-End Optimization)

```rust
ΔG_total = ΔG_task × Ω_self × (1 + Γ_reflect)
```

Where:
- `Ω_self = σ_coherence × (1 - δ_drift) × ρ_alignment`
- `Γ_reflect = Σ(w_i × ΔQ_i) / Σw_i`

---

## 🔒 Key Design

### Convergence Guarantees

| Formula | Safe Range | Behavior |
|---------|------------|----------|
| K_master | τ∈[0,0.99) | `τ/(1-τ)` — bounded growth |
| Φ_cycle | any η,ρ | `e^(min(η×ρ, 7.0))` — cap at 1096 |
| Σ_unified | — | `≥0.95` (standard compliant) / `≤0.8` (standard missing) |

### Five Coefficients (V8.1+)

| Coefficient | Name | Formula |
|-------------|------|---------|
| Φ_network | Network Robustness | `(1-retry)×(1-rate_limit)×conn` |
| Γ_mutation | Change Detection | `code_change < threshold ? 0.1 : code_change` |
| Ω_session | Session Persistence | `(1-restart)×(1-env_loss)×recovery` |
| Π_coord | Process Coordination | `(alive/total)×(1-zombie)×callback` |
| Σ_storage | Storage Reliability | `free_disk×(1-write_fail)×integrity` |

---

## 🧪 Testing

```bash
cd apex_impl
cargo test
```

---

## 📄 License

MIT License © 2026 璇玑帝国 (Xuanji Empire)
