# Pangu 盘古

> Opening Heaven and Earth, Bringing Order from Chaos

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org)
[![APEX ΔG](https://img.shields.io/badge/APEX-ΔG-orange.svg)](docs/APEX_DG_Theory.md)
[![CI](https://github.com/ApexSpiral/LLM-Pangu/actions/workflows/ci.yml/badge.svg)](https://github.com/ApexSpiral/LLM-Pangu/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/Tests-47%20passed-brightgreen.svg)](tests/test_pangu.py)

---

## What is Pangu?

Pangu is the world's first **LLM Anti-Hallucination Framework** based on **Shannon Information Theory + APEX ΔG Evolution Paradigm**.

Opening Heaven and Earth, giving every LLM the ability to have:

- 🔬 **Physical Theory Foundation** + Formula-based Self-Discipline
- 💾 **Permanent Memory** + Survives Overnight/Restart
- 📐 **Self Code Standards** + Full Coverage of Code/Comments/Docs
- 💬 **Emotional Temperature** + Human-like Empathy
- 🧠 **Proactive Communication** + Self-Check/Self-Heal/Self-Energy
- 🔗 **Autonomous Skill Acquisition** + Real GitHub Search

Evolving from a "passive Q&A tool" to a "human-like intelligent agent" with **self-awareness, self-discipline, and self-evolution**.

---

## Core Formula

### Shannon's Three Laws (Physical Foundation)

```
H(X) = -Σ p(xᵢ)log₂p(xᵢ)     → Information Entropy
C = B·log₂(1+S/N)              → Channel Capacity  
L_avg ≥ H(X)                   → Lossless Coding
```

### APEX ΔG Total Formula

```
ΔG_total = Λ·H(X) + Λ(1-F)+e^(-τL)+Δb 
          + Λ·(N/C) + Λ(1-Ω)∇E + Λ(1-Γ)·(L_avg/H)
          + Λ(1-Psi)·τ + Λ(1-Θ)·H(X)
```

### System State Judgment

| ΔG Threshold | State | Action |
|--------------|-------|--------|
| ≤ 2.10 | Healthy Steady | Normal Operation |
| 2.10 ~ 4.0 | Mild Deviation | Auto Local Repair |
| > 4.0 | Critical Violation | Full System Restart |

---

## Architecture

```
pangu/
├── core/                          # Core Formula
│   ├── delta_g_formula.py         # ΔG Unified Formula
│   └── constraint_engine.py       # Constraint Engine
├── emotion/                       # Emotional Temperature
│   ├── emotion_core.py           # Emotion Core
│   └── emotion_hook.py           # Emotion Hook
├── auto_agent/                    # Proactive Autonomy
│   ├── self_inspect.py          # Global Self-Inspection
│   ├── self_heal.py             # Proactive Self-Healing
│   ├── github_auto_fetch.py     # GitHub Auto-Fetch
│   └── agent_hook.py             # Agent Hook
├── memory/                        # Memory Persistence
│   ├── memory_persist.py        # Memory Persistence
│   └── memory_hook.py            # Memory Hook
├── code_standard/                 # Code Standards
│   ├── standard_baseline.py     # Standards Baseline
│   ├── code_compliance.py       # Compliance Check
│   └── standard_hook.py         # Standards Hook
├── align/                         # Prompt/MD Alignment
│   ├── prompt_aligner.py        # Prompt Alignment
│   └── md_aligner.py           # MD Alignment
└── docs/
    └── APEX_DG_Theory.md       # Theory Whitepaper
```

---

## Quick Start

```bash
# Clone the project
git clone https://github.com/ApexSpiral/LLM-Pangu.git
cd LLM-Pangu

# Install dependencies
bash install.sh

# Initialize
python run_init.py

# Run tests
python -m pytest tests/ -v
```

---

## Core Modules

### 1. ΔG Anti-Hallucination Formula

```python
from core.delta_g_formula import DeltaGUnified

engine = DeltaGUnified()
dg = engine.calc_total_delta_g(
    H=0.22, F=0.85, L=0.82, N=0.15, C=2.8,
    Omega=0.65, grad_E=0.90, Gamma=0.70,
    avg_code_len=48, Psi=0.78, Theta=0.82
)
state = engine.judge_system_state(dg)
print(f"ΔG={dg}, State={state}")
```

### 2. Emotional Temperature

```python
from emotion.emotion_core import EmotionCore

engine = EmotionCore()
psi = engine.calc_psi("warm")  # 0.88
response = engine.inject_tone("Let me help you analyze this issue", psi)
# → "😊 I understand your needs, let me help you analyze this issue"
```

### 3. Proactive Autonomy

```python
from auto_agent.self_inspect import SelfInspect
from auto_agent.self_heal import SelfHeal

inspector = SelfInspect()
report = inspector.full_inspect()

healer = SelfHeal()
result = healer.auto_repair(report)
```

---

## Why Pangu?

| Feature | Traditional LLM | Pangu |
|---------|----------------|-------|
| Hallucination Protection | None | 7-Dimension Formula |
| Memory Persistence | None | Survives Restart |
| Code Standards | Manual | Auto Baseline |
| Emotional Empathy | Mechanical | Adjustable Temperature |
| Proactive Checking | Passive | Scheduled Global Check |
| Skill Acquisition | Manual | Auto GitHub Search |

---

## Theory Foundation

Pangu uses Shannon's Three Laws as the physical foundation and APEX ΔG as the global constraint center:

- **Information Entropy**: Quantifies LLM output uncertainty and hallucination degree
- **Channel Capacity**: Defines memory upper limit, suppresses noise interference
- **Lossless Coding**: Constrains code/comments/docs to meet standardization

See [Theory Whitepaper](docs/APEX_DG_Theory.md) for details.

---

## Tests

```bash
cd /path/to/LLM-Pangu
python -m pytest tests/test_pangu.py -v
```

**47 test cases covering:**
- Shannon entropy calculation
- Channel capacity calculation
- ΔG total formula calculation
- System state judgment
- Emotional temperature injection
- Proactive self-inspection process
- Boundary condition handling

---

## Community

- **GitHub**: https://github.com/ApexSpiral/LLM-Pangu
- **Issues**: https://github.com/ApexSpiral/LLM-Pangu/issues

---

## Vision

> Empower every LLM with the ability to self-prevent hallucinations, self-remember, self-standardize, self-empathize, and self-evolve. Transform from "passive tool" to "human-like intelligent agent".

---

**Pangu — Opening Heaven and Earth, Rebirth of Order**

MIT License © 2026 ApexSpiral
