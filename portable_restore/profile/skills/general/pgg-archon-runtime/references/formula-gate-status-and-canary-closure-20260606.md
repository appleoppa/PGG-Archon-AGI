# 2026-06-06 — /goal 公式门禁状态面板与 bounded canary 闭环经验

## 触发背景

用户指出：虽然设定了“每次对话及工作都代入完整公式验证 AGI 为基本准则”，但实际执行时用户“没感觉到”。这说明只把公式内化为思考规则不够；AGI/进化/系统任务必须让公式门禁可见、可运行、可测试、可读回。

## 已沉淀的工程模式

### 1. 显式公式门禁状态面板

新增/采用模式：

```bash
PYTHONPATH=$HERMES_AGENT \
$HERMES_AGENT/venv/bin/python -m agent.pgg_archon_formula_gate_status \
  '本轮任务描述'
```

输出必须包含：

- `/goal` 来源；
- 总纲1：AGI L0-L5 六维；
- 总纲2：`Agent_Evolve = LDR(K) → GapDetect → CodeSelfFix → HotReload → TaskSolve → KnowledgeSettle`；
- T 目标但明确 `not T5 proof`；
- Manifest evidence；
- 真实性边界：not full AGI / not official benchmark / not legal correctness / not production takeover。

### 2. Manifest evidence 计数口径

不要只统计 exact `PASS`。Manifest 里存在：

- `PASS`；
- `PASS_*` / `PASS_SCAFFOLD_*` / `PASS_RUST_*` 等 PASS-family；
- `WATCH`；
- `PARTIAL_*`。

状态面板应分开展示：

```text
latest PASS族=N
exact PASS=M
```

这样既不低估 scaffold/canary 的真实进化证据，也不把 `PARTIAL` / `WATCH` 冒充 PASS。

### 3. OmniRoute enforce/substitution canary 边界

逐级推进，不跳级：

1. route_suggest / mirror-only；
2. default-off enforce canary；
3. enforce window test；
4. substitution plan；
5. single bounded substitution canary；
6. fallback-window telemetry。

任何一步都不能宣称 global route enforcement 或 production takeover。

关键边界字段：

- `same_class_substitution_success`：同类 provider 替代是否成功；
- `fallback_participation_success`：fallback lane 是否可调用；
- `cross_class_fallback`：是否跨类 fallback；
- `fail_open_passthrough`：未 enforce 时原路径继续，不阻断。

DeepSeek fallback 成功只能证明 fallback lane 可调用，不能冒充 GPT same-class substitution 成功。

### 4. MiMo audit retry 规则

MiMo 是 third-party judge，不参与 ordinary processing。

当 MiMo 审计输出 `OK_UNPARSED` / timeout / ERROR 时，可以做一次 targeted retry，但只有满足：

```text
retry.status == OK_PARSED
retry.audit_verdict in {PASS, WATCH, BLOCKED}
```

才替换原结果。否则必须保留原失败/未解析状态，不能硬转 PASS。

Prompt 应尽量要求：

```text
STRICT JSON，不要 Markdown 代码块；reason 一句话；禁止双引号、换行、反斜杠。
```

### 5. Promptfoo / Legal boundary / Rust gate 口径

Promptfoo 自建测试套件应表述为：

```text
自建 promptfoo CLI smoke（使用 promptfoo 官方 CLI 工具执行）
```

不得写成“官方 benchmark 分数”。

Promptfoo finalize 在 closure 生成后，应回填 Manifest：

- `closure_path`；
- `closure_sha256`。

Rust gate 应校验 report / audit summary / closure / manifest sha256，仍只证明 internal smoke/gate，不证明官方 benchmark 或法律正确性。

## 验证清单

每次推进此类任务至少运行：

```bash
PYTHONPATH=$PWD venv/bin/python -m pytest -q <focused tests>
PYTHONPATH=$PWD venv/bin/python -m py_compile <touched python files>
```

Rust/PyO3 crate 在 macOS 上优先：

```bash
PYO3_PYTHON=$PWD/venv/bin/python /Users/appleoppa/.cargo/bin/cargo test --manifest-path <Cargo.toml>
```

避免系统 Python 3.9 与 `abi3-py311` 冲突。

## Pitfalls

- 用户说“没感觉到你执行公式”时，不要辩解“我内化了”；应立刻切换到显式公式门禁。
- `Manifest latest PASS` 只数 exact `PASS` 会低估 `PASS_*` scaffold/canary 状态；但也不能把 `WATCH`/`PARTIAL` 算 PASS。
- broad `except Exception` 会把 FastAPI `HTTPException(400)` 吞成 500；Web API validator 后要 `except HTTPException: raise`。
- fallback lane 成功不是 same-class substitution 成功。
- `workspace/`、promptfoo raw artifacts、runtime evidence 不能进 repo；放 `~/.hermes/workspace/` 并保持 git clean。
