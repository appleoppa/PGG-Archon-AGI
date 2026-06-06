# Local AGI Process Objective Scoring — Reference

Use when the user asks to “全面测试本机 AGI 进程 / 客观评分 / 全面审计 PGG Archon”. This reference captures a reusable scoring workflow from a real 2026-06-03 audit.

## Evidence-first sequence

1. **Runtime inventory**
   - `ps -axo pid,ppid,pcpu,pmem,etime,args | egrep -i 'apex|pgg|archon|agnes|claude|codex|gpt|ollama|openhuman|claw|mcp|dify|flowise|n8n'`
   - `launchctl list | egrep -i 'apex|pgg|archon|ollama|openhuman|claw|mcp|dify|flowise|n8n|hermes'`
   - `lsof -nP -iTCP -sTCP:LISTEN`
   - For launchd labels, use `launchctl print gui/$(id -u)/<label>` to verify `state`, `pid`, `program`, `arguments`, stdout/stderr, working directory.

2. **HTTP / port smoke**
   - Probe known local ports and distinguish “expected absent” from failure.
   - WebUI health may be at `/health`; `/api/health` can require auth. Do not call auth-protected API failure a runtime failure if public `/health` passes.

3. **Manifest and ledger readback**
   - Read `~/.hermes/data/EVOLUTION_MANIFEST.json` and `~/.hermes/data/pgg-background-evolution/status.json`.
   - Treat manifest scores as claims until independently checked.
   - Preserve metric semantics: infrastructure readiness is not external AGI capability.

4. **Import and CLI checks**
   - Import actual modules from the active Hermes venv.
   - Run Rust/native CLI help and bounded commands, e.g. `apex13 --help`, `apex13 background --mode autoloop`.
   - If `eval` requires `--workspace`, run with the correct workspace and compare against background mode.

5. **Tests**
   - Use exact known test files rather than shell globs that may not expand or may match nothing.
   - Run relevant tests, not only collection. Report pass/fail counts and the concrete failure API/contract.

6. **Multi-profile reality checks**
   - Count actual skills under each profile.
   - Hash profile memories to detect cloned/non-specialized profile state.
   - Smoke the orchestration import path; profile gateways running ≠ case pipeline usable.

7. **Logs and noise**
   - Summarize recent errors from default gateway and pgg profile logs.
   - Classify provider connection/TTFB issues as stability risk, not necessarily total outage.

8. **Git/governance state**
   - Check untracked or modified PGG/APEX overlays. Untracked core capability files reduce reproducibility and should lower governance score.

## Suggested scoring dimensions

Use weighted dimensions and calculate explicitly:

- Process/service runtime — 15%
- Component importability and structural integrity — 15%
- Tests/regression stability — 18%
- Rust-native evolution and convergence — 16%
- Multi-agent/legal case pipeline — 14%
- Model provider availability/stability — 10%
- Governance/truthfulness/reproducibility — 12%

Report both the weighted total and why each dimension was discounted.

## Common pitfalls

- **Manifest mismatch**: a manifest can report `32/32 importable` while direct imports fail. Prefer direct import evidence.
- **File existence ≠ capability**: provider monkeypatch files, case orchestrator files, and profile directories need import/smoke/test proof.
- **Gateway running ≠ department specialization**: if all profile memories share the same hash, report specialization as partial even if gateways are alive.
- **Infrastructure score ≠ AGI score**: Rust background readiness or ΔE can be strong while end-to-end legal/case/provider stability remains mid-range.
- **Protected/expected-absent components**: do not restore APEX-MEM, OpenClaw, Ollama, LM Studio, etc. just because ports are closed; classify absence.

## Reporting pattern

Keep the user-facing report concise and fieldized:

```text
状态：已完成只读全面测试
总分：XX / 100
口径：运行态 + 结构 + 测试 + 治理；不是 full AGI 或外部 benchmark 分
已核验：process / launchd / ports / HTTP / manifest / imports / tests / logs / git
P0：...
P1：...
结论：...
下一步：按 P1 修复顺序推进
```
