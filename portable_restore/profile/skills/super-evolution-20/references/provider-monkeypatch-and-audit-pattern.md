# Provider Monkeypatch + Audit Trail + Fail-Closed 模式

2026-06-01 为关闭 GPT-5.5 审计的三个 P0 缺口（不可绕过性45、可验证性40、生产审计38）而实现。

## 1. Provider Monkeypatch (`provider_monkeypatch.py`)

**解决的问题**: kernel.py 是 wrapper 级，有人可以绕过它直连 SDK。

**方案**: Monkey-patch `openai.OpenAI.__init__` 和 `anthropic.Anthropic.__init__`，使得任何人创建客户端实例时自动被拦截并包装。

**核心代码模式**:
```python
_original_openai_init = openai.OpenAI.__init__
@functools.wraps(_original_openai_init)
def _patched_openai_init(self, *args, **kwargs):
    _original_openai_init(self, *args, **kwargs)
    # 自动将 chat.completions.create 包装为 kernel 调用
    original_create = self.chat.completions.create
    self.chat.completions.create = _make_kernel_wrapper(original_create)
```

**来源**: MLflow OpenAI autologging 的 `safe_patch` 模式 (github.com/mlflow/mlflow)

**验证**: `se20/health.py` 检查 `_PATCHED` 状态

## 2. Audit Trail (`audit_trail.py`)

**解决的问题**: 无生产级审计日志，无法检测篡改。

**方案**: 追加式 JSONL 文件 + SHA-256 hash chain 链接每条记录。

**核心模式**:
```
log_entry = {
  "entry_id": uuid,
  "timestamp": ISO datetime,
  "event_type": "info|warn|error|audit",
  "source": "module_name",
  "details": { ... },
  "prev_hash": "sha256_of_previous_entry",
  "entry_hash": "sha256_of_this_entry_content+prev_hash"
}
```

**功能**:
- `append(event_type, source, details)` — 追加写入，原子性保证（fsync）
- `verify()` — 遍历整个链检查 hash 连续性，返回第一个断裂点
- `get_stats()` — 条目数、文件大小、最新 hash 前缀

**来源**: Merkle-tree / crypto_log hash chain 模式

## 3. Fail-Closed (`fail_closed.py`)

**解决的问题**: 生产环境需要"如果内核不可用则禁止 LLM 调用"的零信任模式。

**方案**: Circuit-breaker 熔断器 + context manager 包装。

**核心模式**:
```python
@fail_closed
def llm_call(prompt):
    return provider.call(prompt)  # 如果health_check失败，自动抛出FailClosedError
```

**行为**:
- `closed=False`（默认开放）— 允许调用
- 每次调用前调用 `health_check()` 快照
- 发现关键组件（kernel、monkeypatch、audit_trail）不可用时自动熔断
- 通过 `reset()` 恢复

## 4. Health Check (`health.py`)

**解决的问题**: 统一可见性：8条规则 + 3个新模块是否都在运行。

**方案**: 11项检查器，每项返回 `{rule, name, healthy, status, detail}`。

检查项:
- R1: Ω_A — Akashic Memory
- R2: β_bg — Post-Evaluation
- R3: α_ack — Convergence Gate
- R4: Θ_TRI — Three-Thinking
- R5: EVM — Entropy Variance
- R6: A·B·TDHLGWB — 5D Behavior
- R7: -ΣΔ_all — Defect Deduction
- R8: ∞loop — Infinite Recursion
- Provider interception (OpenAI + Anthropic)
- Audit trail integrity
- Fail-closed gate status

## 集成方式

所有模块自动注册到 `auto_bootstrap.py`，import 时一起激活：

```python
# auto_bootstrap.py
from se20.provider_monkeypatch import _monkeypatch_openai, _monkeypatch_anthropic
_monkeypatch_openai()
_monkeypatch_anthropic()

from se20.audit_trail import AuditTrail
AuditTrail().info("system", "SE20 kernel activated")

from se20.health import health_check
health_check()  # 记录初始状态
```
