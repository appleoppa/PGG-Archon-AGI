---
name: rust-core-module-development
description: Rust 核心模块开发：从零实现 Hermes 核心能力，包括 PyO3 FFI、编译配置、测试验证
tags: [rust, pyo3, ffi, core-development, performance]
---

# Rust 核心模块开发

为 Hermes 开发 Rust 原生核心模块，通过 PyO3 FFI 与 Python 集成。

## 触发条件

- 需要性能关键模块（token 计数、并发调度、状态机）
- Python 实现存在性能瓶颈或内存安全问题
- 需要精确控制（如精确 token 计数、坐标追踪）
- 需要真实并发（无 GIL 限制）
- 需要把 Rust CLI/daemon sidecar 接入 Feishu/Lark webhook，并补上下文记忆、错误分诊、launchd 常驻和真实 provider 调用闭环

## 项目结构

```
~/.hermes/core-reform/<module-name>/
├── Cargo.toml              # 项目配置
├── .cargo/config.toml      # 编译配置（重要！）
├── src/
│   ├── lib.rs              # 主入口
│   ├── <module>.rs         # 核心模块
│   └── ffi.rs              # Python FFI 接口
├── tests/
└── target/release/
    └── <module>.so         # 编译产物
```

## Cargo.toml 配置

```toml
[package]
name = "hermes_<module>"
version = "0.1.0"
edition = "2021"

[lib]
name = "hermes_<module>"
crate-type = ["cdylib", "rlib"]  # cdylib 用于 Python FFI

[dependencies]
# Python FFI
pyo3 = { version = "0.22", features = ["extension-module"] }

# 序列化
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

# 错误处理
anyhow = "1.0"
thiserror = "1.0"

# 日志
log = "0.4"
env_logger = "0.11"

[dev-dependencies]
# 根据需要添加测试依赖
```

## 编译配置（macOS ARM64）

**关键**：必须创建 `.cargo/config.toml` 配置动态链接：

```toml
[build]
rustflags = ["-C", "link-arg=-undefined", "-C", "link-arg=dynamic_lookup"]

[env]
PYO3_PYTHON = "/Users/appleoppa/.hermes/hermes-agent/venv/bin/python"
```

**说明**：
- `dynamic_lookup`：允许 Python 符号在运行时解析，避免链接错误
- `PYO3_PYTHON`：指定 Hermes venv 的 Python，确保版本一致

## PyO3 FFI 接口模式

### 基本结构

```rust
use pyo3::prelude::*;

#[pyclass]
struct PyMyModule {
    inner: MyModule,
}

#[pymethods]
impl PyMyModule {
    #[new]
    fn new(param: &str) -> PyResult<Self> {
        let inner = MyModule::new(param)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(Self { inner })
    }

    fn method(&self, arg: &str) -> PyResult<String> {
        self.inner.method(arg)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }
}

#[pymodule]
fn hermes_my_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyMyModule>()?;
    Ok(())
}
```

### 返回 Python 字典

```rust
fn return_dict(&self, py: Python) -> PyResult<PyObject> {
    let dict = pyo3::types::PyDict::new_bound(py);
    dict.set_item("key", "value")?;
    dict.set_item("count", 42)?;
    Ok(dict.into())
}
```

### 可选参数

```rust
#[new]
#[pyo3(signature = (required, optional=None))]
fn new(required: &str, optional: Option<usize>) -> PyResult<Self> {
    // ...
}
```

## 编译流程

```bash
cd ~/.hermes/core-reform/<module-name>

# 首次编译
cargo build --release

# 重命名为 Python 可导入的格式
cd target/release
cp lib<module>.dylib <module>.so  # macOS
# 或
cp lib<module>.so <module>.so     # Linux
```

### macOS 二进制部署签名门禁

当把 Rust CLI 二进制从 `target/release/` 复制到运行路径（如 `~/.local/bin/`）后，如果直接运行出现 `Killed: 9`、launchd 反复退出、或 `spctl` 显示 rejected，不要误判为代码逻辑崩溃。先执行签名重置：

```bash
codesign --remove-signature /path/to/binary 2>/dev/null || true
codesign --force --sign - /path/to/binary
/path/to/binary version  # 或 --help/status 做最小运行验证
```

部署型闭环顺序：`cargo test` → `cargo build --release` → 备份旧二进制 → 复制新二进制 → `chmod 755` → 上述 codesign → 最小命令验证 → 重启服务/launchd → 健康检查 → 真实功能烟测。

## 测试验证

### Rust 单元测试

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic() {
        let module = MyModule::new("test").unwrap();
        assert_eq!(module.method("input"), "expected");
    }
}
```

运行：`cargo test --release`

### Python 集成测试

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/path/to/target/release')

import hermes_my_module as hm

# 测试
obj = hm.PyMyModule("param")
result = obj.method("test")
print(f"✅ Result: {result}")
```

运行：`~/.hermes/hermes-agent/venv/bin/python test_python.py`

## Rust CLI/daemon sidecar + Feishu/Lark webhook 经验

当 Rust sidecar 已能接收 Feishu/Lark 事件并调用真实 LLM provider，但用户反馈“笨、不懂上下文、报错不会修复”时，不要把“链路打通”误报成“能力已同步”。必须分别检查：transport（事件通路）、model（真实 provider）、conversation（chat_id 上下文）、triage（错误分诊）、knowledge sync（安全知识同步）、execution/escalation（真实执行/升级）。

关键做法：

1. 用 SQLite 按 `chat_id` 持久化最近 user/assistant 消息；用户说“继续/修复/还是报错/不对”时，prompt 必须注入同一 `chat_id` 最近上下文。
2. 增加错误分诊表，分类 provider_auth/provider_rate_limit/provider_timeout/feishu_config/feishu_encrypt/webhook_payload/runtime_panic/unknown_error，并把 category/evidence/last_error_context/suggested_actions 注入 prompt。
3. 模型调用失败时返回结构化 fallback，并记录到上下文，避免下一轮“继续修复”失去依据。
4. 明确边界：context/evolution ledger 不等于自动学习 Hermes 主智能体；如需学习，必须另建 curated knowledge sync，不得直接吞 raw memory/secrets/session context。
5. macOS 部署后仍需 release build、复制 binary、重新 codesign、launchctl kickstart、status/healthz 烟测。

会话级细节和可复用 SQL/验证流程见：`references/rust-cli-feishu-context-triage-pattern.md`。

## 常见陷阱

### 0. 外部 Rust/Python 仓库不能把 Web UI 启动等同于 Rust 核心部署

外部生成或复刻的仓库常同时包含 Python Web UI、根 Rust crate、嵌套 Rust crates、脚本和自动进化入口。部署时要分层验收：

1. 先做静态安全扫描和入口识别，不直接运行 `install.sh` / `setup.sh`。
2. Python Web UI 可先用本地 `.venv` 部署验证；本地验证服务默认绑定 `127.0.0.1` 且关闭 debug。
3. GitHub Push Protection 拦截历史密钥时，不绕过；创建脱敏镜像，替换 token 后重新提交。
4. Rust 侧先跑 `cargo metadata`，再跑 `cargo check`。遇到 workspace member 无 target、模块实际在 `src/` 外、feature 引用非 optional dependency 等问题，按结构修复后再继续。
5. 如果 Rust 仍有批量语法错误，只能汇报“Web/Python 部分部署成功，Rust 核心未编译通过”，不能把整体说成已部署。

详细排查清单见 `references/external-rust-repo-bootstrap-triage.md`。

### 0a. macOS Rust CLI / launchd 部署门禁

当 Rust 项目不是 PyO3，而是 CLI / daemon / launchd service 时，也要按“源码通过 ≠ 已部署可用”分层验证：

1. **先测源码态**：`cargo test`、`cargo build --release`、`target/release/<bin> version/status/send`。
2. **再测安装态**：复制到 `~/.local/bin` 或目标路径后，必须运行目标路径的二进制，而不是只运行 `target/release`。
3. **macOS 复制后被 Kill 9**：如果 `target/release/<bin>` 能运行，但复制后的二进制在目标路径执行时 `Killed: 9`，对目标文件执行：
   ```bash
   codesign --remove-signature /path/to/bin 2>/dev/null || true
   codesign --force --sign - /path/to/bin
   ```
   然后重新运行目标路径验证。
4. **launchd wrapper 环境不同**：直接运行 `<bin> providers` 可能缺少 wrapper 注入的 `.env` / secrets；要同时验证 `<wrapper> providers` 或 launchd 环境中的 provider 列表。
5. **stale PID 门禁**：daemon 启动逻辑不能只判断 pid 文件存在；必须读取 PID 并用 `kill -0 <pid>` 验证进程真实存活。PID 不存活时应清理 stale pid file 后继续启动。
6. **服务态验证**：`launchctl kickstart -k gui/$(id -u)/<label>` 后，检查 launchctl、进程、`status`、端口/health endpoint（如 `/healthz`）和一条真实业务调用。
7. **仓库清洁**：运行态数据库、`target/.rustc_info.json` 等不要混入提交；必要时把 `*.db`, `*.db-shm`, `*.db-wal` 加入 `.gitignore`，只提交源码/配置/测试相关文件。

### 1. 链接错误（symbol not found）

**症状**：编译时出现 `symbol not found` 错误，如 `_PyType_GetName`, `__Py_IncRef` 等 Python C API 符号找不到。

**原因**：
- macOS 上 PyO3 生成 `.dylib` 而不是 `.so`
- 需要重命名为 `.so` 才能被 Python 导入
- 依赖过多（如 git2, reqwest, tree-sitter）可能导致链接复杂度增加

**解决方案**：
1. 确保 `Cargo.toml` 配置正确：
   ```toml
   [lib]
   crate-type = ["cdylib", "rlib"]

   [dependencies]
   pyo3 = { version = "0.22", features = ["extension-module"] }
   ```

2. 编译后重命名（macOS）：
   ```bash
   cp target/release/libmodule_name.dylib \
      ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/module_name.so
   ```

3. 如果依赖过多导致链接失败：
   - **方案 A**：简化依赖（移除非必需的 crate，如 git2 改用命令行 git，reqwest 改用 curl）
   - **方案 B**：提供 Rust CLI + Python 包装器（推荐）
     ```toml
     # Cargo.toml
     [lib]
     crate-type = ["rlib"]  # 移除 cdylib

     [[bin]]
     name = "tool_name"
     path = "src/bin/tool_name.rs"

     [dependencies]
     clap = { version = "4.0", features = ["derive"] }
     # 移除 pyo3
     ```

     Python 包装器：
     ```python
     import subprocess
     import json

     def call_rust_tool(args):
         result = subprocess.run(
             ["tool_name"] + args,
             capture_output=True,
             text=True,
             check=True
         )
         return json.loads(result.stdout)
     ```

   - **方案 C**：使用 subprocess 调用独立的 Rust 二进制（适合已有 CLI 工具）

4. 验证安装：
   ```bash
   # FFI 方式
   ~/.hermes/hermes-agent/venv/bin/python -c "import module_name; print('✅ 可用')"

   # CLI 方式
   tool_name --help
   ```

**成功案例**（已集成）：
- `hermes_context_engine`: 9.2 MB, 依赖 tiktoken-rs, Python FFI
- `hermes_multi_model_router`: 4.4 MB, 依赖 tokio, Python FFI
- `hermes_eval_center`: 2.4 MB, 依赖 rusqlite, Python FFI
- `devour`: CLI 工具, 依赖 tree-sitter + walkdir, Python 包装器调用

**失败案例及解决方案**：
- `hermes_devour_engine`: 链接失败，依赖 git2 + tree-sitter + reqwest 过多
  - **解决方案**：编译为独立 CLI 工具 + Python 包装器
  - 移除 PyO3 依赖，编译为纯 Rust 二进制
  - 提供 Python subprocess 包装器调用 CLI
  - 优势：无链接问题、独立部署、功能完整

### 1a. 原有症状：
```
ld: symbol(s) not found for architecture arm64
_PyDict_New, _PyModule_Create2, etc.
```

**原因**：未配置动态链接

**修复**：创建 `.cargo/config.toml` 并添加 `dynamic_lookup`

### 2. 模块导入失败

**症状**：`ImportError: dlopen(...): symbol not found`

**原因**：
- 文件名不匹配（需要 `module_name.so`，不是 `libmodule_name.dylib`）
- Python 版本不匹配（编译时用 3.11，运行时用 3.9）
- 依赖库缺失

**解决方案**：
1. 检查文件名和位置
2. 使用正确的 Python 版本编译和运行
3. 验证依赖库已安装

### 3. 可选依赖和特性门控

**场景**：模块需要 PyO3 FFI，但也要支持纯 Rust 使用（如库模式）。

**解决方案**：
```toml
[features]
default = []
python = ["pyo3"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"], optional = true }
```

在代码中：
```rust
#[cfg(feature = "python")]
pub mod ffi;

#[cfg(feature = "python")]
use pyo3::prelude::*;
```

编译：
```bash
# 纯 Rust 库
cargo build --release

# Python FFI
cargo build --release --features python
```

**实际案例**：`hermes_eval_center` 使用此模式，支持纯 Rust 和 Python FFI 两种用法。

### 4. 结构体字段不匹配

**症状**：编译错误 `no field named 'xxx'` 或 `unknown field`

**原因**：FFI 层使用的结构体与内部实现不一致

**解决方案**：
1. 先检查内部结构体定义：
   ```bash
   grep -A 20 "pub struct Trace" src/trace_pool.rs
   ```

2. 根据实际字段调整 FFI 接口：
   ```rust
   // 错误：假设字段
   let trace = Trace {
       tool_name: "...",
       duration_ms: 100.0,  // 字段不存在
   };

   // 正确：使用实际字段
   let trace = Trace {
       task: "...",
       input: "...",
       output: "...",
       tool_calls: "...",
       // ... 其他实际字段
   };
   ```

3. 如果需要不同的接口，创建适配层而不是直接修改内部结构

**实际案例**：`hermes_eval_center` 的 `Trace` 结构体用于训练轨迹（task/input/output），而不是工具调用轨迹（tool_name/duration_ms）。FFI 层需要适配这个差异。

### 5. 方法签名不匹配

**症状**：编译错误 `this function takes N arguments but M were supplied`

**解决方案**：
1. 检查方法实际签名：
   ```bash
   grep -A 5 "pub fn method_name" src/*.rs
   ```

2. 调整调用以匹配签名：
   ```rust
   // 错误：缺少参数
   state_machine.transition(&trace_id, TraceState::Active);

   // 正确：提供所有必需参数
   state_machine.transition(
       trace_id,
       TraceState::Active,
       "reason".to_string(),
       "actor".to_string()
   );
   ```

**实际案例**：`StateMachine::new()` 需要初始状态参数，`transition()` 需要 4 个参数而不是 2 个。

### 6. 原有内容：
```python
ImportError: No module named 'hermes_my_module'
```

**原因**：库文件名不正确

**修复**：
```bash
# macOS
cp libhermes_my_module.dylib hermes_my_module.so

# Linux
cp libhermes_my_module.so hermes_my_module.so
```

### 3. PyO3 API 版本问题

**症状**：
```
error[E0599]: no method named `add_class` found
error[E0599]: no function or associated item named `new` found for struct `PyDict`
```

**原因**：PyO3 0.22 API 变化

**修复**：
- `PyDict::new(py)` → `PyDict::new_bound(py)`
- `m.add_class::<T>()` → `m.add_class::<T>()`（参数类型从 `&PyModule` 变为 `&Bound<'_, PyModule>`）

### 4. 类型推断失败

**症状**：
```
error[E0689]: can't call method `min` on ambiguous numeric type `{float}`
```

**修复**：显式标注类型
```rust
let mut score: f64 = 0.5;  // 而不是 let mut score = 0.5;
```

## 性能优化

### 1. 使用 `--release` 编译

开发时可用 `cargo build`，但最终必须用 `cargo build --release`：
- 优化级别：O3
- 性能提升：10x-100x
- 二进制大小：更大，但性能优先

### 2. 避免不必要的克隆

```rust
// ❌ 慢
fn process(&self, data: String) -> String {
    data.clone()
}

// ✅ 快
fn process(&self, data: &str) -> String {
    data.to_string()
}
```

### 3. 使用 `&str` 而非 `String`

FFI 接口优先使用 `&str`，只在必要时转换为 `String`。

## 集成到 Hermes

### 1. 安装到 venv

```bash
cp target/release/<module>.so \
   ~/.hermes/hermes-agent/venv/lib/python3.11/site-packages/
```

### 2. 在 Python 中使用

```python
# 在 run_agent.py 或其他模块中
try:
    import hermes_my_module as hm
    tokenizer = hm.PyTokenizer("gpt-4")
    count = tokenizer.count_text("Hello, world!")
except ImportError:
    # 降级到 Python 实现
    pass
```

### 3. 验证兼容性

- 运行现有测试套件
- 检查性能提升
- 验证结果一致性

## 备份与回滚

**改造前必须备份**：
```bash
timestamp=$(date +%Y%m%d_%H%M%S)
backup_dir=~/.hermes/backups/core_reform_$timestamp
mkdir -p $backup_dir
cp -r ~/.hermes/hermes-agent $backup_dir/
cp ~/.hermes/config.yaml $backup_dir/
```

**回滚**：
```bash
cp -r $backup_dir/hermes-agent ~/.hermes/
```

## 开发检查清单

- [ ] 创建项目结构
- [ ] 配置 `Cargo.toml`（包含 `crate-type = ["cdylib"]`）
- [ ] 创建 `.cargo/config.toml`（动态链接配置）
- [ ] 实现核心 Rust 模块
- [ ] 实现 PyO3 FFI 接口
- [ ] 编写 Rust 单元测试
- [ ] 编译 release 版本
- [ ] 重命名库文件为 `.so`
- [ ] 编写 Python 集成测试
- [ ] 验证功能正确性
- [ ] 性能基准测试
- [ ] 备份现有系统
- [ ] 集成到 Hermes
- [ ] 验证兼容性
- [ ] 文档更新

## 参考案例

### Context Engine

**功能**：精确 token 计数、坐标追踪、智能压缩

**关键依赖**：
- `tiktoken-rs = "0.5"` - OpenAI tokenizer
- `pyo3 = { version = "0.22", features = ["extension-module"] }`

**性能**：
- Token 计数精度：<1% 误差
- 速度提升：10x+

### 评估中心

**功能**：状态机、SQLite 轨迹池、自动评分

**关键依赖**：
- `rusqlite = { version = "0.32", features = ["bundled"] }`
- `chrono = { version = "0.4", features = ["serde"] }`
- `uuid = { version = "1.0", features = ["v4", "serde"] }`

**架构**：
- 5 状态生命周期管理
- 自动评分触发训练
- 完整转换历史记录

## 参考文档

- **第一阶段实现**：`references/context-engine-eval-center-implementation.md`
- **第三阶段实现**：`references/phase3-devour-engine-implementation.md`
- **CLI + Python 包装器模式**：`references/cli-wrapper-pattern.md` - 当 PyO3 FFI 遇到链接问题时的替代方案
- **第四阶段经验总结**：`references/core-reform-phase4-lessons.md` - 务实的架构决策、完整项目总结、与超级进化的对应关系
- **外部 Rust/Python 仓库部署排查**：`references/external-rust-repo-bootstrap-triage.md` - 脱敏镜像、Web UI 安全启动、workspace/模块路径/feature 修复和部分部署汇报门禁
- **外部 AGI/Rust 仓库全量运行门禁**：`references/external-agi-rust-full-run-gate.md` - 用户要求“立刻全量运行”时的低副作用检查顺序、服务启动门禁、阻断分类和交付模板
- **外部 AGI/Rust 仓库可运行部署模式**：`references/external-agi-rust-runtime-deployment.md` - 大量生成源码残缺时，如何诚实收敛为根 Rust crate 可编译、Web UI 可代理、真实 LLM 可调用的本地部署面
- **Rust CLI 进化流水线持久化账本模式**：`references/rust-cli-evolution-ledger-pattern.md` - 将只输出 stdout/log 的 evolution/benchmark/multi-LLM pipeline 收敛为 SQLite 可查询闭环，含 CLI、测试、部署、读回和提交门禁。
- **Rust CLI 飞书上下文记忆与报错分诊模式**：`references/rust-cli-feishu-context-memory-pattern.md` - 当 Feishu/Lark webhook 机器人“不懂上下文/报错不会修”时，按 chat_id 建 SQLite 对话记忆、构造 contextual prompt、包装错误为可修复任务，并验证部署。

## 相关技能

- `hermes-agent` - Hermes 配置和排障
- `hermes-evolution` - 将改进沉淀为技能

## 注意事项

1. **不要修改 Hermes 核心代码**：新模块应该是独立的，通过 FFI 集成
2. **保持向后兼容**：提供降级到 Python 实现的路径
3. **完整测试**：Rust 单元测试 + Python 集成测试
4. **性能验证**：确保实际有性能提升
5. **文档完整**：API 文档、集成指南、故障排除
