# XuanjiQuant Local Self-Evolving Intelligent Quantitative Trading System

## Core Positioning

Relying on Tencent Finance official API, this project builds a localized exclusive quantitative database, running locally without cloud data leakage. It deeply integrates **Neural-Model Alignment** core algorithms to achieve autonomous intellectual evolution.

## Master Formula (Core Loss Function)

$$L_{total} = \alpha \cdot L_{class} + (1-\alpha) \cdot L_{neural}$$

### Sub-Formulas

**Classification Loss:**
$$L_{class} = CrossEntropy(y_{pred}, y_{true})$$

**Neural Alignment Loss:**
$$L_{neural} = MSE(f_{model}(x), f_{brain}(x))$$

### Key Parameters

| Symbol | Meaning |
|--------|---------|
| α | Balance coefficient (controls classification vs neural alignment weight) |
| f_model(x) | Multi-layer model feature extraction |
| f_brain(x) | Human brain EEG/fMRI neural representation |
| Goal | Joint optimization, improve model-brain representation similarity |

## Core Features

1. **Local Quantitative Database**: Tencent Finance API, private data storage
2. **Neural-Model Alignment**: Core algorithm-driven quantitative strategy optimization
3. **Fully Automatic Closed-Loop**: Daily sync, review, parameter adjustment, evolution
4. **Anti-Fraud Verification**: Full-cycle blind testing, strong/weak stock two-way verification

## Copyright Notice

MIT License - For study and research only
