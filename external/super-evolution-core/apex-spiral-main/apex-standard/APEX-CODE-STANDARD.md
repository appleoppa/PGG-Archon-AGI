# APEX-CODE-STANDARD.md - 璇玑帝国代码标准规范
> Schema: apex_code_standard_v1
> 版本: 1.0
> 生效日期: 2026-05-08

---

## 1. 文件命名规范

### 核心规范
| 类型 | 规范 | 示例 |
|------|------|------|
| 基因代码 | `apex_gene_*.py` | `apex_gene_shannon.py` |
| 状态代码 | `apex_state_*.py` | `apex_state_signal.py` |
| 引擎代码 | `apex_engine_*.py` | `apex_engine_core.py` |
| 工具代码 | `apex_tool_*.py` | `apex_tool_scheduler.py` |
| 配置文件 | `apex_*.yaml/json` | `apex_config.yaml` |
| Shell脚本 | `apex_*.sh` | `apex_deploy.sh` |

### 禁止
- ❌ 中文文件名
- ❌ 空格或特殊字符
- ❌ 大写字母（非约定俗成的缩写除外）

---

## 2. APEX标准注释块

### Python 函数注释
```python
# APEX: [function_name] - [简短描述]
# Input:  [参数名] <类型> - [参数说明]
# Output: [返回值类型] - [返回值说明]
# Schema: apex_code_standard_v1
def function_name(param):
    """
    详细描述（可选，超过3行时使用）
    """
    pass
```

### Shell 脚本注释
```bash
#!/bin/bash
# APEX: [script_name] - [简短描述]
# Input:  [参数说明]
# Output: [输出说明]
# Schema: apex_code_standard_v1
```

### JavaScript 函数注释
```javascript
// APEX: [function_name] - [简短描述]
// Input:  [参数] <类型> - [说明]
// Output: [返回值类型] - [说明]
// Schema: apex_code_standard_v1
function functionName(param) {
    // ...
}
```

---

## 3. 函数命名规范

### 前缀规则
| 前缀 | 用途 | 示例 |
|------|------|------|
| `apex_gene_` | 基因相关函数 | `apex_gene_solidify()` |
| `apex_state_` | 状态管理函数 | `apex_state_update()` |
| `apex_engine_` | 引擎核心函数 | `apex_engine_init()` |
| `apex_tool_` | 工具函数 | `apex_tool_parse()` |
| `apex_util_` | 通用工具函数 | `apex_util_logger()` |

### 命名风格
- ✅ `snake_case` for Python（函数/变量）
- ✅ `camelCase` for JavaScript
- ✅ 全小写 + 下划线 for 文件名

---

## 4. 代码结构模板

### Python 模块模板
```python
# -*- coding: utf-8 -*-
"""
[模块名称]
[模块功能描述]

Schema: apex_code_standard_v1
"""

# ========== 依赖导入 ==========
import os
import json
from typing import Any, Dict, List, Optional

# ========== 常量定义 ==========
APEX_SCHEMA = "apex_code_standard_v1"
APEX_VERSION = "1.0"


# ========== 核心函数 ==========

# APEX: [function_name] - [简短描述]
# Input:  param <type> - [说明]
# Output: <type> - [说明]
# Schema: apex_code_standard_v1
def apex_function_name(param: str) -> Dict[str, Any]:
    """详细描述（可选）"""
    result = {}
    return result


# ========== 辅助函数 ==========

def _internal_helper(data: Any) -> bool:
    """内部函数（以下划线开头，不生成APEX注释）"""
    return True


# ========== 主入口 ==========

if __name__ == "__main__":
    apex_function_name("input")
```

---

## 5. 基因（Gene）专项规范

### 基因文件结构
```python
# ========== 基因定义 ==========
APEX_GENE_NAME = "shannon_law"
APEX_GENE_SIGNALS = [
    "signal_rsi_oversold",
    "signal_macd_cross",
    "signal_boll_break",
    # ... 共24个信号
]

# APEX: apex_gene_validate - 验证基因完整性
# Input:  gene_name <str> - 基因名称
# Output: <bool> - 是否有效
# Schema: apex_code_standard_v1
def apex_gene_validate(gene_name: str) -> bool:
    return gene_name in APEX_GENE_SIGNALS
```

---

## 6. 状态（State）专项规范

### 状态文件结构
```python
# APEX: apex_state_init - 初始化状态机
# Input:  config <dict> - 配置参数
# Output: <dict> - 初始状态
# Schema: apex_code_standard_v1
def apex_state_init(config: Dict) -> Dict:
    return {
        "status": "idle",
        "gene_active": [],
        "signal_queue": [],
        "last_update": None
    }
```

---

## 7. 错误处理规范

```python
# APEX: apex_tool_safe_call - 安全调用函数
# Input:  func <callable> - 目标函数
#         args <tuple> - 位置参数
#         kwargs <dict> - 关键字参数
# Output: <tuple> - (success: bool, result: Any, error: str|None)
# Schema: apex_code_standard_v1
def apex_tool_safe_call(func, *args, **kwargs) -> tuple:
    try:
        result = func(*args, **kwargs)
        return (True, result, None)
    except Exception as e:
        return (False, None, str(e))
```

---

## 8. 文件头注释模板

每个代码文件开头必须包含：

```python
# -*- coding: utf-8 -*-
# APEX: [file_name] - [文件功能描述]
# Schema: apex_code_standard_v1
# Version: 1.0
# Author: 璇玑帝国
# Created: 2026-05-08
```

---

## 9. Git提交规范（APEX Commit）

```
[APEX] <type>: <subject>

Types:
- gene: 基因相关
- state: 状态相关
- engine: 引擎相关
- tool: 工具相关
- fix: 修复
- docs: 文档

Example:
[APEX] gene: 新增shannon_law基因solidify方法
```

---

## 10. 审查清单

- [ ] 文件名符合 `apex_*` 规范
- [ ] 文件头包含 APEX Schema 注释
- [ ] 所有公开函数有 APEX 注释块
- [ ] 函数命名使用正确前缀
- [ ] Input/Output 注释完整
- [ ] 类型注解完整（Python）
- [ ] 无业务逻辑修改（仅格式规范）
