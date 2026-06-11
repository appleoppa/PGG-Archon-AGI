"""PGG Archon AgentSPEX 声明式规约解析器。

输入 YAML 格式工作流定义，输出标准化 W = ⟨T, C, P, M, S⟩ 结构。

安全边界:
  - 纯本地 YAML 解析，无 LLM 调用、无网络、无 Hermes 核心修改
  - 不执行工作流，只做格式化和验证
  - 边界声明中包含："NOT a workflow execution engine"
"""

from __future__ import annotations

from typing import Any

import yaml


# ---------------------------------------------------------------------------
# 输出 schema 常量
# ---------------------------------------------------------------------------
SCHEMA = "PGGSpeParserOutput/v1"


def parse(yaml_text: str) -> dict[str, Any]:
    """解析 YAML 文本 → W=⟨T,C,P,M,S⟩ 标准化结构。

    Args:
        yaml_text: YAML 格式的工作流定义字符串。

    Returns:
        {
          "schema": "PGGSpeParserOutput/v1",
          "parsed": { "W": { "T": [...], "C": [...], "P": [...], "M": [...], "S": {...} } },
          "valid": bool,
          "validation_errors": list[str],
          "boundary": "static format parser; NOT a workflow execution engine; no LLM/network calls; local-only"
        }
    """
    validation_errors: list[str] = []

    try:
        raw: dict[str, Any] | None = yaml.safe_load(yaml_text)
    except yaml.YAMLError as e:
        return _error_result(
            f"YAML 解析失败: {e}",
        )

    if not isinstance(raw, dict):
        return _error_result(
            "YAML 顶层必须是一个 mapping (dict)",
        )

    workflow = raw.get("workflow")
    if not isinstance(workflow, dict):
        return _error_result(
            "缺少 'workflow' 顶层 key，或 workflow 不是 dict",
        )

    # --- 提取 W 五个分量 ---
    w: dict[str, Any] = {}

    # T: Typed Steps
    steps = workflow.get("steps", [])
    if isinstance(steps, list):
        w["T"] = _normalize_steps(steps, validation_errors)
    else:
        validation_errors.append("'workflow.steps' 必须是 list")
        w["T"] = []

    # C: Control Flow
    control = workflow.get("control", [])
    if isinstance(control, list):
        w["C"] = _normalize_control(control, validation_errors)
    else:
        validation_errors.append("'workflow.control' 必须是 list")
        w["C"] = []

    # P: Parallel Execution
    parallel = workflow.get("parallel", [])
    if isinstance(parallel, list):
        w["P"] = _normalize_parallel(parallel, validation_errors)
    else:
        validation_errors.append("'workflow.parallel' 必须是 list")
        w["P"] = []

    # M: Modules
    modules = workflow.get("modules", [])
    if isinstance(modules, list):
        w["M"] = _normalize_modules(modules, validation_errors)
    else:
        validation_errors.append("'workflow.modules' 必须是 list")
        w["M"] = []

    # S: Explicit State
    state = workflow.get("state", {})
    if isinstance(state, dict):
        w["S"] = _normalize_state(state, validation_errors)
    else:
        validation_errors.append("'workflow.state' 必须是 dict")
        w["S"] = {}

    # --- 输出 ---
    valid = len(validation_errors) == 0
    return {
        "schema": SCHEMA,
        "parsed": {"W": w},
        "valid": valid,
        "validation_errors": validation_errors,
        "boundary": (
            "static format parser; NOT a workflow execution engine; "
            "no LLM/network calls; local-only"
        ),
    }


def validate(spec: dict[str, Any]) -> dict[str, Any]:
    """验证已解析的 spec 结构完整性。

    Args:
        spec: parse() 返回的完整输出 dict。

    Returns:
        同 parse 输出格式，含 PASS/BLOCK 状态。
    """
    validation_errors: list[str] = []

    # 检查顶层结构
    if not isinstance(spec, dict):
        return _error_result("spec 必须是 dict")

    if spec.get("schema") != SCHEMA:
        validation_errors.append(f"schema 必须是 {SCHEMA}，实际: {spec.get('schema')}")

    parsed = spec.get("parsed")
    if not isinstance(parsed, dict):
        validation_errors.append("缺少或无效的 'parsed' 字段")
        return {
            "schema": SCHEMA,
            "parsed": spec.get("parsed", {}),
            "valid": False,
            "validation_errors": validation_errors,
            "boundary": (
                "static format parser; NOT a workflow execution engine; "
                "no LLM/network calls; local-only"
            ),
        }

    w = parsed.get("W", {})
    if not isinstance(w, dict):
        validation_errors.append("W 必须是 dict")
        return {
            "schema": SCHEMA,
            "parsed": parsed,
            "valid": False,
            "validation_errors": validation_errors,
            "boundary": (
                "static format parser; NOT a workflow execution engine; "
                "no LLM/network calls; local-only"
            ),
        }

    # 验证每个分量
    _validate_component(w, "T", list, validation_errors)
    _validate_component(w, "C", list, validation_errors)
    _validate_component(w, "P", list, validation_errors)
    _validate_component(w, "M", list, validation_errors)
    _validate_component(w, "S", dict, validation_errors)

    # 验证 steps 中的必填字段
    for i, step in enumerate(w.get("T", [])):
        if not isinstance(step, dict):
            validation_errors.append(f"T[{i}] 必须是 dict")
            continue
        if "name" not in step:
            validation_errors.append(f"T[{i}] 缺少必填字段 'name'")
        if "type" not in step:
            validation_errors.append(f"T[{i}] 缺少必填字段 'type'")

    # 验证 control flow 引用一致性
    t_names = {s.get("name") for s in w.get("T", []) if isinstance(s, dict)}
    m_names = {m.get("name") for m in w.get("M", []) if isinstance(m, dict)}
    all_step_names = t_names | m_names
    # 也包含 module 内部定义的一系列步骤名
    for m in w.get("M", []):
        if isinstance(m, dict):
            for ref in m.get("steps", []):
                all_step_names.add(ref)

    for i, ctrl in enumerate(w.get("C", [])):
        if not isinstance(ctrl, dict):
            continue
        ctrl_name = ctrl.get("name", f"C[{i}]")
        if_true = ctrl.get("if_true")
        if_false = ctrl.get("if_false")
        if if_true is not None and if_true not in all_step_names:
            validation_errors.append(
                f"Control '{ctrl_name}': if_true '{if_true}' "
                f"未在 steps 或 modules 中定义"
            )
        if if_false is not None and if_false not in all_step_names:
            validation_errors.append(
                f"Control '{ctrl_name}': if_false '{if_false}' "
                f"未在 steps 或 modules 中定义"
            )

    # 验证 parallel 引用的 steps
    for i, p in enumerate(w.get("P", [])):
        if not isinstance(p, dict):
            continue
        p_name = p.get("name", f"P[{i}]")
        ref_steps = p.get("steps", [])
        if isinstance(ref_steps, list):
            for ref in ref_steps:
                if ref not in all_step_names:
                    validation_errors.append(
                        f"Parallel '{p_name}': 引用的 step '{ref}' "
                        f"未在 steps 或 modules 中定义"
                    )

    valid = len(validation_errors) == 0 and spec.get("valid", False)
    return {
        "schema": SCHEMA,
        "parsed": parsed,
        "valid": valid,
        "validation_errors": validation_errors,
        "boundary": (
            "static format parser; NOT a workflow execution engine; "
            "no LLM/network calls; local-only"
        ),
    }


def spec_to_steps(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """展平 spec 为可执行步骤列表。

    将 W.T (typed steps) 按顺序展开，并在每一步附加 control/parallel/module 元信息。

    Args:
        spec: parse() 返回的完整输出 dict。

    Returns:
        可执行步骤列表，每步包含 name, type, input, output, _meta 等字段。
    """
    if not isinstance(spec, dict):
        return []

    parsed = spec.get("parsed", {})
    if not isinstance(parsed, dict):
        return []

    w = parsed.get("W", {})
    if not isinstance(w, dict):
        return []

    raw_steps = w.get("T", [])
    if not isinstance(raw_steps, list):
        return []

    # 构建 control 查找索引
    control_map: dict[str, dict[str, Any]] = {}
    for ctrl in w.get("C", []):
        if isinstance(ctrl, dict):
            name = ctrl.get("name", "")
            if name:
                control_map[name] = ctrl

    # 构建 parallel 查找索引
    parallel_map: dict[str, dict[str, Any]] = {}
    for p in w.get("P", []):
        if isinstance(p, dict):
            name = p.get("name", "")
            if name:
                parallel_map[name] = p

    result: list[dict[str, Any]] = []
    for step in raw_steps:
        if not isinstance(step, dict):
            continue
        flat = dict(step)
        step_name = step.get("name", "")
        meta: dict[str, Any] = {}
        # 附加关联的 control
        if step_name in control_map:
            meta["control"] = control_map[step_name]
        # 查找该 step 是否被任何 parallel 引用
        for p_name, p_data in parallel_map.items():
            refs = p_data.get("steps", [])
            if isinstance(refs, list) and step_name in refs:
                meta["parallel"] = p_name
                break
        flat["_meta"] = meta
        result.append(flat)

    return result


# ===================================================================
# Internal helpers
# ===================================================================


def _normalize_steps(
    steps: list[Any], errors: list[str]
) -> list[dict[str, Any]]:
    """标准化 steps → T 向量。"""
    result: list[dict[str, Any]] = []
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            errors.append(f"steps[{i}] 不是 dict，已跳过")
            continue
        entry: dict[str, Any] = {
            "name": s.get("name", f"step_{i}"),
            "type": s.get("type", "unknown"),
        }
        if "input" in s:
            entry["input"] = s["input"]
        if "output" in s:
            entry["output"] = s["output"]
        if "model" in s:
            entry["model"] = s["model"]
        # 保留任意额外字段（扩展友好）
        for k, v in s.items():
            if k not in entry:
                entry[k] = v
        result.append(entry)
    return result


def _normalize_control(
    control: list[Any], errors: list[str]
) -> list[dict[str, Any]]:
    """标准化 control flow → C 向量。"""
    result: list[dict[str, Any]] = []
    for i, c in enumerate(control):
        if not isinstance(c, dict):
            errors.append(f"control[{i}] 不是 dict，已跳过")
            continue
        entry: dict[str, Any] = {
            "name": c.get("name", f"control_{i}"),
            "type": c.get("type", "branch"),
        }
        if "condition" in c:
            entry["condition"] = c["condition"]
        if "if_true" in c:
            entry["if_true"] = c["if_true"]
        if "if_false" in c:
            entry["if_false"] = c["if_false"]
        # 循环类型额外字段
        if "loop_var" in c:
            entry["loop_var"] = c["loop_var"]
        if "loop_over" in c:
            entry["loop_over"] = c["loop_over"]
        result.append(entry)
    return result


def _normalize_parallel(
    parallel: list[Any], errors: list[str]
) -> list[dict[str, Any]]:
    """标准化 parallel execution → P 向量。"""
    result: list[dict[str, Any]] = []
    for i, p in enumerate(parallel):
        if not isinstance(p, dict):
            errors.append(f"parallel[{i}] 不是 dict，已跳过")
            continue
        entry: dict[str, Any] = {
            "name": p.get("name", f"parallel_{i}"),
            "steps": p.get("steps", []),
        }
        if "mode" in p:
            entry["mode"] = p["mode"]
        result.append(entry)
    return result


def _normalize_modules(
    modules: list[Any], errors: list[str]
) -> list[dict[str, Any]]:
    """标准化 modules → M 向量。"""
    result: list[dict[str, Any]] = []
    for i, m in enumerate(modules):
        if not isinstance(m, dict):
            errors.append(f"modules[{i}] 不是 dict，已跳过")
            continue
        entry: dict[str, Any] = {
            "name": m.get("name", f"module_{i}"),
            "steps": m.get("steps", []),
        }
        result.append(entry)
    return result


def _normalize_state(
    state: dict[str, Any], errors: list[str]
) -> dict[str, Any]:
    """标准化 explicit state → S 向量。"""
    result: dict[str, Any] = {}
    variables = state.get("variables")
    if variables is not None:
        if isinstance(variables, dict):
            result["variables"] = dict(variables)
        else:
            errors.append("'state.variables' 必须是 dict")
    if "initial" in state:
        result["initial"] = state["initial"]
    return result


def _validate_component(
    w: dict[str, Any],
    key: str,
    expected_type: type,
    errors: list[str],
) -> None:
    """验证 W 分量类型。"""
    val = w.get(key)
    if val is None:
        errors.append(f"W 缺少 '{key}' 分量")
    elif not isinstance(val, expected_type):
        errors.append(
            f"W['{key}'] 应为 {expected_type.__name__}，"
            f"实际为 {type(val).__name__}"
        )


def _error_result(msg: str) -> dict[str, Any]:
    """生成标准格式的错误结果。"""
    return {
        "schema": SCHEMA,
        "parsed": {
            "W": {"T": [], "C": [], "P": [], "M": [], "S": {}}
        },
        "valid": False,
        "validation_errors": [msg],
        "boundary": (
            "static format parser; NOT a workflow execution engine; "
            "no LLM/network calls; local-only"
        ),
    }
