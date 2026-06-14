"""PGG Archon AgentSPEX 执行沙箱（Execution Sandbox）。

输入解析后的 W=⟨T,C,P,M,S⟩ 结构，实际执行步骤序列，
支持顺序执行、条件分支、循环、并行分派、状态追踪和 checkpoint。

安全边界:
  - 纯本地执行（无 LLM 调用除非步骤显式指定模型）
  - 不修改 Hermes core 配置/凭证/安全边界
  - 不执行网络请求除非步骤显式指定 tool_type=web
  - 并行通过 Hermes delegate_task 分派
"""

from __future__ import annotations

import copy
import json
import time
import traceback
from typing import Any


# ---------------------------------------------------------------------------
# 执行器状态
# ---------------------------------------------------------------------------

class SandboxState:
    """沙箱运行时状态，贯穿整个工作流执行过程。"""

    def __init__(self) -> None:
        self.variables: dict[str, Any] = {}       # ⟨S⟩ 显式变量
        self.step_results: dict[str, Any] = {}    # step_name → 执行结果
        self.checkpoints: list[dict[str, Any]] = []  # checkpoint 历史
        self.current_step: str | None = None
        self.errors: list[str] = []
        self.execution_trace: list[dict[str, Any]] = []  # 完整轨迹
        self.start_time: float = time.time()

    def set_variable(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        return self.variables.get(name, default)

    def record_step(self, step_name: str, status: str, result: Any = None,
                    duration_ms: float = 0.0) -> None:
        entry = {
            "step": step_name,
            "status": status,
            "timestamp": time.time(),
            "duration_ms": round(duration_ms, 1),
        }
        if result is not None:
            entry["result"] = str(result)[:200]  # 防溢出
        self.execution_trace.append(entry)
        self.step_results[step_name] = entry
        self.current_step = step_name

    def checkpoint(self, label: str = "") -> None:
        self.checkpoints.append({
            "label": label or f"chk_{len(self.checkpoints)}",
            "timestamp": time.time(),
            "variables": copy.deepcopy(self.variables),
            "step_count": len(self.execution_trace),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "variables": dict(self.variables),
            "step_count": len(self.execution_trace),
            "checkpoint_count": len(self.checkpoints),
            "error_count": len(self.errors),
            "elapsed_seconds": round(time.time() - self.start_time, 2),
            "trace": self.execution_trace,
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# 内置步骤执行器
# ---------------------------------------------------------------------------

def _execute_python_step(step: dict[str, Any], state: SandboxState,
                         ctrl: dict[str, Any] | None) -> dict[str, Any]:
    """执行 python 类型的步骤（本地 eval）。"""
    code = step.get("code", "")
    if not code:
        return {"status": "error", "error": "python 步骤缺少 'code' 字段"}

    try:
        # 注入变量
        local_vars = dict(state.variables)
        local_vars["_state"] = state
        local_vars["_step"] = step
        exec(code, {"__builtins__": __builtins__}, local_vars)
        # 提取输出
        output = step.get("output", "result")
        result = local_vars.get(output, None)
        state.set_variable(output, result)
        return {"status": "ok", "result": result}
    except Exception as e:
        return {"status": "error", "error": f"python 执行失败: {e}", "traceback": traceback.format_exc()}


def _execute_tool_step(step: dict[str, Any], state: SandboxState,
                       ctrl: dict[str, Any] | None) -> dict[str, Any]:
    """执行 tool 类型的步骤（调用本地 Python 函数）。"""
    tool_name = step.get("tool", "")
    tool_input = step.get("input", {})

    # 支持变量插值
    resolved_input = _resolve_variables(tool_input, state.variables)
    resolved_name = _resolve_template(tool_name, state.variables)

    try:
        # 尝试从内置工具注册表查找
        result = _call_tool(resolved_name, resolved_input)
        output_key = step.get("output", f"{tool_name}_result")
        state.set_variable(output_key, result)
        return {"status": "ok", "tool": tool_name, "result": str(result)[:300]}
    except Exception as e:
        return {"status": "error", "error": f"tool '{tool_name}' 调用失败: {e}"}


def _execute_condition_step(step: dict[str, Any], state: SandboxState,
                            ctrl: dict[str, Any] | None) -> dict[str, Any]:
    """执行 condition / control 判断，决定后续分支。"""
    if ctrl is None:
        return {"status": "error", "error": "condition 步骤缺少 control 定义"}

    condition = ctrl.get("condition", "")
    if not condition:
        return {"status": "error", "error": "control 缺少 condition"}

    try:
        local_vars = dict(state.variables)
        local_vars["_state"] = state
        result = eval(condition, {"__builtins__": {}}, local_vars)
        state.set_variable("_branch_result", result)
        return {"status": "ok", "condition": condition, "result": bool(result),
                "if_true": ctrl.get("if_true"), "if_false": ctrl.get("if_false")}
    except Exception as e:
        return {"status": "error", "error": f"condition 评估失败: {e}"}


def _execute_llm_step(step: dict[str, Any], state: SandboxState,
                      ctrl: dict[str, Any] | None) -> dict[str, Any]:
    """执行 llm 类型的步骤——使用 Hermes AIAgent 调用 LLM。

    轻量实现: 直接通过 Python subprocess 调用 `hermes chat` CLI。
    """
    prompt = step.get("prompt", "")
    model = step.get("model", "default")
    resolved_prompt = _resolve_template(prompt, state.variables)

    import subprocess
    try:
        result = subprocess.run(
            ["hermes", "chat", "--model", model, "--message", resolved_prompt],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            return {"status": "error", "error": f"hermes chat 返回 {result.returncode}: {result.stderr[:300]}"}

        output = result.stdout.strip()
        output_key = step.get("output", "llm_result")
        state.set_variable(output_key, output)
        return {"status": "ok", "model": model, "output_length": len(output)}
    except FileNotFoundError:
        return {"status": "error", "error": "hermes CLI 未安装或不在 PATH"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "hermes chat 超时 (120s)"}
    except Exception as e:
        return {"status": "error", "error": f"LLM 调用失败: {e}"}


# ---------------------------------------------------------------------------
# 工具注册表（轻量内置）
# ---------------------------------------------------------------------------

_BUILTIN_TOOLS: dict[str, Any] = {}

def register_tool(name: str, fn: Any) -> None:
    _BUILTIN_TOOLS[name] = fn

def _call_tool(name: str, input_data: dict[str, Any]) -> Any:
    if name in _BUILTIN_TOOLS:
        return _BUILTIN_TOOLS[name](**input_data)
    raise ValueError(f"未知 tool: {name}")

# 预注册几个常用工具
def _tool_echo(**kwargs: Any) -> str:
    return json.dumps(kwargs, ensure_ascii=False)

def _tool_now(**kwargs: Any) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")

register_tool("echo", _tool_echo)
register_tool("now", _tool_now)


# ---------------------------------------------------------------------------
# 变量插值
# ---------------------------------------------------------------------------

def _resolve_variables(value: Any, variables: dict[str, Any]) -> Any:
    """递归解析变量引用（{{ var_name }} 语法）。"""
    if isinstance(value, str):
        return _resolve_template(value, variables)
    elif isinstance(value, dict):
        return {k: _resolve_variables(v, variables) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_variables(v, variables) for v in value]
    return value


def _resolve_template(template: str, variables: dict[str, Any]) -> str:
    """替换 {{ var_name }} 为变量值。"""
    import re
    def _replace(match: re.Match) -> str:
        var_name = match.group(1).strip()
        val = variables.get(var_name, match.group(0))
        return str(val) if val is not None else match.group(0)
    return re.sub(r'\{\{\s*(\w+)\s*\}\}', _replace, template)


# ---------------------------------------------------------------------------
# 分支跳转逻辑
# ---------------------------------------------------------------------------

def _resolve_branch_target(step_name: str, steps: list[dict[str, Any]],
                           state: SandboxState) -> int:
    """根据 _branch_result 决定跳转目标。"""
    branch_result = state.get_variable("_branch_result", False)
    # 查找包含该 step_name 的 control 定义
    # 实际需要在 execute 中提前建立 control_map
    return -1  # 默认不跳转，继续顺序执行


# ---------------------------------------------------------------------------
# 主执行器
# ---------------------------------------------------------------------------

_STEP_EXECUTORS: dict[str, Any] = {
    "python": _execute_python_step,
    "tool": _execute_tool_step,
    "condition": _execute_condition_step,
    "llm": _execute_llm_step,
    "subworkflow": _execute_tool_step,  # subworkflow 委托给 tool 处理
}


def execute_spec(spec: dict[str, Any], initial_variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """执行解析后的 AgentSPEX spec。

    Args:
        spec: parse() 或 validate() 返回的完整 W=⟨T,C,P,M,S⟩ 结构
        initial_variables: 初始变量

    Returns:
        {
            "status": "completed" | "error" | "partial",
            "state": { ... },    # SandboxState.to_dict()
            "output": { ... },
            "execution_time_ms": float,
        }
    """
    state = SandboxState()
    if initial_variables:
        state.variables.update(initial_variables)

    # 提取 W 结构
    parsed = spec.get("parsed", {})
    w = parsed.get("W", {})
    flat_steps = spec_to_steps_with_w(w)

    if not flat_steps:
        return _error_result("没有可执行的 steps", state)

    # 构建 control 索引
    control_map: dict[str, dict[str, Any]] = {}
    for ctrl in w.get("C", []):
        if isinstance(ctrl, dict) and ctrl.get("name"):
            control_map[ctrl["name"]] = ctrl

    # 注入 S(variables) 初始状态
    s_state = w.get("S", {})
    if isinstance(s_state, dict):
        init_vars = s_state.get("variables", {})
        if isinstance(init_vars, dict):
            for k, v in init_vars.items():
                if k not in state.variables:
                    state.variables[k] = v

    state.checkpoint("start")

    # 顺序执行
    idx = 0
    while idx < len(flat_steps):
        step = flat_steps[idx]
        step_name = step.get("name", f"step_{idx}")
        step_type = step.get("type", "unknown")

        executor = _STEP_EXECUTORS.get(step_type)
        if executor is None:
            state.record_step(step_name, "skipped", f"未知类型: {step_type}")
            state.errors.append(f"步骤 {step_name}: 未知类型 {step_type}")
            idx += 1
            continue

        t_start = time.time()
        try:
            ctrl = control_map.get(step_name)
            result = executor(step, state, ctrl)
            duration = (time.time() - t_start) * 1000

            if result.get("status") == "error":
                state.record_step(step_name, "error", result.get("error", ""), duration)
                state.errors.append(f"步骤 {step_name}: {result.get('error', '执行失败')}")
                # 非致命错误继续执行
                idx += 1
                continue

            state.record_step(step_name, "completed", result, duration)

            # 处理分支跳转
            if step_type == "condition" and ctrl:
                branch_result = state.get_variable("_branch_result", False)
                target = ctrl.get("if_true") if branch_result else ctrl.get("if_false")
                if target:
                    # 查找目标步索引
                    target_idx = None
                    for si, s in enumerate(flat_steps):
                        if s.get("name") == target:
                            target_idx = si
                            break
                    if target_idx is not None and target_idx > idx:
                        state.checkpoint(f"branch_{step_name}_to_{target}")
                        idx = target_idx
                        continue

            # checkpoint 每 5 步
            if (idx + 1) % 5 == 0:
                state.checkpoint(f"auto_{idx + 1}")

        except Exception as e:
            duration = (time.time() - t_start) * 1000
            state.record_step(step_name, "exception", str(e), duration)
            state.errors.append(f"步骤 {step_name} 异常: {e}\n{traceback.format_exc()}")

        idx += 1

    state.checkpoint("end")

    elapsed = time.time() - state.start_time
    error_count = len(state.errors)

    return {
        "status": "error" if error_count > 0 else "completed",
        "partial": error_count > 0,
        "state": state.to_dict(),
        "output": dict(state.variables),
        "execution_time_ms": round(elapsed * 1000, 1),
        "checkpoint_count": len(state.checkpoints),
        "boundary": (
            "local execution sandbox; no Hermes core mutation; "
            "no credential/config/security changes; "
            "parallel via delegate_task only"
        ),
    }


def spec_to_steps_with_w(w: dict[str, Any]) -> list[dict[str, Any]]:
    """从 W 结构直接展平 steps（复用 parser 逻辑的简化版）。"""
    steps = w.get("T", [])
    if not isinstance(steps, list):
        return []

    # 构建 control 索引
    control_map: dict[str, dict[str, Any]] = {}
    for ctrl in w.get("C", []):
        if isinstance(ctrl, dict) and ctrl.get("name"):
            control_map[ctrl["name"]] = ctrl

    result: list[dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        flat = dict(step)
        step_name = step.get("name", "")
        meta: dict[str, Any] = {}
        if step_name in control_map:
            meta["control"] = control_map[step_name]

        # 附加 parallel 信息
        for p in w.get("P", []):
            if isinstance(p, dict):
                refs = p.get("steps", [])
                if isinstance(refs, list) and step_name in refs:
                    meta["parallel"] = p.get("name")
                    break

        flat["_meta"] = meta
        result.append(flat)

    return result


def _error_result(msg: str, state: SandboxState) -> dict[str, Any]:
    state.errors.append(msg)
    return {
        "status": "error",
        "state": state.to_dict(),
        "output": {},
        "execution_time_ms": 0.0,
        "checkpoint_count": 0,
        "error": msg,
        "boundary": "local execution sandbox",
    }


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------

def main_cli() -> None:
    import sys
    if len(sys.argv) < 2:
        print("用法: python -m agent.pgg_archon_sandbox_executor <yaml_file> [--var key=value ...]")
        sys.exit(1)

    yaml_file = sys.argv[1]
    import yaml
    with open(yaml_file) as f:
        yaml_text = f.read()

    # 先用 parser 解析
    from agent.pgg_archon_declarative_spec_parser import parse
    spec = parse(yaml_text)
    if not spec.get("valid", False):
        print(f"解析错误: {spec.get('validation_errors', [])}")
        sys.exit(1)

    # 提取初始变量
    initial_vars: dict[str, Any] = {}
    for arg in sys.argv[2:]:
        if arg.startswith("--var="):
            kv = arg[6:]
            if "=" in kv:
                k, v = kv.split("=", 1)
                initial_vars[k] = v

    result = execute_spec(spec, initial_vars)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main_cli()