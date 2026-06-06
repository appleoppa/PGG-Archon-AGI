# Rust CLI + Python 包装器模式

当 PyO3 FFI 遇到链接问题时的替代方案。

## 适用场景

- 依赖过多导致 PyO3 链接失败（如 git2, reqwest, tree-sitter 组合）
- macOS ARM64 上的符号解析问题
- 需要独立部署的工具
- 工具本身就适合 CLI 形式

## 实现步骤

### 1. Cargo.toml 配置

```toml
[package]
name = "tool_name"
version = "0.1.0"
edition = "2021"

[lib]
name = "tool_name"
crate-type = ["rlib"]  # 只编译为库，不编译 FFI

# CLI 二进制
[[bin]]
name = "tool_name"
path = "src/bin/tool_name.rs"

[dependencies]
# 移除 pyo3
# pyo3 = { version = "0.22", features = ["extension-module"] }

# 添加 CLI 参数解析
clap = { version = "4.0", features = ["derive"] }

# 其他依赖保持不变
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
anyhow = "1.0"
```

### 2. CLI 实现 (src/bin/tool_name.rs)

```rust
use clap::{Parser, Subcommand};
use tool_name::*;

#[derive(Parser)]
#[command(name = "tool_name")]
#[command(about = "工具描述", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// 子命令 1
    Parse {
        #[arg(short, long)]
        file: PathBuf,

        #[arg(short, long, default_value = "json")]
        format: String,
    },

    /// 子命令 2
    Process {
        #[arg(short, long)]
        input: String,

        #[arg(short, long)]
        output: Option<PathBuf>,
    },
}

fn main() -> anyhow::Result<()> {
    env_logger::init();
    let cli = Cli::parse();

    match cli.command {
        Commands::Parse { file, format } => {
            let result = parse_file(&file)?;

            if format == "json" {
                println!("{}", serde_json::to_string_pretty(&result)?);
            } else {
                println!("Summary: {:?}", result);
            }
        }

        Commands::Process { input, output } => {
            let result = process(&input)?;

            if let Some(path) = output {
                std::fs::write(path, serde_json::to_string_pretty(&result)?)?;
            } else {
                println!("{}", serde_json::to_string_pretty(&result)?);
            }
        }
    }

    Ok(())
}
```

### 3. 编译和安装

```bash
cd ~/.hermes/core-reform/tool_name

# 编译
cargo build --release --bin tool_name

# 安装到 PATH
cp target/release/tool_name ~/.local/bin/

# 验证
tool_name --help
```

### 4. Python 包装器

创建 `~/.hermes/hermes-agent/tool_name_wrapper.py`：

```python
"""
Tool Name - Python 包装器

通过 CLI 调用 Rust 实现
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any


class ToolName:
    """工具 Python 接口"""

    def __init__(self, bin_path: str = "tool_name"):
        """
        初始化

        Args:
            bin_path: 二进制文件路径，默认从 PATH 查找
        """
        self.bin_path = bin_path

    def parse_file(self, file_path: str, format: str = "json") -> Dict[str, Any]:
        """
        解析文件

        Args:
            file_path: 文件路径
            format: 输出格式 (json/summary)

        Returns:
            解析结果字典
        """
        result = subprocess.run(
            [self.bin_path, "parse", "--file", file_path, "--format", format],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)

    def process(
        self,
        input_data: str,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        处理数据

        Args:
            input_data: 输入数据
            output_file: 可选的输出文件路径

        Returns:
            处理结果
        """
        cmd = [self.bin_path, "process", "--input", input_data]
        if output_file:
            cmd.extend(["--output", output_file])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        if output_file:
            with open(output_file, 'r') as f:
                return json.load(f)
        else:
            return json.loads(result.stdout)


# 便捷函数
def parse_file(file_path: str, format: str = "json") -> Dict[str, Any]:
    """解析文件"""
    tool = ToolName()
    return tool.parse_file(file_path, format)


def process(input_data: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """处理数据"""
    tool = ToolName()
    return tool.process(input_data, output_file)


if __name__ == "__main__":
    # 示例用法
    import sys

    if len(sys.argv) < 2:
        print("用法: python tool_name_wrapper.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    result = parse_file(file_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

### 5. 使用示例

#### CLI 方式

```bash
# 直接使用 CLI
tool_name parse --file example.py
tool_name process --input "data" --output result.json
```

#### Python 方式

```python
from tool_name_wrapper import parse_file, process

# 解析文件
result = parse_file('example.py')
print(f"找到 {result['functions']} 个函数")

# 处理数据
output = process('input_data')
print(output)
```

## 优势

1. **无链接问题**：不依赖 PyO3，避免 macOS 链接错误
2. **独立部署**：CLI 工具可以独立使用，不依赖 Python
3. **功能完整**：所有 Rust 功能都可用，无 FFI 限制
4. **易于调试**：CLI 输出可以直接查看，不需要 Python 环境
5. **灵活调用**：可以从任何语言调用（Python、Shell、其他）

## 劣势

1. **性能开销**：subprocess 调用有启动开销（~10-50ms）
2. **序列化成本**：需要 JSON 序列化/反序列化
3. **错误处理**：需要解析 stderr 和退出码
4. **状态管理**：每次调用都是独立进程，无法保持状态

## 性能对比

| 场景 | FFI | CLI + 包装器 | 差异 |
|---|---:|---:|---|
| 单次调用 | ~1ms | ~20ms | 启动开销 |
| 批量调用（100次） | ~100ms | ~2s | 累积开销 |
| 长时间运行 | 优秀 | 优秀 | 无差异 |

**建议**：
- 频繁调用（>100次/秒）：优先 FFI
- 偶尔调用或批处理：CLI + 包装器完全可接受
- 依赖复杂导致 FFI 失败：CLI + 包装器是唯一选择

## 实际案例：devour

**背景**：
- 依赖：tree-sitter + git2 + reqwest + walkdir
- PyO3 FFI 在 macOS ARM64 上链接失败
- 符号解析错误：`_PyType_GetName`, `__Py_IncRef` 等

**解决方案**：
1. 移除 PyO3，编译为 CLI 工具
2. 提供 `devour` 命令：
   - `devour parse --file <file>`
   - `devour scan --dir <dir>`
   - `devour extract --file <file>`
3. Python 包装器 `devour_engine.py`

**结果**：
- ✅ 编译成功，无链接错误
- ✅ 功能完整，所有特性可用
- ✅ 性能优秀（AST 解析 <100ms）
- ✅ 易于使用（CLI 和 Python 双接口）

## 最佳实践

1. **JSON 输出**：CLI 默认输出 JSON，便于解析
2. **错误处理**：非零退出码 + stderr 输出错误信息
3. **进度信息**：使用 stderr 输出进度，stdout 只输出结果
4. **批处理**：支持批量输入，减少启动开销
5. **缓存**：对于重复调用，考虑在 Python 层缓存结果

## 相关文档

- Clap 文档：https://docs.rs/clap/
- subprocess 文档：https://docs.python.org/3/library/subprocess.html
