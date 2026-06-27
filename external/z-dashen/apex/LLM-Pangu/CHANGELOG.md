# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.1.0] - 2026-05-08

### Fixed

- README夸大描述全部修正为诚实说明
- 明确标注各项功能的真实实现状态
- LLM接入标注为"开发中"而非"已完成"
- 移除"全球首个"等无法证实的宣称
- CHANGELOG同步更新v1.1.0修复版本

## [1.0.0] - 2026-05-08

### Added

- **Core Formula (core/delta_g_formula.py)**
  - Shannon entropy calculation
  - Shannon channel capacity calculation
  - Code redundancy measurement
  - ΔG unified formula with 7 dimensions
  - System state judgment (steady/mild/critical)

- **Emotion Module (emotion/)**
  - EmotionCore with valence/arousal/dominance
  - 7 base emotions with emoji icons
  - Emotional temperature coefficient (Ψ)
  - Tone injection for responses

- **Auto-Agent Module (auto_agent/)**
  - SelfInspect for global system inspection
  - SelfHeal for proactive self-repair
  - GitHubAutoFetch for real GitHub skill acquisition
  - AgentHook for module orchestration

- **Memory Module (memory/)**
  - MemoryPersist for cross-session persistence
  - MemoryHook for LLM integration

- **Code Standards Module (code_standard/)**
  - StandardBaseline for self-built code standards
  - CodeCompliance for automated checking
  - StandardHook for LLM integration

- **Alignment Module (align/)**
  - PromptAligner for prompt standardization
  - MDAligner for markdown format alignment

- **Documentation (docs/)**
  - APEX_DG_Theory.md - Complete theory whitepaper
  - Shannon + APEX integration
  - 7-module binding with formulas

- **Tests (tests/)**
  - 47 test cases covering all modules
  - 100% pass rate

- **CI/CD (.github/workflows/)**
  - GitHub Actions automated testing
  - Python 3.8+ support

### Features

- 7-module closed-loop architecture
- Physical foundation: Shannon Information Theory
- Global constraint: APEX ΔG Formula
- Human-like emotional temperature
- Proactive self-inspection and self-healing
- Real GitHub skill acquisition

---

## [0.0.0] - 2026-05-07

### Added

- Initial project creation
