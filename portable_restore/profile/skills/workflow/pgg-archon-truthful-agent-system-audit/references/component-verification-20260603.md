# PGG Archon Component Verification Snapshot — 2026-06-03

## Verified System State

### PGG Profiles (12 confirmed)
pgg-zhixing, pgg-xunshi, pgg-zhinao, pgg-shenji, pgg-zhengju, pgg-anguan, pgg-xingshi, pgg-minshi, pgg-feisu, pgg-tuiyan, pgg-guwen, pgg-law

Skill counts per profile: pgg-anguan=88, pgg-feisu=88, others similar range. NOT 1 per profile as initially estimated.

### Python Modules
| Module | Importable | Location | Functional |
|---|---|---|---|
| apex_god | ✓ | hermes-agent/apex_god/__init__.py | ✗ Empty __init__.py, no real code |
| hermes_apex_evolution | ✓ | venv/lib/python3.11/site-packages/ | ✓ Has .so file, real functions |
| constraint_engine | ✗ | Only in external repo (github/z-dashen/apex/LLM-Pangu/) | N/A in main system |
| self_healing | ✗ | Not found anywhere | N/A |
| gene_db | ✗ | Not found anywhere | N/A |

### Launchd Services (15 total, 12 active)
- 12 gateway services: ai.hermes.gateway-pgg-* (all with valid PIDs)
- 2 dead services: com.appleoppa.apex-god.autoloop, com.appleoppa.apex-god.ars (exit code 0, PID=-)
- 1 evol-watcher service

### Key Files
| File | Found | Location |
|---|---|---|
| constraint_engine.py | ✓ | workspace/github/z-dashen/apex/LLM-Pangu/core/ (external) |
| self_healing.py | ✗ | Not found |
| gene_db.py | ✗ | Not found |
| boundary_enforcer.py | ✗ | Not found |
| apex_evolution_tool.py | ✓ | hermes-agent/tools/ (145 lines) |
| legal_benchmark.py | ✓ | apex_god/ |

### Critical Finding: Profile Memory Hash
All 12 profiles had identical MEMORY.md (MD5: ceae7670f12db0ab82bee90ac1a5815b). This indicates batch-generated placeholder content, not specialized agent memories.

### Workspace Stats
- 693 Python files in workspace
- 47 subdirectories in workspace
- 法律知识库 exists at workspace/知识库
- 苹果中枢办案库 exists with real case files (PGG-MS-20260601-0001/0002/0004)

## Assessment Scores (4-LLM consensus)

| Dimension | GPT-5.5 | Claude | DeepSeek | MIMO |
|---|---|---|---|---|
| Architecture | 38 | 35 | - | - |
| Code Usability | 25 | 20 | - | - |
| Security | 42 | 🔴 High Risk | - | 🔴 High Risk |
| Autonomy/Evolution | 15 | 🔴 Missing | - | - |
| Legal Coverage | 55 | - | 68 | - |
| Observability | 35 | - | - | - |
| Legal Accuracy | - | - | 62 | - |
| Case Workflow | - | - | 82 | - |
| Document Gen | - | - | 45 | - |
| Compliance | - | - | 75 | 🔴 High Risk |

Weighted composite: 39.4/100 (down from previous 46.5 due to more thorough verification)

## Self-Assessment Gap Analysis

| Metric | AGENTS.md Claim | External Verification | Gap |
|---|---|---|---|
| Phase Status | Phase217 PASS | Code usability 8-12% | Severe |
| GeneDB | gene 172 read back | File does not exist | Complete fabrication |
| Self-healing | Full self-heal | Fake success on LLM failure | False |
| Component availability | 99.9% | 6.5-12% | 87-93 points |
| AGI relevance | L6 Legal AGI | Narrow-domain Legal AI | Overclaimed |
